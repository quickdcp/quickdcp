-- 0004_qc_constraints.sql
-- Optional: enforce one QC report row per job, if qc_reports exists.

DO $$
BEGIN
    -- If qc_reports is not defined yet, skip silently.
    IF to_regclass('public.qc_reports') IS NULL THEN
        RAISE NOTICE 'public.qc_reports does not exist, skipping 0004_qc_constraints';
        RETURN;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'qc_reports_job_unique'
          AND conrelid = 'public.qc_reports'::regclass
    ) OR EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relname = 'qc_reports_job_unique'
          AND relkind = 'i'
    ) THEN
        RAISE NOTICE 'qc_reports_job_unique already exists, skipping';
        RETURN;
    END IF;

    ALTER TABLE public.qc_reports
        ADD CONSTRAINT qc_reports_job_unique UNIQUE (job_id);
END $$;
