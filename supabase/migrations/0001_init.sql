-- QuickDCP Supabase/Postgres bootstrap schema

-- Ensure supabase_admin exists for local dev (compat with Supabase image)
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'supabase_admin') then
    create role supabase_admin login superuser;
  end if;
end $$;

-- Optionally run the rest of the script as supabase_admin
set role supabase_admin;

-- Enable useful extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- Namespace for helper functions
create schema if not exists qd;

-- Customers table (one row per customer/operator)
create table if not exists public.customers (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text,
  created_at timestamptz default now()
);

-- Jobs table: one logical render job
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references public.customers(id) on delete cascade,
  job_id text not null unique,
  status text not null default 'QUEUED',
  profile jsonb not null default '{}'::jsonb,
  manifest jsonb not null default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists jobs_customer_idx on public.jobs(customer_id);
create index if not exists jobs_status_idx on public.jobs(status);

-- Proofs table: authoritative proof record for each job
create table if not exists public.proofs (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  status text not null default 'PENDING',
  manifest_sha256 text not null,
  tsa_ok boolean not null default false,
  tsa_tsr_uri text,
  fp_proof_id text,
  fp_verified boolean,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create unique index if not exists proofs_job_unique on public.proofs(job_id);
create index if not exists proofs_status_idx on public.proofs(status);

-- KDMs (stub for future expansion)
create table if not exists public.kdms (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.jobs(id) on delete cascade,
  device_cn text not null,
  email text,
  valid_from timestamptz not null,
  valid_until timestamptz not null,
  tsa_tsr_uri text,
  created_at timestamptz default now()
);
create index if not exists kdms_job_idx on public.kdms(job_id);

-- Basic RLS (per customer)
alter table public.jobs enable row level security;
alter table public.proofs enable row level security;
alter table public.kdms enable row level security;

-- Session helper: resolve current customer from setting
create or replace function qd.qd_customer_id() returns uuid
language sql stable as $$
  select id
  from public.customers
  where code = current_setting('qd.customer_code', true)::text
  limit 1
$$;

-- Jobs RLS: only see your own jobs
create policy jobs_rls on public.jobs
  using (customer_id = qd.qd_customer_id())
  with check (customer_id = qd.qd_customer_id());

-- Proofs RLS: only proofs for your jobs
create policy proofs_rls on public.proofs
  using (job_id in (select id from public.jobs where customer_id = qd.qd_customer_id()))
  with check (job_id in (select id from public.jobs where customer_id = qd.qd_customer_id()));

-- KDMs RLS: only KDMs for your jobs
create policy kdms_rls on public.kdms
  using (job_id in (select id from public.jobs where customer_id = qd.qd_customer_id()))
  with check (job_id in (select id from public.jobs where customer_id = qd.qd_customer_id()));

-- Seed demo customer for local dev
insert into public.customers(code)
values ('demo')
on conflict (code) do nothing;
