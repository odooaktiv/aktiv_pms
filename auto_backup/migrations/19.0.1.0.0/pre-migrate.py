# Copyright 2024 OCA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# Migration script: 17.0.1.0.0 -> 19.0.1.0.0
# pre-migrate: runs BEFORE the ORM updates the schema


def migrate(cr, version):
    """Pre-migration: nothing structural to change for this module.

    The db.backup model schema is identical between 17.0 and 19.0.
    No column renames, no field type changes, no removed columns.
    This script is provided as a safe placeholder and for future use.
    """
    if not version:
        return
