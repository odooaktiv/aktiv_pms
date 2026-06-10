# Migration script: 17.0.x -> 19.0.1.0.0
# post-migrate: runs AFTER the ORM updates the schema
#
# Problem: Odoo 19 added utm_source_referral ("Referral") to utm/data/utm_source_data.xml.
# When upgrading from V17, the database already has a manually-created "Referral" utm.source
# record (no XML ID).  The upgrade process inserts a NEW record and auto-renames it
# "Referral [2]" to avoid the UNIQUE constraint, then registers the XML ID against the
# duplicate.  This script redirects the XML ID to the original record and removes the duplicate.
#
# Generalised: handles any utm.source duplicate whose name matches "<base> [N]" pattern,
# where Odoo's ir_model_data points to the [N] copy and a clean "<base>" record already exists.

import re
import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)

_DUPLICATE_PATTERN = re.compile(r'^(.+)\s+\[\d+\]$')

"""
Migration: Base Odoo project.task state values → aktiv_pms custom states.

Converts standard Odoo state values (defined in the base project module) to
the aktiv_pms custom values, then removes the stale selection entries from
ir_model_fields_selection so they no longer appear merged in the UI dropdown.

State mapping applied:
    1_done               → done      (Done)
    1_canceled           → cancel    (Cancel)
    01_in_progress       → new       (Planned)  — change if a different state is preferred
    02_changes_requested → dev       (Development)
    03_approved          → approval  (Customer Approval)
    04_waiting_normal    → new       (Planned)
"""

BASE_TO_CUSTOM = {
    '1_done':                'done',
    '1_canceled':            'cancel',
    '01_in_progress':        'new',         # review: change to 'dev' if preferred
    '02_changes_requested':  'dev',
    '03_approved':           'approval',
    '04_waiting_normal':     'new',
}


