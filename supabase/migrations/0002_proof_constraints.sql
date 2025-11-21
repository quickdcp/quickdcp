-- 0002_proof_constraints.sql
-- Ensure only one proof row per job_id, but be safe if something already
-- created an index/constraint called proofs_job_unique.

DO $$
BEGIN
    -- If table doesn't exist yet, skip
    IF to_regclass('public.proofs') IS NULL THEN
        RAISE NOTICE 'public.proofs does not exist, skipping 0002_proof_constraints';
        RETURN;
    END IF;

    -- If a constraint or index with this name already exists, skip.
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'proofs_job_unique'
          AND conrelid = 'public.proofs'::regclass
    ) OR EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relname = 'proofs_job_unique'
          AND relkind = 'i'
    ) THEN
        RAISE NOTICE 'proofs_job_unique already exists, skipping';
        RETURN;
    END IF;

    -- Otherwise, add a proper UNIQUE constraint on job_id.
    ALTER TABLE public.proofs
        ADD CONSTRAINT proofs_job_unique UNIQUE (job_id);
END $$;
