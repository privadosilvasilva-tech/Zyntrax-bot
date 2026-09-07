import discord
from discord import app_commands
from discord.ext import commands
from cogs._utils_select import RoleSelectComAutocomplete, ChannelSelectComAutocomplete
import asyncio
import json
import logging
import os
import copy
from datetime import datetime, timezone

logger = logging.getLogger("bot.verificacao")

CONFIG_FILE = "config/verificacao_config.json"

CORES = [
    ("Vermelho", "🔴", 0xE74C3C), ("Laranja", "🟠", 0xE67E22), ("Amarelo", "🟡", 0xF1C40F),
    ("Verde", "🟢", 0x2ECC71), ("Azul", "🔵", 0x3498DB), ("Roxo", "🟣", 0x9B59B6),
    ("Rosa", "🌸", 0xFF69B4), ("Ciano", "🔷", 0x1ABC9C), ("Dourado", "🟨", 0xF39C12),
    ("Cinza", "⬜", 0x95A5A6), ("Índigo", "🔹", 0x5865F2), ("Preto", "⚫", 0x23272A),
    ("Branco", "⚪", 0xFFFFFF),
]

# =====================================================================
# VARIÁVEIS DISPONÍVEIS NO PAINEL DE VERIFICAÇÃO
# O painel é uma mensagem única (não é por membro), então as variáveis
# aqui são sobre o servidor, não sobre uma pessoa específica.
# =====================================================================
VARIAVEIS = [
    ("{servidor}", "Nome do servidor"),
    ("{contagem_membros}", "Total de membros do servidor"),
    ("{cargo_verificado}", "Menciona o cargo dado após verificar"),
]


def substituir_variaveis(texto: str | None, guild: discord.Guild, cargo_verificado_id: int | None) -> str | None:
    if not texto:
        return texto
    cargo_txt = f"<@&{cargo_verificado_id}>" if cargo_verificado_id else "*(nenhum cargo configurado)*"
    mapa = {
        "{servidor}": guild.name,
        "{contagem_membros}": str(guild.member_count),
        "{cargo_verificado}": cargo_txt,
    }
    for chave, valor in mapa.items():
        texto = texto.replace(chave, valor)
    return texto


# =====================================================================
# PERSISTÊNCIA
# =====================================================================

def config_padrao() -> dict:
    return {
        "ativo": False,
        "canal_verificacao": None,
        "canal_log": None,
        "cargo_verificado": None,
        "cargo_nao_verificado": None,
        "categoria_liberada": None,
        "dm_ativo": True,
        "dm_mensagem": None,
        "title": "Verificação",
        "description": "Clique no botão abaixo para se verificar e liberar o acesso ao servidor.",
        "footer": None,
        "color": 0x2ECC71,
        "thumbnail": None,
        "image": None,
        "mensagem_id": None,
    }


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config de verificação, recriando: {e}")
    return {}


def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = config_padrao()
    else:
        for chave, valor in config_padrao().items():
            config[gid].setdefault(chave, valor)
    return config[gid]


# =====================================================================
# SESSÕES DE EDIÇÃO EM MEMÓRIA
# =====================================================================

BUILD_SESSIONS: dict = {}


def _key(guild_id: int, user_id: int) -> str:
    return f"{guild_id}:{user_id}"


def carregar_sessao(guild_id: int, user_id: int) -> dict:
    key = _key(guild_id, user_id)
    if key not in BUILD_SESSIONS:
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        BUILD_SESSIONS[key] = copy.deepcopy(gconf)
    return BUILD_SESSIONS[key]


def montar_preview(sessao: dict, guild: discord.Guild) -> discord.Embed:
    titulo = substituir_variaveis(sessao.get("title"), guild, sessao.get("cargo_verificado"))
    descricao = substituir_variaveis(sessao.get("description"), guild, sessao.get("cargo_verificado")) or "*Sem descrição*"
    rodape = substituir_variaveis(sessao.get("footer"), guild, sessao.get("cargo_verificado"))

    embed = discord.Embed(title=titulo, description=descricao, color=sessao.get("color", 0x2ECC71))
    if sessao.get("thumbnail"):
        embed.set_thumbnail(url=sessao["thumbnail"])
    if sessao.get("image"):
        embed.set_image(url=sessao["image"])
    if rodape:
        embed.set_footer(text=rodape)
    return embed


