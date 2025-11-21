-- 0020_job_telemetry_views.sql
-- Convenience views for dashboards: secure because they respect RLS
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_views
        WHERE schemaname = 'public' AND viewname = 'job_audit_summary'
    ) THEN
        CREATE VIEW public.job_audit_summary AS
        SELECT
            j.id            AS job_id,
            j.customer_id   AS customer_id,
            j.status        AS job_status,
            MIN(a.created_at) FILTER (WHERE a.event_type = 'job.created') AS created_at,
            MAX(a.created_at) FILTER (WHERE a.event_type = 'job.updated') AS last_update_at,
            COUNT(*) FILTER (WHERE a.event_type LIKE 'kdm.%')           AS kdm_events,
            COUNT(*) FILTER (WHERE a.event_type LIKE 'proof.%')         AS proof_events
        FROM public.jobs j
        LEFT JOIN public.audit_logs a
          ON a.job_id = j.id
        GROUP BY j.id, j.customer_id, j.status;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_views
        WHERE schemaname = 'public' AND viewname = 'job_billing_summary'
    ) THEN
        CREATE VIEW public.job_billing_summary AS
        SELECT
            u.job_id,
            u.customer_id,
            SUM(u.quantity * u.unit_price_cents) AS total_cents
        FROM public.billing_usage u
        GROUP BY u.job_id, u.customer_id;
    END IF;
END $$;
