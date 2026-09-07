import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import os

CONFIG_FILE = "config/loja_config.json"
ADMIN_ID = 1526990069255114913

def carregar():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar(dados):
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

class CargoSelect(ui.RoleSelect):
    def __init__(self, guild_id, tipo, produto_id, produto_nome):
        super().__init__(
            placeholder="Selecione os cargos...",
            min_values=1,
            max_values=25
        )
        self.guild_id = guild_id
        self.tipo = tipo
        self.produto_id = produto_id
        self.produto_nome = produto_nome

    async def callback(self, interaction: discord.Interaction):
        roles_ids = [role.id for role in self.values]
        
        config = carregar()
        gid = str(self.guild_id)
        
        if gid not in config:
            config[gid] = {}
        if self.tipo not in config[gid]:
            config[gid][self.tipo] = {"produtos": []}
        
        for p in config[gid][self.tipo]["produtos"]:
            if p["id"] == self.produto_id:
                p["cargos_id"] = roles_ids
                break
        
        salvar(config)
        roles_txt = ", ".join([f"<@&{rid}>" for rid in roles_ids])
        await interaction.response.send_message(
            f"✅ {len(roles_ids)} cargo(s) configurado(s):\n{roles_txt}",
            ephemeral=True
        )

class SelecionarCargoView(discord.ui.View):
    def __init__(self, guild_id, tipo, produto_id, produto_nome):
        super().__init__(timeout=600)
        select = CargoSelect(guild_id, tipo, produto_id, produto_nome)
        self.add_item(select)

class SelecionarProdutoView(discord.ui.View):
    def __init__(self, guild_id, tipo):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.tipo = tipo
        config = carregar()
        loja = config.get(str(guild_id), {}).get(tipo, {})
        produtos = loja.get("produtos", [])
        
        if produtos:
            options = []
            for p in produtos[:25]:
                cargos_ids = p.get("cargos_id", [])
                cargo_txt = f" [{len(cargos_ids)} cargo(s)]" if cargos_ids else " [Sem cargo]"
                options.append(
                    discord.SelectOption(
                        label=p["nome"][:100],
                        value=p["id"],
                        description=f"R$ {p['valor']}{cargo_txt}"[:100]
                    )
                )
            
            select = discord.ui.Select(
                placeholder="Escolha um produto...",
                options=options,
                min_values=1,
                max_values=1
            )
            select.callback = self.on_select
            self.add_item(select)
    
    async def on_select(self, interaction: discord.Interaction):
        produto_id = interaction.data["values"][0]
        config = carregar()
        loja = config.get(str(self.guild_id), {}).get(self.tipo, {})
        produto = next((p for p in loja.get("produtos", []) if p["id"] == produto_id), None)
        
        if produto:
            view = SelecionarCargoView(self.guild_id, self.tipo, produto_id, produto["nome"])
            await interaction.response.send_message(
                f"**Escolha os cargos para `{produto['nome']}`:**",
                view=view,
                ephemeral=True
            )

class AdminPainelView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id
    
    @discord.ui.button(label="🪙 Loja Fictícia", style=discord.ButtonStyle.primary)
    async def ficticio_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SelecionarProdutoView(self.guild_id, "ficticio")
        await interaction.response.send_message(
            "**Selecione um produto:**",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(label="💳 Loja Real", style=discord.ButtonStyle.success)
    async def real_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SelecionarProdutoView(self.guild_id, "real")
        await interaction.response.send_message(
            "**Selecione um produto:**",
            view=view,
            ephemeral=True
        )

class LojaAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="loja-admin", description="Admin - Configurar cargos")
    @app_commands.guild_only()
    async def loja_admin_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("❌ Exclusivo!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Admin - Configurar Cargos",
            color=0xFF0000
        )
        
        view = AdminPainelView(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LojaAdmin(bot))
