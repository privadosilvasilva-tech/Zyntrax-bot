import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { getSetupState, updateSettings } from "@/lib/account.functions";
import { Field } from "@/routes/index";

export const Route = createFileRoute("/_authenticated/by-andry")({
  head: () => ({
    meta: [{ title: "BY ANDRY | Configurações" }],
  }),
  component: ByAndryPage,
});

function ByAndryPage() {
  const { role } = useAuth();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["settings"],
    queryFn: () => getSetupState(),
  });

  const [turmaNome, setTurmaNome] = useState("");
  const [bgmVideoId, setBgmVideoId] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (data) {
      setTurmaNome(data.turmaNome);
      setBgmVideoId(data.bgmVideoId);
    }
  }, [data]);

  if (role !== "owner") {
    return (
      <AppShell title="BY ANDRY">
        <p className="surface-card rounded-2xl p-6 text-muted-foreground">
          Somente o proprietário pode acessar esta página.
        </p>
      </AppShell>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await updateSettings({ data: { turmaNome, bgmVideoId } });
      toast.success("Configurações salvas!");
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível salvar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="BY ANDRY">
      <form onSubmit={submit} className="surface-card max-w-lg space-y-4 rounded-2xl p-6">
        <h2 className="font-display text-lg font-semibold">Configurações da turma</h2>
        <Field label="Nome da turma" value={turmaNome} onChange={setTurmaNome} required />
        <Field
          label="ID do vídeo do YouTube (música de fundo)"
          value={bgmVideoId}
          onChange={setBgmVideoId}
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-[var(--gradient-primary)] px-5 py-2.5 font-medium text-primary-foreground disabled:opacity-60"
        >
          Salvar
        </button>
      </form>
    </AppShell>
  );
}
