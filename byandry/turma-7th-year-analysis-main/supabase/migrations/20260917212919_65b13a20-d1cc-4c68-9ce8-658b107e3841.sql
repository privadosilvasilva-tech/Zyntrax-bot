ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TYPE public.app_role ADD VALUE IF NOT EXISTS 'professor';