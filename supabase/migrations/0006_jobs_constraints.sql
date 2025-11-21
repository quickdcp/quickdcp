-- 0006_jobs_constraints.sql
DO $$
BEGIN
    IF to_regclass('public.jobs') IS NULL THEN
        RAISE NOTICE 'public.jobs does not exist, skipping 0006_jobs_constraints';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'jobs_customer_status_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX jobs_customer_status_idx
            ON public.jobs(customer_id, status);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'jobs_created_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX jobs_created_idx
            ON public.jobs(created_at);
    END IF;
END $$;
