-- 0019_api_keys.sql
DO $$
BEGIN
    IF to_regclass('public.api_keys') IS NULL THEN
        CREATE TABLE public.api_keys (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id   uuid NOT NULL
                          REFERENCES public.customers(id) ON DELETE CASCADE,
            name          text NOT NULL,
            hashed_key    text NOT NULL,          -- hash of the api key, not the raw secret
            scopes        text[] NOT NULL DEFAULT ARRAY[]::text[],
            last_used_at  timestamptz,
            created_at    timestamptz NOT NULL DEFAULT now(),
            revoked_at    timestamptz
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'api_keys_customer_created_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX api_keys_customer_created_idx
            ON public.api_keys(customer_id, created_at DESC);
    END IF;
END $$;

ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'api_keys'
          AND policyname = 'api_keys_rls'
    ) THEN
        CREATE POLICY api_keys_rls
            ON public.api_keys
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;
END $$;
