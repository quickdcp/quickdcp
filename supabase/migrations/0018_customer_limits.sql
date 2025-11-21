-- 0018_customer_limits.sql
DO $$
BEGIN
    IF to_regclass('public.customer_limits') IS NULL THEN
        CREATE TABLE public.customer_limits (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id        uuid NOT NULL
                               REFERENCES public.customers(id) ON DELETE CASCADE,
            max_storage_gb     integer,
            max_concurrent_jobs integer,
            max_daily_jobs     integer,
            max_monthly_kdms   integer,
            notes              text,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),
            UNIQUE (customer_id)
        );
    END IF;
END $$;

ALTER TABLE public.customer_limits ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'customer_limits'
          AND policyname = 'customer_limits_rls'
    ) THEN
        CREATE POLICY customer_limits_rls
            ON public.customer_limits
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;
END $$;
