import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import logging
import os
import copy
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("bot.formularios")

CONFIG_FILE = "config/formularios_config.json"
SUBMISSOES_FILE = "config/formularios_submissoes.json"
PERGUNTAS_POR_TELA = 5  # limite do Discord: só dá 5 campos de texto por modal
PRAZO_INCOMPLETO_HORAS = 24

CORES = [
    ("Vermelho", "🔴", 0xE74C3C), ("Laranja", "🟠", 0xE67E22), ("Amarelo", "🟡", 0xF1C40F),
    ("Verde", "🟢", 0x2ECC71), ("Azul", "🔵", 0x3498DB), ("Roxo", "🟣", 0x9B59B6),
    ("Rosa", "🌸", 0xFF69B4), ("Ciano", "🔷", 0x1ABC9C), ("Dourado", "🟨", 0xF39C12),
    ("Cinza", "⬜", 0x95A5A6), ("Índigo", "🔹", 0x5865F2), ("Preto", "⚫", 0x23272A),
    ("Branco", "⚪", 0xFFFFFF),
]


# =====================================================================
# PERSISTÊNCIA — CONFIGURAÇÃO DOS TIPOS DE FORMULÁRIO
# =====================================================================

def tipo_padrao(nome: str) -> dict:
    return {
        "nome": nome,
        "ativo": False,
        "title": None,
        "description": None,
        "perguntas": [],
        "color": 0x2C2F33,
        "thumbnail": None,
        "image": None,
        "canal_envio": None,
        "canal_analise": None,
        "canal_resultados": None,
        "cargo_aprovado": None,
        "revisores": [],
        "mensagem_envio_id": None,
    }


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config de formulários, recriando: {e}")
    return {}


