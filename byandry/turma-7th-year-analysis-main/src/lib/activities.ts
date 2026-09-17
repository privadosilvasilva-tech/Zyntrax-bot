export type ActivityRow = {
  id: string;
  public_id: string;
  title: string;
  subject: string | null;
  teacher: string | null;
  description: string | null;
  type: string;
  due_date: string | null;
  due_time: string | null;
  file_url: string | null;
  manual_status: string | null;
  author_id: string | null;
  created_at: string;
};

export type Status = "pendente" | "entregue" | "atrasada" | "sem-prazo";

export function activityStatus(a: Pick<ActivityRow, "due_date" | "manual_status">): Status {
  if (a.manual_status === "entregue") return "entregue";
  if (!a.due_date) return "sem-prazo";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(`${a.due_date}T00:00:00`);
  return due < today ? "atrasada" : "pendente";
}

export const STATUS_LABEL: Record<Status, string> = {
  pendente: "Pendente",
  entregue: "Entregue",
  atrasada: "Atrasada",
  "sem-prazo": "Sem prazo",
};

export const STATUS_CLASS: Record<Status, string> = {
  pendente: "bg-primary/15 text-primary",
  entregue: "bg-emerald-500/15 text-emerald-400",
  atrasada: "bg-destructive/15 text-destructive",
  "sem-prazo": "bg-muted text-muted-foreground",
};

export const TYPE_LABEL: Record<string, string> = {
  ATIVIDADE: "Atividade",
  TRABALHO: "Trabalho",
  AVISO: "Aviso",
};

export function formatDate(date: string | null) {
  if (!date) return "Sem prazo";
  return new Date(`${date}T00:00:00`).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
  });
}

export function formatDateLong(date: string | null) {
  if (!date) return "Sem prazo";
  return new Date(`${date}T00:00:00`).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}
