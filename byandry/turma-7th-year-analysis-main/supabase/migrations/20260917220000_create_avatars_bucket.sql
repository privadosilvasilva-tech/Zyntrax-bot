-- As políticas de storage.objects para o bucket "avatars" já existiam (migration
-- 20260917212948), mas o bucket em si nunca foi criado por nenhuma migration.
-- Sem isso, upload/remoção de foto falha com "Bucket not found".
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'avatars',
  'avatars',
  false,
  3145728, -- 3 MB, mesmo limite já validado no frontend (perfil.tsx)
  ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
ON CONFLICT (id) DO NOTHING;