def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_guild_tipos(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    config.setdefault(gid, {})
    return config[gid]


# =====================================================================
# PERSISTÊNCIA — SUBMISSÕES (respostas enviadas pelos membros)
# =====================================================================

def load_submissoes() -> dict:
    if os.path.exists(SUBMISSOES_FILE):
        try:
            with open(SUBMISSOES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler submissões de formulários, recriando: {e}")
    return {}


def save_submissoes(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(SUBMISSOES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_submissao(subs: dict, guild_id: int, tipo_nome: str, user_id: int) -> dict | None:
    return subs.get(str(guild_id), {}).get(tipo_nome, {}).get(str(user_id))


def set_submissao(subs: dict, guild_id: int, tipo_nome: str, user_id: int, dados: dict) -> None:
    gid, uid = str(guild_id), str(user_id)
    subs.setdefault(gid, {}).setdefault(tipo_nome, {})[uid] = dados


# =====================================================================
# SESSÕES DE CONSTRUÇÃO (admin configurando um tipo) — em memória
# =====================================================================

BUILD_SESSIONS: dict = {}   # key = "guild:user" -> tipo dict sendo editado
TEMP_RESPOSTAS: dict = {}   # key = "guild:tipo:user" -> lista de respostas em andamento


def _bkey(guild_id: int, user_id: int) -> str:
    return f"{guild_id}:{user_id}"


def _rkey(guild_id: int, tipo_nome: str, user_id: int) -> str:
    return f"{guild_id}:{tipo_nome}:{user_id}"


def embed_valido(tipo: dict) -> bool:
    return bool(tipo.get("title") or tipo.get("description")) and bool(tipo.get("perguntas"))


def montar_preview(tipo: dict) -> discord.Embed:
    embed = discord.Embed(
        title=tipo.get("title") or "Formulário sem título",
        description=tipo.get("description") or "*Sem descrição*",
        color=tipo.get("color", 0x2C2F33),
    )
    if tipo.get("perguntas"):
        lista = "\n".join(f"{i+1}. {p}" for i, p in enumerate(tipo["perguntas"]))
        embed.add_field(name=f"Perguntas ({len(tipo['perguntas'])})", value=lista[:1024], inline=False)
    if tipo.get("thumbnail"):
        embed.set_thumbnail(url=tipo["thumbnail"])
    if tipo.get("image"):
        embed.set_image(url=tipo["image"])
    return embed


def montar_embed_publico(tipo: dict) -> discord.Embed:
    """Embed que fica no canal de envio, sem a lista de perguntas (só some quando responder)."""
    embed = discord.Embed(
        title=tipo.get("title") or "Formulário",
        description=tipo.get("description") or "Clique no botão abaixo para responder.",
        color=tipo.get("color", 0x2C2F33),
    )
    if tipo.get("thumbnail"):
        embed.set_thumbnail(url=tipo["thumbnail"])
    if tipo.get("image"):
        embed.set_image(url=tipo["image"])
    embed.set_footer(text=f"{len(tipo.get('perguntas', []))} pergunta(s)")
    return embed


def montar_meta_embed(tipo: dict, nota: str | None = None) -> discord.Embed:
    status = "🟢 Ativo" if tipo.get("ativo") else "🔴 Inativo"
    canal_envio = f"<#{tipo['canal_envio']}>" if tipo.get("canal_envio") else "`-`"
    canal_analise = f"<#{tipo['canal_analise']}>" if tipo.get("canal_analise") else "`-`"
    canal_resultados = f"<#{tipo['canal_resultados']}>" if tipo.get("canal_resultados") else "`-`"
    cargo = f"<@&{tipo['cargo_aprovado']}>" if tipo.get("cargo_aprovado") else "`Nenhum`"
    revisores = ", ".join(f"<@{r}>" for r in tipo.get("revisores", [])) or "`Nenhum (qualquer admin)`"

    embed = discord.Embed(
        title=f"🔧 Formulário: {tipo['nome']}",
        description=f"**{nota}**" if nota else None,
        color=tipo.get("color", 0x2C2F33),
    )
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Envio", value=canal_envio, inline=True)
    embed.add_field(name="Análise", value=canal_analise, inline=True)
    embed.add_field(name="Resultados", value=canal_resultados, inline=True)
    embed.add_field(name="Cargo ao aprovar", value=cargo, inline=True)
    embed.add_field(name="Perguntas", value=f"`{len(tipo.get('perguntas', []))}`", inline=True)
    embed.add_field(name="Revisores", value=revisores, inline=False)
    embed.set_footer(text="⬇️ Pré-visualização do formulário abaixo")
    return embed


# =====================================================================
# VIEW BASE
# =====================================================================

class BaseView(discord.ui.View):
    dono_id: int | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.dono_id is None:
            return True
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True
            )
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        logger.error(f"Erro no componente '{item}' do sistema de formulários", exc_info=error)
        msg = "❌ Ocorreu um erro ao processar essa ação. Tente novamente."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass


# =====================================================================
# MODAIS — CONFIGURAÇÃO (texto, pergunta, imagens, id de revisor)
# =====================================================================

class TextoTipoModal(discord.ui.Modal, title="Texto do Formulário"):
    def __init__(self, key: str, parent_view: "TipoBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        tipo = BUILD_SESSIONS[key]
        self.titulo = discord.ui.TextInput(label="Título", required=False, max_length=256, default=tipo.get("title") or "")
        self.descricao = discord.ui.TextInput(
            label="Descrição", style=discord.TextStyle.paragraph, required=False, max_length=2000,
            default=tipo.get("description") or "",
        )
        self.add_item(self.titulo)
        self.add_item(self.descricao)

    async def on_submit(self, interaction: discord.Interaction):
        tipo = BUILD_SESSIONS[self.key]
        tipo["title"] = self.titulo.value.strip() or None
        tipo["description"] = self.descricao.value.strip() or None
        await self.parent_view.atualizar(interaction)


class AdicionarPerguntaModal(discord.ui.Modal, title="Nova Pergunta"):
    def __init__(self, key: str, parent_view: "TipoBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        self.pergunta = discord.ui.TextInput(
            label="Texto da pergunta", required=True, max_length=200, placeholder="Ex: Qual sua idade?"
        )
        self.add_item(self.pergunta)

    async def on_submit(self, interaction: discord.Interaction):
        tipo = BUILD_SESSIONS[self.key]
        tipo.setdefault("perguntas", []).append(self.pergunta.value.strip())
        await self.parent_view.atualizar(interaction)


class ImagensTipoModal(discord.ui.Modal, title="Foto e Banner"):
    def __init__(self, key: str, parent_view: "TipoBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        tipo = BUILD_SESSIONS[key]
        self.foto = discord.ui.TextInput(label="Foto (thumbnail)", required=False, placeholder="https://...", default=tipo.get("thumbnail") or "")
        self.banner = discord.ui.TextInput(label="Banner", required=False, placeholder="https://...", default=tipo.get("image") or "")
        self.add_item(self.foto)
        self.add_item(self.banner)

    async def on_submit(self, interaction: discord.Interaction):
        tipo = BUILD_SESSIONS[self.key]
        foto, banner = self.foto.value.strip(), self.banner.value.strip()
        if foto and not foto.startswith("http"):
            await interaction.response.send_message("❌ O link da foto precisa começar com http(s).", ephemeral=True)
            return
        if banner and not banner.startswith("http"):
            await interaction.response.send_message("❌ O link do banner precisa começar com http(s).", ephemeral=True)
            return
        tipo["thumbnail"] = foto or None
        tipo["image"] = banner or None
        await self.parent_view.atualizar(interaction)


class RevisorIdModal(discord.ui.Modal, title="Adicionar Revisor por ID"):
    def __init__(self, key: str, parent_view: "RevisoresView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        self.id_input = discord.ui.TextInput(label="ID do membro", required=True, placeholder="123456789012345678")
        self.add_item(self.id_input)

    async def on_submit(self, interaction: discord.Interaction):
        tipo = BUILD_SESSIONS[self.key]
        try:
            uid = int(self.id_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ ID inválido — precisa ser só números.", ephemeral=True)
            return
        if uid not in tipo["revisores"]:
            tipo["revisores"].append(uid)
        await self.parent_view.atualizar(interaction)


# =====================================================================
# SELECTS — COR, CANAIS, CARGO, REVISOR
# =====================================================================

class CorSelect(discord.ui.Select):
    def __init__(self, key: str, parent_view: "TipoBuilderView"):
        self.key = key
        self.parent_view = parent_view
        options = [discord.SelectOption(label=n, emoji=e, value=str(c)) for n, e, c in CORES]
        super().__init__(placeholder="Escolha uma cor", options=options)

    async def callback(self, interaction: discord.Interaction):
        BUILD_SESSIONS[self.key]["color"] = int(self.values[0])
        await self.parent_view.atualizar(interaction)


class CanalTipoSelect(discord.ui.ChannelSelect):
    def __init__(self, key: str, campo: str, parent_view: "TipoBuilderView"):
        self.key = key
        self.campo = campo
        self.parent_view = parent_view
        super().__init__(
            placeholder="Selecione o canal", channel_types=[discord.ChannelType.text, discord.ChannelType.news]
        )

    async def callback(self, interaction: discord.Interaction):
        BUILD_SESSIONS[self.key][self.campo] = self.values[0].id
        await self.parent_view.atualizar(interaction)


class CargoAprovadoSelect(discord.ui.RoleSelect):
    def __init__(self, key: str, parent_view: "TipoBuilderView"):
        self.key = key
        self.parent_view = parent_view
        super().__init__(placeholder="Selecione o cargo ao aprovar")

    async def callback(self, interaction: discord.Interaction):
        BUILD_SESSIONS[self.key]["cargo_aprovado"] = self.values[0].id
        await self.parent_view.atualizar(interaction)


class RevisorSelect(discord.ui.UserSelect):
    def __init__(self, key: str, parent_view: "RevisoresView"):
        self.key = key
        self.parent_view = parent_view
        super().__init__(placeholder="Selecione um membro pra adicionar")

    async def callback(self, interaction: discord.Interaction):
        tipo = BUILD_SESSIONS[self.key]
        uid = self.values[0].id
        if uid not in tipo["revisores"]:
            tipo["revisores"].append(uid)
        await self.parent_view.atualizar(interaction)


# =====================================================================
# PAINEL: REVISORES
# =====================================================================

class RevisoresView(BaseView):
    def __init__(self, key: str, parent_view: "TipoBuilderView", dono_id: int):
        super().__init__(timeout=300)
        self.key = key
        self.parent_view = parent_view
        self.dono_id = dono_id
        self.add_item(RevisorSelect(key, self))

    async def atualizar(self, interaction: discord.Interaction):
        tipo = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=self)

    @discord.ui.button(label="🔢 Adicionar por ID", style=discord.ButtonStyle.secondary, row=1)
    async def por_id_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RevisorIdModal(self.key, self))

    @discord.ui.button(label="🧹 Limpar Revisores", style=discord.ButtonStyle.danger, row=1)
    async def limpar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        BUILD_SESSIONS[self.key]["revisores"] = []
        await self.atualizar(interaction)

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
    async def voltar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=self.parent_view)


# =====================================================================
# PAINEL: CONSTRUTOR DE UM TIPO DE FORMULÁRIO
# =====================================================================

class TipoBuilderView(BaseView):
    def __init__(self, key: str, dono_id: int):
        super().__init__(timeout=900)
        self.key = key
        self.dono_id = dono_id

    async def atualizar(self, interaction: discord.Interaction):
        tipo = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=self)

    def _persistir(self, guild_id: int):
        tipo = BUILD_SESSIONS[self.key]
        config = load_config()
        tipos = get_guild_tipos(config, guild_id)
        tipos[tipo["nome"]] = copy.deepcopy(tipo)
        save_config(config)

    @discord.ui.button(label="📝 Texto", style=discord.ButtonStyle.primary, row=0)
    async def texto_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TextoTipoModal(self.key, self))

    @discord.ui.button(label="➕ Add Pergunta", style=discord.ButtonStyle.primary, row=0)
    async def add_pergunta_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdicionarPerguntaModal(self.key, self))

    @discord.ui.button(label="➖ Remover Última", style=discord.ButtonStyle.secondary, row=0)
    async def remover_pergunta_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = BUILD_SESSIONS[self.key]
        if tipo["perguntas"]:
            tipo["perguntas"].pop()
        await self.atualizar(interaction)

    @discord.ui.button(label="🖼️ Imagens", style=discord.ButtonStyle.primary, row=0)
    async def imagens_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImagensTipoModal(self.key, self))

    @discord.ui.button(label="🎨 Cor", style=discord.ButtonStyle.secondary, row=1)
    async def cor_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CorSelect(self.key, self))
        view.add_item(self._voltar_button())
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=view)

    @discord.ui.button(label="📤 Canal de Envio", style=discord.ButtonStyle.secondary, row=1)
    async def canal_envio_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_canal_select(interaction, "canal_envio")

    @discord.ui.button(label="🔎 Canal de Análise", style=discord.ButtonStyle.secondary, row=1)
    async def canal_analise_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_canal_select(interaction, "canal_analise")

    @discord.ui.button(label="📊 Canal de Resultados", style=discord.ButtonStyle.secondary, row=1)
    async def canal_resultados_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_canal_select(interaction, "canal_resultados")

    async def _abrir_canal_select(self, interaction: discord.Interaction, campo: str):
        tipo = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CanalTipoSelect(self.key, campo, self))
        view.add_item(self._voltar_button())
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=view)

    @discord.ui.button(label="🎭 Cargo ao Aprovar", style=discord.ButtonStyle.secondary, row=2)
    async def cargo_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CargoAprovadoSelect(self.key, self))
        view.add_item(self._voltar_button())
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=view)

    @discord.ui.button(label="🛡️ Revisores", style=discord.ButtonStyle.secondary, row=2)
    async def revisores_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = BUILD_SESSIONS[self.key]
        view = RevisoresView(self.key, self, self.dono_id)
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=view)

    def _voltar_button(self) -> discord.ui.Button:
        btn = discord.ui.Button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)

        async def callback(interaction: discord.Interaction):
            tipo = BUILD_SESSIONS[self.key]
            await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=self)

        btn.callback = callback
        return btn

    @discord.ui.button(label="💾 Salvar", style=discord.ButtonStyle.success, row=3)
    async def salvar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._persistir(interaction.guild_id)
        tipo = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            embeds=[montar_meta_embed(tipo, nota=f"✅ **{tipo['nome']}** salvo!"), montar_preview(tipo)], view=self
        )

    @discord.ui.button(label="📨 Publicar / Atualizar", style=discord.ButtonStyle.success, row=3)
    async def publicar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = BUILD_SESSIONS[self.key]
        if not embed_valido(tipo):
            await interaction.response.send_message("❌ Configure texto e ao menos uma pergunta antes de publicar.", ephemeral=True)
            return
        if not tipo.get("canal_envio"):
            await interaction.response.send_message("❌ Configure o canal de envio antes de publicar.", ephemeral=True)
            return
        canal = interaction.guild.get_channel(tipo["canal_envio"])
        if canal is None:
            await interaction.response.send_message("❌ Canal de envio não encontrado.", ephemeral=True)
            return

        embed_pub = montar_embed_publico(tipo)
        view_pub = FormularioEnvioView(interaction.guild_id, tipo["nome"])

        try:
            if tipo.get("mensagem_envio_id"):
                try:
                    msg = await canal.fetch_message(tipo["mensagem_envio_id"])
                    await msg.edit(embed=embed_pub, view=view_pub)
                except discord.NotFound:
                    msg = await canal.send(embed=embed_pub, view=view_pub)
                    tipo["mensagem_envio_id"] = msg.id
            else:
                msg = await canal.send(embed=embed_pub, view=view_pub)
                tipo["mensagem_envio_id"] = msg.id
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sem permissão para enviar/editar mensagens nesse canal.", ephemeral=True)
            return

        tipo["ativo"] = True
        self._persistir(interaction.guild_id)
        await interaction.response.edit_message(
            embeds=[montar_meta_embed(tipo, nota=f"✅ Publicado em {canal.mention} e ativado!"), montar_preview(tipo)],
            view=self,
        )

    @discord.ui.button(label="🔴 Desativar", style=discord.ButtonStyle.danger, row=4)
    async def desativar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = BUILD_SESSIONS[self.key]
        tipo["ativo"] = False
        self._persistir(interaction.guild_id)
        await self.atualizar(interaction)

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=4)
    async def voltar_final_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FormulariosPainelView(self.dono_id)
        await interaction.response.edit_message(embed=await view.texto_painel(interaction.guild_id), view=view)


