import discord
from discord import app_commands
from discord.ext import commands
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("bot.logs")
CONFIG_FILE = "config/logs_config.json"

LOG_TYPES = {
    "cargo_add": {"label": "Cargo Adicionado", "emoji": "➕"},
    "cargo_remove": {"label": "Cargo Removido", "emoji": "➖"},
    "canal_criado": {"label": "Canal Criado", "emoji": "📁"},
    "canal_deletado": {"label": "Canal Deletado", "emoji": "🗑️"},
    "msg_deletada": {"label": "Mensagem Deletada", "emoji": "❌"},
    "msg_editada": {"label": "Mensagem Editada", "emoji": "✏️"},
    "membro_banido": {"label": "Membro Banido", "emoji": "🚫"},
    "membro_kickado": {"label": "Membro Removido", "emoji": "👢"},
    "warn_aplicado": {"label": "Aviso Aplicado", "emoji": "⚠️"},
    "timeout_aplicado": {"label": "Timeout Aplicado", "emoji": "⏱️"},
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config de logs: {e}")
    return {}

def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {"canais": {}, "autorizados_usuarios": [], "autorizados_cargos": []}
    else:
        config[gid].setdefault("canais", {})
        config[gid].setdefault("autorizados_usuarios", [])
        config[gid].setdefault("autorizados_cargos", [])
    return config[gid]

class BaseView(discord.ui.View):
    """
    View base usada por todos os menus/botões deste cog.
    Qualquer exceção não tratada em um callback (botão ou select) cai aqui
    em vez de deixar a interação sem resposta até o Discord acusar
    'A interação não respondeu a tempo'.
    """

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        logger.error(f"Erro no componente '{item}' do painel de logs", exc_info=error)
        msg = "❌ Ocorreu um erro ao processar essa ação. Tenta novamente."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

class MembroSelect(discord.ui.UserSelect):
    def __init__(self, adicionar: bool, guild_cfg: dict):
        self.adicionar = adicionar
        super().__init__(placeholder="Pesquise e selecione um membro", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        user = self.values[0]
        config = load_config()
        guild_cfg = get_guild_config(config, interaction.guild_id)
        lista = guild_cfg["autorizados_usuarios"]

        if self.adicionar:
            if user.id not in lista:
                lista.append(user.id)
                desc = f"{user.mention} agora pode configurar logs."
            else:
                desc = f"{user.mention} já tinha permissão."
        else:
            if user.id in lista:
                lista.remove(user.id)
                desc = f"{user.mention} não pode mais configurar logs."
            else:
                desc = f"{user.mention} não estava autorizado."

        save_config(config)
        embed = discord.Embed(title="✅ Atualizado", description=desc, color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CargoSelect(discord.ui.RoleSelect):
    def __init__(self, adicionar: bool, guild_cfg: dict):
        self.adicionar = adicionar
        super().__init__(placeholder="🔍 Digite para filtrar cargos", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        cargo = self.values[0]
        config = load_config()
        guild_cfg = get_guild_config(config, interaction.guild_id)
        lista = guild_cfg["autorizados_cargos"]

        if self.adicionar:
            if cargo.id not in lista:
                lista.append(cargo.id)
                desc = f"Membros com {cargo.mention} agora podem configurar logs."
            else:
                desc = f"{cargo.mention} já tinha permissão."
        else:
            if cargo.id in lista:
                lista.remove(cargo.id)
                desc = f"{cargo.mention} não pode mais configurar logs."
            else:
                desc = f"{cargo.mention} não estava autorizado."

        save_config(config)
        embed = discord.Embed(title="✅ Atualizado", description=desc, color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PermissaoView(BaseView):
    def __init__(self, guild_cfg: dict):
        super().__init__(timeout=120)
        self.guild_cfg = guild_cfg

    @discord.ui.button(label="➕ Autorizar Membro", style=discord.ButtonStyle.success, row=0)
    async def add_membro(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = MembroSelect(True, self.guild_cfg)
        view = BaseView()
        view.add_item(select)
        await interaction.response.send_message("👤 **Selecione um membro:**", view=view, ephemeral=True)

    @discord.ui.button(label="➖ Remover Membro", style=discord.ButtonStyle.danger, row=0)
    async def rem_membro(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = MembroSelect(False, self.guild_cfg)
        view = BaseView()
        view.add_item(select)
        await interaction.response.send_message("👤 **Selecione um membro:**", view=view, ephemeral=True)

    @discord.ui.button(label="➕ Autorizar Cargo", style=discord.ButtonStyle.success, row=1)
    async def add_cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = CargoSelect(True, self.guild_cfg)
        view = BaseView()
        view.add_item(select)
        await interaction.response.send_message("🏷️ **Selecione um cargo:**", view=view, ephemeral=True)

    @discord.ui.button(label="➖ Remover Cargo", style=discord.ButtonStyle.danger, row=1)
    async def rem_cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = CargoSelect(False, self.guild_cfg)
        view = BaseView()
        view.add_item(select)
        await interaction.response.send_message("🏷️ **Selecione um cargo:**", view=view, ephemeral=True)

class TipoLogSelect(discord.ui.Select):
    def __init__(self, canal_id: int):
        self.canal_id = canal_id
        opcoes = [discord.SelectOption(label=info["label"], emoji=info["emoji"], value=tipo) for tipo, info in LOG_TYPES.items()]
        super().__init__(placeholder="Selecione os tipos de log", options=opcoes, min_values=1, max_values=len(opcoes))

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        for tipo in self.values:
            gconf["canais"][tipo] = self.canal_id
        save_config(config)
        embed = discord.Embed(title="✅ Logs Configurados", description=f"<#{self.canal_id}> receberá {len(self.values)} tipos de eventos.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class TipoLogSelectView(BaseView):
    def __init__(self, canal_id: int):
        super().__init__(timeout=120)
        self.add_item(TipoLogSelect(canal_id))

class CanalSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="🔍 Digite para filtrar canais",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        canal_id = self.values[0].id
        canal = interaction.guild.get_channel(canal_id)

        if canal is not None and not canal.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                "❌ Não tenho permissão para enviar mensagens nesse canal. Escolha outro.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📋 Selecione os Tipos de Log",
            description=f"Canal: <#{canal_id}>\nEscolha quais eventos serão enviados para esse canal.",
            color=discord.Color.purple(),
        )
        await interaction.response.send_message(embed=embed, view=TipoLogSelectView(canal_id), ephemeral=True)

class CanalSelectView(BaseView):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(CanalSelect())

class RemoverLogSelect(discord.ui.Select):
    def __init__(self, guild_cfg: dict):
        opcoes = []
        for tipo, canal_id in guild_cfg["canais"].items():
            info = LOG_TYPES.get(tipo)
            if not info:
                continue
            opcoes.append(
                discord.SelectOption(label=f"{info['label']}"[:100], value=tipo, emoji=info["emoji"])
            )

        super().__init__(
            placeholder="Selecione os tipos para remover",
            options=opcoes,
            min_values=1,
            max_values=len(opcoes),
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        for tipo in self.values:
            if tipo in gconf["canais"]:
                del gconf["canais"][tipo]
        save_config(config)
        embed = discord.Embed(
            title="✅ Removido",
            description=f"{len(self.values)} tipo(s) de log foram removidos.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RemoverLogView(BaseView):
    def __init__(self, guild_cfg: dict):
        super().__init__(timeout=120)
        self.add_item(RemoverLogSelect(guild_cfg))

class LogsView(BaseView):
    def __init__(self, guild: discord.Guild, dono_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.dono_id = dono_id
        self.guild_cfg = get_guild_config(load_config(), guild.id)

        botao = discord.ui.Button(label="◀️ Voltar ao Menu", style=discord.ButtonStyle.secondary, row=1)
        async def voltar_callback(interaction: discord.Interaction):
            from cogs.configuracoes import PainelConfiguracoesView
            view = PainelConfiguracoesView(self.dono_id)
            await interaction.response.edit_message(embed=view.texto_painel(), view=view)
        botao.callback = voltar_callback
        self.add_item(botao)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="📋 Configurar Canal", style=discord.ButtonStyle.primary, row=0)
    async def configurar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📌 Selecione um Canal",
            description="Escolha o canal onde os logs serão enviados.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, view=CanalSelectView(), ephemeral=True)

    @discord.ui.button(label="🗑️ Remover Log", style=discord.ButtonStyle.danger, row=0)
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.guild_cfg["canais"]:
            await interaction.response.send_message("❌ Nenhum log configurado.", ephemeral=True)
            return
        embed = discord.Embed(title="🗑️ Remover Logs", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, view=RemoverLogView(self.guild_cfg), ephemeral=True)

    @discord.ui.button(label="🔐 Permissões", style=discord.ButtonStyle.secondary, row=0)
    async def permissoes(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🔐 Gerenciar Permissões", description="Escolha quem pode configurar logs.", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, view=PermissaoView(self.guild_cfg), ephemeral=True)

    @discord.ui.button(label="📊 Ver Configurações", style=discord.ButtonStyle.secondary, row=1)
    async def ver(self, interaction: discord.Interaction, button: discord.ui.Button):
        canais_txt = "\n".join([f"> <#{cid}>" for cid in set(self.guild_cfg["canais"].values())]) or "> Nenhum"
        embed = discord.Embed(title="📊 Configurações de Logs", color=discord.Color.blurple())
        embed.add_field(name="📺 Canais Configurados", value=canais_txt, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="logs", description="Configurar sistema de logs do servidor")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def logs_cmd(self, interaction: discord.Interaction):
        view = LogsView(interaction.guild, interaction.user.id)
        embed = discord.Embed(title="🧾 Logs do Servidor", description="Escolha o que você quer fazer abaixo.", color=0xFAA61A)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Logs(bot))
