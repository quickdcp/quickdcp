-- 0016_signatures.sql
DO $$
BEGIN
    IF to_regclass('public.signatures') IS NULL THEN
        CREATE TABLE public.signatures (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id   uuid NOT NULL
                          REFERENCES public.customers(id) ON DELETE CASCADE,
            job_id        uuid REFERENCES public.jobs(id) ON DELETE SET NULL,
            proof_id      uuid REFERENCES public.proofs(id) ON DELETE SET NULL,
            kdm_id        uuid REFERENCES public.kdms(id) ON DELETE SET NULL,
            signature_type text NOT NULL,       -- operator_approval, tsa, manifest_hash
            algo          text NOT NULL,        -- e.g. "RSA-SHA256"
            fingerprint   text NOT NULL,        -- base64 / hex digest
            payload       jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_by    text,
            created_at    timestamptz NOT NULL DEFAULT now()
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'signatures_customer_created_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX signatures_customer_created_idx
            ON public.signatures(customer_id, created_at DESC);
    END IF;
END $$;

ALTER TABLE public.signatures ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'signatures'
          AND policyname = 'signatures_rls'
    ) THEN
        CREATE POLICY signatures_rls
            ON public.signatures
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;
END $$;