# =====================================================================
# PAINEL PRINCIPAL: LISTA DE FORMULÁRIOS
# =====================================================================

class NovoFormularioModal(discord.ui.Modal, title="Novo Formulário"):
    def __init__(self, parent_view: "FormulariosPainelView"):
        super().__init__()
        self.parent_view = parent_view
        self.nome = discord.ui.TextInput(label="Nome do formulário", required=True, max_length=60, placeholder="Ex: whitelist, staff, parceria")
        self.add_item(self.nome)

    async def on_submit(self, interaction: discord.Interaction):
        nome = self.nome.value.strip()
        config = load_config()
        tipos = get_guild_tipos(config, interaction.guild_id)
        if nome in tipos:
            await interaction.response.send_message("❌ Já existe um formulário com esse nome.", ephemeral=True)
            return
        tipos[nome] = tipo_padrao(nome)
        save_config(config)

        key = _bkey(interaction.guild_id, interaction.user.id)
        BUILD_SESSIONS[key] = copy.deepcopy(tipos[nome])
        view = TipoBuilderView(key, interaction.user.id)
        tipo = BUILD_SESSIONS[key]
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=view)


class ListaFormulariosSelect(discord.ui.Select):
    def __init__(self, nomes: list, dono_id: int):
        self.dono_id = dono_id
        options = [discord.SelectOption(label=n) for n in nomes[:25]]
        super().__init__(placeholder="Selecione um formulário pra editar", options=options)

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        tipos = get_guild_tipos(config, interaction.guild_id)
        dados = tipos.get(self.values[0])
        if not dados:
            await interaction.response.send_message("❌ Esse formulário não existe mais.", ephemeral=True)
            return
        key = _bkey(interaction.guild_id, interaction.user.id)
        BUILD_SESSIONS[key] = copy.deepcopy(dados)
        BUILD_SESSIONS[key].setdefault("revisores", [])
        view = TipoBuilderView(key, self.dono_id)
        tipo = BUILD_SESSIONS[key]
        await interaction.response.edit_message(embeds=[montar_meta_embed(tipo), montar_preview(tipo)], view=view)


