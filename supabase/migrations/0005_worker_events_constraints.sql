-- 0005_worker_events_constraints.sql
-- Optional: add useful index on worker_events if the table exists.

DO $$
BEGIN
    -- If worker_events is not defined yet, skip silently.
    IF to_regclass('public.worker_events') IS NULL THEN
        RAISE NOTICE 'public.worker_events does not exist, skipping 0005_worker_events_constraints';
        RETURN;
    END IF;

    -- Create index only if it doesn't already exist.
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relname = 'worker_events_job_created_idx'
          AND relkind = 'i'
    ) THEN
        CREATE INDEX worker_events_job_created_idx
            ON public.worker_events(job_id, created_at);
    ELSE
        RAISE NOTICE 'worker_events_job_created_idx already exists, skipping';
    END IF;
END $$;
