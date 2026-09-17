import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { KeyRound, Plus, ShieldBan, ShieldCheck, Trash2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ROLE_LABEL, isStaff, useAuth } from "@/components/AuthProvider";
import { RoleTag } from "@/components/RoleTag";
import { UserAvatar } from "@/components/UserAvatar";
import { supabase } from "@/integrations/supabase/client";
import {
  adminCreateUser,
  adminDeleteUser,
  adminResetPassword,
  adminSetBanned,
  adminSetRole,
  type AppRole,
} from "@/lib/account.functions";
import { Field } from "@/routes/index";

export const Route = createFileRoute("/_authenticated/admin")({
  head: () => ({
    meta: [{ title: "Painel admin | BY ANDRY" }],
  }),
  component: AdminPage,
});

type Person = {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  banned: boolean;
  role: AppRole;
};

const ROLE_OPTIONS: AppRole[] = ["aluno", "professor", "support", "admin", "owner"];

function AdminPage() {
  const { role, userId } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data: people, isLoading } = useQuery({
    queryKey: ["admin-people"],
    queryFn: async () => {
      const [{ data, error }, { data: roles, error: rolesError }] = await Promise.all([
        supabase.from("profiles").select("id, username, display_name, avatar_url, banned"),
        supabase.from("user_roles").select("user_id, role"),
      ]);
      if (error) throw error;
      if (rolesError) throw rolesError;
      const roleMap = new Map<string, AppRole>((roles ?? []).map((r) => [r.user_id, r.role as AppRole]));
      return (data ?? [])
        .map((p) => ({ ...p, role: roleMap.get(p.id) ?? "aluno" }) as Person)
        .sort((a, b) => a.display_name.localeCompare(b.display_name));
    },
    enabled: isStaff(role),
  });

  const invalidate = () => void queryClient.invalidateQueries({ queryKey: ["admin-people"] });

  const banMutation = useMutation({
    mutationFn: (input: { userId: string; banned: boolean }) => adminSetBanned({ data: input }),
    onSuccess: (_, vars) => {
      toast.success(vars.banned ? "Usuário banido." : "Usuário desbanido.");
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Não foi possível atualizar."),
  });

  const roleMutation = useMutation({
    mutationFn: (input: { userId: string; role: AppRole }) => adminSetRole({ data: input }),
    onSuccess: () => {
      toast.success("Papel atualizado.");
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Não foi possível atualizar o papel."),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminDeleteUser({ data: { userId: id } }),
    onSuccess: () => {
      toast.success("Usuário excluído.");
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Não foi possível excluir."),
  });

  if (!isStaff(role)) {
    return (
      <AppShell title="Painel admin">
        <p className="surface-card rounded-2xl p-6 text-muted-foreground">
          Você não tem permissão para acessar esta página.
        </p>
      </AppShell>
    );
  }

  return (
    <AppShell title="Painel admin">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">Gerencie os logins da turma.</p>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2 rounded-full bg-[var(--gradient-primary)] px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-soft)]"
        >
          <Plus className="h-4 w-4" /> Novo login
        </button>
      </div>

      {open && <NovoLogin onClose={() => setOpen(false)} onCreated={invalidate} />}

      {isLoading ? (
        <div className="grid gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl bg-muted/50" />
          ))}
        </div>
      ) : (
        <ul className="grid gap-3">
          {(people ?? []).map((p) => (
            <li key={p.id} className="surface-card flex flex-wrap items-center gap-3 rounded-2xl p-4">
              <UserAvatar path={p.avatar_url} name={p.display_name} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">
                  {p.display_name} {p.banned && <span className="text-destructive">(banido)</span>}
                </p>
                <p className="truncate text-sm text-muted-foreground">@{p.username}</p>
              </div>

              <RoleTag role={p.role} size="sm" />

              <select
                value={p.role}
                disabled={p.id === userId || roleMutation.isPending}
                onChange={(e) => roleMutation.mutate({ userId: p.id, role: e.target.value as AppRole })}
                className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm outline-none focus:border-primary disabled:opacity-50"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABEL[r]}
                  </option>
                ))}
              </select>

              <button
                type="button"
                title="Redefinir senha"
                onClick={() => {
                  const pwd = window.prompt(`Nova senha para @${p.username} (mín. 6 caracteres):`);
                  if (!pwd) return;
                  void adminResetPassword({ data: { userId: p.id, password: pwd } })
                    .then(() => toast.success("Senha redefinida."))
                    .catch((e) => toast.error(e instanceof Error ? e.message : "Falha ao redefinir senha."));
                }}
                className="rounded-lg border border-border p-2 text-muted-foreground hover:text-foreground"
              >
                <KeyRound className="h-4 w-4" />
              </button>

              {p.role !== "owner" && (
                <button
                  type="button"
                  title={p.banned ? "Desbanir" : "Banir"}
                  disabled={banMutation.isPending}
                  onClick={() => banMutation.mutate({ userId: p.id, banned: !p.banned })}
                  className="rounded-lg border border-border p-2 text-muted-foreground hover:text-destructive disabled:opacity-50"
                >
                  {p.banned ? <ShieldCheck className="h-4 w-4" /> : <ShieldBan className="h-4 w-4" />}
                </button>
              )}

              {p.role !== "owner" && p.id !== userId && (
                <button
                  type="button"
                  title="Excluir"
                  disabled={deleteMutation.isPending}
                  onClick={() => {
                    if (window.confirm(`Excluir @${p.username}? Essa ação não pode ser desfeita.`)) {
                      deleteMutation.mutate(p.id);
                    }
                  }}
                  className="rounded-lg border border-destructive p-2 text-destructive disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  );
}

function NovoLogin({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<AppRole>("aluno");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await adminCreateUser({ data: { username, password, displayName, role } });
      toast.success("Login criado!");
      onCreated();
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível criar o login.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="surface-card animate-fade-up mb-6 grid gap-4 rounded-2xl p-6 sm:grid-cols-2">
      <Field label="Nome" value={displayName} onChange={setDisplayName} required />
      <Field label="Usuário" value={username} onChange={setUsername} required />
      <Field label="Senha" value={password} onChange={setPassword} type="password" required />
      <div className="space-y-1.5">
        <label htmlFor="role" className="text-sm font-medium text-muted-foreground">Papel</label>
        <select
          id="role"
          value={role}
          onChange={(e) => setRole(e.target.value as AppRole)}
          className="w-full rounded-xl border border-input bg-background px-4 py-2.5 outline-none focus:border-primary"
        >
          {ROLE_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABEL[r]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex gap-3 sm:col-span-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-[var(--gradient-primary)] px-5 py-2.5 font-medium text-primary-foreground disabled:opacity-60"
        >
          Criar login
        </button>
        <button type="button" onClick={onClose} className="rounded-xl border border-border px-5 py-2.5">
          Cancelar
        </button>
      </div>
    </form>
  );
}
