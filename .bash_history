        try:
            await canal.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Erro ao enviar painel!", ephemeral=True)

class CanalSelectView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        
        select = discord.ui.ChannelSelect(
            placeholder="Selecione o canal...",
            min_values=1,
            max_values=1
        )
        select.callback = self.on_canal_select
        self.add_item(select)
    
    async def on_canal_select(self, interaction: discord.Interaction):
        canal_id = interaction.values[0].id
        config = carregar_config()
        gid = str(self.guild_id)
        
        if gid not in config:
            config[gid] = {}
        
        config[gid]["canal_id"] = canal_id
        salvar_config(config)
        
        await interaction.response.send_message(
            f"✅ Canal <#{canal_id}> configurado!",
            ephemeral=True
        )

class ProdutoSelectView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        
        from cogs.loja import carregar as carregar_loja
        config_loja = carregar_loja()
        loja = config_loja.get(str(guild_id), {}).get("ficticio", {})
        produtos = loja.get("produtos", [])
        
        if produtos:
            options = [
                discord.SelectOption(label=p["nome"][:100], value=p["id"])
                for p in produtos[:25]
            ]
            
            select = discord.ui.Select(
                placeholder="Escolha um produto...",
                options=options,
                min_values=1,
                max_values=1
            )
            select.callback = self.on_produto_select
            self.add_item(select)
    
    async def on_produto_select(self, interaction: discord.Interaction):
        produto_id = interaction.data["values"][0]
        await interaction.response.send_modal(ConfigBonusModal(self.guild_id, produto_id))

class ConfigBonusModal(discord.ui.Modal):
    valor = discord.ui.TextInput(label="Valor do Bônus", placeholder="Ex: 1000")
    
    def __init__(self, guild_id, produto_id):
        super().__init__(title="Configurar Bônus")
        self.guild_id = guild_id
        self.produto_id = produto_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor = float(self.valor.value)
        except:
            await interaction.response.send_message("❌ Valor inválido!", ephemeral=True)
            return
        
        config = carregar_config()
        gid = str(self.guild_id)
        
        if gid not in config:
            config[gid] = {"bonuses": {}}
        if "bonuses" not in config[gid]:
            config[gid]["bonuses"] = {}
        
        config[gid]["bonuses"][self.produto_id] = valor
        salvar_config(config)
        
        await interaction.response.send_message(
            f"✅ Bônus de **{formatar_reais(valor)}** configurado!",
            ephemeral=True
        )

def criar_embed_bonus(guild_id):
    config = carregar_config()
    gid = str(guild_id)
    bonuses = config.get(gid, {}).get("bonuses", {})
    
    embed = discord.Embed(
        title="💰 BÔNUS DIÁRIO",
        description="Resgate seu bônus diário e ganhe dinheiro!",
        color=0xFFD700
    )
    
    embed.add_field(
        name="🎁 Como Funciona",
        value="Clique no botão abaixo para resgatar seu bônus diário. Você só pode resgatar uma vez a cada 24 horas!",
        inline=False
    )
    
    if bonuses:
        from cogs.loja import carregar as carregar_loja
        config_loja = carregar_loja()
        loja = config_loja.get(gid, {}).get("ficticio", {})
        produtos = loja.get("produtos", [])
        
        valores_txt = ""
        for produto in produtos:
            if produto["id"] in bonuses:
                valores_txt += f"🏆 **{produto['nome']}**: {formatar_reais(bonuses[produto['id']])}\n"
        
        if valores_txt:
            embed.add_field(name="💵 Valores por Plano", value=valores_txt, inline=False)
    
    embed.add_field(
        name="⏳ Limite",
        value="Um resgate a cada 24 horas",
        inline=True
    )
    
    embed.set_footer(text="Desenvolvido por Silva")
    return embed

class Bonus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="bonus-admin", description="Admin - Configurar bônus diário")
    @app_commands.guild_only()
    async def bonus_admin_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("❌ Exclusivo!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Admin - Configurar Bônus",
            color=0xFF0000
        )
        
        view = ConfigBonusView(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bonus(bot))
EOF

cd ~ && python3 bot.py
cat > ~/cogs/bonus.py << 'EOF'
import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import json
import os
from datetime import datetime, timedelta, timezone
from cogs.carteira import creditar_saldo, obter_saldo, formatar_reais

