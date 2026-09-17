path = "src/lib/account.functions.ts"
content = open(path, encoding="utf-8").read()
count = content.count(".inputValidator(")
if count == 0:
    print("Nenhuma ocorrencia de .inputValidator( encontrada -- talvez ja tenha sido trocado.")
else:
    new_content = content.replace(".inputValidator(", ".validator(")
    open(path, "w", encoding="utf-8").write(new_content)
    print(f"[OK] {count} ocorrencia(s) trocadas de .inputValidator( para .validator( em {path}")
