-- Run AFTER supabase-schema.sql, on the new project.
-- Tells scripts/supabase_migrate.py that these are already applied, so a
-- later run only picks up migrations added after the move.

create table if not exists schema_migrations (
    filename    text primary key,
    applied_at  timestamptz not null default now()
);

insert into schema_migrations (filename) values
    ('001_slice_schema.sql'),
    ('003_partial_tickets.sql'),
    ('004_debt_schema.sql'),
    ('006_debt_tool_support.sql'),
    ('007_import_source.sql'),
    ('008_messages.sql'),
    ('009_dashboard_access.sql'),
    ('010_open_dashboard.sql'),
    ('011_status_editable.sql'),
    ('012_charge_apartment.sql'),
    ('013_call_per_resident.sql'),
    ('014_oxs_service_calls.sql'),
    ('015_category_label.sql'),
    ('016_buildings.sql'),
    ('017_apartment_labels.sql'),
    ('018_reporter_unit.sql'),
    ('019_buildings_rls.sql')
on conflict do nothing;