class FormulariosPainelView(discord.ui.View):
    def __init__(self, dono_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id

    async def texto_painel(self, guild_id: int) -> discord.Embed:
        config = load_config()
        tipos = get_guild_tipos(config, guild_id)
        embed = discord.Embed(title="📋 Formulários", color=0x2C2F33)
        if not tipos:
            embed.description = "Nenhum formulário criado ainda. Toque em \"➕ Criar Novo\"."
            return embed
        linhas = [f"• **{n}** — {'🟢 ativo' if t.get('ativo') else '🔴 inativo'}" for n, t in tipos.items()]
        embed.description = "\n".join(linhas)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="➕ Criar Novo", style=discord.ButtonStyle.success, row=0)
    async def criar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NovoFormularioModal(self))

    @discord.ui.button(label="✏️ Editar Existente", style=discord.ButtonStyle.primary, row=0)
    async def editar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        tipos = get_guild_tipos(config, interaction.guild_id)
        if not tipos:
            await interaction.response.send_message("⚠️ Nenhum formulário criado ainda.", ephemeral=True)
            return
        view = discord.ui.View(timeout=180)
        view.add_item(ListaFormulariosSelect(list(tipos.keys()), self.dono_id))
        voltar = discord.ui.Button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)

        async def voltar_callback(inter: discord.Interaction):
            painel = FormulariosPainelView(self.dono_id)
            await inter.response.edit_message(embed=await painel.texto_painel(inter.guild_id), view=painel)

        voltar.callback = voltar_callback
        view.add_item(voltar)
        await interaction.response.edit_message(embed=await self.texto_painel(interaction.guild_id), view=view)

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
    async def voltar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.configuracoes import PainelConfiguracoesView

        view = PainelConfiguracoesView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)


