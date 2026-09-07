import discord
from discord import app_commands
from discord.ext import commands
import json
import logging
import os

logger = logging.getLogger("bot.autocargo")
CONFIG_FILE = "config/autocargo_config.json"

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config de auto cargo, recriando: {e}")
    return {}

def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {"enabled": False, "cargos": []}
    return config[gid]

def montar_embed_autocargo(guild: discord.Guild, cargos_selecionados: set) -> discord.Embed:
    config = load_config()
    gconf = get_guild_config(config, guild.id)
    status = "🟢 Ativado" if gconf.get("enabled") else "🔴 Desativado"
    
    embed = discord.Embed(
        title="🎯 CONFIGURAR AUTO CARGO",
        description="Selecione quais cargos serão distribuídos automaticamente a novos membros",
        color=0x43B581,
    )
    
    embed.add_field(name="📊 Status", value=status, inline=True)
    embed.add_field(name="🏷️ Cargos Selecionados", value=f"`{len(cargos_selecionados)}`", inline=True)
    embed.add_field(name="　", value="　", inline=True)
    
    if cargos_selecionados:
        cargo_names = []
        for cargo_id in cargos_selecionados:
            cargo = guild.get_role(cargo_id)
            if cargo:
                cargo_names.append(f"> <@&{cargo_id}>")
        if cargo_names:
            embed.add_field(name="✅ Cargos Ativos", value="\n".join(cargo_names), inline=False)
    else:
        embed.add_field(name="✅ Cargos Ativos", value="> `Nenhum cargo selecionado`", inline=False)
    
    embed.set_footer(text="💡 Use o dropdown abaixo para selecionar os cargos desejados")
    return embed

class VoltarParaConfigButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.configuracoes import PainelConfiguracoesView
        view = PainelConfiguracoesView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)

class SelecionarCargosView(discord.ui.View):
    def __init__(self, dono_id: int, guild: discord.Guild):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.guild = guild
        
        config = load_config()
        gconf = get_guild_config(config, guild.id)
        self.cargos_selecionados = set(gconf.get("cargos", []))
        
        self.add_item(SelecionadorDeCargos(self))
        self.add_item(SalvarCargosButton(self))
        self.add_item(AtivarCargosButton(self))
        self.add_item(VoltarParaConfigButton(dono_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True)
            return False
        return True

    async def atualizar(self, interaction: discord.Interaction):
        embed = montar_embed_autocargo(self.guild, self.cargos_selecionados)
        await interaction.response.edit_message(embed=embed)

class SelecionadorDeCargos(discord.ui.RoleSelect):
    def __init__(self, parent_view: SelecionarCargosView):
        super().__init__(placeholder="🔍 Selecione os cargos automáticos", min_values=0, max_values=25)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.cargos_selecionados = {role.id for role in self.values}
        await self.parent_view.atualizar(interaction)

class SalvarCargosButton(discord.ui.Button):
    def __init__(self, parent_view: SelecionarCargosView):
        super().__init__(label="💾 Salvar", style=discord.ButtonStyle.success, row=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, self.parent_view.guild.id)
        gconf["cargos"] = list(self.parent_view.cargos_selecionados)
        save_config(config)
        
        await self.parent_view.atualizar(interaction)
        await interaction.followup.send("✅ Cargos salvos com sucesso!", ephemeral=True)

class AtivarCargosButton(discord.ui.Button):
    def __init__(self, parent_view: SelecionarCargosView):
        super().__init__(label="🟢 Ativar", style=discord.ButtonStyle.success, row=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, self.parent_view.guild.id)
        
        if not gconf.get("enabled") and not self.parent_view.cargos_selecionados:
            await interaction.response.send_message("❌ Selecione pelo menos um cargo antes de ativar.", ephemeral=True)
            return
        
        gconf["enabled"] = not gconf.get("enabled")
        save_config(config)
        
        await self.parent_view.atualizar(interaction)

def abrir_painel_autocargo(dono_id: int, guild: discord.Guild) -> tuple[discord.Embed, SelecionarCargosView]:
    view = SelecionarCargosView(dono_id, guild)
    embed = montar_embed_autocargo(guild, view.cargos_selecionados)
    return embed, view

class AutoCargo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = load_config()
        gconf = get_guild_config(config, member.guild.id)
        
        if not gconf.get("enabled") or not gconf.get("cargos"):
            return
        
        for cargo_id in gconf.get("cargos", []):
            cargo = member.guild.get_role(cargo_id)
            if cargo:
                try:
                    await member.add_roles(cargo)
                    logger.info(f"✅ Cargo '{cargo.name}' dado a {member}")
                except discord.Forbidden:
                    logger.warning(f"⚠️ Sem permissão para dar cargo '{cargo.name}'")
                except Exception as e:
                    logger.error(f"❌ Erro ao dar cargo: {e}", exc_info=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoCargo(bot))
