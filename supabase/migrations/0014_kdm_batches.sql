-- 0014_kdm_batches.sql
DO $$
BEGIN
    IF to_regclass('public.kdm_batches') IS NULL THEN
        CREATE TABLE public.kdm_batches (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id   uuid NOT NULL
                          REFERENCES public.customers(id) ON DELETE CASCADE,
            job_id        uuid NOT NULL
                          REFERENCES public.jobs(id) ON DELETE CASCADE,
            label         text NOT NULL,        -- e.g. "Festival delivery wave 1"
            created_by    text,                 -- operator or system
            total_kdms    integer NOT NULL DEFAULT 0,
            status        text NOT NULL DEFAULT 'draft', -- draft | issuing | complete | failed
            created_at    timestamptz NOT NULL DEFAULT now()
        );
    END IF;

    -- Link existing kdms rows to optional batches
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'kdms'
          AND column_name  = 'batch_id'
    ) THEN
        ALTER TABLE public.kdms
            ADD COLUMN batch_id uuid
                REFERENCES public.kdm_batches(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'kdm_batches_customer_created_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX kdm_batches_customer_created_idx
            ON public.kdm_batches(customer_id, created_at DESC);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'kdms_batch_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX kdms_batch_idx
            ON public.kdms(batch_id);
    END IF;
END $$;

ALTER TABLE public.kdm_batches ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'kdm_batches'
          AND policyname = 'kdm_batches_rls'
    ) THEN
        CREATE POLICY kdm_batches_rls
            ON public.kdm_batches
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;
END $$;