def migrate(cr, version):
    # 1. Convert any remaining base Odoo state values to aktiv_pms custom states.
    #    Safe to re-run: UPDATE WHERE state = old_value is a no-op if no rows match.
    for old_state, new_state in BASE_TO_CUSTOM.items():
        cr.execute(
            "UPDATE project_task SET state = %s WHERE state = %s",
            (new_state, old_state),
        )

    # 2. Remove stale base Odoo selection metadata from ir_model_fields_selection
    #    so the merged dropdown no longer shows the old Odoo states in the UI.
    #    Safe to re-run: DELETE WHERE IN is a no-op if the rows are already gone.
    cr.execute("""
           DELETE FROM ir_model_fields_selection
            WHERE field_id IN (
                SELECT id FROM ir_model_fields
                 WHERE model = 'project.task'
                   AND name = 'state'
            )
              AND value IN %s
       """, (tuple(BASE_TO_CUSTOM.keys()),))

    if not version:
        return
    _repair_project_analytic_plan(cr)
    _fix_utm_source_duplicates(cr)
    _delete_survey_test_entries(cr)
    _restore_missing_crm_lead_and_activity(cr)
    _fix_missing_hr_version_current(cr)
    _fix_missing_expiration_date_columns(cr)
    _fix_project_group_privileges(cr)
    _fix_apps_menu_visibility(cr)
    _fix_apps_menu_groups(cr)
    _fix_portal_website_menus(cr)


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = %s
           AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def _repair_project_analytic_plan(cr):
    """Move v17 project analytic accounts to the v19 Project analytic plan.

    In v19, `analytic.analytic_plan_projects` is the canonical project plan and
    is exposed through `project.project.account_id`. Some migrated databases can
    still have project accounts under the older "Legacy" root plan, which makes
    Odoo expose them as `x_plan<N>_id` analytic dimensions instead.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    project_plan = env.ref(
        "analytic.analytic_plan_projects",
        raise_if_not_found=False,
    )

    if not project_plan:
        project_plan_id = int(
            env["ir.config_parameter"]
            .sudo()
            .get_param("analytic.project_plan", 0)
            or 0
        )
        project_plan = (
            env["account.analytic.plan"]
            .browse(project_plan_id)
            .exists()
        )

    if not project_plan:
        _logger.warning(
            "aktiv_pms migration: skipped analytic plan repair; "
            "no Project analytic plan found"
        )
        return

    env["ir.config_parameter"].sudo().set_param(
        "analytic.project_plan",
        project_plan.id,
    )

    cr.execute(
        """
        SELECT DISTINCT aa.id, aa.plan_id
          FROM project_project pp
          JOIN account_analytic_account aa ON aa.id = pp.account_id
         WHERE pp.account_id IS NOT NULL
           AND aa.plan_id IS NOT NULL
           AND aa.plan_id != %s
        """,
        (project_plan.id,),
    )

    account_rows = cr.fetchall()

    if not account_rows:
        env["account.analytic.plan"].search([])._sync_all_plan_column()
        return

    account_ids = [row[0] for row in account_rows]
    old_plan_ids = sorted({row[1] for row in account_rows})

    for old_plan_id in old_plan_ids:
        column = f"x_plan{old_plan_id}_id"

        if _column_exists(cr, "account_analytic_line", column):
            cr.execute(
                f"""
                UPDATE account_analytic_line
                   SET {column} = NULL
                 WHERE {column} = ANY(%s)
                """,
                (account_ids,),
            )

            _logger.info(
                "aktiv_pms migration: cleared %s on %d analytic lines",
                column,
                cr.rowcount,
            )

    cr.execute(
        """
        UPDATE account_analytic_account
           SET plan_id = %s
         WHERE id = ANY(%s)
        """,
        (project_plan.id, account_ids),
    )

    _logger.info(
        "aktiv_pms migration: moved %d project analytic accounts "
        "to Project plan %s",
        cr.rowcount,
        project_plan.id,
    )

    env["account.analytic.account"].invalidate_model(["plan_id"])
    env["account.analytic.line"].invalidate_model()

def _fix_utm_source_duplicates(cr):
    # Find all utm.source XML IDs whose linked record name looks like "Foo [2]"
    cr.execute(
        """
        SELECT imd.id      AS imd_id,
               imd.module,
               imd.name    AS xml_name,
               us.id       AS dup_id,
               us.name     AS dup_name
        FROM   ir_model_data imd
        JOIN   utm_source us ON us.id = imd.res_id
        WHERE  imd.model = 'utm.source'
          AND  us.name ~ '.+\s+\[\d+\]$'
        """
    )
    duplicates = cr.fetchall()

    if not duplicates:
        _logger.info("aktiv_pms migration: no utm.source duplicates found — nothing to do")
        return

    for imd_id, module, xml_name, dup_id, dup_name in duplicates:
        match = _DUPLICATE_PATTERN.match(dup_name)
        if not match:
            continue
        base_name = match.group(1)

        # Look for the original record with the clean base name
        cr.execute(
            "SELECT id FROM utm_source WHERE name = %s AND id != %s",
            (base_name, dup_id),
        )
        row = cr.fetchone()
        if not row:
            _logger.warning(
                "aktiv_pms migration: duplicate utm.source '%s' (id=%s) found but no "
                "original '%s' record exists — skipping",
                dup_name, dup_id, base_name,
            )
            continue

        original_id = row[0]

        # Redirect any foreign-key references on known tables before deleting
        for table in ('crm_lead', 'link_tracker', 'mailing_mailing'):
            cr.execute(
                f"UPDATE {table} SET source_id = %s WHERE source_id = %s",
                (original_id, dup_id),
            )
            if cr.rowcount:
                _logger.info(
                    "aktiv_pms migration: re-pointed %d %s row(s) from utm.source %s → %s",
                    cr.rowcount, table, dup_id, original_id,
                )

        # Point the XML ID to the original record
        cr.execute(
            "UPDATE ir_model_data SET res_id = %s WHERE id = %s",
            (original_id, imd_id),
        )

        # Delete the duplicate
        cr.execute("DELETE FROM utm_source WHERE id = %s", (dup_id,))

        _logger.info(
            "aktiv_pms migration: merged utm.source duplicate '%s' (id=%s, xmlid=%s.%s) "
            "into original '%s' (id=%s)",
            dup_name, dup_id, module, xml_name, base_name, original_id,
        )

def _delete_survey_test_entries(cr):
    cr.execute("SELECT COUNT(*) FROM survey_user_input WHERE test_entry = TRUE")
    count = cr.fetchone()[0]

    if not count:
        _logger.info("aktiv_pms migration: no survey test entries found — nothing to delete")
        return

    cr.execute("DELETE FROM survey_user_input WHERE test_entry = TRUE")
    _logger.info("aktiv_pms migration: deleted %d survey test entry record(s)", count)


def _restore_missing_crm_lead_and_activity(cr):
    """
    During V17→V19 migration crm.lead id=13478 ("Demo Request: Odoo CPQ" for partner Ivanna,
    created 2026-02-05) and its linked mail.activity id=5046 were not migrated.
    This function restores them idempotently.
    """
    # Restore crm.lead
    cr.execute("SELECT id FROM crm_lead WHERE id = 13478")
    if not cr.fetchone():
        cr.execute(
            """
            INSERT INTO crm_lead (
                id, name, user_id, team_id, company_id, type, priority, stage_id, active,
                expected_revenue, date_deadline, partner_id, contact_name, partner_name,
                email_from, phone, mobile, probability, automated_probability,
                date_open, date_last_stage_update,
                create_uid, create_date, write_uid, write_date,
                color, description, lang_id, country_id, lost_reason_id
            ) VALUES (
                13478, 'Demo Request: Odoo CPQ', 72, 1, 1, 'opportunity', '0', 11, TRUE,
                NULL, NULL, 2281, 'Ivanna', NULL,
                'ivankapalyvoda@gmail.com', NULL, NULL, 99.93, 99.93,
                '2026-02-05 16:45:54.58162', '2026-03-19 13:10:30.414889',
                1, '2026-02-05 12:13:47.807027', 72, '2026-03-19 13:10:30.414889',
                0, NULL, 1, NULL, NULL
            )
            """
        )
        _logger.info("aktiv_pms migration: restored missing crm.lead id=13478 (Demo Request: Odoo CPQ)")
    else:
        _logger.info("aktiv_pms migration: crm.lead id=13478 already present — skipping")

    # Restore mail.activity linked to that lead
    cr.execute("SELECT id FROM mail_activity WHERE id = 5046")
    if not cr.fetchone():
        cr.execute("SELECT id FROM ir_model WHERE model = 'crm.lead'")
        row = cr.fetchone()
        crm_lead_model_id = row[0] if row else None
        cr.execute(
            """
            INSERT INTO mail_activity (
                id, res_model, res_model_id, res_id, res_name,
                summary, note, date_deadline,
                user_id, activity_type_id,
                create_uid, create_date, write_uid, write_date
            ) VALUES (
                5046, 'crm.lead', %s, 13478, 'Demo Request: Odoo CPQ',
                'Never received a response', '<p><br></p>', '2026-05-15',
                72, 4,
                72, '2026-03-19 13:10:42.531606', 72, '2026-03-19 13:10:42.531606'
            )
            """,
            (crm_lead_model_id,),
        )
        _logger.info("aktiv_pms migration: restored missing mail.activity id=5046 (crm.lead 13478)")
    else:
        _logger.info("aktiv_pms migration: mail.activity id=5046 already present — skipping")


def _fix_missing_hr_version_current(cr):
    """
    V17→V19: hr.employee.public is now a SQL VIEW built as:
        SELECT ... FROM hr_employee e JOIN hr_version v ON v.id = e.current_version_id
    Employees whose current_version_id is NULL are invisible to that view, causing
    "Record does not exist or has been deleted (hr.employee.public(N,))" errors.

    Root cause: the V17→V19 migration left hr_version completely empty. There is no
    stored version_id column on hr_employee (it is a computed field in V19).

    Step 1 – create one hr_version row per employee, copying field values from the
             existing hr_employee row. Required NOT NULL columns are given safe defaults.
    Step 2 – set current_version_id on each employee to point at its new version row.
    """
    cr.execute("SELECT COUNT(*) FROM hr_version")
    version_count = cr.fetchone()[0]
    _logger.info("aktiv_pms migration: hr_version table has %d row(s) before fix", version_count)

    # Find a safe fallback user id for NOT NULL FK columns (last_modified_uid, hr_responsible_id)
    cr.execute("SELECT id FROM res_users WHERE active = TRUE ORDER BY id LIMIT 1")
    row = cr.fetchone()
    fallback_uid = row[0] if row else 1

    # Step 1: insert one hr_version per employee that has none yet
    cr.execute(
        """
        INSERT INTO hr_version (
            employee_id,
            name,
            company_id,
            department_id,
            job_id,
            job_title,
            address_id,
            work_location_id,
            resource_calendar_id,
            departure_reason_id,
            departure_date,
            departure_description,
            country_id,
            private_state_id,
            private_country_id,
            private_street,
            private_street2,
            private_city,
            private_zip,
            identification_id,
            ssnid,
            passport_id,
            sex,
            marital,
            spouse_complete_name,
            children,
            km_home_work,
            distance_home_work,
            distance_home_work_unit,
            employee_type,
            additional_note,
            date_version,
            last_modified_uid,
            last_modified_date,
            hr_responsible_id,
            create_uid,
            create_date,
            write_uid,
            write_date,
            active
        )
        SELECT
            e.id,
            e.name,
            e.company_id,
            e.department_id,
            e.job_id,
            e.job_title,
            e.address_id,
            e.work_location_id,
            e.resource_calendar_id,
            e.departure_reason_id,
            e.departure_date,
            e.departure_description,
            e.country_id,
            e.private_state_id,
            e.private_country_id,
            e.private_street,
            e.private_street2,
            e.private_city,
            e.private_zip,
            e.identification_id,
            e.ssnid,
            e.passport_id,
            e.gender,
            COALESCE(e.marital, 'single'),
            e.spouse_complete_name,
            e.children,
            e.km_home_work,
            e.km_home_work,
            'km',
            COALESCE(e.employee_type, 'employee'),
            e.additional_note,
            COALESCE(e.create_date::date, CURRENT_DATE),
            COALESCE(e.write_uid, e.create_uid, %(fallback)s),
            COALESCE(e.write_date, e.create_date, NOW()),
            COALESCE(e.user_id, e.create_uid, %(fallback)s),
            e.create_uid,
            e.create_date,
            e.write_uid,
            e.write_date,
            TRUE
        FROM hr_employee e
        WHERE NOT EXISTS (
            SELECT 1 FROM hr_version v WHERE v.employee_id = e.id
        )
        """,
        {'fallback': fallback_uid},
    )
    inserted = cr.rowcount
    _logger.info(
        "aktiv_pms migration: inserted %d hr_version row(s) for employees", inserted
    )

    # Step 2: set current_version_id for all employees that still lack one
    cr.execute(
        """
        UPDATE hr_employee e
           SET current_version_id = (
               SELECT v.id
                 FROM hr_version v
                WHERE v.employee_id = e.id
                  AND v.active = TRUE
                ORDER BY v.date_version DESC
                LIMIT 1
           )
         WHERE e.current_version_id IS NULL
           AND EXISTS (SELECT 1 FROM hr_version v WHERE v.employee_id = e.id AND v.active = TRUE)
        """
    )
    _logger.info(
        "aktiv_pms migration: set current_version_id for %d employee(s)", cr.rowcount
    )

    # Report any employees still broken (missing hr_version entirely)
    cr.execute(
        "SELECT id, name FROM hr_employee WHERE current_version_id IS NULL AND active = TRUE"
    )
    still_broken = cr.fetchall()
    if still_broken:
        _logger.warning(
            "aktiv_pms migration: %d active employee(s) still have no current_version_id "
            "after fix — they will remain missing from hr.employee.public: %s",
            len(still_broken),
            [(eid, name) for eid, name in still_broken],
        )
    else:
        _logger.info(
            "aktiv_pms migration: all active employees now have current_version_id set"
        )


def _fix_missing_expiration_date_columns(cr):
    """
    V17→V19: Odoo 19 added an expiration_date column to auth_totp_device and
    res_users_apikeys for API key / TOTP device TTL management.  The auto-vacuum
    cron (_gc_user_apikeys) crashes with UndefinedColumn when those columns are
    absent — which happens on databases migrated from V17 where the column did
    not yet exist.

    This fix adds the column (nullable timestamp, no default) to each table if
    it is missing, which is safe because all existing rows will have NULL,
    meaning "no expiration" — preserving existing behaviour.
    """
    for table in ('auth_totp_device', 'res_users_apikeys'):
        cr.execute(
            """
            SELECT 1 FROM information_schema.columns
             WHERE table_name  = %s
               AND column_name = 'expiration_date'
            """,
            (table,),
        )
        if cr.fetchone():
            _logger.info(
                "aktiv_pms migration: %s.expiration_date already exists — skipping", table
            )
            continue

        cr.execute(
            f'ALTER TABLE "{table}" ADD COLUMN expiration_date TIMESTAMP WITHOUT TIME ZONE'
        )
        _logger.info(
            "aktiv_pms migration: added expiration_date column to %s", table
        )


def _fix_project_group_privileges(cr):
    """
    V19 restructure: replace the single shared "Aktiv PMS" res.groups.privilege with
    one privilege per Aktiv PMS role so that each role appears as its own independent
    checkbox row in the Services section of the user access-rights form (V17 layout).

    This runs as a post-migrate script — security.xml has already executed by this point,
    so the four new individual privilege records exist and the groups already have their
    privilege_id set correctly.  All we need to do here is remove the stale old shared
    privilege record (and its ir.model.data entry) that is no longer referenced by any group.
    """
    # Delete the old combined "Aktiv PMS" privilege.
    # By the time post-migrate runs, security.xml has already pointed all four groups to
    # their new individual privileges, so this record has no FK references and can be
    # deleted safely.
    cr.execute(
        """
        DELETE FROM res_groups_privilege
         WHERE id IN (
             SELECT res_id FROM ir_model_data
              WHERE module = 'aktiv_pms'
                AND name   = 'res_groups_privilege_aktiv_pms'
                AND model  = 'res.groups.privilege'
         )
        """
    )
    if cr.rowcount:
        _logger.info(
            "aktiv_pms migration: removed old shared 'Aktiv PMS' privilege record"
        )
    else:
        _logger.info(
            "aktiv_pms migration: old 'Aktiv PMS' privilege already absent — nothing to delete"
        )

    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'aktiv_pms'
           AND name   = 'res_groups_privilege_aktiv_pms'
           AND model  = 'res.groups.privilege'
        """
    )
    if cr.rowcount:
        _logger.info(
            "aktiv_pms migration: removed ir.model.data entry for old 'Aktiv PMS' privilege"
        )


