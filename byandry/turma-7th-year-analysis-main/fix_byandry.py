import sys

def apply(path, old, new, label):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    count = content.count(old)
    if count != 1:
        print(f"[FALHA] {label}: esperava 1 ocorrencia, encontrei {count}. Nada foi alterado em {path}.")
        return False
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] {label}")
    return True

ok = True

ok &= apply(
    "src/components/UserAvatar.tsx",
    '  path?: string | null;\n  name?: string | null;\n  size?: keyof typeof SIZES;',
    '  path?: string | null | undefined;\n  name?: string | null | undefined;\n  size?: keyof typeof SIZES;',
    "UserAvatar.tsx: path/name aceitam undefined",
)

ok &= apply(
    "src/routes/_authenticated/atividades.tsx",
    '    const { error } = await supabase.from("activities").insert({\n      title,',
    '    const { error } = await supabase.from("activities").insert({\n      // gerado pelo trigger `activities_public_id` no banco quando vazio; string\n      // vazia so para satisfazer o tipo `Insert` (nao sobrescreve o trigger).\n      public_id: "",\n      title,',
    "atividades.tsx: public_id no insert",
)

ok &= apply(
    "src/routes/_authenticated/perfil.tsx",
    '    if (!ALLOWED.includes(f.type)) {\n      return toast.error("Use uma imagem JPG, PNG, WEBP ou GIF.");\n    }\n    if (f.size > MAX_BYTES) {\n      return toast.error("A imagem precisa ter no máximo 3 MB.");\n    }\n    setFile(f);',
    '    if (!ALLOWED.includes(f.type)) {\n      toast.error("Use uma imagem JPG, PNG, WEBP ou GIF.");\n      return;\n    }\n    if (f.size > MAX_BYTES) {\n      toast.error("A imagem precisa ter no máximo 3 MB.");\n      return;\n    }\n    setFile(f);',
    "perfil.tsx: pick()",
)

ok &= apply(
    "src/routes/_authenticated/perfil.tsx",
    '    setUploading(false);\n    if (error) return toast.error("Não foi possível remover a foto.");\n    refresh();',
    '    setUploading(false);\n    if (error) {\n      toast.error("Não foi possível remover a foto.");\n      return;\n    }\n    refresh();',
    "perfil.tsx: removeAvatar()",
)

ok &= apply(
    "src/routes/_authenticated/perfil.tsx",
    '    setBusy(false);\n    if (error) return toast.error("Não foi possível salvar.");\n    toast.success("Nome atualizado!");',
    '    setBusy(false);\n    if (error) {\n      toast.error("Não foi possível salvar.");\n      return;\n    }\n    toast.success("Nome atualizado!");',
    "perfil.tsx: saveName()",
)

ok &= apply(
    "src/routes/_authenticated/perfil.tsx",
    '    e.preventDefault();\n    if (password.length < 6) return toast.error("A senha precisa ter ao menos 6 caracteres.");\n    setBusy(true);\n    const { error } = await supabase.auth.updateUser({ password });\n    setBusy(false);\n    if (error) return toast.error("Não foi possível trocar a senha.");\n    setPassword("");',
    '    e.preventDefault();\n    if (password.length < 6) {\n      toast.error("A senha precisa ter ao menos 6 caracteres.");\n      return;\n    }\n    setBusy(true);\n    const { error } = await supabase.auth.updateUser({ password });\n    setBusy(false);\n    if (error) {\n      toast.error("Não foi possível trocar a senha.");\n      return;\n    }\n    setPassword("");',
    "perfil.tsx: savePassword()",
)

if not ok:
    print("\nAlgum trecho nao bateu -- me manda o conteudo atual do arquivo que ajusto.")
    sys.exit(1)
else:
    print("\nTudo aplicado com sucesso.")