# =====================================================================
# FLUXO DO MEMBRO — RESPONDER FORMULÁRIO (com telas encadeadas)
# =====================================================================

def _carregar_tipo(guild_id: int, tipo_nome: str) -> dict | None:
    config = load_config()
    return get_guild_tipos(config, guild_id).get(tipo_nome)


class FormularioEnvioView(discord.ui.View):
    """Botão persistente que fica na embed pública do canal de envio."""

    def __init__(self, guild_id: int, tipo_nome: str):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.tipo_nome = tipo_nome
        self.responder.custom_id = f"form_envio:{guild_id}:{tipo_nome}"

    @discord.ui.button(label="📋 Fazer Formulário", style=discord.ButtonStyle.success)
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = _carregar_tipo(self.guild_id, self.tipo_nome)
        if not tipo or not tipo.get("ativo"):
            await interaction.response.send_message("❌ Esse formulário não está mais disponível.", ephemeral=True)
            return

        subs = load_submissoes()
        atual = get_submissao(subs, self.guild_id, self.tipo_nome, interaction.user.id)
        if atual and atual.get("status") in ("pendente", "incompleto"):
            await interaction.response.send_message(
                "⚠️ Você já tem um formulário em andamento — aguarde ele ser analisado (ou complete o pendente, se marcado como incompleto).",
                ephemeral=True,
            )
            return

        TEMP_RESPOSTAS[_rkey(self.guild_id, self.tipo_nome, interaction.user.id)] = []
        modal = ResponderFormularioModal(self.guild_id, self.tipo_nome, tipo["perguntas"], pagina=0, defaults=None)
        await interaction.response.send_modal(modal)


