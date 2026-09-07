import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import re
import logging
from cogs._utils_select import RoleSelectComAutocomplete

logger = logging.getLogger("bot.antilink")
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
        config[gid] = {"antilink": {"enabled": False, "allowed_roles": [], "allowed_bot_roles": [], "message": "Convites de outros servidores não são permitidos aqui sem permissão."}}
    if "antilink" not in config[gid]:
        config[gid]["antilink"] = {"enabled": False, "allowed_roles": [], "allowed_bot_roles": [], "message": "Convites de outros servidores não são permitidos aqui sem permissão."}
    return config[gid]["antilink"]

class VoltarAntiLinkButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.moderacao import abrir_painel_moderacao
        embed, view = abrir_painel_moderacao(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

class PainelAntiLinkView(discord.ui.View):
    def __init__(self, dono_id: int, guild: discord.Guild, guild_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.guild = guild
        self.guild_id = guild_id
        
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        self.allowed_roles = set(gconf.get("allowed_roles", []))
        self.allowed_bot_roles = set(gconf.get("allowed_bot_roles", []))
        self.enabled = gconf.get("enabled", False)
        self.message = gconf.get("message", "Convites de outros servidores não são permitidos aqui sem permissão.")
        self.add_item(VoltarAntiLinkButton(dono_id))

    def montar_embed(self) -> discord.Embed:
        status = "🟢 Ativado" if self.enabled else "🔴 Desativado"
        
        embed = discord.Embed(
            title="🔗 CONFIGURAR ANTI-LINK DE SERVIDORES",
            description="Configure cargos que podem enviar convites de outros Discord",
            color=0xE74C3C,
        )
        
        embed.add_field(name="📊 Status", value=status, inline=True)
        embed.add_field(name="👥 Cargos Permitidos (Membros)", value=f"`{len(self.allowed_roles)}`", inline=True)
        embed.add_field(name="🤖 Cargos Permitidos (Bots)", value=f"`{len(self.allowed_bot_roles)}`", inline=True)
        
        if self.allowed_roles:
            role_names = []
            for rid in self.allowed_roles:
                role = self.guild.get_role(rid)
                if role:
                    role_names.append(f"> <@&{rid}>")
            if role_names:
                embed.add_field(name="👥 Cargos com Permissão (Membros)", value="\n".join(role_names[:5]), inline=False)
        
        if self.allowed_bot_roles:
            bot_role_names = []
            for rid in self.allowed_bot_roles:
                role = self.guild.get_role(rid)
                if role:
                    bot_role_names.append(f"> <@&{rid}>")
            if bot_role_names:
                embed.add_field(name="🤖 Cargos com Permissão (Bots)", value="\n".join(bot_role_names[:5]), inline=False)
        
        embed.add_field(name="🤖 Bot Zyntrax", value="> ✅ Sempre permitido (automático)", inline=False)
        embed.add_field(name="📝 Mensagem de Aviso", value=f"> \"{self.message}\"", inline=False)
        embed.set_footer(text="💡 Use os botões abaixo para configurar quem pode enviar convites")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        embed = self.montar_embed()
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="👥 Cargos (Membros)", style=discord.ButtonStyle.primary, row=0)
    async def membros_roles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def callback(inter: discord.Interaction, role_id: int):
            if role_id in self.allowed_roles:
                self.allowed_roles.remove(role_id)
            else:
                self.allowed_roles.add(role_id)
            embed = self.montar_embed()
            await inter.response.edit_message(embed=embed)
        
        select = RoleSelectComAutocomplete(callback)
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("👥 **Selecione cargos de MEMBROS que podem enviar convites:**\n*(Digite o nome do cargo para filtrar)*", view=view, ephemeral=True)

    @discord.ui.button(label="🤖 Cargos (Bots)", style=discord.ButtonStyle.primary, row=0)
    async def bots_roles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def callback(inter: discord.Interaction, role_id: int):
            if role_id in self.allowed_bot_roles:
                self.allowed_bot_roles.remove(role_id)
            else:
                self.allowed_bot_roles.add(role_id)
            embed = self.montar_embed()
            await inter.response.edit_message(embed=embed)
        
        select = RoleSelectComAutocomplete(callback)
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("🤖 **Selecione cargos de BOTS que podem enviar convites:**\n*(Digite o nome do cargo para filtrar)*", view=view, ephemeral=True)

    @discord.ui.button(label="🟢 Ativar", style=discord.ButtonStyle.success, row=0)
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
        gconf["allowed_roles"] = list(self.allowed_roles)
        gconf["allowed_bot_roles"] = list(self.allowed_bot_roles)
        gconf["enabled"] = self.enabled
        gconf["message"] = self.message
        save_config(config)
        await interaction.response.send_message("✅ Configuração salva com sucesso!", ephemeral=True)

def abrir_painel_antilink(dono_id: int, guild: discord.Guild, guild_id: int) -> tuple[discord.Embed, PainelAntiLinkView]:
    view = PainelAntiLinkView(dono_id, guild, guild_id)
    embed = view.montar_embed()
    return embed, view

class AntiLink(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.invite_pattern = re.compile(r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9-]+)')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        config = load_config()
        gconf = get_guild_config(config, message.guild.id)
        
        if not gconf.get("enabled"):
            return
        
        if message.author.id == self.bot.user.id:
            return
        
        if message.author.bot is False:
            for role_id in gconf.get("allowed_roles", []):
                if message.author.get_role(role_id):
                    return
        
        if message.author.bot is True:
            for role_id in gconf.get("allowed_bot_roles", []):
                if message.author.get_role(role_id):
                    return
        
        matches = self.invite_pattern.findall(message.content)
        if not matches:
            return
        
        for code in matches:
            try:
                invite = await self.bot.fetch_invite(code)
                if invite.guild.id == message.guild.id:
                    continue
                
                await message.delete()
                msg = gconf.get("message", "Convites de outros servidores não são permitidos aqui sem permissão.")
                await message.author.send(f"⚠️ {msg}")
                logger.info(f"Mensagem deletada de {message.author} por conter convite de outro servidor")
                return
            except discord.NotFound:
                await message.delete()
                msg = gconf.get("message", "Convites de outros servidores não são permitidos aqui sem permissão.")
                await message.author.send(f"⚠️ {msg}")
                return

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiLink(bot))
