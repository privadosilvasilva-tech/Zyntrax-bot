import { Link, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import {
  BookOpen,
  CalendarDays,
  Crown,
  Home,
  LogOut,
  Megaphone,
  MessageCircle,
  Shield,
  User,
} from "lucide-react";
import { isStaff, useAuth } from "@/components/AuthProvider";
import { RoleTag } from "@/components/RoleTag";
import { UserAvatar } from "@/components/UserAvatar";
import { ThemeToggle } from "@/components/ThemeToggle";
import { BackgroundMusic } from "@/components/BackgroundMusic";
import { getSetupState } from "@/lib/account.functions";

const NAV = [
  { to: "/painel", label: "Início", icon: Home, mobile: true },
  { to: "/atividades", label: "Atividades", icon: BookOpen, mobile: true },
  { to: "/calendario", label: "Calendário", icon: CalendarDays, mobile: true },
  { to: "/chat", label: "Chat", icon: MessageCircle, mobile: true },
  { to: "/avisos", label: "Avisos", icon: Megaphone, mobile: false },
  { to: "/perfil", label: "Meu perfil", icon: User, mobile: true },
] as const;

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const { profile, role, signOut } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => getSetupState(),
    staleTime: 5 * 60 * 1000,
  });

  const turma = settings?.turmaNome ?? "BY ANDRY";

  return (
    <div className="flex min-h-screen bg-background">
      <BackgroundMusic videoId={settings?.bgmVideoId ?? ""} />

      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar px-4 py-6 md:flex">
        <Link to="/painel" className="mb-8 flex items-center gap-3 px-2">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--gradient-primary)] text-lg font-bold text-primary-foreground">
            A
          </span>
          <span className="font-display text-lg font-semibold leading-tight text-sidebar-foreground">
            {turma}
          </span>
        </Link>

        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => (
            <SideLink key={item.to} to={item.to} label={item.label} icon={item.icon} active={pathname === item.to} />
          ))}

          {isStaff(role) && (
            <>
              <div className="my-3 h-px bg-sidebar-border" />
              <SideLink to="/admin" label="Painel admin" icon={Shield} active={pathname === "/admin"} />
            </>
          )}
          {role === "owner" && (
            <SideLink to="/by-andry" label="BY ANDRY" icon={Crown} active={pathname === "/by-andry"} />
          )}
        </nav>

        <div className="flex flex-col gap-2">
          <ThemeToggle withLabel />
          <button
            type="button"
            onClick={() => void signOut()}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-destructive"
          >
            <LogOut className="h-4 w-4" /> Sair
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-border bg-background/80 px-4 py-4 backdrop-blur md:px-8">
          <h1 className="font-display text-xl font-semibold md:text-2xl">{title}</h1>
          <div className="mr-14 flex items-center gap-2 text-sm sm:gap-3">
            <span className="hidden sm:inline">
              <RoleTag role={role} size="sm" />
            </span>
            <span className="hidden max-w-[9rem] truncate font-medium sm:inline">
              {profile?.display_name}
            </span>
            <Link to="/perfil" aria-label="Meu perfil">
              <UserAvatar path={profile?.avatar_url} name={profile?.display_name} size="sm" />
            </Link>
          </div>
        </header>

        <main className="flex-1 px-4 pb-28 pt-6 md:px-8 md:pb-10">
          <div className="animate-fade-up mx-auto w-full max-w-6xl">{children}</div>
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-around border-t border-border bg-card/95 py-2 backdrop-blur md:hidden">
        {NAV.filter((n) => n.mobile).map((item) => {
          const Icon = item.icon;
          const active = pathname === item.to;
          return (
            <Link
              key={item.to}
              to={item.to}
              aria-label={item.label}
              className={`flex flex-col items-center gap-1 rounded-lg px-3 py-1 text-[0.65rem] transition-colors ${
                active ? "text-primary" : "text-muted-foreground"
              }`}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function SideLink({
  to,
  label,
  icon: Icon,
  active,
}: {
  to: string;
  label: string;
  icon: typeof Home;
  active: boolean;
}) {
  return (
    <Link
      to={to}
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-[var(--shadow-soft)]"
          : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
      }`}
    >
      <Icon className={`h-4 w-4 ${active ? "text-primary" : ""}`} />
      {label}
    </Link>
  );
}
