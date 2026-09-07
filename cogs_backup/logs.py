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
    "deletadas": {"label": "Mensagens Deletadas", "emoji": "🗑️"},
    "editadas": {"label": "Mensagens Editadas", "emoji": "✏️"},
    "entradas": {"label": "Membros Entram", "emoji": "📥"},
    "saidas": {"label": "Membros Saem", "emoji": "📤"},
    "banidos": {"label": "Membros Banidos", "emoji": "⛔"},
    "desbanidos": {"label": "Membros Desbanidos", "emoji": "♻️"},
    "cargo_add": {"label": "Cargo Adicionado", "emoji": "➕"},
    "cargo_remove": {"label": "Cargo Removido", "emoji": "➖"},
    "canal_criado": {"label": "Canal Criado", "emoji": "📁"},
    "canal_deletado": {"label": "Canal Deletado", "emoji": "🗑️"},
    "voz": {"label": "Atividade de Voz", "emoji": "🔊"},
    "apelido": {"label": "Apelido Alterado", "emoji": "📝"},
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config, recriando: {e}")
    return {}


def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def default_guild_config() -> dict:
    return {"canais": {}, "autorizados_usuarios": [], "autorizados_cargos": []}


def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = default_guild_config()
    else:
        config[gid].setdefault("canais", {})
        config[gid].setdefault("autorizados_usuarios", [])
        config[gid].setdefault("autorizados_cargos", [])
    return config[gid]


