-- 0011_audit_logs.sql
DO $$
BEGIN
    IF to_regclass('public.audit_logs') IS NULL THEN
        CREATE TABLE public.audit_logs (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id  uuid NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
            actor        text NOT NULL,                      -- who did it
            actor_type   text NOT NULL DEFAULT 'system',     -- system | user | api
            event_type   text NOT NULL,                      -- job.created, kdm.issued, etc.
            job_id       uuid REFERENCES public.jobs(id) ON DELETE SET NULL,
            proof_id     uuid REFERENCES public.proofs(id) ON DELETE SET NULL,
            kdm_id       uuid REFERENCES public.kdms(id) ON DELETE SET NULL,
            metadata     jsonb NOT NULL DEFAULT '{}'::jsonb, -- arbitrary structured payload
            created_at   timestamptz NOT NULL DEFAULT now()
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'audit_logs_customer_created_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX audit_logs_customer_created_idx
            ON public.audit_logs(customer_id, created_at DESC);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'audit_logs_job_idx' AND relkind = 'i'
    ) THEN
        CREATE INDEX audit_logs_job_idx
            ON public.audit_logs(job_id);
    END IF;
END $$;

-- RLS: customers see only their own audit entries
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'audit_logs'
          AND policyname = 'audit_logs_rls'
    ) THEN
        CREATE POLICY audit_logs_rls
            ON public.audit_logs
            USING (customer_id = qd.qd_customer_id())
            WITH CHECK (customer_id = qd.qd_customer_id());
    END IF;
END $$;
