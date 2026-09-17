import { ROLE_ICON, ROLE_LABEL } from "@/components/AuthProvider";
import type { AppRole } from "@/lib/account.functions";

const STYLE: Record<AppRole, string> = {
  owner:
    "border-amber-400/60 bg-amber-400/15 text-amber-700 dark:text-amber-300 shadow-[0_0_0_1px_rgba(251,191,36,0.12)]",
  admin: "border-primary/50 bg-primary/12 text-primary",
  professor: "border-emerald-500/50 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
  support: "border-sky-500/50 bg-sky-500/12 text-sky-700 dark:text-sky-300",
  aluno: "border-border bg-muted text-muted-foreground",
};

/** TAG derivada sempre do papel real gravado no sistema. */
export function RoleTag({
  role,
  size = "md",
  className = "",
}: {
  role: AppRole | null | undefined;
  size?: "sm" | "md";
  className?: string;
}) {
  if (!role) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border font-semibold uppercase tracking-wide ${
        size === "sm" ? "px-1.5 py-0.5 text-[0.6rem]" : "px-2.5 py-1 text-[0.7rem]"
      } ${STYLE[role]} ${className}`}
      title={ROLE_LABEL[role]}
    >
      <span aria-hidden>{ROLE_ICON[role]}</span>
      {ROLE_LABEL[role]}
    </span>
  );
}
