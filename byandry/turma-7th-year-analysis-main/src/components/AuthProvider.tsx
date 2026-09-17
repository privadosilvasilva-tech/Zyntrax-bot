import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import type { AppRole } from "@/lib/account.functions";

export const SESSION_KEY = "byandry_session_id";

export type Profile = {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  banned: boolean;
  active_session: string | null;
  created_at: string;
};

type AuthValue = {
  userId: string | null;
  profile: Profile | null;
  role: AppRole | null;
  loading: boolean;
  signOut: (reason?: string) => Promise<void>;
  refresh: () => void;
};

const AuthContext = createContext<AuthValue>({
  userId: null,
  profile: null,
  role: null,
  loading: true,
  signOut: async () => {},
  refresh: () => {},
});

export const useAuth = () => useContext(AuthContext);

export const ROLE_LABEL: Record<AppRole, string> = {
  owner: "Proprietário",
  admin: "Administrador",
  professor: "Professor",
  support: "Suporte",
  aluno: "Aluno",
};

export const ROLE_ICON: Record<AppRole, string> = {
  owner: "👑",
  admin: "🛠️",
  professor: "📚",
  support: "🆘",
  aluno: "👤",
};

export function isStaff(role: AppRole | null) {
  return role === "owner" || role === "admin" || role === "support";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [role, setRole] = useState<AppRole | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const queryClient = useQueryClient();

  const signOut = useCallback(
    async (reason?: string) => {
      await queryClient.cancelQueries();
      queryClient.clear();
      localStorage.removeItem(SESSION_KEY);
      await supabase.auth.signOut().catch(() => {});
      setUserId(null);
      setProfile(null);
      setRole(null);
      if (reason && typeof window !== "undefined") {
        sessionStorage.setItem("byandry_signout_reason", reason);
      }
      window.location.href = "/";
    },
    [queryClient],
  );

  useEffect(() => {
    let mounted = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setUserId(data.session?.user.id ?? null);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" || event === "SIGNED_OUT" || event === "USER_UPDATED") {
        setUserId(session?.user.id ?? null);
      }
    });
    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!userId) {
      setProfile(null);
      setRole(null);
      return;
    }
    let active = true;
    (async () => {
      const [{ data: p }, { data: r }] = await Promise.all([
        supabase.from("profiles").select("*").eq("id", userId).maybeSingle(),
        supabase.from("user_roles").select("role").eq("user_id", userId).maybeSingle(),
      ]);
      if (!active) return;
      if ((p as Profile | null)?.banned) {
        void signOut("Sua conta foi banida do site.");
        return;
      }
      setProfile((p as Profile) ?? null);
      setRole(((r?.role as AppRole) ?? "aluno") as AppRole);
    })();
    return () => {
      active = false;
    };
  }, [userId, tick, signOut]);

  // Sessão única + banimento em tempo real
  useEffect(() => {
    if (!userId) return;
    const channel = supabase
      .channel(`profile-watch-${userId}`)
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "profiles", filter: `id=eq.${userId}` },
        (payload) => {
          const next = payload.new as Profile;
          setProfile(next);
          const mine = localStorage.getItem(SESSION_KEY);
          if (next.banned) {
            void signOut("Sua conta foi banida do site.");
          } else if (next.active_session && mine && next.active_session !== mine) {
            void signOut("Este login foi aberto em outro dispositivo.");
          }
        },
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId, signOut]);

  return (
    <AuthContext.Provider
      value={{ userId, profile, role, loading, signOut, refresh: () => setTick((t) => t + 1) }}
    >
      {children}
    </AuthContext.Provider>
  );
}
