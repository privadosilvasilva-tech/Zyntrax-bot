import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("bot.antiraid")
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
        config[gid] = {"antiraid": {"enabled": False, "join_limit": 5, "time_window": 10}}
    if "antiraid" not in config[gid]:
        config[gid]["antiraid"] = {"enabled": False, "join_limit": 5, "time_window": 10}
    return config[gid]["antiraid"]

class VoltarAntiRaidButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.moderacao import abrir_painel_moderacao
        embed, view = abrir_painel_moderacao(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

class PainelAntiRaidView(discord.ui.View):
    def __init__(self, dono_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.guild_id = guild_id
        
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        self.enabled = gconf.get("enabled", False)
        self.join_limit = gconf.get("join_limit", 5)
        self.time_window = gconf.get("time_window", 10)
        self.add_item(VoltarAntiRaidButton(dono_id))

    def montar_embed(self) -> discord.Embed:
        status = "🟢 Ativado" if self.enabled else "🔴 Desativado"
        
        embed = discord.Embed(
            title="🚨 CONFIGURAR ANTI-RAID",
            description="Bloqueie entradas suspeitas em massa e ataques coordenados",
            color=0xE74C3C,
        )
        
        embed.add_field(name="📊 Status", value=status, inline=True)
        embed.add_field(name="👥 Limite de Joins", value=f"`{self.join_limit}`", inline=True)
        embed.add_field(name="⏱️ Janela de Tempo", value=f"`{self.time_window}s`", inline=True)
        
        embed.add_field(name="🛡️ Configuração Atual", value=
            f"> Se mais de **{self.join_limit}** usuários entram em **{self.time_window}s**\n"
            "> Sistema ativa automaticamente:\n"
            "> • Slowmode no servidor\n"
            "> • Aviso para moderadores\n"
            "> • Restrição de novos membros",
            inline=False
        )
        
        embed.set_footer(text="💡 Use os botões abaixo para ajustar os limites")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        embed = self.montar_embed()
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="➕ Joins", style=discord.ButtonStyle.primary, row=0)
    async def adicionar_joins_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.join_limit < 50:
            self.join_limit += 1
            await self.atualizar(interaction)

    @discord.ui.button(label="➖ Joins", style=discord.ButtonStyle.primary, row=0)
    async def remover_joins_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.join_limit > 1:
            self.join_limit -= 1
            await self.atualizar(interaction)

    @discord.ui.button(label="➕ Tempo", style=discord.ButtonStyle.primary, row=0)
    async def adicionar_tempo_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.time_window < 60:
            self.time_window += 1
            await self.atualizar(interaction)

    @discord.ui.button(label="➖ Tempo", style=discord.ButtonStyle.primary, row=1)
    async def remover_tempo_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.time_window > 1:
            self.time_window -= 1
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
        gconf["join_limit"] = self.join_limit
        gconf["time_window"] = self.time_window
        save_config(config)
        
        await interaction.response.send_message("✅ Configuração salva com sucesso!", ephemeral=True)

def abrir_painel_antiraid(dono_id: int, guild_id: int) -> tuple[discord.Embed, PainelAntiRaidView]:
    view = PainelAntiRaidView(dono_id, guild_id)
    embed = view.montar_embed()
    return embed, view

class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.join_tracker = {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = load_config()
        gconf = get_guild_config(config, member.guild.id)
        
        if not gconf.get("enabled"):
            return
        
        guild_id = member.guild.id
        now = datetime.now()
        
        if guild_id not in self.join_tracker:
            self.join_tracker[guild_id] = []
        
        self.join_tracker[guild_id].append(now)
        
        # Limpar entradas antigas
        time_limit = now - timedelta(seconds=gconf.get("time_window", 10))
        self.join_tracker[guild_id] = [t for t in self.join_tracker[guild_id] if t > time_limit]
        
        # Verificar limite
        if len(self.join_tracker[guild_id]) >= gconf.get("join_limit", 5):
            logger.warning(f"🚨 Possível raid detectada em {member.guild.name}")
            
            # Ativar slowmode
            for channel in member.guild.text_channels:
                try:
                    await channel.edit(slowmode_delay=5)
                except discord.Forbidden:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaid(bot))
