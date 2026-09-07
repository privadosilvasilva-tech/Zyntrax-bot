import json
import os

def setup_token():
    print("=" * 50)
    print("⚙️  CONFIGURAÇÃO INICIAL DO BOT")
    print("=" * 50)
    print()
    
    token = input("MTU0MDE2MzUzNjQwNjE5MjE0OA.GP1LN2.ZZppNEyW5O7b87z6H0DEAvBNswDbmKmMPcEevU ").strip()
    
    if not token:
        print("❌ Token vazio! Tente novamente.")
        return
    
    # Salvar em arquivo de config
    config = {"token": token}
    
    os.makedirs("config", exist_ok=True)
    
    with open("config/token.json", "w") as f:
        json.dump(config, f)
    
    print()
    print("✅ Token salvo com sucesso!")
    print("🚀 Agora execute: python bot.py")
    print()

if __name__ == "__main__":
    setup_token()
