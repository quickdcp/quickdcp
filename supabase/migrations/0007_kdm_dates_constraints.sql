-- 0007_kdm_dates_constraints.sql
DO $$
BEGIN
    IF to_regclass('public.kdms') IS NULL THEN
        RAISE NOTICE 'public.kdms does not exist, skipping 0007_kdm_dates_constraints';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'kdm_valid_range_chk'
    ) THEN
        ALTER TABLE public.kdms
            ADD CONSTRAINT kdm_valid_range_chk
            CHECK (valid_until > valid_from);
    END IF;
END $$;