def montar_meta_embed(sessao: dict, nota: str | None = None) -> discord.Embed:
    status = "🟢 Ativo" if sessao.get("ativo") else "🔴 Inativo"
    canal_v = f"<#{sessao['canal_verificacao']}>" if sessao.get("canal_verificacao") else "`-`"
    canal_l = f"<#{sessao['canal_log']}>" if sessao.get("canal_log") else "`-`"
    cargo_v = f"<@&{sessao['cargo_verificado']}>" if sessao.get("cargo_verificado") else "`Nenhum`"
    cargo_nv = f"<@&{sessao['cargo_nao_verificado']}>" if sessao.get("cargo_nao_verificado") else "`Nenhum (opcional)`"
    categoria = f"<#{sessao['categoria_liberada']}>" if sessao.get("categoria_liberada") else "`Nenhuma (só o canal de verificação fica visível)`"
    dm_status = "🟢 Ativada" if sessao.get("dm_ativo", True) else "🔴 Desativada"

    embed = discord.Embed(
        title="🔧 Sistema de Verificação",
        description=f"**{nota}**" if nota else None,
        color=0x5865F2,
    )
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Painel", value=canal_v, inline=True)
    embed.add_field(name="Log", value=canal_l, inline=True)
    embed.add_field(name="Cargo ao verificar", value=cargo_v, inline=True)
    embed.add_field(name="Cargo Não Verificado", value=cargo_nv, inline=True)
    embed.add_field(name="Categoria liberada", value=categoria, inline=True)
    embed.add_field(name="DM pós-verificação", value=dm_status, inline=True)
    embed.set_footer(text="⬇️ Pré-visualização da mensagem que será publicada no canal")
    return embed


def config_valida(sessao: dict) -> bool:
    return bool(sessao.get("canal_verificacao")) and bool(sessao.get("cargo_verificado"))


# =====================================================================
# BLOQUEIO DE CANAIS
# Só ficam visíveis pro cargo "Não Verificado": o canal de verificação
# e os canais dentro da categoria liberada configurada no painel.
# Todo o resto do servidor fica escondido pra esse cargo.
# =====================================================================

async def aplicar_bloqueio_canais(guild: discord.Guild, sessao: dict) -> tuple[int, int]:
    cargo_id = sessao.get("cargo_nao_verificado")
    if not cargo_id:
        return (0, 0)
    cargo = guild.get_role(cargo_id)
    if cargo is None:
        return (0, 0)

    liberados: set[int] = set()
    if sessao.get("canal_verificacao"):
        liberados.add(sessao["canal_verificacao"])
    if sessao.get("categoria_liberada"):
        categoria = guild.get_channel(sessao["categoria_liberada"])
        if isinstance(categoria, discord.CategoryChannel):
            liberados.add(categoria.id)
            for canal in categoria.channels:
                liberados.add(canal.id)

    sucesso, falhas = 0, 0
    for canal in guild.channels:
        pode_ver = canal.id in liberados
        overwrite = canal.overwrites_for(cargo)
        if overwrite.view_channel == pode_ver:
            sucesso += 1
            continue
        overwrite.view_channel = pode_ver
        try:
            await canal.set_permissions(cargo, overwrite=overwrite, reason="Bloqueio de canais - sistema de verificação")
            sucesso += 1
        except (discord.Forbidden, discord.HTTPException):
            falhas += 1
    return (sucesso, falhas)


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
        logger.error(f"Erro no componente '{item}' do painel de verificação", exc_info=error)
        msg = "❌ Ocorreu um erro ao processar essa ação. Tente novamente."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass


# =====================================================================
# MODAIS
# =====================================================================

