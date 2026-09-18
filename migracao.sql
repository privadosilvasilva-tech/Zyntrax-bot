CREATE TABLE public.push_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  endpoint TEXT NOT NULL UNIQUE,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, DELETE ON public.push_subscriptions TO authenticated;
GRANT ALL ON public.push_subscriptions TO service_role;
ALTER TABLE public.push_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own subscriptions select" ON public.push_subscriptions
  FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "own subscriptions insert" ON public.push_subscriptions
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "own subscriptions delete" ON public.push_subscriptions
  FOR DELETE TO authenticated USING (auth.uid() = user_id);

CREATE TABLE public.login_credentials (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT NOT NULL,
  password TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT ALL ON public.login_credentials TO service_role;
ALTER TABLE public.login_credentials ENABLE ROW LEVEL SECURITY;
CREATE POLICY "owner reads credentials" ON public.login_credentials
  FOR SELECT TO authenticated USING (private.has_role(auth.uid(), 'owner'));

DROP POLICY "staff insert activities" ON public.activities;
DROP POLICY "staff update activities" ON public.activities;
CREATE POLICY "staff insert activities" ON public.activities
  FOR INSERT TO authenticated
  WITH CHECK (
    private.is_staff(auth.uid())
    AND (type <> 'AVISO' OR private.has_role(auth.uid(), 'owner'))
  );
CREATE POLICY "staff update activities" ON public.activities
  FOR UPDATE TO authenticated
  USING (
    private.is_staff(auth.uid())
    AND (type <> 'AVISO' OR private.has_role(auth.uid(), 'owner'))
  );

CREATE EXTENSION IF NOT EXISTS pg_net;

CREATE SCHEMA IF NOT EXISTS private;

CREATE TABLE IF NOT EXISTS private.app_secrets (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
REVOKE ALL ON private.app_secrets FROM PUBLIC, authenticated, anon;
GRANT ALL ON private.app_secrets TO service_role;
INSERT INTO private.app_secrets (key, value)
VALUES ('push_trigger_secret', 'byandry_' || replace(gen_random_uuid()::text, '-', ''))
ON CONFLICT (key) DO NOTHING;

CREATE OR REPLACE FUNCTION private.notify_push()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = private, public AS $$
DECLARE
  secret TEXT;
BEGIN
  SELECT value INTO secret FROM private.app_secrets WHERE key = 'push_trigger_secret';
  PERFORM net.http_post(
    url := 'https://tjmhhgnghmxwduqtmdtv.supabase.co/functions/v1/send-push',
    headers := jsonb_build_object('Content-Type', 'application/json', 'x-webhook-secret', secret),
    body := jsonb_build_object('table', TG_TABLE_NAME, 'record', to_jsonb(NEW))
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS activities_notify_push ON public.activities;
CREATE TRIGGER activities_notify_push
AFTER INSERT ON public.activities
FOR EACH ROW EXECUTE FUNCTION private.notify_push();

DROP TRIGGER IF EXISTS messages_notify_push ON public.messages;
CREATE TRIGGER messages_notify_push
AFTER INSERT ON public.messages
FOR EACH ROW EXECUTE FUNCTION private.notify_push();
