import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { supabase } from "@/integrations/supabase/client";
import { STATUS_CLASS, activityStatus, type ActivityRow } from "@/lib/activities";

export const Route = createFileRoute("/_authenticated/calendario")({
  head: () => ({
    meta: [
      { title: "Calendário | BY ANDRY" },
      { name: "description", content: "Veja as entregas e avaliações da turma no calendário mensal." },
      { property: "og:title", content: "Calendário | BY ANDRY" },
      { property: "og:description", content: "Entregas e avaliações da turma no calendário mensal." },
    ],
  }),
  component: Calendario,
});

const WEEK = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

function Calendario() {
  const today = new Date();
  const [cursor, setCursor] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [selected, setSelected] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ["activities"],
    queryFn: async () => {
      const { data, error } = await supabase.from("activities").select("*");
      if (error) throw error;
      return data as ActivityRow[];
    },
  });

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array<null>(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  const byDate = new Map<string, ActivityRow[]>();
  for (const a of data ?? []) {
    if (!a.due_date) continue;
    byDate.set(a.due_date, [...(byDate.get(a.due_date) ?? []), a]);
  }
  const key = (d: number) =>
    `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

  const selectedItems = selected ? (byDate.get(selected) ?? []) : [];

  return (
    <AppShell title="Calendário">
      <div className="surface-card rounded-2xl p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <button
            type="button"
            aria-label="Mês anterior"
            onClick={() => setCursor(new Date(year, month - 1, 1))}
            className="rounded-lg border border-border p-2 hover:text-primary"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <p className="font-display text-lg font-semibold capitalize">
            {cursor.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}
          </p>
          <button
            type="button"
            aria-label="Próximo mês"
            onClick={() => setCursor(new Date(year, month + 1, 1))}
            className="rounded-lg border border-border p-2 hover:text-primary"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        <div className="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground">
          {WEEK.map((w) => (
            <span key={w} className="py-2">{w}</span>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {cells.map((d, i) => {
            if (d === null) return <div key={`e${i}`} />;
            const k = key(d);
            const items = byDate.get(k) ?? [];
            const isToday =
              d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
            return (
              <button
                key={k}
                type="button"
                onClick={() => setSelected(k)}
                className={`flex aspect-square flex-col items-center justify-center rounded-xl border text-sm transition-colors ${
                  selected === k
                    ? "border-primary bg-primary/15 text-primary"
                    : isToday
                      ? "border-primary/50"
                      : "border-transparent hover:bg-muted/50"
                }`}
              >
                {d}
                {items.length > 0 && <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary" />}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-6">
        <h3 className="mb-3 font-display text-lg font-semibold">
          {selected ? `Entregas de ${selected.split("-").reverse().join("/")}` : "Selecione um dia"}
        </h3>
        {selected && selectedItems.length === 0 && (
          <p className="surface-card rounded-2xl p-5 text-muted-foreground">Nada marcado nesse dia.</p>
        )}
        <ul className="grid gap-3">
          {selectedItems.map((a) => {
            const st = activityStatus(a);
            return (
              <li key={a.id} className="surface-card flex items-center justify-between gap-3 rounded-2xl p-4">
                <div>
                  <p className="font-medium">{a.title}</p>
                  <p className="text-sm text-muted-foreground">{a.public_id} · {a.subject ?? "—"}</p>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs ${STATUS_CLASS[st]}`}>{st}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </AppShell>
  );
}
