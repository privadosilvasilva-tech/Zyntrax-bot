import { createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

export type AppRole = "owner" | "admin" | "professor" | "support" | "aluno";

export const USERNAME_DOMAIN = "byandry.local";

export function usernameToEmail(username: string) {
  return `${normalizeUsername(username)}@${USERNAME_DOMAIN}`;
}

export function normalizeUsername(username: string) {
  return username
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]/g, "");
}

/** Existe algum usuário cadastrado? (usado na tela de primeira configuração) */
export const getSetupState = createServerFn({ method: "GET" }).handler(async () => {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { count } = await supabaseAdmin
    .from("profiles")
    .select("id", { count: "exact", head: true });
  const { data: settings } = await supabaseAdmin.from("settings").select("key,value");
  const map = Object.fromEntries((settings ?? []).map((s) => [s.key, s.value ?? ""]));
  return {
    needsSetup: (count ?? 0) === 0,
    turmaNome: map["turma_nome"] ?? "BY ANDRY",
    bgmVideoId: map["bgm_video_id"] ?? "",
  };
});

/** Cria a conta do proprietário — só funciona enquanto não existir nenhum usuário. */
export const createOwnerAccount = createServerFn({ method: "POST" })
  .validator((d: { username: string; password: string; displayName: string }) => d)
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { count } = await supabaseAdmin
      .from("profiles")
      .select("id", { count: "exact", head: true });
    if ((count ?? 0) > 0) throw new Error("A turma já foi configurada.");

    const username = normalizeUsername(data.username);
    if (username.length < 3) throw new Error("Usuário inválido (mínimo 3 caracteres).");
    if (data.password.length < 6) throw new Error("A senha precisa ter ao menos 6 caracteres.");

    const { data: created, error } = await supabaseAdmin.auth.admin.createUser({
      email: usernameToEmail(username),
      password: data.password,
      email_confirm: true,
    });
    if (error || !created.user) throw new Error(error?.message ?? "Falha ao criar conta.");

    await supabaseAdmin.from("profiles").insert({
      id: created.user.id,
      username,
      display_name: data.displayName.trim() || username,
    });
    await supabaseAdmin.from("user_roles").insert({ user_id: created.user.id, role: "owner" });
    await supabaseAdmin
      .from("logs")
      .insert({ user_id: created.user.id, action: "Conta de proprietário criada", target: username });

    return { ok: true, email: usernameToEmail(username) };
  });

async function requireStaff(context: { supabase: any; userId: string }, needOwner = false) {
  const { data: roles } = await context.supabase
    .from("user_roles")
    .select("role")
    .eq("user_id", context.userId);
  const list = (roles ?? []).map((r: { role: AppRole }) => r.role);
  if (needOwner ? !list.includes("owner") : !list.some((r: AppRole) => r === "owner" || r === "admin")) {
    throw new Error("Você não tem permissão para isso.");
  }
  return list as AppRole[];
}

/** Proprietário/administrador cria um login novo. */
export const adminCreateUser = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .validator(
    (d: { username: string; password: string; displayName: string; role: AppRole }) => d,
  )
  .handler(async ({ data, context }) => {
    const myRoles = await requireStaff(context);
    if ((data.role === "owner" || data.role === "admin") && !myRoles.includes("owner")) {
      throw new Error("Só o proprietário pode criar administradores.");
    }
    const username = normalizeUsername(data.username);
    if (username.length < 3) throw new Error("Usuário inválido (mínimo 3 caracteres).");
    if (data.password.length < 6) throw new Error("A senha precisa ter ao menos 6 caracteres.");

    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: exists } = await supabaseAdmin
      .from("profiles")
      .select("id")
      .eq("username", username)
      .maybeSingle();
    if (exists) throw new Error("Esse nome de usuário já existe.");

    const { data: created, error } = await supabaseAdmin.auth.admin.createUser({
      email: usernameToEmail(username),
      password: data.password,
      email_confirm: true,
    });
    if (error || !created.user) throw new Error(error?.message ?? "Falha ao criar usuário.");

    await supabaseAdmin.from("profiles").insert({
      id: created.user.id,
      username,
      display_name: data.displayName.trim() || username,
    });
    await supabaseAdmin.from("user_roles").insert({ user_id: created.user.id, role: data.role });
    await supabaseAdmin
      .from("logs")
      .insert({ user_id: context.userId, action: "Criou usuário", target: username });
    return { ok: true };
  });