def _fix_apps_menu_groups(cr):
    """
    Restrict the 'Apps' home-menu item to group_system + group_erp_manager and
    ensure the built-in 'admin' user is always in group_system.

    During V17→V19 migration:
      - base.menu_management groups_id is cleared, making Apps visible to all users.
      - The 'admin' user may have been left only in group_erp_manager, losing Apps access.

    Fix:
      1. Replace the menu's group links with group_system + group_erp_manager.
      2. Add 'admin' to group_system if missing.

    Safe to re-run: idempotent INSERT/DELETE.
    """
    # Resolve IDs from ir_model_data
    cr.execute(
        """
        SELECT imd.name, imd.res_id
          FROM ir_model_data imd
         WHERE imd.module = 'base'
           AND imd.name IN ('menu_management', 'group_system', 'group_erp_manager')
           AND imd.model IN ('ir.ui.menu', 'res.groups')
        """
    )
    rows = dict(cr.fetchall())
    menu_id          = rows.get('menu_management')
    group_system_id  = rows.get('group_system')
    group_erp_id     = rows.get('group_erp_manager')

    if not menu_id or not group_system_id or not group_erp_id:
        _logger.warning(
            "aktiv_pms migration: could not resolve Apps menu or required groups — skipping"
        )
        return

    # 1. Replace menu group links with group_system + group_erp_manager
    cr.execute("DELETE FROM ir_ui_menu_group_rel WHERE menu_id = %s", (menu_id,))
    cr.execute(
        """
        INSERT INTO ir_ui_menu_group_rel (menu_id, gid)
        VALUES (%s, %s), (%s, %s)
        """,
        (menu_id, group_system_id, menu_id, group_erp_id),
    )
    _logger.info(
        "aktiv_pms migration: Apps menu restricted to group_system + group_erp_manager"
    )

    # 2. Ensure 'admin' user is in group_system
    cr.execute(
        """
        INSERT INTO res_groups_users_rel (gid, uid)
        SELECT %s, ru.id
          FROM res_users ru
         WHERE ru.login = 'admin'
           AND NOT EXISTS (
               SELECT 1 FROM res_groups_users_rel
                WHERE gid = %s AND uid = ru.id
           )
        """,
        (group_system_id, group_system_id),
    )
    if cr.rowcount:
        _logger.info("aktiv_pms migration: added 'admin' user to group_system")
    else:
        _logger.info("aktiv_pms migration: 'admin' already in group_system — skipping")


