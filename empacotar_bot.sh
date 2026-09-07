#!/bin/bash
cd ~/zyntrax-bot || exit 1

NOME_ZIP="bot_projeto_$(date +%Y%m%d_%H%M%S).zip"

zip -r "$NOME_ZIP" . \
  -x ".env" \
  -x ".env.*" \
  -x "*.env" \
  -x "*env*.json" \
  -x "config/*" \
  -x "config.json" \
  -x "config.yaml" \
  -x "config.yml" \
  -x "settings.json" \
  -x "secrets*" \
  -x "*secret*" \
  -x "*token*" \
  -x "*credential*" \
  -x "*.key" \
  -x "*.pem" \
  -x "*.pfx" \
  -x "*.zip" \
  -x "node_modules/*" \
  -x "venv/*" \
  -x ".venv/*" \
  -x "__pycache__/*" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x ".git/*" \
  -x "*.log"

echo ""
echo "=== Verificando se algo suspeito ficou dentro do ZIP ==="
unzip -l "$NOME_ZIP" | grep -iE "token|secret|credential|\.env|config|settings"

echo ""
echo "=== Procurando token 'hardcoded' direto no código ==="
grep -rniE "token\s*=\s*[\"'][a-zA-Z0-9._-]{20,}" \
  --include="*.py" --include="*.js" --include="*.ts" --include="*.json" . \
  | grep -v "$NOME_ZIP"

echo ""
echo "ZIP gerado: $NOME_ZIP"
echo "Confira os avisos acima antes de enviar."
