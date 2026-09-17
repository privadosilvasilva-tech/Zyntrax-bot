import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, LogIn, ShieldCheck } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { SESSION_KEY } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  claimSession,
  createOwnerAccount,
  getSetupState,
  usernameToEmail,
} from "@/lib/account.functions";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Entrar | BY ANDRY — Central da Turma" },
      {
        name: "description",
        content:
          "Acesse a central da turma BY ANDRY: atividades, calendário, avisos e chat em tempo real.",
      },
      { property: "og:title", content: "Entrar | BY ANDRY — Central da Turma" },
      {
        property: "og:description",
        content: "Acesse a central da turma: atividades, calendário, avisos e chat.",
      },
    ],
  }),
  component: Entrada,
});

function Entrada() {
  const navigate = useNavigate();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["setup-state"],
    queryFn: () => getSetupState(),
  });

  useEffect(() => {
    const reason = sessionStorage.getItem("byandry_signout_reason");
    if (reason) {
      sessionStorage.removeItem("byandry_signout_reason");
      toast.error(reason);
    }
    supabase.auth.getSession().then(({ data: s }) => {
      if (s.session) void navigate({ to: "/painel" });
    });
  }, [navigate]);

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <div className="aurora-bg absolute inset-0 -z-10" />
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-md">
        <div className="animate-fade-up mb-8 text-center">
          <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--gradient-primary)] font-display text-2xl font-bold text-primary-foreground">
            A
          </span>
          <h1 className="font-display text-3xl font-semibold">
            {data?.turmaNome ?? "BY ANDRY"}
          </h1>
          <p className="mt-2 text-muted-foreground">
            Central da turma — atividades, calendário, avisos e chat.
          </p>
        </div>

        <div className="surface-card animate-fade-up rounded-2xl p-6 md:p-8">
          {isLoading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : data?.needsSetup ? (
            <SetupForm onDone={() => void refetch()} />
          ) : (
            <LoginForm />
          )}
        </div>
      </div>
    </div>
  );
}

async function finishLogin(navigate: ReturnType<typeof useNavigate>) {
  const sessionId = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, sessionId);
  await claimSession({ data: { sessionId } });
  await navigate({ to: "/painel" });
}

function LoginForm() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: usernameToEmail(username),
        password,
      });
      if (error) throw new Error("Usuário ou senha incorretos.");
      await finishLogin(navigate);
    } catch (err) {
      await supabase.auth.signOut().catch(() => {});
      toast.error(err instanceof Error ? err.message : "Não foi possível entrar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <h2 className="font-display text-xl font-semibold">Entrar</h2>
      <Field label="Usuário" value={username} onChange={setUsername} autoComplete="username" required />
      <Field
        label="Senha"
        value={password}
        onChange={setPassword}
        type="password"
        autoComplete="current-password"
        required
      />
      <SubmitButton busy={busy} icon={<LogIn className="h-4 w-4" />}>
        Entrar
      </SubmitButton>
      <p className="text-center text-xs text-muted-foreground">
        Os logins são criados pelo proprietário da turma.
      </p>
    </form>
  );
}

function SetupForm({ onDone }: { onDone: () => void }) {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await createOwnerAccount({ data: { username, password, displayName } });
      const { error } = await supabase.auth.signInWithPassword({
        email: usernameToEmail(username),
        password,
      });
      if (error) throw new Error("Conta criada, mas o login falhou. Tente entrar novamente.");
      toast.success("Conta de proprietário criada!");
      onDone();
      await finishLogin(navigate);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível criar a conta.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <h2 className="flex items-center gap-2 font-display text-xl font-semibold">
        <ShieldCheck className="h-5 w-5 text-primary" /> Primeira configuração
      </h2>
      <p className="text-sm text-muted-foreground">
        Crie a conta do proprietário. Depois é você quem cria os logins da turma.
      </p>
      <Field label="Seu nome" value={displayName} onChange={setDisplayName} required />
      <Field label="Usuário" value={username} onChange={setUsername} autoComplete="username" required />
      <Field
        label="Senha"
        value={password}
        onChange={setPassword}
        type="password"
        autoComplete="new-password"
        required
      />
      <SubmitButton busy={busy} icon={<ShieldCheck className="h-4 w-4" />}>
        Criar conta e entrar
      </SubmitButton>
    </form>
  );
}

export function Field({
  label,
  value,
  onChange,
  type = "text",
  required,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  autoComplete?: string;
}) {
  const id = `f-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium text-muted-foreground">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        required={required}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-foreground outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/30"
      />
    </div>
  );
}

function SubmitButton({
  busy,
  icon,
  children,
}: {
  busy: boolean;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--gradient-primary)] px-4 py-3 font-medium text-primary-foreground shadow-[var(--shadow-elegant)] transition-transform hover:scale-[1.01] disabled:opacity-60"
    >
      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
      {children}
    </button>
  );
}
