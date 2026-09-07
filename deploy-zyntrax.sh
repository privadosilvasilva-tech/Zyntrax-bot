#!/bin/bash

echo "🚀 Deploy Extraordinário - Zyntrax"
echo ""

cd ~/zyntrax-dashboard

echo "📝 Configurando Git..."
git config user.name "zyntrax-bot"
git config user.email "bot@zyntrax.dev"

echo "📦 Adicionando arquivos..."
git add .

echo "💾 Commitando..."
git commit -m "✨ Forms extraordinários instalados - V2.0"

echo ""
echo "🔑 Agora coloque seu GitHub token:"
echo "   (Cole o token e pressione Enter)"
echo ""
read -sp "Token: " GITHUB_TOKEN

echo ""
echo ""
echo "🚀 Fazendo push para GitHub..."

# Usar token para autenticar
git push https://zyntrax-bot:$GITHUB_TOKEN@github.com/privadosilvasilva-tech/Site-Zyntrax.git main

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Deploy enviado com sucesso!"
  echo ""
  echo "⏳ Aguarde 2-3 minutos para Vercel fazer o deploy..."
  echo ""
  echo "📍 Seu site estará em:"
  echo "   https://site-zyntrax.vercel.app"
  echo ""
  echo "🎉 Sucesso!"
else
  echo ""
  echo "❌ Erro ao fazer push. Verifique o token."
fi
