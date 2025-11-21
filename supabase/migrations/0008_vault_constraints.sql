-- 0008_vault_constraints.sql
DO $$
BEGIN
    IF to_regclass('public.vault') IS NULL THEN
        RAISE NOTICE 'public.vault does not exist, skipping 0008_vault_constraints';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'vault_job_fkey'
    ) THEN
        ALTER TABLE public.vault
            ADD CONSTRAINT vault_job_fkey
            FOREIGN KEY (job_id)
            REFERENCES public.jobs(id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'vault_fingerprint_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX vault_fingerprint_idx
            ON public.vault(fingerprint);
    END IF;
END $$;
