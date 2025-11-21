-- 0003_kdms_constraints.sql
-- Enforce at most one KDM row per job.

DO $$
BEGIN
    -- If kdms table doesn't exist yet, skip.
    IF to_regclass('public.kdms') IS NULL THEN
        RAISE NOTICE 'public.kdms does not exist, skipping 0003_kdms_constraints';
        RETURN;
    END IF;

    -- If a constraint or index with this name already exists, skip.
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'kdms_job_unique'
          AND conrelid = 'public.kdms'::regclass
    ) OR EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relname = 'kdms_job_unique'
          AND relkind = 'i'
    ) THEN
        RAISE NOTICE 'kdms_job_unique already exists, skipping';
        RETURN;
    END IF;

    ALTER TABLE public.kdms
        ADD CONSTRAINT kdms_job_unique UNIQUE (job_id);
END $$;
