import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging

logger = logging.getLogger("bot.logs_moderacao")
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
        config[gid] = {"logs": {"enabled": False, "channel_id": None}}
    if "logs" not in config[gid]:
        config[gid]["logs"] = {"enabled": False, "channel_id": None}
    return config[gid]["logs"]

class VoltarLogsModButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.moderacao import abrir_painel_moderacao
        embed, view = abrir_painel_moderacao(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

class PainelLogsModView(discord.ui.View):
    def __init__(self, dono_id: int, guild: discord.Guild, guild_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.guild = guild
        self.guild_id = guild_id
        
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        self.enabled = gconf.get("enabled", False)
        self.channel_id = gconf.get("channel_id", None)
        self.add_item(VoltarLogsModButton(dono_id))

    def montar_embed(self) -> discord.Embed:
        status = "🟢 Ativado" if self.enabled else "🔴 Desativado"
        channel_info = "Não configurado"
        
        if self.channel_id:
            channel = self.guild.get_channel(self.channel_id)
            if channel:
                channel_info = channel.mention
        
        embed = discord.Embed(
            title="📊 LOGS DE MODERAÇÃO",
            description="Configure o registro de ações de moderação do servidor",
            color=0x7289DA,
        )
        
        embed.add_field(name="📊 Status", value=status, inline=True)
        embed.add_field(name="📝 Canal", value=channel_info, inline=True)
        embed.add_field(name="　", value="　", inline=True)
        
        embed.add_field(name="📋 Eventos Registrados", value=
            "> ✅ Aviso (Warn)\n"
            "> ✅ Timeout\n"
            "> ✅ Kick\n"
            "> ✅ Ban\n"
            "> ✅ Mensagens deletadas\n"
            "> ✅ Links bloqueados\n"
            "> ✅ Spam detectado",
            inline=False
        )
        
        embed.set_footer(text="💡 Use os botões abaixo para configurar os logs")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        embed = self.montar_embed()
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="📝 Selecionar Canal", style=discord.ButtonStyle.primary, row=0)
    async def canal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        channels = [ch for ch in self.guild.text_channels]
        options = [discord.SelectOption(label=ch.name[:100], value=str(ch.id)) for ch in channels[:25]]
        
        select = discord.ui.Select(
            placeholder="Selecione o canal para logs",
            options=options
        )
        
        async def select_callback(interaction: discord.Interaction):
            self.channel_id = int(select.values[0])
            await self.atualizar(interaction)
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("Escolha o canal para registrar logs:", view=view, ephemeral=True)

    @discord.ui.button(label="🟢 Ativar", style=discord.ButtonStyle.success, row=0)
    async def ativar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.channel_id:
            await interaction.response.send_message("❌ Selecione um canal primeiro!", ephemeral=True)
            return
        
        self.enabled = not self.enabled
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["enabled"] = self.enabled
        gconf["channel_id"] = self.channel_id
        save_config(config)
        
        await self.atualizar(interaction)

    @discord.ui.button(label="💾 Salvar", style=discord.ButtonStyle.success, row=1)
    async def salvar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["enabled"] = self.enabled
        gconf["channel_id"] = self.channel_id
        save_config(config)
        
        await interaction.response.send_message("✅ Configuração salva com sucesso!", ephemeral=True)

def abrir_painel_logs_mod(dono_id: int, guild: discord.Guild, guild_id: int) -> tuple[discord.Embed, PainelLogsModView]:
    view = PainelLogsModView(dono_id, guild, guild_id)
    embed = view.montar_embed()
    return embed, view

class LogsMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(LogsMod(bot))
