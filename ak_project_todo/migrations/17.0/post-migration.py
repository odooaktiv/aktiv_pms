from openupgradelib import openupgrade


def migrate(cr, version):
    # Step 2: Insert data from note_note to project_task
    # cr.execute("""
    #     INSERT INTO project_task (name, description, state, create_date, write_date, create_uid, write_uid)
    #     SELECT name, COALESCE(memo, ''), '54', '01_in_progress', create_date, write_date, create_uid, write_uid
    #     FROM note_note
    # """)

    cr.execute("""
        INSERT INTO project_tags (name, create_date, write_date, is_sop_bank)
        SELECT name, create_date, write_date, True
        FROM note_tag
        ON CONFLICT (name) DO UPDATE
        SET
            create_date = EXCLUDED.create_date,
            write_date = EXCLUDED.write_date
    """)
    cr.execute("""
        INSERT INTO project_task_type (name, create_date, write_date, sop_stage)
        SELECT name, create_date, write_date, True
        FROM note_stage
        ON CONFLICT (name) DO UPDATE
        SET
            create_date = EXCLUDED.create_date,
            write_date = EXCLUDED.write_date
    """)

    # # Step 3: Migrate many-to-many relationships (tags)
    # cr.execute("""
    #     INSERT INTO project_tags_project_task_rel (project_task_id, project_tags_id)
    #     SELECT n.id, t.tag_id
    #     FROM note_tags_rel t
    #     JOIN note_note n ON t.note_id = n.id
    # """)



    # Step 4: Adjust sequences if necessary
    # openupgrade.logged_query(
    #     cr, 
    #     """
    #     SELECT setval(
    #         pg_get_serial_sequence('project_task', 'id'), 
    #         COALESCE(MAX(id), 1), 
    #         MAX(id) IS NOT NULL
    #     ) FROM project_task
    #     """
    # )

    openupgrade.logged_query(
        cr, 
        """
        SELECT setval(
            pg_get_serial_sequence('project_tags', 'id'), 
            COALESCE(MAX(id), 1), 
            MAX(id) IS NOT NULL
        ) FROM project_tags
        """
    )
