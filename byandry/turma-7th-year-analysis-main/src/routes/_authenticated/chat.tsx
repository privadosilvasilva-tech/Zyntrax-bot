import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/AppShell";
import { isStaff, useAuth } from "@/components/AuthProvider";
import { RoleTag } from "@/components/RoleTag";
import { UserAvatar } from "@/components/UserAvatar";
import { supabase } from "@/integrations/supabase/client";
import type { AppRole } from "@/lib/account.functions";

export const Route = createFileRoute("/_authenticated/chat")({
  head: () => ({
    meta: [
      { title: "Chat da turma | BY ANDRY" },
      { name: "description", content: "Converse com a turma em tempo real, com foto e tag de cada pessoa." },
      { property: "og:title", content: "Chat da turma | BY ANDRY" },
      { property: "og:description", content: "Converse com a turma em tempo real, com foto e tag de cada pessoa." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Chat,
});

type Message = {
  id: string;
  user_id: string | null;
  content: string;
  deleted: boolean;
  created_at: string;
};

type Person = {
  id: string;
  display_name: string;
  username: string;
  avatar_url: string | null;
};

function Chat() {
  const { userId, role } = useAuth();
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: messages, isLoading } = useQuery({
    queryKey: ["messages"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("messages")
        .select("*")
        .order("created_at", { ascending: true })
        .limit(200);
      if (error) throw error;
      return data as Message[];
    },
  });

  const { data: people } = useQuery({
    queryKey: ["profiles-min"],
    queryFn: async () => {
      const [{ data, error }, { data: roles }] = await Promise.all([
        supabase.from("profiles").select("id, display_name, username, avatar_url"),
        supabase.from("user_roles").select("user_id, role"),
      ]);
      if (error) throw error;
      const roleMap = new Map<string, AppRole>(
        (roles ?? []).map((r) => [r.user_id as string, r.role as AppRole]),
      );
      return (data as Person[]).map((p) => ({ ...p, role: roleMap.get(p.id) ?? "aluno" }));
    },
  });

  const personOf = (id: string | null) => people?.find((p) => p.id === id);

  // Tempo real: mensagens, perfis (foto/nome) e papéis (tag)
  useEffect(() => {
    const channel = supabase
      .channel("chat-live")
      .on("postgres_changes", { event: "*", schema: "public", table: "messages" }, () => {
        void queryClient.invalidateQueries({ queryKey: ["messages"] });
      })
      .on("postgres_changes", { event: "*", schema: "public", table: "profiles" }, () => {
        void queryClient.invalidateQueries({ queryKey: ["profiles-min"] });
      })
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [queryClient]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages?.length]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const content = text.trim();
    if (!content || !userId) return;
    setText("");
    const { error } = await supabase.from("messages").insert({ user_id: userId, content });
    if (error) toast.error("Não foi possível enviar a mensagem.");
  }

  async function removeMessage(id: string) {
    const { error } = await supabase.from("messages").update({ deleted: true }).eq("id", id);
    if (error) toast.error("Não foi possível apagar.");
  }

  const list = messages ?? [];

  return (
    <AppShell title="Chat da turma">
      <div className="surface-card flex h-[calc(100dvh-14rem)] min-h-80 flex-col overflow-hidden rounded-2xl md:h-[calc(100dvh-13rem)]">
        <div className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden px-2 py-4 sm:px-4">
          {isLoading ? (
            <div className="space-y-3 px-2">
              {[0, 1, 2].map((i) => (
                <div key={i} className="flex animate-pulse gap-3">
                  <span className="h-10 w-10 shrink-0 rounded-full bg-muted" />
                  <span className="h-16 flex-1 rounded-2xl bg-muted" />
                </div>
              ))}
            </div>
          ) : list.length === 0 ? (
            <p className="py-12 text-center text-muted-foreground">
              Nenhuma mensagem ainda. Seja o primeiro a falar!
            </p>
          ) : (
            list.map((m, i) => {
              const mine = m.user_id === userId;
              const person = personOf(m.user_id);
              const prev = list[i - 1];
              const grouped =
                prev &&
                prev.user_id === m.user_id &&
                new Date(m.created_at).getTime() - new Date(prev.created_at).getTime() < 5 * 60_000;

              return (
                <article
                  key={m.id}
                  className={`animate-fade-up flex gap-2 px-1 sm:gap-3 ${grouped ? "mt-0.5" : "mt-3"}`}
                >
                  <div className="w-8 shrink-0 sm:w-10">
                    {!grouped && (
                      <UserAvatar
                        path={person?.avatar_url}
                        name={person?.display_name}
                        size="sm"
                        className="sm:h-10 sm:w-10 sm:text-xs"
                      />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    {!grouped && (
                      <div className="mb-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="max-w-[9rem] truncate text-sm font-semibold sm:max-w-none">
                          {person?.display_name ?? "Usuário"}
                        </span>
                        <RoleTag role={person?.role as AppRole | undefined} size="sm" />
                        <span className="text-[0.65rem] text-muted-foreground">
                          {new Date(m.created_at).toLocaleTimeString("pt-BR", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    )}

                    <div
                      className={`group relative inline-block max-w-full rounded-2xl border px-3.5 py-2 text-sm transition-colors sm:px-4 ${
                        mine
                          ? "border-primary/30 bg-primary/10"
                          : person?.role === "owner"
                            ? "border-amber-400/40 bg-amber-400/10"
                            : "border-border bg-muted/60"
                      }`}
                    >
                      <p
                        className={`whitespace-pre-wrap break-words [overflow-wrap:anywhere] ${
                          m.deleted ? "italic text-muted-foreground" : ""
                        }`}
                      >
                        {m.deleted ? "Mensagem apagada" : m.content}
                      </p>
                      {!m.deleted && (mine || isStaff(role)) && (
                        <button
                          type="button"
                          onClick={() => void removeMessage(m.id)}
                          className="mt-1 text-[0.65rem] text-muted-foreground underline transition-opacity hover:text-destructive"
                        >
                          apagar
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              );
            })
          )}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={send}
          className="flex items-center gap-2 border-t border-border bg-card/70 p-3 backdrop-blur"
        >
          <label htmlFor="msg" className="sr-only">
            Mensagem
          </label>
          <input
            id="msg"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Escreva uma mensagem…"
            className="min-w-0 flex-1 rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none transition-colors focus:border-primary"
          />
          <button
            type="submit"
            aria-label="Enviar mensagem"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--gradient-primary)] text-primary-foreground transition-transform hover:scale-105"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </AppShell>
  );
}
