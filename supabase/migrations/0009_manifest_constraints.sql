-- 0009_manifest_constraints.sql
DO $$
BEGIN
    IF to_regclass('public.manifests') IS NULL THEN
        RAISE NOTICE 'public.manifests does not exist, skipping 0009_manifest_constraints';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'manifests_job_unique'
    ) THEN
        ALTER TABLE public.manifests
            ADD CONSTRAINT manifests_job_unique UNIQUE (job_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'manifests_job_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX manifests_job_idx
            ON public.manifests(job_id);
    END IF;
END $$;
