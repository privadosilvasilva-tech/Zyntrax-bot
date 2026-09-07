import discord
from discord import app_commands
from discord.ext import commands
import json
import logging
import os
import copy
from datetime import datetime, timezone

logger = logging.getLogger("bot.embeds")

CONFIG_FILE = "config/embeds_config.json"
MAX_BOTOES = 5

# ---------------------- TEMAS (fácil de adicionar mais) ----------------------
# Para criar um tema novo, basta adicionar uma linha aqui. Não há limite.
TEMAS = {
    "regras":        {"label": "Regras",        "emoji": "📜", "color": 0xE74C3C},
    "aviso":         {"label": "Aviso",         "emoji": "⚠️", "color": 0xF1C40F},
    "anuncio":       {"label": "Anúncio",       "emoji": "📢", "color": 0x3498DB},
    "informacao":    {"label": "Informação",    "emoji": "ℹ️", "color": 0x5865F2},
    "sucesso":       {"label": "Sucesso",       "emoji": "✅", "color": 0x2ECC71},
    "erro":          {"label": "Erro",          "emoji": "❌", "color": 0xC0392B},
    "evento":        {"label": "Evento",        "emoji": "🎉", "color": 0x9B59B6},
    "boasvindas":    {"label": "Boas-vindas",   "emoji": "👋", "color": 0x1ABC9C},
    "despedida":     {"label": "Despedida",     "emoji": "🚪", "color": 0xE67E22},
    "manutencao":    {"label": "Manutenção",    "emoji": "🛠️", "color": 0x95A5A6},
    "parceria":      {"label": "Parceria",      "emoji": "🤝", "color": 0xFF69B4},
    "sorteio":       {"label": "Sorteio",       "emoji": "🎁", "color": 0xF39C12},
    "atualizacao":   {"label": "Atualização",   "emoji": "🆕", "color": 0x00BFFF},
    "suporte":       {"label": "Suporte",       "emoji": "🎫", "color": 0x2C3E50},
    "denuncia":      {"label": "Denúncia",      "emoji": "🚨", "color": 0xB22222},
    "verificacao":   {"label": "Verificação",   "emoji": "🔑", "color": 0x27AE60},
    "cargo":         {"label": "Cargo",         "emoji": "🎭", "color": 0x8E44AD},
    "votacao":       {"label": "Votação",       "emoji": "🗳️", "color": 0x16A085},
    "comunidade":    {"label": "Comunidade",    "emoji": "🌐", "color": 0x3498DB},
    "personalizado": {"label": "Personalizado", "emoji": "🎨", "color": 0x2C2F33},
}

# ---------------------- PALETA DE CORES (escolher, não digitar) ----------------------
CORES = [
    ("Vermelho", "🔴", 0xE74C3C),
    ("Laranja", "🟠", 0xE67E22),
    ("Amarelo", "🟡", 0xF1C40F),
    ("Verde", "🟢", 0x2ECC71),
    ("Azul", "🔵", 0x3498DB),
    ("Roxo", "🟣", 0x9B59B6),
    ("Rosa", "🌸", 0xFF69B4),
    ("Ciano", "🔷", 0x1ABC9C),
    ("Dourado", "🟨", 0xF39C12),
    ("Cinza", "⬜", 0x95A5A6),
    ("Índigo", "🔹", 0x5865F2),
    ("Vinho", "🟥", 0x800020),
    ("Preto", "⚫", 0x23272A),
    ("Branco", "⚪", 0xFFFFFF),
    ("Marrom", "🟤", 0x8B4513),
]

BUILD_SESSIONS: dict = {}


def _session_key(guild_id: int, user_id: int) -> str:
    return f"{guild_id}:{user_id}"


