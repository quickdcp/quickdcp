-- 0013_billing_core.sql
DO $$
BEGIN
    IF to_regclass('public.billing_accounts') IS NULL THEN
        CREATE TABLE public.billing_accounts (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id        uuid NOT NULL UNIQUE
                               REFERENCES public.customers(id) ON DELETE CASCADE,
            provider           text NOT NULL DEFAULT 'internal', -- internal | stripe | custom
            external_id        text,                             -- e.g. stripe customer id
            status             text NOT NULL DEFAULT 'active',   -- active | trial | suspended
            currency           text NOT NULL DEFAULT 'USD',
            credit_cents       bigint NOT NULL DEFAULT 0,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now()
        );
    END IF;

    IF to_regclass('public.billing_usage') IS NULL THEN
        CREATE TABLE public.billing_usage (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id        uuid NOT NULL
                               REFERENCES public.customers(id) ON DELETE CASCADE,
            billing_account_id uuid NOT NULL
                               REFERENCES public.billing_accounts(id) ON DELETE CASCADE,
            job_id             uuid REFERENCES public.jobs(id) ON DELETE SET NULL,
            component          text NOT NULL,          -- storage, encode_minutes, kdm, api_call
            quantity           numeric(20, 6) NOT NULL,
            unit               text NOT NULL,          -- GB, minute, count, call
            unit_price_cents   bigint NOT NULL,        -- price per unit at time of usage
            currency           text NOT NULL DEFAULT 'USD',
            occurred_at        timestamptz NOT NULL DEFAULT now(),
            metadata           jsonb NOT NULL DEFAULT '{}'::jsonb
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'billing_usage_customer_time_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX billing_usage_customer_time_idx
            ON public.billing_usage(customer_id, occurred_at DESC);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'billing_usage_job_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX billing_usage_job_idx
            ON public.billing_usage(job_id);
    END IF;
END $$;

ALTER TABLE public.billing_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_usage   ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'billing_accounts'
          AND policyname = 'billing_accounts_rls'
    ) THEN
        CREATE POLICY billing_accounts_rls
            ON public.billing_accounts
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'billing_usage'
          AND policyname = 'billing_usage_rls'
    ) THEN
        CREATE POLICY billing_usage_rls
            ON public.billing_usage
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;
END $$;
