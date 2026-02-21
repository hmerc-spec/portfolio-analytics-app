-- 003_timestamps.sql
-- Adds updated_at/completed_at columns and update triggers.

-- updated_at columns
alter table learning_entries add column if not exists updated_at timestamptz default now();
alter table bug_entries add column if not exists updated_at timestamptz default now();
alter table projects add column if not exists updated_at timestamptz default now();
alter table features add column if not exists updated_at timestamptz default now();

-- completed_at columns
alter table bug_entries add column if not exists completed_at timestamptz;
alter table projects add column if not exists completed_at timestamptz;
alter table features add column if not exists completed_at timestamptz;

-- trigger function
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- triggers
DROP TRIGGER IF EXISTS set_updated_at_learning_entries ON learning_entries;
create trigger set_updated_at_learning_entries
before update on learning_entries
for each row
execute function set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_bug_entries ON bug_entries;
create trigger set_updated_at_bug_entries
before update on bug_entries
for each row
execute function set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_projects ON projects;
create trigger set_updated_at_projects
before update on projects
for each row
execute function set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_features ON features;
create trigger set_updated_at_features
before update on features
for each row
execute function set_updated_at();
