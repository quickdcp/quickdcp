-- Enable extensions
create extension if not exists "pgcrypto";
create extension if not exists "uuid-ossp";

-- Customers (maps to X-QD-Customer header)
create table if not exists public.customers (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  created_at timestamptz default now()
);

-- Jobs table
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  job_id text unique not null,
  customer_id uuid references public.customers(id) on delete cascade,
  status text not null default 'QUEUED',
  profile jsonb not null default '{}',
  manifest jsonb not null default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists jobs_customer_idx on public.jobs(customer_id);
create index if not exists jobs_jobid_idx on public.jobs(job_id);

-- Proofs table
create table if not exists public.proofs (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.jobs(id) on delete cascade,
  manifest_sha256 text not null,
  tsa_ok boolean default false,
  fp_proof_id text,
  fp_verified boolean default false,
  status text default 'PENDING',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists proofs_job_idx on public.proofs(job_id);
create index if not exists proofs_sha_idx on public.proofs(manifest_sha256);

-- KDMs
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

-- Row Level Security
alter table public.jobs enable row level security;
alter table public.proofs enable row level security;
alter table public.kdms enable row level security;

-- Helper: map active customer code → ID
create or replace function qd_customer_id()
returns uuid
language sql
stable
as $$
  select id from public.customers
  where code = current_setting('qd.customer_code', true)::text
  limit 1;
$$;

-- RLS Policies
create policy jobs_rls on public.jobs
  using (customer_id = qd_customer_id())
  with check (customer_id = qd_customer_id());

create policy proofs_rls on public.proofs
  using (job_id in (select id from public.jobs where customer_id = qd_customer_id()))
  with check (job_id in (select id from public.jobs where customer_id = qd_customer_id()));

create policy kdms_rls on public.kdms
  using (job_id in (select id from public.jobs where customer_id = qd_customer_id()))
  with check (job_id in (select id from public.jobs where customer_id = qd_customer_id()));

-- Seed demo customer
insert into public.customers(code)
values ('demo')
on conflict do nothing;