class TextoModal(discord.ui.Modal, title="Texto do Painel de Verificação"):
    def __init__(self, key: str, parent_view: "VerificacaoBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        sessao = BUILD_SESSIONS[key]
        self.titulo = discord.ui.TextInput(label="Título", required=False, max_length=256, default=sessao.get("title") or "")
        self.descricao = discord.ui.TextInput(
            label="Descrição", style=discord.TextStyle.paragraph, required=False, max_length=2000,
            default=sessao.get("description") or "",
        )
        self.rodape = discord.ui.TextInput(label="Rodapé", required=False, max_length=2048, default=sessao.get("footer") or "")
        self.add_item(self.titulo)
        self.add_item(self.descricao)
        self.add_item(self.rodape)

    async def on_submit(self, interaction: discord.Interaction):
        sessao = BUILD_SESSIONS[self.key]
        sessao["title"] = self.titulo.value.strip() or None
        sessao["description"] = self.descricao.value.strip() or None
        sessao["footer"] = self.rodape.value.strip() or None
        await self.parent_view.atualizar(interaction)


class ImagensModal(discord.ui.Modal, title="Foto e Banner"):
    def __init__(self, key: str, parent_view: "VerificacaoBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        sessao = BUILD_SESSIONS[key]
        self.foto = discord.ui.TextInput(label="Foto (thumbnail)", required=False, placeholder="https://...", default=sessao.get("thumbnail") or "")
        self.banner = discord.ui.TextInput(label="Banner", required=False, placeholder="https://...", default=sessao.get("image") or "")
        self.add_item(self.foto)
        self.add_item(self.banner)

    async def on_submit(self, interaction: discord.Interaction):
        sessao = BUILD_SESSIONS[self.key]
        foto, banner = self.foto.value.strip(), self.banner.value.strip()
        if foto and not foto.startswith("http"):
            await interaction.response.send_message("❌ O link da foto precisa começar com http(s).", ephemeral=True)
            return
        if banner and not banner.startswith("http"):
            await interaction.response.send_message("❌ O link do banner precisa começar com http(s).", ephemeral=True)
            return
        sessao["thumbnail"] = foto or None
        sessao["image"] = banner or None
        await self.parent_view.atualizar(interaction)


class DMModal(discord.ui.Modal, title="Mensagem de DM pós-verificação"):
    def __init__(self, key: str, parent_view: "VerificacaoBuilderView"):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        sessao = BUILD_SESSIONS[key]
        self.mensagem = discord.ui.TextInput(
            label="Mensagem enviada na DM",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1500,
            default=sessao.get("dm_mensagem") or "",
            placeholder="Deixe em branco para usar a mensagem padrão.",
        )
        self.add_item(self.mensagem)

    async def on_submit(self, interaction: discord.Interaction):
        sessao = BUILD_SESSIONS[self.key]
        sessao["dm_mensagem"] = self.mensagem.value.strip() or None
        await self.parent_view.atualizar(interaction)


# =====================================================================
# SELECTS
# =====================================================================

class CorSelect(discord.ui.Select):
    def __init__(self, key: str, parent_view: "VerificacaoBuilderView"):
        self.key = key
        self.parent_view = parent_view
        options = [discord.SelectOption(label=n, emoji=e, value=str(c)) for n, e, c in CORES]
        super().__init__(placeholder="Escolha uma cor", options=options)

    async def callback(self, interaction: discord.Interaction):
        BUILD_SESSIONS[self.key]["color"] = int(self.values[0])
        await self.parent_view.atualizar(interaction)


class CanalSelect(discord.ui.ChannelSelect):
    def __init__(self, key: str, campo: str, parent_view: "VerificacaoBuilderView"):
        self.key = key
        self.campo = campo
        self.parent_view = parent_view
        super().__init__(placeholder="Selecione o canal", channel_types=[discord.ChannelType.text, discord.ChannelType.news])

    async def callback(self, interaction: discord.Interaction):
        BUILD_SESSIONS[self.key][self.campo] = self.values[0].id
        await self.parent_view.atualizar(interaction)


class CargoSelect(discord.ui.RoleSelect):
    def __init__(self, key: str, campo: str, parent_view: "VerificacaoBuilderView"):
        self.key = key
        self.campo = campo
        self.parent_view = parent_view
        super().__init__(placeholder="Selecione o cargo")

    async def callback(self, interaction: discord.Interaction):
        BUILD_SESSIONS[self.key][self.campo] = self.values[0].id
        await self.parent_view.atualizar(interaction)


class CategoriaSelect(discord.ui.ChannelSelect):
    def __init__(self, key: str, parent_view: "VerificacaoBuilderView"):
        self.key = key
        self.parent_view = parent_view
        super().__init__(placeholder="Selecione a categoria liberada", channel_types=[discord.ChannelType.category])

    async def callback(self, interaction: discord.Interaction):
        BUILD_SESSIONS[self.key]["categoria_liberada"] = self.values[0].id
        await self.parent_view.atualizar(interaction)


# =====================================================================
# PAINEL: CONSTRUTOR DA VERIFICAÇÃO
# =====================================================================

class VerificacaoBuilderView(BaseView):
    def __init__(self, key: str, dono_id: int):
        super().__init__(timeout=900)
        self.key = key
        self.dono_id = dono_id

    def _atualizar_labels(self):
        sessao = BUILD_SESSIONS[self.key]
        self.dm_toggle_btn.label = "🔔 DM: Ativada" if sessao.get("dm_ativo", True) else "🔕 DM: Desativada"

    async def atualizar(self, interaction: discord.Interaction):
        sessao = BUILD_SESSIONS[self.key]
        self._atualizar_labels()
        await interaction.response.edit_message(embeds=[montar_meta_embed(sessao), montar_preview(sessao, interaction.guild)], view=self)

    def _persistir(self, guild_id: int):
        sessao = BUILD_SESSIONS[self.key]
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        config[str(guild_id)] = copy.deepcopy(sessao)
        save_config(config)

    def _voltar_button(self, row: int = 1) -> discord.ui.Button:
        btn = discord.ui.Button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=row)

        async def callback(interaction: discord.Interaction):
            sessao = BUILD_SESSIONS[self.key]
            await interaction.response.edit_message(embeds=[montar_meta_embed(sessao), montar_preview(sessao, interaction.guild)], view=self)

        btn.callback = callback
        return btn

    @discord.ui.button(label="📝 Texto", style=discord.ButtonStyle.primary, row=0)
    async def texto_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TextoModal(self.key, self))

    @discord.ui.button(label="🖼️ Imagens", style=discord.ButtonStyle.primary, row=0)
    async def imagens_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImagensModal(self.key, self))

    @discord.ui.button(label="🎨 Cor", style=discord.ButtonStyle.primary, row=0)
    async def cor_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessao = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CorSelect(self.key, self))
        view.add_item(self._voltar_button())
        await interaction.response.edit_message(embeds=[montar_meta_embed(sessao), montar_preview(sessao, interaction.guild)], view=view)

    @discord.ui.button(label="ℹ️ Variáveis", style=discord.ButtonStyle.secondary, row=0)
    async def variaveis_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        linhas = [f"`{var}` — {desc}" for var, desc in VARIAVEIS]
        await interaction.response.send_message(
            "**Variáveis disponíveis** (toque e segure pra copiar):\n" + "\n".join(linhas), ephemeral=True
        )

    @discord.ui.button(label="📺 Canal do Painel", style=discord.ButtonStyle.secondary, row=1)
    async def canal_painel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_canal_select(interaction, "canal_verificacao")

    @discord.ui.button(label="📊 Canal de Log", style=discord.ButtonStyle.secondary, row=1)
    async def canal_log_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_canal_select(interaction, "canal_log")

    @discord.ui.button(label="📁 Categoria Liberada", style=discord.ButtonStyle.secondary, row=1)
    async def categoria_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessao = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CategoriaSelect(self.key, self))
        view.add_item(self._voltar_button())
        await interaction.response.edit_message(embeds=[montar_meta_embed(sessao), montar_preview(sessao, interaction.guild)], view=view)

    async def _abrir_canal_select(self, interaction: discord.Interaction, campo: str):
        sessao = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CanalSelect(self.key, campo, self))
        view.add_item(self._voltar_button())
        await interaction.response.edit_message(embeds=[montar_meta_embed(sessao), montar_preview(sessao, interaction.guild)], view=view)

    @discord.ui.button(label="🎭 Cargo ao Verificar", style=discord.ButtonStyle.secondary, row=2)
    async def cargo_verificado_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_cargo_select(interaction, "cargo_verificado")

    @discord.ui.button(label="🚫 Cargo Não Verificado", style=discord.ButtonStyle.secondary, row=2)
    async def cargo_nao_verificado_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_cargo_select(interaction, "cargo_nao_verificado")

    @discord.ui.button(label="💌 Mensagem DM", style=discord.ButtonStyle.secondary, row=2)
    async def dm_msg_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DMModal(self.key, self))

    async def _abrir_cargo_select(self, interaction: discord.Interaction, campo: str):
        sessao = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CargoSelect(self.key, campo, self))
        view.add_item(self._voltar_button())
        await interaction.response.edit_message(embeds=[montar_meta_embed(sessao), montar_preview(sessao, interaction.guild)], view=view)

    @discord.ui.button(label="💾 Salvar", style=discord.ButtonStyle.success, row=3)
    async def salvar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._persistir(interaction.guild_id)
        sessao = BUILD_SESSIONS[self.key]
        self._atualizar_labels()
        await interaction.response.edit_message(
            embeds=[montar_meta_embed(sessao, nota="✅ Salvo!"), montar_preview(sessao, interaction.guild)], view=self
        )

    @discord.ui.button(label="🔒 Aplicar Bloqueio", style=discord.ButtonStyle.success, row=3)
    async def aplicar_bloqueio_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessao = BUILD_SESSIONS[self.key]
        if not sessao.get("cargo_nao_verificado"):
            await interaction.response.send_message(
                "❌ Configure o cargo \"Não Verificado\" antes de aplicar o bloqueio.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        sucesso, falhas = await aplicar_bloqueio_canais(interaction.guild, sessao)
        aviso = f"🔒 Bloqueio aplicado em {sucesso} canal(is)."
        if falhas:
            aviso += f" ⚠️ {falhas} falharam — confira se o cargo do bot está ACIMA do cargo não verificado e tem permissão de Gerenciar Canais."
        await interaction.followup.send(aviso, ephemeral=True)

    @discord.ui.button(label="📨 Publicar / Atualizar", style=discord.ButtonStyle.success, row=3)
    async def publicar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessao = BUILD_SESSIONS[self.key]
        if not config_valida(sessao):
            await interaction.response.send_message("❌ Configure o canal do painel e o cargo ao verificar antes de publicar.", ephemeral=True)
            return
        canal = interaction.guild.get_channel(sessao["canal_verificacao"])
        if canal is None:
            await interaction.response.send_message("❌ Canal do painel não encontrado.", ephemeral=True)
            return

        embed = montar_preview(sessao, interaction.guild)
        view_pub = VerificarView(interaction.guild_id)

        try:
            if sessao.get("mensagem_id"):
                try:
                    msg = await canal.fetch_message(sessao["mensagem_id"])
                    await msg.edit(embed=embed, view=view_pub)
                except discord.NotFound:
                    msg = await canal.send(embed=embed, view=view_pub)
                    sessao["mensagem_id"] = msg.id
            else:
                msg = await canal.send(embed=embed, view=view_pub)
                sessao["mensagem_id"] = msg.id
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sem permissão para enviar/editar mensagens nesse canal.", ephemeral=True)
            return

        sessao["ativo"] = True
        self._persistir(interaction.guild_id)

        aviso_bloqueio = ""
        if sessao.get("cargo_nao_verificado"):
            sucesso, falhas = await aplicar_bloqueio_canais(interaction.guild, sessao)
            aviso_bloqueio = f"\n🔒 Bloqueio de canais aplicado ({sucesso} ok"
            if falhas:
                aviso_bloqueio += f", {falhas} falharam"
            aviso_bloqueio += ")."

        nota = f"✅ Publicado em {canal.mention} e ativado!{aviso_bloqueio}"
        await interaction.response.edit_message(
            embeds=[montar_meta_embed(sessao, nota=nota), montar_preview(sessao, interaction.guild)],
            view=self,
        )

    @discord.ui.button(label="🔴 Desativar", style=discord.ButtonStyle.danger, row=4)
    async def desativar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessao = BUILD_SESSIONS[self.key]
        sessao["ativo"] = False
        self._persistir(interaction.guild_id)
        await self.atualizar(interaction)

    @discord.ui.button(label="🔔 DM: Ativada", style=discord.ButtonStyle.secondary, row=4)
    async def dm_toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessao = BUILD_SESSIONS[self.key]
        sessao["dm_ativo"] = not sessao.get("dm_ativo", True)
        self._persistir(interaction.guild_id)
        await self.atualizar(interaction)

    @discord.ui.button(label="◀️ Voltar ao Menu", style=discord.ButtonStyle.secondary, row=4)
    async def voltar_menu_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.configuracoes import PainelConfiguracoesView

        view = PainelConfiguracoesView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)


