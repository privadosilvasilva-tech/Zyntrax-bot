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

DROP POLICY "staff insert activities" ON public.activities;
DROP POLICY "staff update activities" ON public.activities;
DROP POLICY "staff delete activities" ON public.activities;
CREATE POLICY "staff insert activities" ON public.activities FOR INSERT TO authenticated WITH CHECK (private.is_staff(auth.uid()));
CREATE POLICY "staff update activities" ON public.activities FOR UPDATE TO authenticated USING (private.is_staff(auth.uid()));
CREATE POLICY "staff delete activities" ON public.activities FOR DELETE TO authenticated USING (private.is_staff(auth.uid()));

DROP POLICY "update own or staff" ON public.messages;
DROP POLICY "delete own or staff" ON public.messages;
CREATE POLICY "update own or staff" ON public.messages FOR UPDATE TO authenticated USING (auth.uid() = user_id OR private.is_staff(auth.uid()));
CREATE POLICY "delete own or staff" ON public.messages FOR DELETE TO authenticated USING (auth.uid() = user_id OR private.is_staff(auth.uid()));

DROP POLICY "logs readable by staff" ON public.logs;
CREATE POLICY "logs readable by staff" ON public.logs FOR SELECT TO authenticated USING (private.is_staff(auth.uid()));

DROP POLICY "settings owner write" ON public.settings;
CREATE POLICY "settings owner write" ON public.settings FOR ALL TO authenticated USING (private.has_role(auth.uid(),'owner')) WITH CHECK (private.has_role(auth.uid(),'owner'));

DROP FUNCTION public.has_role(uuid, public.app_role);
DROP FUNCTION public.is_staff(uuid);