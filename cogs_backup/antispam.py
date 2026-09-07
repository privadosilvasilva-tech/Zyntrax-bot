import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging

logger = logging.getLogger("bot.antispam")
CONFIG_FILE = "config/moderacao_config.json"

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {"antispam": {"enabled": False, "repetition_limit": 3, "caps_limit": 70}}
    if "antispam" not in config[gid]:
        config[gid]["antispam"] = {"enabled": False, "repetition_limit": 3, "caps_limit": 70}
    return config[gid]["antispam"]

class VoltarAntiSpamButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.moderacao import abrir_painel_moderacao
        embed, view = abrir_painel_moderacao(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

class PainelAntiSpamView(discord.ui.View):
    def __init__(self, dono_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.guild_id = guild_id
        
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        self.enabled = gconf.get("enabled", False)
        self.repetition_limit = gconf.get("repetition_limit", 3)
        self.caps_limit = gconf.get("caps_limit", 70)
        self.add_item(VoltarAntiSpamButton(dono_id))

    def montar_embed(self) -> discord.Embed:
        status = "🟢 Ativado" if self.enabled else "🔴 Desativado"
        
        embed = discord.Embed(
            title="⚠️ CONFIGURAR ANTI-SPAM",
            description="Configure proteção contra mensagens repetidas e flood",
            color=0xE74C3C,
        )
        
        embed.add_field(name="📊 Status", value=status, inline=True)
        embed.add_field(name="🔄 Limite de Repetição", value=f"`{self.repetition_limit}x`", inline=True)
        embed.add_field(name="📝 Limite de CAPS", value=f"`{self.caps_limit}%`", inline=True)
        
        embed.add_field(name="ℹ️ Como Funciona", value=
            "> • Bloqueia a mesma mensagem repetida X vezes\n"
            "> • Detecta textos com CAPS LOCK excessivo\n"
            "> • Aplica timeout automático ao infrator",
            inline=False
        )
        
        embed.set_footer(text="💡 Use os botões abaixo para ajustar os limites")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        embed = self.montar_embed()
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="➕ Repetição", style=discord.ButtonStyle.primary, row=0)
    async def adicionar_rep_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repetition_limit < 10:
            self.repetition_limit += 1
            await self.atualizar(interaction)

    @discord.ui.button(label="➖ Repetição", style=discord.ButtonStyle.primary, row=0)
    async def remover_rep_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repetition_limit > 1:
            self.repetition_limit -= 1
            await self.atualizar(interaction)

    @discord.ui.button(label="➕ CAPS", style=discord.ButtonStyle.primary, row=0)
    async def adicionar_caps_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.caps_limit < 100:
            self.caps_limit += 5
            await self.atualizar(interaction)

    @discord.ui.button(label="➖ CAPS", style=discord.ButtonStyle.primary, row=1)
    async def remover_caps_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.caps_limit > 50:
            self.caps_limit -= 5
            await self.atualizar(interaction)

    @discord.ui.button(label="🟢 Ativar", style=discord.ButtonStyle.success, row=1)
    async def ativar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.enabled = not self.enabled
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["enabled"] = self.enabled
        save_config(config)
        
        await self.atualizar(interaction)

    @discord.ui.button(label="💾 Salvar", style=discord.ButtonStyle.success, row=1)
    async def salvar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["enabled"] = self.enabled
        gconf["repetition_limit"] = self.repetition_limit
        gconf["caps_limit"] = self.caps_limit
        save_config(config)
        
        await interaction.response.send_message("✅ Configuração salva com sucesso!", ephemeral=True)

def abrir_painel_antispam(dono_id: int, guild_id: int) -> tuple[discord.Embed, PainelAntiSpamView]:
    view = PainelAntiSpamView(dono_id, guild_id)
    embed = view.montar_embed()
    return embed, view

class AntiSpam(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_messages = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        config = load_config()
        gconf = get_guild_config(config, message.guild.id)
        
        if not gconf.get("enabled"):
            return
        
        # Verificar repetição
        user_id = message.author.id
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        
        self.user_messages[user_id].append(message.content)
        self.user_messages[user_id] = self.user_messages[user_id][-gconf.get("repetition_limit", 3):]
        
        # Se todas as últimas mensagens são iguais
        if len(self.user_messages[user_id]) == gconf.get("repetition_limit", 3):
            if len(set(self.user_messages[user_id])) == 1:
                try:
                    await message.delete()
                    logger.info(f"Mensagem deletada de {message.author} por spam de repetição")
                except discord.Forbidden:
                    pass
                return
        
        # Verificar CAPS LOCK
        caps_limit = gconf.get("caps_limit", 70)
        if len(message.content) > 5:
            caps_count = sum(1 for c in message.content if c.isupper())
            caps_percentage = (caps_count / len(message.content)) * 100
            
            if caps_percentage > caps_limit:
                try:
                    await message.delete()
                    logger.info(f"Mensagem deletada de {message.author} por excesso de CAPS")
                except discord.Forbidden:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiSpam(bot))
