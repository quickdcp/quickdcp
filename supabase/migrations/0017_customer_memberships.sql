-- 0017_customer_memberships.sql
-- Maps auth users to customers (multi-tenant)
DO $$
BEGIN
    IF to_regclass('public.customer_memberships') IS NULL THEN
        CREATE TABLE public.customer_memberships (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id   uuid NOT NULL
                          REFERENCES public.customers(id) ON DELETE CASCADE,
            user_id       uuid NOT NULL,             -- supabase auth.users.id
            role          text NOT NULL DEFAULT 'member',  -- owner | admin | member | read_only
            created_at    timestamptz NOT NULL DEFAULT now(),
            UNIQUE (customer_id, user_id)
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'customer_memberships_user_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX customer_memberships_user_idx
            ON public.customer_memberships(user_id);
    END IF;
END $$;

ALTER TABLE public.customer_memberships ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    -- Users can only see memberships for their current customer
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'customer_memberships'
          AND policyname = 'customer_memberships_rls'
    ) THEN
        CREATE POLICY customer_memberships_rls
            ON public.customer_memberships
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;
END $$;