def abrir_painel_verificacao(guild_id: int, user_id: int) -> tuple[str, VerificacaoBuilderView, dict]:
    key = _key(guild_id, user_id)
    BUILD_SESSIONS[key] = carregar_sessao(guild_id, user_id)
    view = VerificacaoBuilderView(key, user_id)
    view._atualizar_labels()
    return key, view, BUILD_SESSIONS[key]


# =====================================================================
# BOTÃO PERSISTENTE — VERIFICAR-SE
# =====================================================================

class VerificarView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.verificar.custom_id = f"verificacao_botao:{guild_id}"

    @discord.ui.button(label="✅ Verificar-se", style=discord.ButtonStyle.success)
    async def verificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        sessao = get_guild_config(config, self.guild_id)

        if not sessao.get("ativo") or not sessao.get("cargo_verificado"):
            await interaction.response.send_message("❌ A verificação não está disponível no momento.", ephemeral=True)
            return

        membro = interaction.user
        cargo_verificado = interaction.guild.get_role(sessao["cargo_verificado"])
        if cargo_verificado is None:
            await interaction.response.send_message("❌ O cargo de verificado não existe mais — avise um administrador.", ephemeral=True)
            return

        if cargo_verificado in membro.roles:
            await interaction.response.send_message("✅ Você já está verificado!", ephemeral=True)
            return

        try:
            await membro.add_roles(cargo_verificado, reason="Verificação concluída")
            cargo_nao_verificado = (
                interaction.guild.get_role(sessao["cargo_nao_verificado"]) if sessao.get("cargo_nao_verificado") else None
            )
            if cargo_nao_verificado and cargo_nao_verificado in membro.roles:
                await membro.remove_roles(cargo_nao_verificado, reason="Verificação concluída")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não consegui te dar o cargo — o cargo do bot precisa ficar ACIMA do cargo de verificado na lista de cargos.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("✅ Verificação concluída! Bem-vindo(a) ao servidor.", ephemeral=True)

        asyncio.create_task(self._enviar_dm_pos_verificacao(membro, sessao))

        canal_log = interaction.guild.get_channel(sessao["canal_log"]) if sessao.get("canal_log") else None
        if canal_log:
            idade_dias = (datetime.now(timezone.utc) - membro.created_at).days
            embed = discord.Embed(
                title="✅ Novo Membro Verificado",
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_thumbnail(url=membro.display_avatar.url)
            embed.add_field(name="Membro", value=membro.mention, inline=True)
            embed.add_field(name="Cargo recebido", value=cargo_verificado.mention, inline=True)
            embed.add_field(name="Conta criada há", value=f"{idade_dias} dias", inline=True)
            embed.add_field(name="Entrou no servidor em", value=discord.utils.format_dt(membro.joined_at, style="F") if membro.joined_at else "—", inline=False)
            embed.set_footer(text=f"ID: {membro.id}")
            try:
                await canal_log.send(embed=embed)
            except discord.Forbidden:
                logger.warning("Sem permissão para postar no canal de log de verificação")

    async def _enviar_dm_pos_verificacao(self, membro: discord.Member, sessao: dict):
        """Manda uma DM pro membro 5 segundos depois de verificar (dá tempo dos
        cargos/permissões propagarem no Discord antes de avisar ele)."""
        await asyncio.sleep(5)
        if not sessao.get("dm_ativo", True):
            return
        texto = sessao.get("dm_mensagem") or (
            f"✅ Você foi verificado(a) com sucesso em **{membro.guild.name}**!\n"
            f"Agora você já tem acesso aos canais liberados do servidor. Seja bem-vindo(a)! 🎉"
        )
        texto = substituir_variaveis(texto, membro.guild, sessao.get("cargo_verificado"))
        embed = discord.Embed(description=texto, color=sessao.get("color", 0x2ECC71))
        embed.set_author(name=membro.guild.name, icon_url=membro.guild.icon.url if membro.guild.icon else None)
        try:
            await membro.send(embed=embed)
        except discord.Forbidden:
            logger.info(f"Não consegui mandar DM de verificação pra {membro.id} (DMs fechadas para o bot).")
        except discord.HTTPException as e:
            logger.warning(f"Erro ao enviar DM pós-verificação: {e}")


# =====================================================================
# COG
# =====================================================================

class Verificacao(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        config = load_config()
        for gid_str, sessao in config.items():
            if sessao.get("ativo") and sessao.get("canal_verificacao"):
                self.bot.add_view(VerificarView(int(gid_str)))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = load_config()
        sessao = config.get(str(member.guild.id))
        if not sessao or not sessao.get("ativo") or not sessao.get("cargo_nao_verificado"):
            return
        cargo = member.guild.get_role(sessao["cargo_nao_verificado"])
        if cargo:
            try:
                await member.add_roles(cargo, reason="Aguardando verificação")
            except discord.Forbidden:
                logger.warning(f"Sem permissão para dar o cargo de não verificado no servidor {member.guild.id}")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        # Garante que qualquer canal novo já nasça bloqueado pro cargo de
        # não verificado, a não ser que esteja na categoria liberada.
        config = load_config()
        sessao = config.get(str(channel.guild.id))
        if not sessao or not sessao.get("ativo") or not sessao.get("cargo_nao_verificado"):
            return
        await aplicar_bloqueio_canais(channel.guild, sessao)


async def setup(bot: commands.Bot):
    await bot.add_cog(Verificacao(bot))