def tem_permissao(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    if interaction.user.id == interaction.guild.owner_id:
        return True
    if interaction.user.guild_permissions.administrator:
        return True

    config = load_config()
    guild_cfg = config.get(str(interaction.guild_id), {})

    if interaction.user.id in guild_cfg.get("autorizados_usuarios", []):
        return True

    cargos_autorizados = set(guild_cfg.get("autorizados_cargos", []))
    user_role_ids = {r.id for r in interaction.user.roles}
    if cargos_autorizados & user_role_ids:
        return True

    return False


# ---------------------- BASE COM TRATAMENTO DE ERRO ----------------------

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


# ---------------------- MODAIS ----------------------

class AutorizarMembroModal(discord.ui.Modal):
    membro_id = discord.ui.TextInput(
        label="ID ou menção do membro",
        placeholder="123456789012345678 ou @usuario",
        required=True,
        max_length=32,
    )

    def __init__(self, remover: bool = False):
        super().__init__(title="Remover Autorização" if remover else "Autorizar Membro")
        self.remover = remover

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.membro_id.value.strip().lstrip("<@!").rstrip(">")
        if not raw.isdigit():
            await interaction.response.send_message(
                "❌ ID inválido. Envie apenas o ID numérico ou marque o usuário.", ephemeral=True
            )
            return

        user_id = int(raw)
        config = load_config()
        guild_cfg = get_guild_config(config, interaction.guild_id)
        lista = guild_cfg["autorizados_usuarios"]

        membro = interaction.guild.get_member(user_id)
        referencia = membro.mention if membro else f"`{user_id}`"

        if self.remover:
            if user_id in lista:
                lista.remove(user_id)
                save_config(config)
                desc = f"{referencia} não pode mais configurar logs."
                cor = discord.Color.orange()
            else:
                desc = f"{referencia} não estava autorizado."
                cor = discord.Color.yellow()
        else:
            if user_id not in lista:
                lista.append(user_id)
                save_config(config)
                desc = f"{referencia} agora pode configurar logs."
                cor = discord.Color.green()
            else:
                desc = f"{referencia} já tinha permissão."
                cor = discord.Color.yellow()

        embed = discord.Embed(description=desc, color=cor)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logger.error("Erro no modal de autorização", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Ocorreu um erro ao processar.", ephemeral=True)


# ---------------------- SELECTS DE CARGO ----------------------

class CargoSelect(discord.ui.RoleSelect):
    def __init__(self, remover: bool = False):
        self.remover = remover
        placeholder = "Selecione o cargo a remover" if remover else "Selecione o cargo a autorizar"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        cargo = self.values[0]
        config = load_config()
        guild_cfg = get_guild_config(config, interaction.guild_id)
        lista = guild_cfg["autorizados_cargos"]

        if self.remover:
            if cargo.id in lista:
                lista.remove(cargo.id)
                save_config(config)
                desc = f"{cargo.mention} não autoriza mais configurar logs."
                cor = discord.Color.orange()
            else:
                desc = f"{cargo.mention} não estava autorizado."
                cor = discord.Color.yellow()
        else:
            if cargo.id not in lista:
                lista.append(cargo.id)
                save_config(config)
                desc = f"Membros com {cargo.mention} agora podem configurar logs."
                cor = discord.Color.green()
            else:
                desc = f"{cargo.mention} já tinha permissão."
                cor = discord.Color.yellow()

        embed = discord.Embed(description=desc, color=cor)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CargoSelectView(BaseView):
    def __init__(self, remover: bool = False):
        super().__init__(timeout=120)
        self.add_item(CargoSelect(remover))


# ---------------------- PAINEL DE PERMISSÕES ----------------------

class PermissoesView(BaseView):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="➕ Autorizar Membro", style=discord.ButtonStyle.success, row=0)
    async def add_membro(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AutorizarMembroModal(remover=False))

    @discord.ui.button(label="➖ Remover Membro", style=discord.ButtonStyle.danger, row=0)
    async def rem_membro(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AutorizarMembroModal(remover=True))

    @discord.ui.button(label="➕ Autorizar Cargo", style=discord.ButtonStyle.success, row=1)
    async def add_cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(description="Selecione o cargo a autorizar:", color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, view=CargoSelectView(remover=False), ephemeral=True)

    @discord.ui.button(label="➖ Remover Cargo", style=discord.ButtonStyle.danger, row=1)
    async def rem_cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(description="Selecione o cargo a remover:", color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, view=CargoSelectView(remover=True), ephemeral=True)


# ---------------------- CONFIGURAR CANAL / TIPOS ----------------------

class TipoLogSelect(discord.ui.Select):
    def __init__(self, canal_id: int):
        self.canal_id = canal_id
        opcoes = [
            discord.SelectOption(label=info["label"], value=chave, emoji=info["emoji"])
            for chave, info in LOG_TYPES.items()
        ]
        super().__init__(
            placeholder="Selecione um ou mais tipos de log",
            options=opcoes,
            min_values=1,
            max_values=len(opcoes),
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        guild_cfg = get_guild_config(config, interaction.guild_id)
        for tipo in self.values:
            guild_cfg["canais"][tipo] = self.canal_id
        save_config(config)

        tipos_texto = "\n".join(f"{LOG_TYPES[t]['emoji']} {LOG_TYPES[t]['label']}" for t in self.values)
        embed = discord.Embed(
            title="✅ Log Configurado",
            description=f"Canal: <#{self.canal_id}>",
            color=discord.Color.green(),
        )
        embed.add_field(name="Tipos ativados", value=tipos_texto, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class TipoLogSelectView(BaseView):
    def __init__(self, canal_id: int):
        super().__init__(timeout=120)
        self.add_item(TipoLogSelect(canal_id))


class CanalSelect(discord.ui.ChannelSelect):
    """
    Usa o componente nativo de seleção de canal do Discord: o próprio cliente
    exibe uma busca em tempo real por nome, sem limite de 25 canais imposto
    por nós (diferente de um discord.ui.Select comum com opções fixas).
    """

    def __init__(self):
        super().__init__(
            placeholder="Pesquise e selecione o canal de destino",
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


# ---------------------- REMOVER LOG ----------------------

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
        guild_cfg = get_guild_config(config, interaction.guild_id)
        removidos = []
        for tipo in self.values:
            if tipo in guild_cfg["canais"]:
                del guild_cfg["canais"][tipo]
                removidos.append(LOG_TYPES[tipo]["label"])
        save_config(config)

        desc = "\n".join(f"• {r}" for r in removidos) if removidos else "Nenhum tipo removido."
        embed = discord.Embed(title="🗑️ Logs Removidos", description=desc, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RemoverLogView(BaseView):
    def __init__(self, guild_cfg: dict):
        super().__init__(timeout=120)
        self.add_item(RemoverLogSelect(guild_cfg))


# ---------------------- PAINEL PRINCIPAL ----------------------

class LogsView(BaseView):
    def __init__(self, guild: discord.Guild, dono_id: int | None = None):
        super().__init__(timeout=180)
        self.guild = guild
        self.dono_id = dono_id
        if dono_id is not None:
            self._adicionar_botao_voltar()

    def _adicionar_botao_voltar(self):
        botao = discord.ui.Button(label="◀️ Voltar ao Menu", style=discord.ButtonStyle.secondary, row=1)

        async def callback(interaction: discord.Interaction):
            from cogs.configuracoes import PainelConfiguracoesView

            view = PainelConfiguracoesView(self.dono_id)
            await interaction.response.edit_message(embed=view.texto_painel(), view=view)

        botao.callback = callback
        self.add_item(botao)

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
        config = load_config()
        guild_cfg = get_guild_config(config, interaction.guild_id)
        if not guild_cfg["canais"]:
            await interaction.response.send_message("⚠️ Nenhum log configurado ainda.", ephemeral=True)
            return
        embed = discord.Embed(
            title="🗑️ Remover Configuração",
            description="Selecione os tipos que deseja desativar.",
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, view=RemoverLogView(guild_cfg), ephemeral=True)

    @discord.ui.button(label="🔐 Permissões", style=discord.ButtonStyle.secondary, row=0)
    async def permissoes(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔐 Gerenciar Permissões",
            description="Escolha quem pode configurar os logs deste servidor.",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, view=PermissoesView(), ephemeral=True)

    @discord.ui.button(label="📊 Ver Configurações", style=discord.ButtonStyle.secondary, row=1)
    async def ver(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        guild_cfg = get_guild_config(config, interaction.guild_id)

        embed = discord.Embed(
            title="⚙️ Configuração Atual de Logs",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )

        if guild_cfg["canais"]:
            texto = "\n".join(
                f"{LOG_TYPES[t]['emoji']} {LOG_TYPES[t]['label']} → <#{c}>"
                for t, c in guild_cfg["canais"].items()
                if t in LOG_TYPES
            )
            embed.add_field(name="📋 Logs Ativos", value=texto or "Nenhum", inline=False)
        else:
            embed.add_field(name="📋 Logs Ativos", value="Nenhum configurado", inline=False)

        membros = guild_cfg["autorizados_usuarios"]
        embed.add_field(
            name="👤 Membros Autorizados",
            value=", ".join(f"<@{m}>" for m in membros) if membros else "Nenhum",
            inline=False,
        )

        cargos = guild_cfg["autorizados_cargos"]
        embed.add_field(
            name="🎭 Cargos Autorizados",
            value=", ".join(f"<@&{c}>" for c in cargos) if cargos else "Nenhum",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------------------- REGISTRO DE AUDITORIA (quem fez a ação) ----------------------
# Eventos normais do Discord (on_guild_channel_delete, on_member_ban, etc.) não dizem
# QUEM fez a ação — só o resultado. Pra descobrir o autor, sem precisar de nenhuma
# permissão nova (já vem incluído em "Administrador", que o bot já tem), a gente
# consulta o Registro de Auditoria do próprio servidor logo depois do evento.

async def buscar_executor(
    guild: discord.Guild, action: discord.AuditLogAction, target_id: int | None = None, janela_segundos: int = 8
) -> discord.User | discord.Member | None:
    try:
        async for entry in guild.audit_logs(action=action, limit=5):
            if target_id is not None and getattr(entry.target, "id", None) != target_id:
                continue
            idade = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
            if idade <= janela_segundos:
                return entry.user
    except discord.Forbidden:
        logger.warning(
            "Sem permissão para ler o Registro de Auditoria — o cargo do bot precisa da permissão "
            "'Ver Registro de Auditoria' (já incluída em Administrador)."
        )
    except Exception as e:
        logger.error("Erro ao consultar o Registro de Auditoria", exc_info=e)
    return None


def campo_executor(embed: discord.Embed, executor) -> None:
    """Adiciona o campo 'Feito por' na embed, se a gente conseguiu identificar quem fez a ação."""
    embed.add_field(name="Feito por", value=executor.mention if executor else "*Não identificado*", inline=True)


# ---------------------- COG ----------------------

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def enviar_log(self, guild: discord.Guild, tipo: str, embed: discord.Embed):
        try:
            config = load_config()
            guild_cfg = config.get(str(guild.id))
            if not guild_cfg:
                return
            canal_id = guild_cfg.get("canais", {}).get(tipo)
            if not canal_id:
                return
            canal = guild.get_channel(int(canal_id))
            if canal is None:
                return
            await canal.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"Sem permissão para enviar no canal do tipo '{tipo}' (guild {guild.id})")
        except Exception as e:
            logger.error(f"Erro ao enviar log '{tipo}' na guild {guild.id}", exc_info=e)

    @app_commands.command(name="logs", description="Gerenciar sistema de logs do servidor")
    @app_commands.guild_only()
    async def logs_cmd(self, interaction: discord.Interaction):
        if not tem_permissao(interaction):
            embed = discord.Embed(
                title="❌ Sem Permissão",
                description="Você não tem autorização para gerenciar os logs deste servidor.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Painel de Logs",
            description="Configure os eventos que serão registrados neste servidor.",
            color=discord.Color.purple(),
        )
        await interaction.response.send_message(embed=embed, view=LogsView(interaction.guild), ephemeral=True)

    @logs_cmd.error
    async def logs_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.NoPrivateMessage):
            msg = "❌ Esse comando só pode ser usado dentro de um servidor."
        else:
            logger.error("Erro no comando /logs", exc_info=error)
            msg = "❌ Ocorreu um erro inesperado ao executar o comando."

        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    # -------------------- LISTENERS --------------------

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        executor = await buscar_executor(message.guild, discord.AuditLogAction.message_delete, target_id=message.author.id)
        embed = discord.Embed(title="🗑️ Mensagem Deletada", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Autor", value=message.author.mention, inline=True)
        embed.add_field(name="Canal", value=message.channel.mention, inline=True)
        # Se ninguém aparecer no Registro de Auditoria, foi o próprio autor que apagou —
        # o Discord só registra ali quando é OUTRA pessoa (ex: moderador) que deleta.
        campo_executor(embed, executor or message.author)
        embed.add_field(name="Conteúdo", value=message.content[:1024] or "*Sem conteúdo (anexo ou embed)*", inline=False)
        embed.set_footer(text=f"ID do autor: {message.author.id}")
        await self.enviar_log(message.guild, "deletadas", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = discord.Embed(title="✏️ Mensagem Editada", color=discord.Color.gold(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Autor", value=before.author.mention, inline=True)
        embed.add_field(name="Canal", value=before.channel.mention, inline=True)
        embed.add_field(name="Antes", value=before.content[:1024] or "*Vazio*", inline=False)
        embed.add_field(name="Depois", value=after.content[:1024] or "*Vazio*", inline=False)
        embed.set_footer(text=f"ID do autor: {before.author.id}")
        await self.enviar_log(before.guild, "editadas", embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        idade_dias = (datetime.now(timezone.utc) - member.created_at).days
        embed = discord.Embed(title="📥 Membro Entrou", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Usuário", value=member.mention, inline=True)
        embed.add_field(name="Conta criada há", value=f"{idade_dias} dias", inline=True)
        embed.set_footer(text=f"ID: {member.id}")
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.enviar_log(member.guild, "entradas", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Verifica se foi expulsão (kick) antes de tratar como saída voluntária —
        # kick não tem evento próprio no discord.py, só aparece no Registro de Auditoria.
        executor = await buscar_executor(member.guild, discord.AuditLogAction.kick, target_id=member.id)
        cargos = [r.mention for r in member.roles if r.name != "@everyone"]

        if executor:
            embed = discord.Embed(title="👢 Membro Expulso", color=discord.Color.dark_orange(), timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Usuário", value=member.mention, inline=True)
            campo_executor(embed, executor)
            embed.add_field(name="Cargos que tinha", value=", ".join(cargos)[:1024] if cargos else "Nenhum", inline=False)
            embed.set_footer(text=f"ID: {member.id}")
            await self.enviar_log(member.guild, "saidas", embed)
            return

        embed = discord.Embed(title="📤 Membro Saiu", color=discord.Color.orange(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Usuário", value=member.mention, inline=True)
        embed.add_field(name="Cargos que tinha", value=", ".join(cargos)[:1024] if cargos else "Nenhum", inline=False)
        embed.set_footer(text=f"ID: {member.id}")
        await self.enviar_log(member.guild, "saidas", embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        executor = await buscar_executor(guild, discord.AuditLogAction.ban, target_id=user.id)
        embed = discord.Embed(title="⛔ Membro Banido", color=discord.Color.dark_red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Usuário", value=f"{user} ({user.mention})", inline=False)
        campo_executor(embed, executor)
        embed.set_footer(text=f"ID: {user.id}")
        await self.enviar_log(guild, "banidos", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        executor = await buscar_executor(guild, discord.AuditLogAction.unban, target_id=user.id)
        embed = discord.Embed(title="♻️ Membro Desbanido", color=discord.Color.teal(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Usuário", value=f"{user} ({user.mention})", inline=False)
        campo_executor(embed, executor)
        embed.set_footer(text=f"ID: {user.id}")
        await self.enviar_log(guild, "desbanidos", embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            executor = await buscar_executor(after.guild, discord.AuditLogAction.member_update, target_id=after.id)
            embed = discord.Embed(title="📝 Apelido Alterado", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Usuário", value=after.mention, inline=False)
            embed.add_field(name="Antes", value=before.nick or "*Nenhum*", inline=True)
            embed.add_field(name="Depois", value=after.nick or "*Nenhum*", inline=True)
            # Se ninguém aparecer no Registro de Auditoria, foi o próprio membro que mudou.
            campo_executor(embed, executor or after)
            embed.set_footer(text=f"ID: {after.id}")
            await self.enviar_log(after.guild, "apelido", embed)

        antes_ids = {r.id for r in before.roles}
        depois_ids = {r.id for r in after.roles}

        for role in after.roles:
            if role.id not in antes_ids:
                executor = await buscar_executor(after.guild, discord.AuditLogAction.member_role_update, target_id=after.id)
                embed = discord.Embed(title="➕ Cargo Adicionado", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
                embed.add_field(name="Usuário", value=after.mention, inline=True)
                embed.add_field(name="Cargo", value=role.mention, inline=True)
                campo_executor(embed, executor)
                embed.set_footer(text=f"ID: {after.id}")
                await self.enviar_log(after.guild, "cargo_add", embed)

        for role in before.roles:
            if role.id not in depois_ids:
                executor = await buscar_executor(after.guild, discord.AuditLogAction.member_role_update, target_id=after.id)
                embed = discord.Embed(title="➖ Cargo Removido", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
                embed.add_field(name="Usuário", value=after.mention, inline=True)
                embed.add_field(name="Cargo", value=role.mention, inline=True)
                campo_executor(embed, executor)
                embed.set_footer(text=f"ID: {after.id}")
                await self.enviar_log(after.guild, "cargo_remove", embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        executor = await buscar_executor(channel.guild, discord.AuditLogAction.channel_create, target_id=channel.id)
        embed = discord.Embed(title="📁 Canal Criado", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Nome", value=channel.name, inline=True)
        embed.add_field(name="Tipo", value=str(channel.type), inline=True)
        campo_executor(embed, executor)
        embed.set_footer(text=f"ID: {channel.id}")
        await self.enviar_log(channel.guild, "canal_criado", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        executor = await buscar_executor(channel.guild, discord.AuditLogAction.channel_delete, target_id=channel.id)
        embed = discord.Embed(title="🗑️ Canal Deletado", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Nome", value=channel.name, inline=True)
        embed.add_field(name="Tipo", value=str(channel.type), inline=True)
        campo_executor(embed, executor)
        embed.set_footer(text=f"ID: {channel.id}")
        await self.enviar_log(channel.guild, "canal_deletado", embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(title="🔊 Entrou em Canal de Voz", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Usuário", value=member.mention, inline=True)
            embed.add_field(name="Canal", value=after.channel.mention, inline=True)
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(title="🔊 Saiu de Canal de Voz", color=discord.Color.orange(), timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Usuário", value=member.mention, inline=True)
            embed.add_field(name="Canal", value=before.channel.mention, inline=True)
        elif before.channel != after.channel:
            embed = discord.Embed(title="🔊 Trocou de Canal de Voz", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Usuário", value=member.mention, inline=True)
            embed.add_field(name="De", value=before.channel.mention, inline=True)
            embed.add_field(name="Para", value=after.channel.mention, inline=True)
        else:
            return

        embed.set_footer(text=f"ID: {member.id}")
        await self.enviar_log(member.guild, "voz", embed)


async def setup(bot):
    await bot.add_cog(Logs(bot))
