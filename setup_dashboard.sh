#!/bin/bash
echo "🚀 Criando projeto..."
mkdir -p ~/zyntrax-dashboard/{app/login,lib,utils,types}
cd ~/zyntrax-dashboard
cat > package.json << 'PACKAGE'
{"name":"zyntrax-dashboard","version":"1.0.0","private":true,"scripts":{"dev":"next dev","build":"next build","start":"next start"},"dependencies":{"react":"^18.2.0","react-dom":"^18.2.0","next":"^14.0.0","typescript":"^5.0.0","@types/react":"^18.0.0","@types/react-dom":"^18.0.0","tailwindcss":"^3.3.0","postcss":"^8.4.0","autoprefixer":"^10.4.0","axios":"^1.6.0"}}
PACKAGE
echo "✅ Criado!"