/** Banir / desbanir (banido não consegue entrar e é desconectado). */
export const adminSetBanned = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .validator((d: { userId: string; banned: boolean }) => d)
  .handler(async ({ data, context }) => {
    await requireStaff(context);
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: target } = await supabaseAdmin
      .from("user_roles")
      .select("role")
      .eq("user_id", data.userId);
    if ((target ?? []).some((r) => r.role === "owner")) {
      throw new Error("O proprietário não pode ser banido.");
    }
    await supabaseAdmin
      .from("profiles")
      .update({ banned: data.banned, active_session: null })
      .eq("id", data.userId);
    await supabaseAdmin.auth.admin.signOut(data.userId, "global").catch(() => {});
    await supabaseAdmin.from("logs").insert({
      user_id: context.userId,
      action: data.banned ? "Baniu usuário" : "Desbaniu usuário",
      target: data.userId,
    });
    return { ok: true };
  });

export const adminDeleteUser = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .validator((d: { userId: string }) => d)
  .handler(async ({ data, context }) => {
    await requireStaff(context, true);
    if (data.userId === context.userId) throw new Error("Você não pode excluir a si mesmo.");
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    await supabaseAdmin.auth.admin.deleteUser(data.userId);
    await supabaseAdmin
      .from("logs")
      .insert({ user_id: context.userId, action: "Excluiu usuário", target: data.userId });
    return { ok: true };
  });

export const adminSetRole = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .validator((d: { userId: string; role: AppRole }) => d)
  .handler(async ({ data, context }) => {
    await requireStaff(context, true);
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    await supabaseAdmin.from("user_roles").delete().eq("user_id", data.userId);
    await supabaseAdmin.from("user_roles").insert({ user_id: data.userId, role: data.role });
    await supabaseAdmin
      .from("logs")
      .insert({ user_id: context.userId, action: `Alterou papel para ${data.role}`, target: data.userId });
    return { ok: true };
  });

export const adminResetPassword = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .validator((d: { userId: string; password: string }) => d)
  .handler(async ({ data, context }) => {
    await requireStaff(context);
    if (data.password.length < 6) throw new Error("A senha precisa ter ao menos 6 caracteres.");
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    await supabaseAdmin.auth.admin.updateUserById(data.userId, { password: data.password });
    await supabaseAdmin
      .from("logs")
      .insert({ user_id: context.userId, action: "Trocou a senha de um usuário", target: data.userId });
    return { ok: true };
  });

/** Reivindica a sessão única: derruba qualquer outro dispositivo usando o mesmo login. */
export const claimSession = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .validator((d: { sessionId: string }) => d)
  .handler(async ({ data, context }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: profile } = await supabaseAdmin
      .from("profiles")
      .select("banned")
      .eq("id", context.userId)
      .maybeSingle();
    if (!profile) throw new Error("Perfil não encontrado.");
    if (profile.banned) throw new Error("Esta conta foi banida do site.");
    await supabaseAdmin
      .from("profiles")
      .update({ active_session: data.sessionId, last_seen: new Date().toISOString() })
      .eq("id", context.userId);
    return { ok: true };
  });

export const updateSettings = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .validator((d: { turmaNome?: string; bgmVideoId?: string }) => d)
  .handler(async ({ data, context }) => {
    await requireStaff(context, true);
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    if (data.turmaNome !== undefined) {
      await supabaseAdmin.from("settings").upsert({ key: "turma_nome", value: data.turmaNome });
    }
    if (data.bgmVideoId !== undefined) {
      await supabaseAdmin.from("settings").upsert({ key: "bgm_video_id", value: data.bgmVideoId });
    }
    return { ok: true };
  });
