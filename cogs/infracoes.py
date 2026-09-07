import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging

logger = logging.getLogger("bot.infracoes")
CONFIG_FILE = "config/moderacao_config.json"
INFRACTIONS_FILE = "config/infractions.json"

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
        config[gid] = {"infracoes": {"enabled": False, "escalacao": []}}
    if "infracoes" not in config[gid]:
        config[gid]["infracoes"] = {"enabled": False, "escalacao": []}
    return config[gid]["infracoes"]

class VoltarInfracoesButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.moderacao import abrir_painel_moderacao
        embed, view = abrir_painel_moderacao(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

class PainelInfracoesView(discord.ui.View):
    def __init__(self, dono_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.guild_id = guild_id
        
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        self.enabled = gconf.get("enabled", False)
        self.add_item(VoltarInfracoesButton(dono_id))

    def montar_embed(self) -> discord.Embed:
        status = "🟢 Ativado" if self.enabled else "🔴 Desativado"
        
        embed = discord.Embed(
            title="📋 SISTEMA DE INFRAÇÕES",
            description="Configure níveis de punição automática para infrações",
            color=0x7289DA,
        )
        
        embed.add_field(name="📊 Status", value=status, inline=True)
        embed.add_field(name="⚠️ Warn Automático", value="`Habilitado`", inline=True)
        embed.add_field(name="　", value="　", inline=True)
        
        embed.add_field(name="📈 Escalonamento de Punições", value=
            "> 1ª infração → Aviso\n"
            "> 2ª → Timeout 5min\n"
            "> 3ª → Timeout 1h\n"
            "> 4ª → Kick\n"
            "> 5ª → Ban permanente",
            inline=False
        )
        
        embed.set_footer(text="💡 Use o botão abaixo para ativar o sistema")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        embed = self.montar_embed()
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="🟢 Ativar Warn Automático", style=discord.ButtonStyle.success, row=0)
    async def ativar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.enabled = not self.enabled
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["enabled"] = self.enabled
        save_config(config)
        
        await self.atualizar(interaction)
        status = "✅ Ativado" if self.enabled else "❌ Desativado"
        await interaction.followup.send(f"{status} warn automático para infrações!", ephemeral=True)

    @discord.ui.button(label="💾 Salvar", style=discord.ButtonStyle.success, row=0)
    async def salvar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["enabled"] = self.enabled
        save_config(config)
        
        await interaction.response.send_message("✅ Configuração salva com sucesso!", ephemeral=True)

def abrir_painel_infracoes(dono_id: int, guild_id: int) -> tuple[discord.Embed, PainelInfracoesView]:
    view = PainelInfracoesView(dono_id, guild_id)
    embed = view.montar_embed()
    return embed, view

class Infracoes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(Infracoes(bot))
