import { createFileRoute } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Camera, Loader2, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { RoleTag } from "@/components/RoleTag";
import { UserAvatar } from "@/components/UserAvatar";
import { supabase } from "@/integrations/supabase/client";
import { Field } from "@/routes/index";

export const Route = createFileRoute("/_authenticated/perfil")({
  head: () => ({
    meta: [
      { title: "Meu perfil | BY ANDRY" },
      { name: "description", content: "Sua foto, seu nome e suas preferências na central da turma." },
      { property: "og:title", content: "Meu perfil | BY ANDRY" },
      { property: "og:description", content: "Sua foto, seu nome e suas preferências na central da turma." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Perfil,
});

const MAX_BYTES = 3 * 1024 * 1024;
const ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/gif"];

function Perfil() {
  const { profile, role, userId, refresh, signOut } = useAuth();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [displayName, setDisplayName] = useState(profile?.display_name ?? "");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (profile?.display_name && !displayName) setDisplayName(profile.display_name);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.display_name]);

  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (!ALLOWED.includes(f.type)) {
      toast.error("Use uma imagem JPG, PNG, WEBP ou GIF.");
      return;
    }
    if (f.size > MAX_BYTES) {
      toast.error("A imagem precisa ter no máximo 3 MB.");
      return;
    }
    setFile(f);
  }

  async function saveAvatar() {
    if (!file || !userId) return;
    setUploading(true);
    try {
      const ext = (file.name.split(".").pop() ?? "jpg").toLowerCase().replace(/[^a-z0-9]/g, "");
      const path = `${userId}/avatar-${Date.now()}.${ext || "jpg"}`;
      const { error: upErr } = await supabase.storage
        .from("avatars")
        .upload(path, file, { contentType: file.type, upsert: true });
      if (upErr) throw upErr;

      const previous = profile?.avatar_url;
      const { error } = await supabase.from("profiles").update({ avatar_url: path }).eq("id", userId);
      if (error) throw error;
      if (previous) await supabase.storage.from("avatars").remove([previous]).catch(() => {});

      setFile(null);
      refresh();
      void queryClient.invalidateQueries({ queryKey: ["profiles-min"] });
      toast.success("Foto de perfil atualizada!");
    } catch {
      toast.error("Não foi possível enviar a foto. Tente novamente.");
    } finally {
      setUploading(false);
    }
  }

  async function removeAvatar() {
    if (!userId || !profile?.avatar_url) return;
    setUploading(true);
    const path = profile.avatar_url;
    const { error } = await supabase.from("profiles").update({ avatar_url: null }).eq("id", userId);
    if (!error) await supabase.storage.from("avatars").remove([path]).catch(() => {});
    setUploading(false);
    if (error) {
      toast.error("Não foi possível remover a foto.");
      return;
    }
    refresh();
    void queryClient.invalidateQueries({ queryKey: ["profiles-min"] });
    toast.success("Foto removida.");
  }

  async function saveName(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setBusy(true);
    const { error } = await supabase
      .from("profiles")
      .update({ display_name: displayName.trim() })
      .eq("id", userId);
    setBusy(false);
    if (error) {
      toast.error("Não foi possível salvar.");
      return;
    }
    toast.success("Nome atualizado!");
    refresh();
    void queryClient.invalidateQueries({ queryKey: ["profiles-min"] });
  }

  async function savePassword(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 6) {
      toast.error("A senha precisa ter ao menos 6 caracteres.");
      return;
    }
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password });
    setBusy(false);
    if (error) {
      toast.error("Não foi possível trocar a senha.");
      return;
    }
    setPassword("");
    toast.success("Senha atualizada!");
  }

  return (
    <AppShell title="Meu perfil">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="surface-card animate-fade-up rounded-2xl p-6 md:col-span-2">
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
            <div className="relative">
              {preview ? (
                <span className="relative inline-flex h-28 w-28 items-center justify-center overflow-hidden rounded-full ring-2 ring-primary ring-offset-2 ring-offset-background">
                  <img src={preview} alt="Prévia da nova foto" className="h-full w-full object-cover" />
                </span>
              ) : (
                <UserAvatar path={profile?.avatar_url} name={profile?.display_name} size="xl" ring />
              )}
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                aria-label="Escolher foto de perfil"
                className="absolute -bottom-1 -right-1 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--gradient-primary)] text-primary-foreground shadow-[var(--shadow-soft)] transition-transform hover:scale-105"
              >
                <Camera className="h-4 w-4" />
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                onChange={pick}
                className="hidden"
              />
            </div>

            <div className="min-w-0 flex-1 text-center sm:text-left">
              <h2 className="font-display truncate text-2xl font-semibold">
                {profile?.display_name ?? "—"}
              </h2>
              <p className="truncate text-sm text-muted-foreground">@{profile?.username}</p>
              <div className="mt-3 flex justify-center sm:justify-start">
                <RoleTag role={role} />
              </div>

              <p className="mt-4 text-xs text-muted-foreground">
                JPG, PNG, WEBP ou GIF · até 3 MB. Só você pode alterar a sua foto.
              </p>

              <div className="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
                {file ? (
                  <>
                    <button
                      type="button"
                      onClick={() => void saveAvatar()}
                      disabled={uploading}
                      className="inline-flex items-center gap-2 rounded-xl bg-[var(--gradient-primary)] px-5 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-60"
                    >
                      {uploading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4" />
                      )}
                      Salvar foto
                    </button>
                    <button
                      type="button"
                      onClick={() => setFile(null)}
                      disabled={uploading}
                      className="rounded-xl border border-border px-5 py-2.5 text-sm font-medium disabled:opacity-60"
                    >
                      Cancelar
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileRef.current?.click()}
                    className="inline-flex items-center gap-2 rounded-xl border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:border-primary"
                  >
                    <Upload className="h-4 w-4" /> Escolher foto
                  </button>
                )}
                {profile?.avatar_url && !file && (
                  <button
                    type="button"
                    onClick={() => void removeAvatar()}
                    disabled={uploading}
                    className="inline-flex items-center gap-2 rounded-xl border border-destructive px-5 py-2.5 text-sm font-medium text-destructive disabled:opacity-60"
                  >
                    <Trash2 className="h-4 w-4" /> Remover
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        <form onSubmit={saveName} className="surface-card space-y-4 rounded-2xl p-6">
          <h2 className="font-display text-lg font-semibold">Nome de exibição</h2>
          <Field label="Nome" value={displayName} onChange={setDisplayName} required />
          <button
            type="submit"
            disabled={busy}
            className="rounded-xl bg-[var(--gradient-primary)] px-5 py-2.5 font-medium text-primary-foreground disabled:opacity-60"
          >
            Salvar
          </button>
        </form>

        <form onSubmit={savePassword} className="surface-card space-y-4 rounded-2xl p-6">
          <h2 className="font-display text-lg font-semibold">Trocar senha</h2>
          <Field
            label="Nova senha"
            value={password}
            onChange={setPassword}
            type="password"
            autoComplete="new-password"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-xl border border-border px-5 py-2.5 font-medium disabled:opacity-60"
          >
            Atualizar senha
          </button>
        </form>

        <div className="surface-card rounded-2xl p-6 md:col-span-2">
          <h2 className="font-display text-lg font-semibold">Sessão</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Sua conta só pode estar aberta em um dispositivo por vez.
          </p>
          <button
            type="button"
            onClick={() => void signOut()}
            className="mt-4 rounded-xl border border-destructive px-5 py-2.5 font-medium text-destructive"
          >
            Sair da conta
          </button>
        </div>
      </div>
    </AppShell>
  );
}