def nova_sessao() -> dict:
    return {
        "title": None,
        "description": None,
        "footer": None,
        "color": 0x2C2F33,
        "thumbnail": None,
        "image": None,
        "theme": None,
        "buttons": [],
        "mentions": [],
        "_editing_name": None,
        "_pending_channel_button": None,
    }


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config de embeds, recriando: {e}")
    return {}


def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_guild_saved(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {"saved": {}}
    config[gid].setdefault("saved", {})
    return config[gid]["saved"]


def montar_preview(session: dict) -> discord.Embed:
    embed = discord.Embed(
        title=session.get("title") or None,
        description=session.get("description") or "*Sem descrição — use '📝 Texto' para editar*",
        color=session.get("color", 0x2C2F33),
    )
    if session.get("thumbnail"):
        embed.set_thumbnail(url=session["thumbnail"])
    if session.get("image"):
        embed.set_image(url=session["image"])
    if session.get("footer"):
        embed.set_footer(text=session["footer"])
    return embed


def montar_meta_texto(session: dict) -> str:
    tema = session.get("theme")
    tema_txt = f"{TEMAS[tema]['emoji']} {TEMAS[tema]['label']}" if tema and tema in TEMAS else "Nenhum"
    botoes = session.get("buttons", [])
    mencoes = session.get("mentions", [])
    partes = [
        "🔧 **Construtor de Embed**",
        f"Tema: `{tema_txt}` • Botões: `{len(botoes)}/{MAX_BOTOES}` • Menções: {' '.join(mencoes) if mencoes else '`Nenhuma`'}",
    ]
    if session.get("_editing_name"):
        partes.append(f"✏️ Editando embed salva: **{session['_editing_name']}**")
    return "\n".join(partes)


def montar_view_final(botoes: list) -> discord.ui.View | None:
    if not botoes:
        return None
    view = discord.ui.View(timeout=None)
    for b in botoes[:MAX_BOTOES]:
        view.add_item(discord.ui.Button(label=b["label"][:80], url=b["url"], style=discord.ButtonStyle.link))
    return view


def embed_valida(session: dict) -> bool:
    return bool(session.get("title") or session.get("description"))


# ---------------------- VIEW BASE COM TRATAMENTO DE ERRO ----------------------

class BaseView(discord.ui.View):
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        logger.error(f"Erro no componente '{item}' do construtor de embeds", exc_info=error)
        msg = "❌ Ocorreu um erro ao processar essa ação. Tente novamente."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass


# ---------------------- MODAIS ----------------------

class TextoModal(discord.ui.Modal, title="Texto da Embed"):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        session = BUILD_SESSIONS[key]
        self.titulo = discord.ui.TextInput(
            label="Título (destacado no topo)",
            required=False,
            max_length=256,
            default=session.get("title") or "",
        )
        self.descricao = discord.ui.TextInput(
            label="Descrição",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=4000,
            default=session.get("description") or "",
        )
        self.rodape = discord.ui.TextInput(
            label="Rodapé (footer)",
            required=False,
            max_length=2048,
            default=session.get("footer") or "",
        )
        self.add_item(self.titulo)
        self.add_item(self.descricao)
        self.add_item(self.rodape)

    async def on_submit(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        session["title"] = self.titulo.value.strip() or None
        session["description"] = self.descricao.value.strip() or None
        session["footer"] = self.rodape.value.strip() or None
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


class ImagensModal(discord.ui.Modal, title="Foto e Banner"):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        session = BUILD_SESSIONS[key]
        self.foto = discord.ui.TextInput(
            label="Foto (thumbnail - imagem pequena)",
            required=False,
            placeholder="https://...",
            default=session.get("thumbnail") or "",
        )
        self.banner = discord.ui.TextInput(
            label="Banner (imagem grande)",
            required=False,
            placeholder="https://...",
            default=session.get("image") or "",
        )
        self.add_item(self.foto)
        self.add_item(self.banner)

    async def on_submit(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        foto = self.foto.value.strip()
        banner = self.banner.value.strip()
        if foto and not foto.startswith("http"):
            await interaction.response.send_message("❌ O link da foto precisa começar com http(s).", ephemeral=True)
            return
        if banner and not banner.startswith("http"):
            await interaction.response.send_message("❌ O link do banner precisa começar com http(s).", ephemeral=True)
            return
        session["thumbnail"] = foto or None
        session["image"] = banner or None
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


class BotaoURLModal(discord.ui.Modal, title="Novo Botão de Link"):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        self.texto = discord.ui.TextInput(label="Texto do botão", required=True, max_length=80)
        self.url = discord.ui.TextInput(label="Link (URL)", required=True, placeholder="https://...")
        self.add_item(self.texto)
        self.add_item(self.url)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.url.value.strip().startswith("http"):
            await interaction.response.send_message("❌ O link precisa começar com http(s).", ephemeral=True)
            return
        session = BUILD_SESSIONS[self.key]
        session["buttons"].append({"label": self.texto.value.strip(), "url": self.url.value.strip()})
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


class BotaoCanalLabelModal(discord.ui.Modal, title="Texto do Botão de Canal"):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        self.texto = discord.ui.TextInput(label="Texto do botão", required=True, max_length=80)
        self.add_item(self.texto)

    async def on_submit(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        canal_id = session.pop("_pending_channel_button", None)
        if not canal_id:
            await interaction.response.send_message("❌ Canal não encontrado, tente novamente.", ephemeral=True)
            return
        url = f"https://discord.com/channels/{interaction.guild_id}/{canal_id}"
        session["buttons"].append({"label": self.texto.value.strip(), "url": url})
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


class SalvarEmbedModal(discord.ui.Modal, title="Salvar Embed"):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        session = BUILD_SESSIONS[key]
        self.nome = discord.ui.TextInput(
            label="Nome para salvar",
            required=True,
            max_length=60,
            default=session.get("_editing_name") or "",
        )
        self.add_item(self.nome)

    async def on_submit(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        if not embed_valida(session):
            await interaction.response.send_message("❌ Adicione ao menos um título ou descrição antes de salvar.", ephemeral=True)
            return
        nome = self.nome.value.strip()
        config = load_config()
        saved = get_guild_saved(config, interaction.guild_id)
        dados = copy.deepcopy(session)
        dados.pop("_editing_name", None)
        dados.pop("_pending_channel_button", None)
        saved[nome] = dados
        save_config(config)
        session["_editing_name"] = nome
        await interaction.response.edit_message(
            content=f"✅ Embed salva como **{nome}**!\n\n" + montar_meta_texto(session),
            embed=montar_preview(session),
            view=self.parent_view,
        )


# ---------------------- SELECTS: COR E TEMA ----------------------

class CorSelect(discord.ui.Select):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        self.key = key
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=nome, emoji=emoji, value=str(cor))
            for nome, emoji, cor in CORES
        ]
        super().__init__(placeholder="Escolha uma cor", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        session["color"] = int(self.values[0])
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


class CorView(BaseView):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__(timeout=180)
        self.add_item(CorSelect(key, parent_view))
        self.add_item(VoltarButton(key, parent_view))


class TemaSelect(discord.ui.Select):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        self.key = key
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=info["label"], emoji=info["emoji"], value=chave)
            for chave, info in TEMAS.items()
        ]
        super().__init__(placeholder="Escolha um tema", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        chave = self.values[0]
        info = TEMAS[chave]
        session["theme"] = chave
        session["color"] = info["color"]
        if not session.get("title"):
            session["title"] = f"{info['emoji']} {info['label']}"
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


class TemaView(BaseView):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__(timeout=180)
        self.add_item(TemaSelect(key, parent_view))
        self.add_item(VoltarButton(key, parent_view))


# ---------------------- BOTÃO: URL OU CANAL ----------------------

class CanalParaBotaoSelect(discord.ui.ChannelSelect):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        self.key = key
        self.parent_view = parent_view
        super().__init__(
            placeholder="Selecione o canal de destino do botão",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        if len(session["buttons"]) >= MAX_BOTOES:
            await interaction.response.send_message(f"❌ Limite de {MAX_BOTOES} botões atingido.", ephemeral=True)
            return
        session["_pending_channel_button"] = self.values[0].id
        await interaction.response.send_modal(BotaoCanalLabelModal(self.key, self.parent_view))


class CanalParaBotaoView(BaseView):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__(timeout=180)
        self.add_item(CanalParaBotaoSelect(key, parent_view))
        self.add_item(VoltarButton(key, parent_view))


class BotaoTipoView(BaseView):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__(timeout=180)
        self.key = key
        self.parent_view = parent_view

    @discord.ui.button(label="🔗 Link (URL)", style=discord.ButtonStyle.primary)
    async def url_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        if len(session["buttons"]) >= MAX_BOTOES:
            await interaction.response.send_message(f"❌ Limite de {MAX_BOTOES} botões atingido.", ephemeral=True)
            return
        await interaction.response.send_modal(BotaoURLModal(self.key, self.parent_view))

    @discord.ui.button(label="📺 Canal do Servidor", style=discord.ButtonStyle.primary)
    async def canal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session),
            embed=montar_preview(session),
            view=CanalParaBotaoView(self.key, self.parent_view),
        )

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


# ---------------------- MARCAR CARGO / CANAL (menção real) ----------------------

class CargoMencaoSelect(discord.ui.RoleSelect):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        self.key = key
        self.parent_view = parent_view
        super().__init__(placeholder="Selecione o cargo para marcar", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        mencao = self.values[0].mention
        if mencao not in session["mentions"]:
            session["mentions"].append(mencao)
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


class CanalMencaoSelect(discord.ui.ChannelSelect):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        self.key = key
        self.parent_view = parent_view
        super().__init__(placeholder="Selecione o canal para marcar", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        mencao = self.values[0].mention
        if mencao not in session["mentions"]:
            session["mentions"].append(mencao)
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


class MarcarTipoView(BaseView):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__(timeout=180)
        self.key = key
        self.parent_view = parent_view

    @discord.ui.button(label="🎭 Marcar Cargo", style=discord.ButtonStyle.primary)
    async def cargo_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.add_item(CargoMencaoSelect(self.key, self.parent_view))
        view.add_item(VoltarButton(self.key, self.parent_view))
        await interaction.response.edit_message(content=montar_meta_texto(session), embed=montar_preview(session), view=view)

    @discord.ui.button(label="📺 Marcar Canal", style=discord.ButtonStyle.primary)
    async def canal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.add_item(CanalMencaoSelect(self.key, self.parent_view))
        view.add_item(VoltarButton(self.key, self.parent_view))
        await interaction.response.edit_message(content=montar_meta_texto(session), embed=montar_preview(session), view=view)

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


# ---------------------- MINHAS EMBEDS (usar / editar / excluir) ----------------------

class SavedEmbedsSelect(discord.ui.Select):
    def __init__(self, key: str, parent_view: "EmbedBuilderView", nomes: list):
        self.key = key
        self.parent_view = parent_view
        options = [discord.SelectOption(label=nome[:100], value=nome) for nome in nomes[:25]]
        super().__init__(placeholder="Selecione uma embed salva", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        nome = self.values[0]
        view = SavedEmbedActionsView(self.key, self.parent_view, nome)
        await interaction.response.edit_message(
            content=f"📂 Embed selecionada: **{nome}**\n" + montar_meta_texto(session),
            embed=montar_preview(session),
            view=view,
        )


class SavedEmbedsView(BaseView):
    def __init__(self, key: str, parent_view: "EmbedBuilderView", nomes: list):
        super().__init__(timeout=180)
        self.add_item(SavedEmbedsSelect(key, parent_view, nomes))
        self.add_item(VoltarButton(key, parent_view))


class SavedEmbedActionsView(BaseView):
    def __init__(self, key: str, parent_view: "EmbedBuilderView", nome: str):
        super().__init__(timeout=180)
        self.key = key
        self.parent_view = parent_view
        self.nome = nome

    @discord.ui.button(label="✏️ Editar", style=discord.ButtonStyle.primary)
    async def editar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        saved = get_guild_saved(config, interaction.guild_id)
        dados = saved.get(self.nome)
        if not dados:
            await interaction.response.send_message("❌ Essa embed não existe mais.", ephemeral=True)
            return
        session = BUILD_SESSIONS[self.key]
        session.clear()
        session.update(copy.deepcopy(dados))
        session["_editing_name"] = self.nome
        session["_pending_channel_button"] = None
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )

    @discord.ui.button(label="📤 Enviar", style=discord.ButtonStyle.success)
    async def enviar(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.add_item(EnviarChannelSelect(self.key, self.parent_view, nome_salvo=self.nome))
        view.add_item(VoltarButton(self.key, self.parent_view))
        await interaction.response.edit_message(content=montar_meta_texto(session), embed=montar_preview(session), view=view)

    @discord.ui.button(label="🗑️ Excluir", style=discord.ButtonStyle.danger)
    async def excluir(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        saved = get_guild_saved(config, interaction.guild_id)
        saved.pop(self.nome, None)
        save_config(config)
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=f"🗑️ Embed **{self.nome}** excluída.\n" + montar_meta_texto(session),
            embed=montar_preview(session),
            view=self.parent_view,
        )

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


# ---------------------- ENVIAR ----------------------

class EnviarChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, key: str, parent_view: "EmbedBuilderView", nome_salvo: str = None):
        self.key = key
        self.parent_view = parent_view
        self.nome_salvo = nome_salvo
        super().__init__(
            placeholder="Selecione o canal de destino",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if self.nome_salvo:
            config = load_config()
            saved = get_guild_saved(config, interaction.guild_id)
            dados = saved.get(self.nome_salvo)
            if not dados:
                await interaction.response.send_message("❌ Essa embed não existe mais.", ephemeral=True)
                return
            session_dados = dados
        else:
            session_dados = BUILD_SESSIONS[self.key]

        if not embed_valida(session_dados):
            await interaction.response.send_message("❌ Adicione ao menos um título ou descrição antes de enviar.", ephemeral=True)
            return

        canal = self.values[0]
        embed = montar_preview(session_dados)
        view_final = montar_view_final(session_dados.get("buttons", []))
        conteudo = " ".join(session_dados.get("mentions", [])) or None

        try:
            resolved = await interaction.guild.fetch_channel(canal.id)
            await resolved.send(content=conteudo, embed=embed, view=view_final)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para enviar mensagens nesse canal.", ephemeral=True)
            return
        except Exception as e:
            logger.error("Erro ao enviar embed", exc_info=e)
            await interaction.response.send_message("❌ Ocorreu um erro ao enviar a embed.", ephemeral=True)
            return

        session = BUILD_SESSIONS.get(self.key, session_dados)
        await interaction.response.edit_message(
            content=f"✅ Embed enviada em {canal.mention}!\n" + montar_meta_texto(session),
            embed=montar_preview(session),
            view=self.parent_view,
        )


# ---------------------- BOTÃO VOLTAR (reutilizável) ----------------------

class VoltarButton(discord.ui.Button):
    def __init__(self, key: str, parent_view: "EmbedBuilderView"):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
        self.key = key
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=self.parent_view
        )


# ---------------------- PAINEL PRINCIPAL ----------------------

class EmbedBuilderView(BaseView):
    def __init__(self, key: str):
        super().__init__(timeout=600)
        self.key = key

    @discord.ui.button(label="📝 Texto", style=discord.ButtonStyle.primary, row=0)
    async def texto_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TextoModal(self.key, self))

    @discord.ui.button(label="🖼️ Imagens", style=discord.ButtonStyle.primary, row=0)
    async def imagens_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImagensModal(self.key, self))

    @discord.ui.button(label="🎨 Cor", style=discord.ButtonStyle.primary, row=0)
    async def cor_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=CorView(self.key, self)
        )

    @discord.ui.button(label="🏷️ Tema", style=discord.ButtonStyle.primary, row=0)
    async def tema_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=TemaView(self.key, self)
        )

    @discord.ui.button(label="🔗 Botão", style=discord.ButtonStyle.secondary, row=1)
    async def botao_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=BotaoTipoView(self.key, self)
        )

    @discord.ui.button(label="📣 Marcar", style=discord.ButtonStyle.secondary, row=1)
    async def marcar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=MarcarTipoView(self.key, self)
        )

    @discord.ui.button(label="🧹 Limpar Tudo", style=discord.ButtonStyle.secondary, row=1)
    async def limpar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        BUILD_SESSIONS[self.key] = nova_sessao()
        session = BUILD_SESSIONS[self.key]
        await interaction.response.edit_message(
            content="🧹 Painel limpo.\n" + montar_meta_texto(session), embed=montar_preview(session), view=self
        )

    @discord.ui.button(label="💾 Salvar", style=discord.ButtonStyle.success, row=2)
    async def salvar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SalvarEmbedModal(self.key, self))

    @discord.ui.button(label="📂 Minhas Embeds", style=discord.ButtonStyle.success, row=2)
    async def minhas_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        saved = get_guild_saved(config, interaction.guild_id)
        session = BUILD_SESSIONS[self.key]
        if not saved:
            await interaction.response.edit_message(
                content="⚠️ Nenhuma embed salva ainda.\n" + montar_meta_texto(session),
                embed=montar_preview(session),
                view=self,
            )
            return
        await interaction.response.edit_message(
            content=montar_meta_texto(session),
            embed=montar_preview(session),
            view=SavedEmbedsView(self.key, self, list(saved.keys())),
        )

    @discord.ui.button(label="📤 Enviar", style=discord.ButtonStyle.success, row=2)
    async def enviar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        if not embed_valida(session):
            await interaction.response.send_message("❌ Adicione ao menos um título ou descrição antes de enviar.", ephemeral=True)
            return
        view = BaseView(timeout=180)
        view.add_item(EnviarChannelSelect(self.key, self))
        view.add_item(VoltarButton(self.key, self))
        await interaction.response.edit_message(content=montar_meta_texto(session), embed=montar_preview(session), view=view)

    @discord.ui.button(label="❌ Fechar", style=discord.ButtonStyle.danger, row=3)
    async def fechar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        BUILD_SESSIONS.pop(self.key, None)
        await interaction.response.edit_message(content="✅ Painel de embeds fechado.", embed=None, view=None)


# ---------------------- COG ----------------------

class Embeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Abrir o construtor de embeds personalizadas")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def embed_cmd(self, interaction: discord.Interaction):
        key = _session_key(interaction.guild_id, interaction.user.id)
        BUILD_SESSIONS[key] = nova_sessao()
        session = BUILD_SESSIONS[key]
        view = EmbedBuilderView(key)
        await interaction.response.send_message(
            content=montar_meta_texto(session), embed=montar_preview(session), view=view, ephemeral=True
        )

    @embed_cmd.error
    async def embed_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você precisa ser administrador para usar o construtor de embeds."
        elif isinstance(error, app_commands.NoPrivateMessage):
            msg = "❌ Esse comando só pode ser usado dentro de um servidor."
        else:
            logger.error("Erro no comando /embed", exc_info=error)
            msg = "❌ Ocorreu um erro inesperado ao executar o comando."

        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Embeds(bot))