def _fix_apps_menu_visibility(cr):
    """
    V17→V19 migration issue: Odoo's migration assigned base.group_system
    ("Role / Administrator") to project-role users who should not be system
    administrators, causing the Apps home-menu icon to appear for everyone.

    Strategy:
      - Users in group_system who have NO aktiv_pms project role  →  pure
        admins, leave untouched.
      - Users in group_system who ALSO have an aktiv_pms project role  →
        downgrade: remove from group_system, ensure they are in
        group_erp_manager (Settings: User) so they keep normal settings access.

    Safe to re-run: DELETE/INSERT are no-ops when rows already match.
    """
    # -- resolve group ids --------------------------------------------------
    cr.execute(
        """
        SELECT imd.name, rg.id
          FROM ir_model_data imd
          JOIN res_groups rg ON rg.id = imd.res_id
         WHERE imd.module = 'base'
           AND imd.name IN ('group_system', 'group_erp_manager')
           AND imd.model = 'res.groups'
        """
    )
    group_ids = dict(cr.fetchall())
    group_system_id      = group_ids.get('group_system')
    group_erp_manager_id = group_ids.get('group_erp_manager')

    if not group_system_id or not group_erp_manager_id:
        _logger.warning("aktiv_pms migration: could not resolve base groups — skipping")
        return

    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE module = 'aktiv_pms'
           AND name   IN (
               'group_aktiv_project_manager',
               'group_aktiv_project_QA',
               'group_aktiv_project_functional',
               'group_aktiv_project_team_leader'
           )
           AND model = 'res.groups'
        """
    )
    project_group_ids = tuple(r[0] for r in cr.fetchall())
    if not project_group_ids:
        _logger.warning("aktiv_pms migration: aktiv_pms project groups not found — skipping")
        return

    # -- find users to downgrade --------------------------------------------
    # Users in group_system AND in at least one project role group.
    # Users in group_system but NOT in any project role group are pure admins
    # and are intentionally excluded from this query.
    cr.execute(
        """
        SELECT DISTINCT uid
          FROM res_groups_users_rel
         WHERE gid = %s
           AND uid IN (
               SELECT uid FROM res_groups_users_rel WHERE gid IN %s
           )
        """,
        (group_system_id, project_group_ids),
    )
    users_to_downgrade = [r[0] for r in cr.fetchall()]

    if not users_to_downgrade:
        _logger.info(
            "aktiv_pms migration: no project-role users found in base.group_system — nothing to do"
        )
        return

    _logger.info(
        "aktiv_pms migration: downgrading %d user(s) from group_system → group_erp_manager: %s",
        len(users_to_downgrade), users_to_downgrade,
    )

    # -- remove from group_system -------------------------------------------
    cr.execute(
        """
        DELETE FROM res_groups_users_rel
         WHERE gid = %s AND uid IN %s
        """,
        (group_system_id, tuple(users_to_downgrade)),
    )

    # -- ensure group_erp_manager membership (Settings: User) ---------------
    cr.execute(
        """
        INSERT INTO res_groups_users_rel (gid, uid)
        SELECT %s, u.uid
          FROM unnest(%s::int[]) AS u(uid)
         WHERE NOT EXISTS (
             SELECT 1 FROM res_groups_users_rel e
              WHERE e.gid = %s AND e.uid = u.uid
         )
        """,
        (group_erp_manager_id, users_to_downgrade, group_erp_manager_id),
    )
    _logger.info(
        "aktiv_pms migration: Apps menu now restricted to pure-admin users only"
    )


def _fix_portal_website_menus(cr):
    """Ensure 'Project Dashboard' → /my/projects and 'Timesheets' → /my/timesheets."""

    fixes = [
        ("Project Dashboard", "/my/projects"),
        ("Timesheets",        "/my/timesheets"),
    ]

    for menu_name, target_url in fixes:
        # name is stored as jsonb in V19 (translatable field); cast to text for comparison
        cr.execute(
            """
            SELECT id, name, url, page_id
              FROM website_menu
             WHERE name::text ILIKE %s
                OR name->>'en_US' ILIKE %s
            """,
            (f'%{menu_name}%', menu_name),
        )
        rows = cr.fetchall()

        if not rows:
            _logger.warning(
                "aktiv_pms migration: website.menu '%s' not found — skipping", menu_name
            )
            continue

        for row_id, row_name, row_url, row_page_id in rows:
            if row_url == target_url and not row_page_id:
                _logger.info(
                    "aktiv_pms migration: website.menu '%s' (id=%s) already correct — skipping",
                    row_name, row_id,
                )
                continue

            cr.execute(
                "UPDATE website_menu SET url = %s, page_id = NULL WHERE id = %s",
                (target_url, row_id),
            )
            _logger.info(
                "aktiv_pms migration: fixed website.menu '%s' (id=%s): "
                "url '%s' → '%s', page_id %s → NULL",
                row_name, row_id, row_url, target_url, row_page_id,
            )
