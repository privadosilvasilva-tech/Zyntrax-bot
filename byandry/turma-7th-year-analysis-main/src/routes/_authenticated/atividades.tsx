import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { isStaff, useAuth } from "@/components/AuthProvider";
import { supabase } from "@/integrations/supabase/client";
import {
  STATUS_CLASS,
  STATUS_LABEL,
  TYPE_LABEL,
  activityStatus,
  formatDateLong,
  type ActivityRow,
} from "@/lib/activities";
import { Field } from "@/routes/index";

export const Route = createFileRoute("/_authenticated/atividades")({
  head: () => ({
    meta: [
      { title: "Atividades | BY ANDRY" },
      { name: "description", content: "Todas as atividades, trabalhos e avaliações da turma." },
      { property: "og:title", content: "Atividades | BY ANDRY" },
      { property: "og:description", content: "Todas as atividades, trabalhos e avaliações da turma." },
    ],
  }),
  component: Atividades,
});

const FILTERS = ["todas", "pendente", "atrasada", "entregue", "sem-prazo"] as const;

function Atividades() {
  const { role } = useAuth();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("todas");
  const [open, setOpen] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["activities"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("activities")
        .select("*")
        .order("due_date", { ascending: true, nullsFirst: false });
      if (error) throw error;
      return data as ActivityRow[];
    },
  });

  const remove = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from("activities").delete().eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success("Atividade removida.");
      void queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
    onError: () => toast.error("Não foi possível remover."),
  });

  const list = (data ?? []).filter((a) => filter === "todas" || activityStatus(a) === filter);

  return (
    <AppShell title="Atividades">
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-full border px-4 py-1.5 text-sm capitalize transition-colors ${
              filter === f
                ? "border-primary bg-primary/15 text-primary"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {f}
          </button>
        ))}
        {isStaff(role) && (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="ml-auto flex items-center gap-2 rounded-full bg-[var(--gradient-primary)] px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-soft)]"
          >
            <Plus className="h-4 w-4" /> Nova
          </button>
        )}
      </div>

      {open && isStaff(role) && <NovaAtividade onClose={() => setOpen(false)} />}

      {error ? (
        <p className="surface-card rounded-2xl p-6 text-destructive">
          Não foi possível carregar as atividades.
        </p>
      ) : isLoading ? (
        <div className="grid gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-2xl bg-muted/50" />
          ))}
        </div>
      ) : list.length === 0 ? (
        <p className="surface-card rounded-2xl p-8 text-center text-muted-foreground">
          Nenhuma atividade por aqui.
        </p>
      ) : (
        <ul className="grid gap-3">
          {list.map((a) => {
            const st = activityStatus(a);
            return (
              <li key={a.id} className="surface-card rounded-2xl p-5 transition-transform hover:-translate-y-0.5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-mono text-muted-foreground">{a.public_id}</p>
                    <h3 className="font-display text-lg font-semibold">{a.title}</h3>
                    <p className="text-sm text-muted-foreground">
                      {[TYPE_LABEL[a.type] ?? a.type, a.subject, a.teacher].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_CLASS[st]}`}>
                    {STATUS_LABEL[st]}
                  </span>
                </div>
                {a.description && <p className="mt-3 text-sm text-muted-foreground">{a.description}</p>}
                <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                  <span>Entrega: {formatDateLong(a.due_date)}{a.due_time ? ` às ${a.due_time.slice(0, 5)}` : ""}</span>
                  {a.file_url && (
                    <a href={a.file_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                      Abrir anexo
                    </a>
                  )}
                  {isStaff(role) && (
                    <button
                      type="button"
                      onClick={() => remove.mutate(a.id)}
                      className="ml-auto flex items-center gap-1 text-destructive hover:underline"
                    >
                      <Trash2 className="h-4 w-4" /> Excluir
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </AppShell>
  );
}

function NovaAtividade({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [teacher, setTeacher] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("ATIVIDADE");
  const [dueDate, setDueDate] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const { error } = await supabase.from("activities").insert({
      // gerado pelo trigger `activities_public_id` no banco quando vazio; string
      // vazia so para satisfazer o tipo `Insert` (nao sobrescreve o trigger).
      public_id: "",
      title,
      subject: subject || null,
      teacher: teacher || null,
      description: description || null,
      type,
      due_date: dueDate || null,
      file_url: fileUrl || null,
      author_id: userId,
    });
    setBusy(false);
    if (error) {
      toast.error("Não foi possível criar a atividade.");
      return;
    }
    toast.success("Atividade criada!");
    void queryClient.invalidateQueries({ queryKey: ["activities"] });
    onClose();
  }

  return (
    <form onSubmit={submit} className="surface-card animate-fade-up mb-6 grid gap-4 rounded-2xl p-6 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <Field label="Título" value={title} onChange={setTitle} required />
      </div>
      <Field label="Matéria" value={subject} onChange={setSubject} />
      <Field label="Professor" value={teacher} onChange={setTeacher} />
      <div className="space-y-1.5">
        <label htmlFor="tipo" className="text-sm font-medium text-muted-foreground">Tipo</label>
        <select
          id="tipo"
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="w-full rounded-xl border border-input bg-background px-4 py-2.5 outline-none focus:border-primary"
        >
          <option value="ATIVIDADE">Atividade</option>
          <option value="TRABALHO">Trabalho</option>
          <option value="AVISO">Avaliação/Aviso</option>
        </select>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="prazo" className="text-sm font-medium text-muted-foreground">Data de entrega</label>
        <input
          id="prazo"
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="w-full rounded-xl border border-input bg-background px-4 py-2.5 outline-none focus:border-primary"
        />
      </div>
      <div className="sm:col-span-2">
        <Field label="Link do anexo (opcional)" value={fileUrl} onChange={setFileUrl} />
      </div>
      <div className="sm:col-span-2">
        <label htmlFor="desc" className="text-sm font-medium text-muted-foreground">Descrição</label>
        <textarea
          id="desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="mt-1.5 w-full rounded-xl border border-input bg-background px-4 py-2.5 outline-none focus:border-primary"
        />
      </div>
      <div className="flex gap-3 sm:col-span-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-[var(--gradient-primary)] px-5 py-2.5 font-medium text-primary-foreground disabled:opacity-60"
        >
          Salvar
        </button>
        <button type="button" onClick={onClose} className="rounded-xl border border-border px-5 py-2.5">
          Cancelar
        </button>
      </div>
    </form>
  );
}
