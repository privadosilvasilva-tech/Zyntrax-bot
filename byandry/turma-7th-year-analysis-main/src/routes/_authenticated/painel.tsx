import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, CalendarDays, MessageCircle } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { supabase } from "@/integrations/supabase/client";
import { activityStatus, formatDate } from "@/lib/activities";

export const Route = createFileRoute("/_authenticated/painel")({
  head: () => ({
    meta: [
      { title: "Início | BY ANDRY" },
      { name: "description", content: "Resumo das atividades, avisos e novidades da turma." },
      { property: "og:title", content: "Início | BY ANDRY" },
      { property: "og:description", content: "Resumo das atividades, avisos e novidades da turma." },
    ],
  }),
  component: Painel,
});

function Painel() {
  const { profile } = useAuth();
  const { data: activities, isLoading } = useQuery({
    queryKey: ["activities"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("activities")
        .select("*")
        .order("due_date", { ascending: true });
      if (error) throw error;
      return data;
    },
  });

  const pendentes = (activities ?? []).filter((a) => activityStatus(a) === "pendente");
  const proximas = pendentes.slice(0, 4);

  return (
    <AppShell title={`Olá, ${profile?.display_name ?? ""}`}>
      <section className="surface-card relative mb-8 overflow-hidden rounded-2xl p-6 md:p-10">
        <div className="aurora-bg absolute inset-0 -z-10" />
        <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Central da turma</p>
        <h2 className="mt-2 font-display text-3xl font-semibold md:text-4xl">
          Tudo da turma <span className="gradient-text">em um só lugar</span>
        </h2>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Acompanhe as atividades, veja o calendário e converse com a turma em tempo real.
        </p>
      </section>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Atividades pendentes" value={isLoading ? "—" : String(pendentes.length)} icon={BookOpen} />
        <StatCard label="Total cadastrado" value={isLoading ? "—" : String(activities?.length ?? 0)} icon={CalendarDays} />
        <Link to="/chat" className="surface-card flex items-center gap-4 rounded-2xl p-5 transition-transform hover:-translate-y-1">
          <MessageCircle className="h-6 w-6 text-primary" />
          <div>
            <p className="font-medium">Abrir o chat</p>
            <p className="text-sm text-muted-foreground">Converse com a turma</p>
          </div>
        </Link>
      </div>

      <h3 className="mb-3 mt-10 font-display text-xl font-semibold">Próximas entregas</h3>
      {isLoading ? (
        <div className="grid gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl bg-muted/50" />
          ))}
        </div>
      ) : proximas.length === 0 ? (
        <p className="surface-card rounded-2xl p-6 text-muted-foreground">
          Nenhuma atividade pendente por enquanto.
        </p>
      ) : (
        <ul className="grid gap-3">
          {proximas.map((a) => (
            <li key={a.id} className="surface-card flex items-center justify-between gap-4 rounded-2xl p-5">
              <div className="min-w-0">
                <p className="truncate font-medium">{a.title}</p>
                <p className="text-sm text-muted-foreground">
                  {a.public_id} · {a.subject ?? "Sem matéria"}
                </p>
              </div>
              <span className="shrink-0 text-sm text-muted-foreground">{formatDate(a.due_date)}</span>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  );
}

function StatCard({ label, value, icon: Icon }: { label: string; value: string; icon: typeof BookOpen }) {
  return (
    <div className="surface-card rounded-2xl p-5">
      <Icon className="mb-3 h-6 w-6 text-primary" />
      <p className="font-display text-3xl font-semibold">{value}</p>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}
