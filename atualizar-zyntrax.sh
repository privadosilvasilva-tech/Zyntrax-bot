#!/data/data/com.termux/files/usr/bin/bash
set -e

# ajuste o caminho abaixo pro seu projeto no Termux
cd ~/zyntrax-bot || { echo "❌ Pasta do projeto não encontrada"; exit 1; }

echo "📦 Adicionando alterações..."
git add -A

if git diff --cached --quiet; then
    echo "⚠️  Nada novo para commitar."
else
    git commit -m "update: $(date '+%Y-%m-%d %H:%M')"
fi

echo "🚀 Enviando para o GitHub..."
git push origin main

echo "✅ Push feito!"
echo "🔄 O bot no Replit vai detectar e se reiniciar sozinho em até 2 minutos."
