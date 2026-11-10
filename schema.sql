create table if not exists public.jobs (
  job_id text primary key,
  company text not null,
  title text not null,
  location text,
  url text not null,
  description text,
  salary_min numeric,
  salary_max numeric,
  source text not null,
  first_seen timestamptz default now(),
  last_seen timestamptz default now(),
  status text not null default 'new',
  constraint status_valid check (status in ('new','review','approved','applied','skipped'))
);
create index if not exists jobs_last_seen_idx on public.jobs(last_seen desc);
alter table public.jobs enable row level security;
-- No anon/authenticated policies: only backend service-role access.
