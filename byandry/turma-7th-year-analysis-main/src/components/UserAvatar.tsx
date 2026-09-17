import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";

/** Resolve o caminho salvo no perfil para uma URL assinada (bucket privado). */
export function useAvatarUrl(path?: string | null) {
  return useQuery({
    queryKey: ["avatar-url", path],
    enabled: !!path,
    staleTime: 45 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    queryFn: async () => {
      const { data, error } = await supabase.storage
        .from("avatars")
        .createSignedUrl(path as string, 60 * 60);
      if (error) return null;
      return data?.signedUrl ?? null;
    },
  });
}

export function initialsOf(name?: string | null) {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

const SIZES = {
  sm: "h-8 w-8 text-[0.65rem]",
  md: "h-10 w-10 text-xs",
  lg: "h-16 w-16 text-base",
  xl: "h-28 w-28 text-2xl",
} as const;

export function UserAvatar({
  path,
  name,
  size = "md",
  className = "",
  ring = false,
}: {
  path?: string | null | undefined;
  name?: string | null | undefined;
  size?: keyof typeof SIZES;
  className?: string;
  ring?: boolean;
}) {
  const { data: url, isLoading } = useAvatarUrl(path);
  const [broken, setBroken] = useState(false);

  return (
    <span
      className={`relative inline-flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full bg-[var(--gradient-primary)] font-semibold text-primary-foreground transition-transform duration-200 ${
        SIZES[size]
      } ${ring ? "ring-2 ring-primary/40 ring-offset-2 ring-offset-background" : ""} ${className}`}
      aria-hidden={false}
      role="img"
      aria-label={name ? `Foto de ${name}` : "Foto de perfil"}
    >
      {path && isLoading && <span className="absolute inset-0 animate-pulse bg-muted" />}
      {url && !broken ? (
        <img
          src={url}
          alt=""
          loading="lazy"
          onError={() => setBroken(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <span>{initialsOf(name)}</span>
      )}
    </span>
  );
}
