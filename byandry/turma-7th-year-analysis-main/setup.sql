
CREATE TYPE public.app_role AS ENUM ('owner','admin','support','aluno','professor');

CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  avatar_url TEXT,
  banned BOOLEAN NOT NULL DEFAULT false,
  active_session UUID,
  last_seen TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, UPDATE ON public.profiles TO authenticated;
GRANT ALL ON public.profiles TO service_role;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "profiles readable by authenticated" ON public.profiles FOR SELECT TO authenticated USING (true);
CREATE POLICY "own profile update" ON public.profiles FOR UPDATE TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role public.app_role NOT NULL,
  UNIQUE (user_id, role)
);
GRANT SELECT ON public.user_roles TO authenticated;
GRANT ALL ON public.user_roles TO service_role;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "roles readable by authenticated" ON public.user_roles FOR SELECT TO authenticated USING (true);

CREATE SCHEMA IF NOT EXISTS private;
GRANT USAGE ON SCHEMA private TO authenticated, service_role;

CREATE OR REPLACE FUNCTION private.has_role(_user_id uuid, _role public.app_role)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role);
$$;

CREATE OR REPLACE FUNCTION private.is_staff(_user_id uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role IN ('owner','admin','support'));
$$;
REVOKE EXECUTE ON FUNCTION private.has_role(uuid, public.app_role) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION private.is_staff(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.has_role(uuid, public.app_role) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.is_staff(uuid) TO authenticated, service_role;

CREATE TABLE public.activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  public_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  subject TEXT,
  teacher TEXT,
  description TEXT,
  type TEXT NOT NULL DEFAULT 'ATIVIDADE',
  due_date DATE,
  due_time TEXT,
  file_url TEXT,
  manual_status TEXT,
  author_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.activities TO authenticated;
GRANT ALL ON public.activities TO service_role;
ALTER TABLE public.activities ENABLE ROW LEVEL SECURITY;
CREATE POLICY "activities readable" ON public.activities FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff insert activities" ON public.activities FOR INSERT TO authenticated WITH CHECK (private.is_staff(auth.uid()));
CREATE POLICY "staff update activities" ON public.activities FOR UPDATE TO authenticated USING (private.is_staff(auth.uid()));
CREATE POLICY "staff delete activities" ON public.activities FOR DELETE TO authenticated USING (private.is_staff(auth.uid()));

CREATE SEQUENCE public.activity_seq START 1;
GRANT USAGE ON SEQUENCE public.activity_seq TO authenticated, service_role;

CREATE OR REPLACE FUNCTION public.set_activity_public_id()
RETURNS trigger LANGUAGE plpgsql SET search_path = public AS $$
DECLARE prefix TEXT;
BEGIN
  IF NEW.public_id IS NULL OR NEW.public_id = '' THEN
    prefix := CASE NEW.type WHEN 'TRABALHO' THEN 'TRB' WHEN 'AVISO' THEN 'AVS' ELSE 'ATV' END;
    NEW.public_id := prefix || '-' || LPAD(nextval('public.activity_seq')::text, 3, '0');
  END IF;
  NEW.updated_at := now();
  RETURN NEW;
END; $$;
CREATE TRIGGER activities_public_id BEFORE INSERT OR UPDATE ON public.activities
FOR EACH ROW EXECUTE FUNCTION public.set_activity_public_id();

CREATE TABLE public.messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  deleted BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.messages TO authenticated;
GRANT ALL ON public.messages TO service_role;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "messages readable" ON public.messages FOR SELECT TO authenticated USING (true);
CREATE POLICY "insert own message" ON public.messages FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update own or staff" ON public.messages FOR UPDATE TO authenticated USING (auth.uid() = user_id OR private.is_staff(auth.uid()));
CREATE POLICY "delete own or staff" ON public.messages FOR DELETE TO authenticated USING (auth.uid() = user_id OR private.is_staff(auth.uid()));

CREATE TABLE public.logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  target TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT ON public.logs TO authenticated;
GRANT ALL ON public.logs TO service_role;
ALTER TABLE public.logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "logs readable by staff" ON public.logs FOR SELECT TO authenticated USING (private.is_staff(auth.uid()));
CREATE POLICY "logs insert authenticated" ON public.logs FOR INSERT TO authenticated WITH CHECK (true);

CREATE TABLE public.settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
GRANT SELECT ON public.settings TO authenticated, anon;
GRANT ALL ON public.settings TO service_role;
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "settings readable" ON public.settings FOR SELECT TO authenticated, anon USING (true);
CREATE POLICY "settings owner write" ON public.settings FOR ALL TO authenticated USING (private.has_role(auth.uid(),'owner')) WITH CHECK (private.has_role(auth.uid(),'owner'));
INSERT INTO public.settings (key, value) VALUES ('turma_nome','BY ANDRY'), ('bgm_video_id','5qap5aO4i9A');

ALTER PUBLICATION supabase_realtime ADD TABLE public.messages;
ALTER PUBLICATION supabase_realtime ADD TABLE public.activities;
ALTER PUBLICATION supabase_realtime ADD TABLE public.profiles;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('avatars', 'avatars', false, 3145728, ARRAY['image/jpeg','image/png','image/webp','image/gif'])
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Turma pode ver avatares" ON storage.objects FOR SELECT TO authenticated USING (bucket_id = 'avatars');
CREATE POLICY "Usuario envia o proprio avatar" ON storage.objects FOR INSERT TO authenticated WITH CHECK (bucket_id = 'avatars' AND (storage.foldername(name))[1] = auth.uid()::text);
CREATE POLICY "Usuario atualiza o proprio avatar" ON storage.objects FOR UPDATE TO authenticated USING (bucket_id = 'avatars' AND (storage.foldername(name))[1] = auth.uid()::text) WITH CHECK (bucket_id = 'avatars' AND (storage.foldername(name))[1] = auth.uid()::text);
CREATE POLICY "Usuario apaga o proprio avatar" ON storage.objects FOR DELETE TO authenticated USING (bucket_id = 'avatars' AND (storage.foldername(name))[1] = auth.uid()::text);