class ContinuarFormularioView(discord.ui.View):
    """Botão intermediário pra abrir a próxima tela de perguntas (não precisa ser persistente)."""

    def __init__(self, guild_id: int, tipo_nome: str, perguntas: list, pagina: int, defaults: list | None, dono_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.tipo_nome = tipo_nome
        self.perguntas = perguntas
        self.pagina = pagina
        self.defaults = defaults
        self.dono_id = dono_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.dono_id

    @discord.ui.button(label="➡️ Continuar", style=discord.ButtonStyle.success)
    async def continuar(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ResponderFormularioModal(self.guild_id, self.tipo_nome, self.perguntas, self.pagina, self.defaults)
        await interaction.response.send_modal(modal)


class ResponderFormularioModal(discord.ui.Modal):
    def __init__(self, guild_id: int, tipo_nome: str, perguntas: list, pagina: int, defaults: list | None):
        inicio = pagina * PERGUNTAS_POR_TELA
        fim = inicio + PERGUNTAS_POR_TELA
        self.perguntas_pagina = perguntas[inicio:fim]
        super().__init__(title=f"Formulário — Parte {pagina + 1}")
        self.guild_id = guild_id
        self.tipo_nome = tipo_nome
        self.perguntas = perguntas
        self.pagina = pagina
        self.campos = []
        for i, pergunta in enumerate(self.perguntas_pagina):
            default = defaults[inicio + i] if defaults and len(defaults) > inicio + i else ""
            campo = discord.ui.TextInput(
                label=pergunta[:45],
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=1000,
                default=default,
            )
            self.campos.append(campo)
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        rkey = _rkey(self.guild_id, self.tipo_nome, interaction.user.id)
        respostas = TEMP_RESPOSTAS.setdefault(rkey, [])
        respostas.extend([c.value.strip() for c in self.campos])

        proxima_pagina = self.pagina + 1
        if proxima_pagina * PERGUNTAS_POR_TELA < len(self.perguntas):
            view = ContinuarFormularioView(
                self.guild_id, self.tipo_nome, self.perguntas, proxima_pagina, respostas, interaction.user.id
            )
            await interaction.response.send_message(
                f"✅ Parte {self.pagina + 1} recebida! Faltam mais perguntas — toque em Continuar.",
                view=view,
                ephemeral=True,
            )
            return

        # última página — finaliza e envia pra análise
        await self._finalizar(interaction, respostas)

    async def _finalizar(self, interaction: discord.Interaction, respostas: list):
        tipo = _carregar_tipo(self.guild_id, self.tipo_nome)
        if not tipo:
            await interaction.response.send_message("❌ Esse formulário não existe mais.", ephemeral=True)
            return

        subs = load_submissoes()
        dados = {
            "respostas": respostas,
            "status": "pendente",
            "enviado_em": datetime.now(timezone.utc).isoformat(),
            "prazo_incompleto": None,
            "analisado_por": None,
            "aprovado_por": None,
            "reprovado_por": None,
            "canal_analise_id": tipo.get("canal_analise"),
            "mensagem_analise_id": None,
        }
        set_submissao(subs, self.guild_id, self.tipo_nome, interaction.user.id, dados)
        save_submissoes(subs)
        TEMP_RESPOSTAS.pop(_rkey(self.guild_id, self.tipo_nome, interaction.user.id), None)

        await interaction.response.send_message("✅ Formulário enviado! Você será avisado por DM quando for analisado.", ephemeral=True)

        # posta no canal de análise + notifica
        guild = interaction.client.get_guild(self.guild_id)
        canal = guild.get_channel(tipo["canal_analise"]) if tipo.get("canal_analise") else None
        if canal:
            embed = _montar_embed_analise(tipo, interaction.user, respostas, dados)
            view = AnaliseView(self.guild_id, self.tipo_nome, interaction.user.id)
            try:
                msg = await canal.send(
                    content=f"📥 Novo formulário de {interaction.user.mention} — **{tipo['nome']}**",
                    embed=embed,
                    view=view,
                )
                dados["mensagem_analise_id"] = msg.id
                set_submissao(subs, self.guild_id, self.tipo_nome, interaction.user.id, dados)
                save_submissoes(subs)
            except discord.Forbidden:
                logger.warning(f"Sem permissão pra postar no canal de análise do formulário {self.tipo_nome}")


def _montar_embed_analise(tipo: dict, membro: discord.abc.User, respostas: list, dados: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"📋 {tipo['nome']} — {membro.display_name}",
        color=tipo.get("color", 0x2C2F33),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    for i, (pergunta, resposta) in enumerate(zip(tipo["perguntas"], respostas)):
        embed.add_field(name=f"{i+1}. {pergunta}", value=resposta[:1024] or "*(vazio)*", inline=False)
    embed.set_footer(text=f"Solicitante: {membro} • ID {membro.id}")
    return embed


# =====================================================================
# FLUXO DE ANÁLISE — APROVAR / REPROVAR / INCOMPLETO
# =====================================================================

def _pode_revisar(tipo: dict, member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    if not tipo.get("revisores"):
        return False
    return member.id in tipo["revisores"]


class AnaliseView(discord.ui.View):
    def __init__(self, guild_id: int, tipo_nome: str, autor_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.tipo_nome = tipo_nome
        self.autor_id = autor_id
        self.aprovar.custom_id = f"form_aprovar:{guild_id}:{tipo_nome}:{autor_id}"
        self.reprovar.custom_id = f"form_reprovar:{guild_id}:{tipo_nome}:{autor_id}"
        self.incompleto.custom_id = f"form_incompleto:{guild_id}:{tipo_nome}:{autor_id}"

    async def _checar_permissao(self, interaction: discord.Interaction) -> dict | None:
        tipo = _carregar_tipo(self.guild_id, self.tipo_nome)
        if not tipo:
            await interaction.response.send_message("❌ Esse formulário não existe mais.", ephemeral=True)
            return None
        if not _pode_revisar(tipo, interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão pra analisar este formulário.", ephemeral=True)
            return None
        return tipo

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success, row=0)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = await self._checar_permissao(interaction)
        if not tipo:
            return
        await self._resolver(interaction, tipo, "aprovado")

    @discord.ui.button(label="❌ Reprovar", style=discord.ButtonStyle.danger, row=0)
    async def reprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = await self._checar_permissao(interaction)
        if not tipo:
            return
        await self._resolver(interaction, tipo, "reprovado")

    @discord.ui.button(label="⚠️ Marcar Incompleto", style=discord.ButtonStyle.secondary, row=0)
    async def incompleto(self, interaction: discord.Interaction, button: discord.ui.Button):
        tipo = await self._checar_permissao(interaction)
        if not tipo:
            return

        subs = load_submissoes()
        dados = get_submissao(subs, self.guild_id, self.tipo_nome, self.autor_id)
        if not dados:
            await interaction.response.send_message("❌ Essa submissão não existe mais.", ephemeral=True)
            return

        prazo = datetime.now(timezone.utc) + timedelta(hours=PRAZO_INCOMPLETO_HORAS)
        dados["status"] = "incompleto"
        dados["prazo_incompleto"] = prazo.isoformat()
        dados["analisado_por"] = interaction.user.id
        set_submissao(subs, self.guild_id, self.tipo_nome, self.autor_id, dados)
        save_submissoes(subs)

        await interaction.response.edit_message(
            content=interaction.message.content + f"\n\n⚠️ Marcado como **incompleto** por {interaction.user.mention}.",
            view=None,
        )

        guild = interaction.client.get_guild(self.guild_id)
        membro = guild.get_member(self.autor_id) if guild else None
        if membro:
            try:
                embed_dm = discord.Embed(
                    title=f"⚠️ Seu formulário \"{tipo['nome']}\" está incompleto",
                    description=(
                        "Um revisor marcou seu formulário como incompleto. "
                        f"Você tem exatamente **{PRAZO_INCOMPLETO_HORAS} horas** pra corrigir e reenviar. "
                        "Se corrigir a tempo, ele volta pra análise automaticamente."
                    ),
                    color=0xF1C40F,
                )
                embed_dm.add_field(
                    name="Prazo", value=discord.utils.format_dt(prazo, style="F"), inline=False
                )
                view_dm = CompletarFormularioView(self.guild_id, self.tipo_nome, self.autor_id)
                await membro.send(embed=embed_dm, view=view_dm)
            except discord.Forbidden:
                logger.warning(f"Não consegui mandar DM de incompleto pro membro {self.autor_id}")

    async def _resolver(self, interaction: discord.Interaction, tipo: dict, resultado: str):
        subs = load_submissoes()
        dados = get_submissao(subs, self.guild_id, self.tipo_nome, self.autor_id)
        if not dados:
            await interaction.response.send_message("❌ Essa submissão não existe mais.", ephemeral=True)
            return

        dados["status"] = resultado
        dados["analisado_por"] = interaction.user.id
        if resultado == "aprovado":
            dados["aprovado_por"] = interaction.user.id
        else:
            dados["reprovado_por"] = interaction.user.id
        set_submissao(subs, self.guild_id, self.tipo_nome, self.autor_id, dados)
        save_submissoes(subs)

        guild = interaction.client.get_guild(self.guild_id)
        membro = guild.get_member(self.autor_id) if guild else None

        cargo_dado = None
        if resultado == "aprovado" and membro and tipo.get("cargo_aprovado"):
            cargo = guild.get_role(tipo["cargo_aprovado"])
            if cargo:
                try:
                    await membro.add_roles(cargo, reason=f"Formulário {tipo['nome']} aprovado")
                    cargo_dado = cargo
                except discord.Forbidden:
                    logger.warning(f"Sem permissão pra dar o cargo {cargo.id} ao aprovar formulário")

        emoji = "✅" if resultado == "aprovado" else "❌"
        await interaction.response.edit_message(
            content=interaction.message.content + f"\n\n{emoji} **{resultado.capitalize()}** por {interaction.user.mention}.",
            view=None,
        )

        if membro:
            try:
                texto = f"Seu formulário **{tipo['nome']}** foi **{resultado}**."
                if cargo_dado:
                    texto += f" Você recebeu o cargo {cargo_dado.name}."
                await membro.send(texto)
            except discord.Forbidden:
                pass

        canal_resultados = guild.get_channel(tipo["canal_resultados"]) if tipo.get("canal_resultados") else None
        if canal_resultados:
            embed_resultado = discord.Embed(
                title=f"{emoji} Formulário {resultado} — {tipo['nome']}",
                color=0x2ECC71 if resultado == "aprovado" else 0xE74C3C,
                timestamp=datetime.now(timezone.utc),
            )
            embed_resultado.add_field(name="Solicitante", value=f"<@{self.autor_id}>", inline=True)
            embed_resultado.add_field(name="Analisado por", value=interaction.user.mention, inline=True)
            if resultado == "aprovado":
                embed_resultado.add_field(name="Aprovado por", value=interaction.user.mention, inline=True)
            else:
                embed_resultado.add_field(name="Reprovado por", value=interaction.user.mention, inline=True)
            embed_resultado.add_field(name="Cargo dado", value=cargo_dado.mention if cargo_dado else "Nenhum", inline=True)
            try:
                await canal_resultados.send(embed=embed_resultado)
            except discord.Forbidden:
                logger.warning("Sem permissão pra postar no canal de resultados")


# =====================================================================
# DM — COMPLETAR FORMULÁRIO INCOMPLETO
# =====================================================================

class CompletarFormularioView(discord.ui.View):
    def __init__(self, guild_id: int, tipo_nome: str, user_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.tipo_nome = tipo_nome
        self.user_id = user_id
        self.completar.custom_id = f"form_completar:{guild_id}:{tipo_nome}:{user_id}"

    @discord.ui.button(label="✏️ Completar Formulário", style=discord.ButtonStyle.primary)
    async def completar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Esse botão não é seu.", ephemeral=True)
            return

        tipo = _carregar_tipo(self.guild_id, self.tipo_nome)
        if not tipo:
            await interaction.response.send_message("❌ Esse formulário não existe mais.", ephemeral=True)
            return

        subs = load_submissoes()
        dados = get_submissao(subs, self.guild_id, self.tipo_nome, self.user_id)
        if not dados or dados.get("status") != "incompleto":
            await interaction.response.send_message("❌ Não há um formulário incompleto pendente pra você.", ephemeral=True)
            return

        prazo = datetime.fromisoformat(dados["prazo_incompleto"])
        if datetime.now(timezone.utc) > prazo:
            await interaction.response.send_message(
                "⌛ O prazo de 24 horas pra corrigir esse formulário já passou. Fale com a equipe do servidor.",
                ephemeral=True,
            )
            return

        TEMP_RESPOSTAS[_rkey(self.guild_id, self.tipo_nome, self.user_id)] = []
        modal = ResponderFormularioModal(
            self.guild_id, self.tipo_nome, tipo["perguntas"], pagina=0, defaults=dados["respostas"]
        )
        await interaction.response.send_modal(modal)


# =====================================================================
# TAREFA PERIÓDICA — EXPIRAR FORMULÁRIOS INCOMPLETOS APÓS 24H
# =====================================================================

class Formularios(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.verificar_prazos.start()

    def cog_unload(self):
        self.verificar_prazos.cancel()

    async def cog_load(self):
        # Reregistra os botões persistentes (envio, análise, DM de completar)
        # pra continuarem funcionando depois de reiniciar o bot.
        config = load_config()
        for gid_str, tipos in config.items():
            for nome, tipo in tipos.items():
                if tipo.get("ativo") and tipo.get("canal_envio"):
                    self.bot.add_view(FormularioEnvioView(int(gid_str), nome))

        subs = load_submissoes()
        for gid_str, tipos_subs in subs.items():
            for nome, membros in tipos_subs.items():
                for uid_str, dados in membros.items():
                    if dados.get("status") == "pendente":
                        self.bot.add_view(AnaliseView(int(gid_str), nome, int(uid_str)))
                    elif dados.get("status") == "incompleto":
                        self.bot.add_view(CompletarFormularioView(int(gid_str), nome, int(uid_str)))

    @tasks.loop(minutes=30)
    async def verificar_prazos(self):
        subs = load_submissoes()
        mudou = False
        for gid_str, tipos_subs in subs.items():
            for nome, membros in tipos_subs.items():
                tipo = _carregar_tipo(int(gid_str), nome)
                for uid_str, dados in membros.items():
                    if dados.get("status") != "incompleto" or not dados.get("prazo_incompleto"):
                        continue
                    prazo = datetime.fromisoformat(dados["prazo_incompleto"])
                    if datetime.now(timezone.utc) <= prazo:
                        continue
                    # prazo estourou — marca como reprovado automaticamente
                    dados["status"] = "reprovado"
                    dados["reprovado_por"] = None
                    mudou = True
                    guild = self.bot.get_guild(int(gid_str))
                    if guild and tipo:
                        membro = guild.get_member(int(uid_str))
                        if membro:
                            try:
                                await membro.send(
                                    f"⌛ O prazo de {PRAZO_INCOMPLETO_HORAS}h pra corrigir seu formulário "
                                    f"**{tipo['nome']}** expirou. Ele foi reprovado automaticamente."
                                )
                            except discord.Forbidden:
                                pass
                        canal_resultados = guild.get_channel(tipo.get("canal_resultados")) if tipo else None
                        if canal_resultados:
                            embed = discord.Embed(
                                title=f"⌛ Formulário expirado — {tipo['nome']}",
                                description="O prazo de 24h pra corrigir um formulário incompleto expirou. Reprovado automaticamente.",
                                color=0xE74C3C,
                            )
                            embed.add_field(name="Solicitante", value=f"<@{uid_str}>")
                            try:
                                await canal_resultados.send(embed=embed)
                            except discord.Forbidden:
                                pass
        if mudou:
            save_submissoes(subs)

    @verificar_prazos.before_loop
    async def antes_verificar(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Formularios(bot))
