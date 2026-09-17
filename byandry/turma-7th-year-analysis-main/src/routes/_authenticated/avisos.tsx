import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Megaphone } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { supabase } from "@/integrations/supabase/client";
import { formatDateLong, type ActivityRow } from "@/lib/activities";

export const Route = createFileRoute("/_authenticated/avisos")({
  head: () => ({
    meta: [
      { title: "Avisos | BY ANDRY" },
      { name: "description", content: "Avisos e avaliações importantes da turma." },
      { property: "og:title", content: "Avisos | BY ANDRY" },
      { property: "og:description", content: "Avisos e avaliações importantes da turma." },
    ],
  }),
  component: Avisos,
});

function Avisos() {
  const { data, isLoading } = useQuery({
    queryKey: ["activities"],
    queryFn: async () => {
      const { data, error } = await supabase.from("activities").select("*");
      if (error) throw error;
      return data as ActivityRow[];
    },
  });

  const avisos = (data ?? [])
    .filter((a) => a.type === "AVISO")
    .sort((a, b) => b.created_at.localeCompare(a.created_at));

  return (
    <AppShell title="Avisos">
      {isLoading ? (
        <div className="h-24 animate-pulse rounded-2xl bg-muted/50" />
      ) : avisos.length === 0 ? (
        <p className="surface-card rounded-2xl p-8 text-center text-muted-foreground">
          Nenhum aviso publicado ainda.
        </p>
      ) : (
        <ul className="grid gap-3">
          {avisos.map((a) => (
            <li key={a.id} className="surface-card rounded-2xl p-5">
              <div className="flex items-start gap-3">
                <Megaphone className="mt-1 h-5 w-5 shrink-0 text-accent" />
                <div>
                  <h3 className="font-display text-lg font-semibold">{a.title}</h3>
                  {a.description && <p className="mt-1 text-muted-foreground">{a.description}</p>}
                  <p className="mt-2 text-sm text-muted-foreground">{formatDateLong(a.due_date)}</p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  );
}
