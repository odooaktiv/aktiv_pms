# Copyright 2024 OCA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# Migration script: 17.0.1.0.0 -> 19.0.1.0.0
# post-migrate: runs AFTER the ORM updates the schema

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Post-migration tasks for auto_backup 17.0 → 19.0.

    1. Rename the view XML ID view_backup_conf_tree → view_backup_conf_list.

    2. Drop the old _sql_constraints-style DB constraint names so the ORM
       can recreate them under the new models.Constraint naming convention.

       _sql_constraints (17.0) used the pattern:
           {table}_{name}  →  db_backup_name_unique
                              db_backup_days_to_keep_positive

       models.Constraint (19.0) uses the attribute name directly:
           {table}_{attribute_name}  →  same names in this case, so no
           rename is required for these two constraints. PostgreSQL will
           find them already present and leave them intact.

       If your upgrade DB has constraints under a different legacy name
       (e.g. from a very old version), drop them here so the ORM can
       recreate them cleanly.
    """
    if not version:
        return

    # 1. Rename the view XML ID from *_tree to *_list
    cr.execute(
        """
        UPDATE ir_model_data
        SET name = 'view_backup_conf_list'
        WHERE module = 'auto_backup'
          AND name = 'view_backup_conf_tree'
        """
    )
    if cr.rowcount:
        _logger.info(
            "auto_backup migration: renamed XML ID "
            "view_backup_conf_tree -> view_backup_conf_list (%d row)",
            cr.rowcount,
        )

    # 2. Rename old _sql_constraints-style PG constraint names to the new
    #    models.Constraint naming convention.
    #
    #    17.0 _sql_constraints used attribute names WITHOUT leading '_':
    #      ("name_unique", ...)         → PG name: db_backup_name_unique
    #      ("days_to_keep_positive", .) → PG name: db_backup_days_to_keep_positive
    #
    #    19.0 models.Constraint uses attribute names WITH leading '_':
    #      _name_unique                 → PG name: db_backup__name_unique
    #      _days_to_keep_positive       → PG name: db_backup__days_to_keep_positive
    #
    #    The ORM will CREATE the new names automatically after this script runs.
    #    We only need to DROP the old names so there is no conflict.
    old_constraints = [
        ("db_backup", "db_backup_name_unique"),
        ("db_backup", "db_backup_days_to_keep_positive"),
    ]
    for table, constraint_name in old_constraints:
        cr.execute(
            f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name}"
        )
        if cr.rowcount >= 0:
            _logger.info(
                "auto_backup migration: dropped old constraint %s.%s",
                table,
                constraint_name,
            )
