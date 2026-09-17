path = "vite.config.ts"
old = '''export default defineConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
});'''
new = '''export default defineConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
  // Forca o build pra rodar como servidor Node generico (Render, Railway, etc)
  // em vez do preset padrao cloudflare-module.
  nitro: {
    preset: "node-server",
  },
});'''
content = open(path, encoding="utf-8").read()
count = content.count(old)
if count != 1:
    print(f"[FALHA] esperava 1 ocorrencia, encontrei {count}. Nada foi alterado.")
else:
    content = content.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("[OK] vite.config.ts atualizado com preset node-server")