CONFIG_FILE = "config/bonus_config.json"
DADOS_FILE = "config/bonus_dados.json"
ADMIN_ID = 1526990069255114913

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_config(dados):
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def carregar_dados():
    if os.path.exists(DADOS_FILE):
        try:
            with open(DADOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_dados(dados):
    os.makedirs("config", exist_ok=True)
    with open(DADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

class ResgatarBonusButton(discord.ui.Button):
    def __init__(self, guild_id):
        super().__init__(label="💰 Resgatar Bônus Diário", style=discord.ButtonStyle.success, emoji="🎁")
        self.guild_id = guild_id
    
    async def callback(self, interaction: discord.Interaction):
        config = carregar_config()
        dados = carregar_dados()
        gid = str(self.guild_id)
        uid = str(interaction.user.id)
        
        if gid not in config:
            await interaction.response.send_message("❌ Bônus não configurado!", ephemeral=True)
            return
        
        bonuses = config[gid].get("bonuses", {})
        if not bonuses:
            await interaction.response.send_message("❌ Nenhum bônus cadastrado!", ephemeral=True)
            return
        
        chave_resgate = f"{gid}_{uid}"
        if chave_resgate in dados:
            ultimo_resgate = datetime.fromisoformat(dados[chave_resgate]["timestamp"])
            agora = datetime.now(timezone.utc)
            diff = agora - ultimo_resgate
            
            if diff.total_seconds() < 86400:
                tempo_restante = 86400 - diff.total_seconds()
                horas = int(tempo_restante // 3600)
                minutos = int((tempo_restante % 3600) // 60)
                await interaction.response.send_message(
                    f"⏳ Você já resgatou hoje! Tente novamente em **{horas}h {minutos}m**",
                    ephemeral=True
                )
                return
        
        from cogs.loja import carregar as carregar_loja
        config_loja = carregar_loja()
        loja = config_loja.get(gid, {}).get("ficticio", {})
        produtos = loja.get("produtos", [])
        
        plano_usuario = None
        for produto in produtos:
            cargos_ids = produto.get("cargos_id", [])
            user_roles = {r.id for r in interaction.user.roles}
            if cargos_ids and user_roles & set(cargos_ids):
                plano_usuario = produto["id"]
                break
        
        if not plano_usuario:
            await interaction.response.send_message(
                "❌ Você não tem nenhum plano ativo!",
                ephemeral=True
            )
            return
        
        bonus_valor = bonuses.get(plano_usuario, 0)
        if bonus_valor <= 0:
            await interaction.response.send_message("❌ Bônus inválido!", ephemeral=True)
            return
        
        creditar_saldo(self.guild_id, interaction.user.id, bonus_valor, detalhe="Bônus Diário")
        
        if chave_resgate not in dados:
            dados[chave_resgate] = {}
        dados[chave_resgate]["timestamp"] = datetime.now(timezone.utc).isoformat()
        dados[chave_resgate]["valor"] = bonus_valor
        salvar_dados(dados)
        
        await interaction.response.send_message(
            f"✅ Bônus de **{formatar_reais(bonus_valor)}** resgatado com sucesso!",
            ephemeral=True
        )

class BonusView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.add_item(ResgatarBonusButton(guild_id))

class CanalSelect(ui.ChannelSelect):
    def __init__(self, guild_id):
        super().__init__(
            placeholder="Selecione o canal...",
            min_values=1,
            max_values=1
        )
        self.guild_id = guild_id
    
    async def callback(self, interaction: discord.Interaction):
        canal_id = self.values[0].id
        config = carregar_config()
        gid = str(self.guild_id)
        
        if gid not in config:
            config[gid] = {}
        
        config[gid]["canal_id"] = canal_id
        salvar_config(config)
        
        await interaction.response.send_message(
            f"✅ Canal <#{canal_id}> configurado!",
            ephemeral=True
        )

class CanalSelectView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.add_item(CanalSelect(guild_id))

class ConfigBonusView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id
    
    @discord.ui.button(label="⚙️ Configurar Canal", style=discord.ButtonStyle.primary)
    async def canal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CanalSelectView(self.guild_id)
        await interaction.response.send_message(
            "Selecione o canal:",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(label="💰 Configurar Valores", style=discord.ButtonStyle.success)
    async def valores_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Selecione um produto:",
            view=ProdutoSelectView(self.guild_id),
            ephemeral=True
        )
    
    @discord.ui.button(label="📤 Enviar Painel", style=discord.ButtonStyle.success)
    async def enviar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = carregar_config()
        gid = str(self.guild_id)
        
        if gid not in config or not config[gid].get("canal_id"):
            await interaction.response.send_message("❌ Configure o canal primeiro!", ephemeral=True)
            return
        
        canal_id = config[gid]["canal_id"]
        canal = interaction.guild.get_channel(canal_id)
        if not canal:
            await interaction.response.send_message("❌ Canal não encontrado!", ephemeral=True)
            return
        
        embed = criar_embed_bonus(self.guild_id)
        view = BonusView(self.guild_id)
        
        try:
            await canal.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Erro ao enviar!", ephemeral=True)

class ProdutoSelectView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        
        from cogs.loja import carregar as carregar_loja
        config_loja = carregar_loja()
        loja = config_loja.get(str(guild_id), {}).get("ficticio", {})
        produtos = loja.get("produtos", [])
        
        if produtos:
            options = [
                discord.SelectOption(label=p["nome"][:100], value=p["id"])
                for p in produtos[:25]
            ]
            
            select = discord.ui.Select(
                placeholder="Escolha um produto...",
                options=options,
                min_values=1,
                max_values=1
            )
            select.callback = self.on_produto_select
            self.add_item(select)
    
    async def on_produto_select(self, interaction: discord.Interaction):
        produto_id = interaction.data["values"][0]
        await interaction.response.send_modal(ConfigBonusModal(self.guild_id, produto_id))

class ConfigBonusModal(discord.ui.Modal):
    valor = discord.ui.TextInput(label="Valor do Bônus", placeholder="Ex: 1000")
    
    def __init__(self, guild_id, produto_id):
        super().__init__(title="Configurar Bônus")
        self.guild_id = guild_id
        self.produto_id = produto_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor = float(self.valor.value)
        except:
            await interaction.response.send_message("❌ Valor inválido!", ephemeral=True)
            return
        
        config = carregar_config()
        gid = str(self.guild_id)
        
        if gid not in config:
            config[gid] = {"bonuses": {}}
        if "bonuses" not in config[gid]:
            config[gid]["bonuses"] = {}
        
        config[gid]["bonuses"][self.produto_id] = valor
        salvar_config(config)
        
        await interaction.response.send_message(
            f"✅ Bônus de **{formatar_reais(valor)}** configurado!",
            ephemeral=True
        )

def criar_embed_bonus(guild_id):
    config = carregar_config()
    gid = str(guild_id)
    bonuses = config.get(gid, {}).get("bonuses", {})
    
    embed = discord.Embed(
        title="💰 BÔNUS DIÁRIO",
        description="Resgate seu bônus diário e ganhe dinheiro!",
        color=0xFFD700
    )
    
    embed.add_field(
        name="🎁 Como Funciona",
        value="Clique no botão para resgatar! Só uma vez a cada 24 horas!",
        inline=False
    )
    
    if bonuses:
        from cogs.loja import carregar as carregar_loja
        config_loja = carregar_loja()
        loja = config_loja.get(gid, {}).get("ficticio", {})
        produtos = loja.get("produtos", [])
        
        valores_txt = ""
        for produto in produtos:
            if produto["id"] in bonuses:
                valores_txt += f"🏆 **{produto['nome']}**: {formatar_reais(bonuses[produto['id']])}\n"
        
        if valores_txt:
            embed.add_field(name="💵 Valores por Plano", value=valores_txt, inline=False)
    
    embed.set_footer(text="Desenvolvido por Silva")
    return embed

class Bonus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="bonus-admin", description="Admin - Configurar bônus")
    @app_commands.guild_only()
    async def bonus_admin_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("❌ Exclusivo!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Admin - Configurar Bônus",
            color=0xFF0000
        )
        
        view = ConfigBonusView(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bonus(bot))
EOF

cd ~ && python3 bot.py
grep "def creditar_saldo" ~/cogs/carteira.py
sed -i 's/creditar_saldo(self.guild_id, interaction.user.id, bonus_valor, detalhe=/creditar_saldo(self.guild_id, interaction.user.id, bonus_valor, "ficticio", detalhe=/g' ~/cogs/bonus.py
cd ~ && python3 bot.py
grep "creditar_saldo" ~/cogs/bonus.py
cd ~ && python3 bot.py
find ~/cogs -name "*.pyc" -delete && find ~/cogs -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; echo "✓ Cache limpo"
cd ~ && python3 bot.py
cd ~ && rm -f bot-railway.zip && zip -r bot-railway.zip bot.py cogs/ config/ .env -x "*.pyc" "__pycache__/*" && echo "✓ Zipado!"
cp ~/bot-railway.zip ~/storage/shared/Download/ && ls -lh ~/storage/shared/Download/bot-railway.zip
cd ~ && git init && git add . && git commit -m "Bot Zyntrax" && git remote add origin https://github.com/privadoilvasilva-tech /zyntrax-bot.git && git push -u origin main
git rm --cached suporte-bot
git commit -m "Remove embedded repo"
git push -u origin main
git branch -M master main
git push -u origin main
git remote -v
git remote add origin https://github.com/privadosilvasilva-tech/zyntrax-bot.git
git push -u origin main
-git remote remove origin
git remote add origin https://github.com/privadosilvasilva-tech/zyntrax-bot.git
git remote remove origin
git remote add origin https://github.com/privadosilvasilva-tech/zyntrax-bot.git
git push -u origin main
it remote set-url origin https://github.com/privadosilvasilva-tech/Zyntrax-bot.git
nano .enb
nano .env
