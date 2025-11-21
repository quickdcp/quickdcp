-- 0015_queue_tuning.sql
DO $$
BEGIN
    IF to_regclass('public.queue_configs') IS NULL THEN
        CREATE TABLE public.queue_configs (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id         uuid NOT NULL
                                REFERENCES public.customers(id) ON DELETE CASCADE,
            max_concurrent_jobs integer NOT NULL DEFAULT 2,
            max_ingest_mbps     integer,          -- soft limit per customer
            default_priority    integer NOT NULL DEFAULT 0,  -- -10 (low) .. +10 (high)
            burst_limit_jobs    integer NOT NULL DEFAULT 4,
            notes               text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now()
        );

        CREATE UNIQUE INDEX queue_configs_customer_unique
            ON public.queue_configs(customer_id);
    END IF;
END $$;

ALTER TABLE public.queue_configs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'queue_configs'
          AND policyname = 'queue_configs_rls'
    ) THEN
        CREATE POLICY queue_configs_rls
            ON public.queue_configs
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;
END $$;
