# CHANGELOG
All notable changes to this project will be documented in this file.

# [19.0.1.0.2] - 2026-11-27
- Added the "Project Type" model (`project.type`) with the default types Fixed Cost, Success Pack and Time and Material. New types can be added from Project > Configuration > Project Types.
- Added the "Project Type" field on the project (required, default Success Pack; shown in the form, list, search and group-by). Existing projects without a type are set to Success Pack on upgrade.
- Added the "Project Tracker Link" field on the project (shown after "Is Customer Project?", required and validated as an http(s) link for customer projects).
- Added the "Customer Previous Tools" model (`project.customer.tool`, name only) and a many2many on the project, shown only for customer projects. Everyone can view it; only Project Lead and Project Functional can create and edit it.
- Added the "Customer Tools" configuration menu (Project > Configuration), visible to Project Lead and Project Functional.

# [19.0.1.0.1] - 2026-06-10
- Added the post-migration script that removes the duplicated "Referral" utm.source created while upgrading from v17.

# [19.0.1.0.0] - 2026-05-08
- Migrated the "aktiv_pms" v17 to the module in v19.
