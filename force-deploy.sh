#!/bin/bash
echo "🚀 Forçando Deploy..."
cd ~/zyntrax-dashboard
git config user.name "zyntrax-bot"
git config user.email "bot@zyntrax.dev"
git commit --allow-empty -m "🔄 Forçar rebuild na Vercel"
echo ""
echo "🔑 Cole seu GitHub token:"
read -sp "Token: " TOKEN
echo ""
git push https://zyntrax-bot:$TOKEN@github.com/privadosilvasilva-tech/Site-Zyntrax.git main
echo ""
echo "✅ Deploy forçado enviado!"
