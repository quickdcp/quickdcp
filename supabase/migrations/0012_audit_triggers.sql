-- 0012_audit_triggers.sql
-- Audit function + basic triggers for jobs/proofs/kdms.
-- Fully idempotent: safe to run on clean or existing DB.

----------------------------------------------------------------------
-- 1. Create qd_add_audit_log(p_...) helper if missing
----------------------------------------------------------------------

DO $$
BEGIN
    -- If audit_logs table doesn't exist, skip this migration.
    IF to_regclass('public.audit_logs') IS NULL THEN
        RAISE NOTICE 'public.audit_logs does not exist, skipping 0012_audit_triggers';
        RETURN;
    END IF;

    -- Only create the function if it does not already exist.
    IF NOT EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'qd_add_audit_log'
          AND pronamespace = 'qd'::regnamespace
    ) THEN
        CREATE FUNCTION qd.qd_add_audit_log(
            p_customer_id uuid,
            p_actor       text,
            p_actor_type  text,
            p_event_type  text,
            p_job_id      uuid,
            p_proof_id    uuid,
            p_kdm_id      uuid,
            p_metadata    jsonb
        )
        RETURNS void
        LANGUAGE plpgsql
        AS $func$
        BEGIN
            INSERT INTO public.audit_logs(
                customer_id,
                actor,
                actor_type,
                event_type,
                job_id,
                proof_id,
                kdm_id,
                metadata
            )
            VALUES (
                p_customer_id,
                COALESCE(p_actor, 'system'),
                COALESCE(p_actor_type, 'system'),
                p_event_type,
                p_job_id,
                p_proof_id,
                p_kdm_id,
                COALESCE(p_metadata, '{}'::jsonb)
            );
        END;
        $func$;
    END IF;
END $$;

----------------------------------------------------------------------
-- 2. Trigger helper functions that call qd_add_audit_log
----------------------------------------------------------------------

-- Jobs audit trigger function
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'qd_jobs_audit_trigger_fn'
          AND pronamespace = 'qd'::regnamespace
    ) THEN
        CREATE FUNCTION qd.qd_jobs_audit_trigger_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $func$
        DECLARE
            v_customer_id uuid;
            v_event_type  text;
            v_row         public.jobs;
        BEGIN
            -- Resolve customer from RLS helper if available; otherwise from row.
            IF EXISTS (
                SELECT 1 FROM pg_proc
                WHERE proname = 'qd_customer_id'
                  AND pronamespace = 'qd'::regnamespace
            ) THEN
                v_customer_id := qd.qd_customer_id();
            ELSE
                v_customer_id := COALESCE(NEW.customer_id, OLD.customer_id);
            END IF;

            IF TG_OP = 'INSERT' THEN
                v_event_type := 'job_insert';
                v_row := NEW;
            ELSIF TG_OP = 'UPDATE' THEN
                v_event_type := 'job_update';
                v_row := NEW;
            ELSE
                v_event_type := 'job_delete';
                v_row := OLD;
            END IF;

            PERFORM qd.qd_add_audit_log(
                v_customer_id,
                current_user,
                'user',
                v_event_type,
                v_row.id,
                NULL,
                NULL,
                jsonb_build_object(
                    'status', v_row.status,
                    'job_code', v_row.code
                )
            );

            RETURN NULL;
        END;
        $func$;
    END IF;
END $$;

-- Proofs audit trigger function
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'qd_proofs_audit_trigger_fn'
          AND pronamespace = 'qd'::regnamespace
    ) THEN
        CREATE FUNCTION qd.qd_proofs_audit_trigger_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $func$
        DECLARE
            v_customer_id uuid;
            v_job_id      uuid;
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_proc
                WHERE proname = 'qd_customer_id'
                  AND pronamespace = 'qd'::regnamespace
            ) THEN
                v_customer_id := qd.qd_customer_id();
            END IF;

            v_job_id := COALESCE(NEW.job_id, OLD.job_id);

            PERFORM qd.qd_add_audit_log(
                v_customer_id,
                current_user,
                'user',
                'proof_change',
                v_job_id,
                COALESCE(NEW.id, OLD.id),
                NULL,
                jsonb_build_object(
                    'op', TG_OP
                )
            );

            RETURN NULL;
        END;
        $func$;
    END IF;
END $$;

-- KDMs audit trigger function
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'qd_kdms_audit_trigger_fn'
          AND pronamespace = 'qd'::regnamespace
    ) THEN
        CREATE FUNCTION qd.qd_kdms_audit_trigger_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $func$
        DECLARE
            v_customer_id uuid;
            v_job_id      uuid;
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_proc
                WHERE proname = 'qd_customer_id'
                  AND pronamespace = 'qd'::regnamespace
            ) THEN
                v_customer_id := qd.qd_customer_id();
            END IF;

            v_job_id := COALESCE(NEW.job_id, OLD.job_id);

            PERFORM qd.qd_add_audit_log(
                v_customer_id,
                current_user,
                'user',
                'kdm_change',
                v_job_id,
                NULL,
                COALESCE(NEW.id, OLD.id),
                jsonb_build_object(
                    'op', TG_OP,
                    'valid_from', COALESCE(NEW.valid_from, OLD.valid_from),
                    'valid_until', COALESCE(NEW.valid_until, OLD.valid_until)
                )
            );

            RETURN NULL;
        END;
        $func$;
    END IF;
END $$;

----------------------------------------------------------------------
-- 3. Create triggers (idempotent) on core tables
----------------------------------------------------------------------

DO $$
BEGIN
    ------------------------------------------------------------------
    -- Jobs
    ------------------------------------------------------------------
    IF to_regclass('public.jobs') IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'jobs_audit_trg') THEN
            -- keep existing trigger
        ELSE
            CREATE TRIGGER jobs_audit_trg
                AFTER INSERT OR UPDATE OR DELETE ON public.jobs
                FOR EACH ROW
                EXECUTE FUNCTION qd.qd_jobs_audit_trigger_fn();
        END IF;
    END IF;

    ------------------------------------------------------------------
    -- Proofs
    ------------------------------------------------------------------
    IF to_regclass('public.proofs') IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'proofs_audit_trg') THEN
            -- keep existing trigger
        ELSE
            CREATE TRIGGER proofs_audit_trg
                AFTER INSERT OR UPDATE OR DELETE ON public.proofs
                FOR EACH ROW
                EXECUTE FUNCTION qd.qd_proofs_audit_trigger_fn();
        END IF;
    END IF;

    ------------------------------------------------------------------
    -- KDMs
    ------------------------------------------------------------------
    IF to_regclass('public.kdms') IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'kdms_audit_trg') THEN
            -- keep existing trigger
        ELSE
            CREATE TRIGGER kdms_audit_trg
                AFTER INSERT OR UPDATE OR DELETE ON public.kdms
                FOR EACH ROW
                EXECUTE FUNCTION qd.qd_kdms_audit_trigger_fn();
        END IF;
    END IF;
END $$;
