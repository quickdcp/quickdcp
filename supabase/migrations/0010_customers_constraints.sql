-- 0010_customers_constraints.sql
DO $$
BEGIN
    IF to_regclass('public.customers') IS NULL THEN
        RAISE NOTICE 'public.customers does not exist, skipping 0010_customers_constraints';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'customers_code_unique'
    ) THEN
        ALTER TABLE public.customers
            ADD CONSTRAINT customers_code_unique UNIQUE (code);
    END IF;
END $$;
