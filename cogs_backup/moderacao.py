import discord
from discord import app_commands
from discord.ext import commands
import json
import os

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
        config[gid] = {
            "filtro_palavras": {"enabled": False, "palavras": [], "aviso": "Essa palavra não é permitida aqui."},
            "antilink": {"enabled": False, "allowed_members": [], "allowed_bots": [], "message": "Convites de outros servidores não são permitidos aqui sem permissão."},
            "antispam": {"enabled": False, "repetition_limit": 3, "caps_limit": 70},
            "antiraid": {"enabled": False, "join_limit": 5, "time_window": 10},
            "infracoes": {"enabled": False, "escalacao": []},
            "logs": {"enabled": False, "channel_id": None}
        }
    return config[gid]

# ─────────────────────────────────────────────────────────────────
# PAINEL MODERAÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────

class VoltarModeracaoButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.configuracoes import PainelConfiguracoesView
        view = PainelConfiguracoesView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)

class PainelModeracaoView(discord.ui.View):
    def __init__(self, dono_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.add_item(VoltarModeracaoButton(dono_id))

    def montar_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🛡️ MODERAÇÃO E SEGURANÇA",
            description="Configure sistemas de proteção e moderação automática do servidor",
            color=0xE74C3C,
        )
        
        embed.add_field(
            name="⚠️ FILTROS E CONTEÚDO",
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False
        )
        
        embed.add_field(
            name="🚫 Filtro de Palavras",
            value="> Bloqueie palavras personalizadas (sem limite)\n> Configure ações automáticas",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Anti-Link de Servidores",
            value="> Bloqueie convites de outros Discord\n> Configure quem pode enviar",
            inline=False
        )
        
        embed.add_field(
            name="🔐 PROTEÇÃO CONTRA ATAQUES",
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Anti-Spam",
            value="> Detecte mensagens repetidas e flood\n> Configure limites e punições",
            inline=False
        )
        
        embed.add_field(
            name="🚨 Anti-Raid",
            value="> Bloqueie entradas suspeitas em massa\n> Ative proteção automática",
            inline=False
        )
        
        embed.add_field(
            name="📋 INFRAÇÕES E HISTÓRICO",
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False
        )
        
        embed.add_field(
            name="📋 Sistema de Infrações",
            value="> Configure níveis de punição\n> Ativar warn automático",
            inline=False
        )
        
        embed.add_field(
            name="📊 Logs de Moderação",
            value="> Canal para registrar ações\n> O que deve ser registrado",
            inline=False
        )
        
        embed.set_footer(text="💡 Clique nos botões abaixo para configurar")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="🚫 Filtro Palavras", style=discord.ButtonStyle.danger, row=0)
    async def filtro_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.filtro_palavras import abrir_painel_filtro
        embed, view = abrir_painel_filtro(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔗 Anti-Link", style=discord.ButtonStyle.danger, row=0)
    async def antilink_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.antilink import abrir_painel_antilink
        embed, view = abrir_painel_antilink(self.dono_id, interaction.guild, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚠️ Anti-Spam", style=discord.ButtonStyle.danger, row=0)
    async def antispam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.antispam import abrir_painel_antispam
        embed, view = abrir_painel_antispam(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🚨 Anti-Raid", style=discord.ButtonStyle.danger, row=1)
    async def antiraid_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.antiraid import abrir_painel_antiraid
        embed, view = abrir_painel_antiraid(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📋 Infrações", style=discord.ButtonStyle.primary, row=1)
    async def infracoes_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.infracoes import abrir_painel_infracoes
        embed, view = abrir_painel_infracoes(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📊 Logs Mod", style=discord.ButtonStyle.secondary, row=1)
    async def logs_mod_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.logs_moderacao import abrir_painel_logs_mod
        embed, view = abrir_painel_logs_mod(self.dono_id, interaction.guild, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

def abrir_painel_moderacao(dono_id: int, guild_id: int) -> tuple[discord.Embed, PainelModeracaoView]:
    view = PainelModeracaoView(dono_id)
    embed = view.montar_embed()
    return embed, view

class Moderacao(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderacao(bot))
