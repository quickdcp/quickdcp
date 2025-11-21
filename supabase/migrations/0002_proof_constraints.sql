-- Ensure only one proof row per job
alter table public.proofs
  add constraint proofs_job_unique unique (job_id);
