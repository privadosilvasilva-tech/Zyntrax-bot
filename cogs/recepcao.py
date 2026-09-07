import discord
from discord import app_commands
from discord.ext import commands
from cogs._utils_select import RoleSelectComAutocomplete, ChannelSelectComAutocomplete
import json
import logging
import os
import copy
from datetime import datetime, timezone

logger = logging.getLogger("bot.recepcao")

CONFIG_FILE = "config/recepcao_config.json"

# =====================================================================
# VARIÁVEIS DISPONÍVEIS
# Usadas no título, descrição e rodapé da embed de Entrada/Saída.
# Pra adicionar uma nova variável: só adicionar uma linha aqui em
# VARIAVEIS e uma linha correspondente na função substituir_variaveis().
# =====================================================================
VARIAVEIS = [
    ("{membro}", "Nome do membro (sem marcar)"),
    ("{membro_mencao}", "Marca o membro de verdade (@fulano)"),
    ("{membro_tag}", "Nome#0000 / @usuario do membro"),
    ("{servidor}", "Nome do servidor"),
    ("{contagem_membros}", "Total de membros depois da entrada/saída"),
    ("{contagem_membros_ordinal}", 'Ex: "342º membro"'),
    ("{data_entrada}", "Data/hora do evento (entrada ou saída)"),
    ("{conta_criada_em}", "Data de criação da conta Discord do membro"),
    ("{avatar_url}", "Link do avatar do membro (use em Foto/Banner)"),
]


def _ordinal(n: int) -> str:
    return f"{n}º"


def substituir_variaveis(texto: str | None, member: discord.Member, guild: discord.Guild) -> str | None:
    if not texto:
        return texto
    agora = datetime.now(timezone.utc)
    mapa = {
        "{membro}": member.display_name,
        "{membro_mencao}": member.mention,
        "{membro_tag}": str(member),
        "{servidor}": guild.name,
        "{contagem_membros}": str(guild.member_count),
        "{contagem_membros_ordinal}": _ordinal(guild.member_count),
        "{data_entrada}": discord.utils.format_dt(agora, style="F"),
        "{conta_criada_em}": discord.utils.format_dt(member.created_at, style="F"),
        "{avatar_url}": str(member.display_avatar.url),
    }
    for chave, valor in mapa.items():
        texto = texto.replace(chave, valor)
    return texto


# ---------------------- CONFIG (persistência em JSON) ----------------------

def secao_padrao() -> dict:
    return {
        "enabled": False,
        "channel_id": None,
        "title": None,
        "description": None,
        "footer": None,
        "color": 0x2C2F33,
        "thumbnail": None,
        "image": None,
        "ping_member": False,
    }


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config de recepção, recriando: {e}")
    return {}


def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {"entrada": secao_padrao(), "saida": secao_padrao()}
    config[gid].setdefault("entrada", secao_padrao())
    config[gid].setdefault("saida", secao_padrao())
    return config[gid]


# ---------------------- SESSÕES DE EDIÇÃO EM MEMÓRIA ----------------------
# key = "guild_id:user_id:tipo"  (tipo = "entrada" ou "saida")

BUILD_SESSIONS: dict = {}


def _session_key(guild_id: int, user_id: int, tipo: str) -> str:
    return f"{guild_id}:{user_id}:{tipo}"


def carregar_sessao(guild_id: int, user_id: int, tipo: str) -> dict:
    key = _session_key(guild_id, user_id, tipo)
    if key not in BUILD_SESSIONS:
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        BUILD_SESSIONS[key] = copy.deepcopy(gconf[tipo])
    return BUILD_SESSIONS[key]


def montar_preview(session: dict, membro_exemplo: discord.Member, guild: discord.Guild) -> discord.Embed:
    titulo = substituir_variaveis(session.get("title"), membro_exemplo, guild)
    descricao = substituir_variaveis(session.get("description"), membro_exemplo, guild) or (
        "*Sem descrição — use '📝 Texto' para editar*"
    )
    rodape = substituir_variaveis(session.get("footer"), membro_exemplo, guild)

    embed = discord.Embed(title=titulo, description=descricao, color=session.get("color", 0x2C2F33))

    thumb = substituir_variaveis(session.get("thumbnail"), membro_exemplo, guild)
    if thumb:
        embed.set_thumbnail(url=thumb)
    banner = substituir_variaveis(session.get("image"), membro_exemplo, guild)
    if banner:
        embed.set_image(url=banner)
    if rodape:
        embed.set_footer(text=rodape)
    return embed


def montar_meta_embed(session: dict, tipo: str, nota: str | None = None) -> discord.Embed:
    nome_tipo = "Entrada" if tipo == "entrada" else "Saída"
    status = "🟢 Ativado" if session.get("enabled") else "🔴 Desativado"
    canal = f"<#{session['channel_id']}>" if session.get("channel_id") else "`Nenhum`"
    ping = "Sim" if session.get("ping_member") else "Não"

    embed = discord.Embed(
        title=f"🔧 Configurar {nome_tipo}",
        description=f"**{nota}**" if nota else None,
        color=0x2C2F33,
    )
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Canal", value=canal, inline=True)
    embed.add_field(name="Marcar membro", value=ping, inline=True)
    embed.set_footer(text="⬇️ Pré-visualização abaixo usa seus próprios dados como exemplo")
    return embed


def embed_valida(session: dict) -> bool:
    return bool(session.get("title") or session.get("description"))


# ---------------------- VIEW BASE (dono do painel + tratamento de erro) ----------------------

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
        logger.error(f"Erro no componente '{item}' do painel de recepção", exc_info=error)
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
    def __init__(self, key: str, tipo: str, parent_view: "EntradaSaidaView"):
        super().__init__()
        self.key = key
        self.tipo = tipo
        self.parent_view = parent_view
        session = BUILD_SESSIONS[key]
        self.titulo = discord.ui.TextInput(
            label="Título",
            required=False,
            max_length=256,
            default=session.get("title") or "",
        )
        self.descricao = discord.ui.TextInput(
            label="Descrição (aceita variáveis, ex: {membro})",
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
        await self.parent_view.atualizar(interaction)


class ImagensModal(discord.ui.Modal, title="Foto e Banner"):
    def __init__(self, key: str, tipo: str, parent_view: "EntradaSaidaView"):
        super().__init__()
        self.key = key
        self.tipo = tipo
        self.parent_view = parent_view
        session = BUILD_SESSIONS[key]
        self.foto = discord.ui.TextInput(
            label="Foto (thumbnail) — ou use {avatar_url}",
            required=False,
            placeholder="https://... ou {avatar_url}",
            default=session.get("thumbnail") or "",
        )
        self.banner = discord.ui.TextInput(
            label="Banner (imagem grande)",
            required=False,
            placeholder="https://... ou {avatar_url}",
            default=session.get("image") or "",
        )
        self.add_item(self.foto)
        self.add_item(self.banner)

    async def on_submit(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        foto = self.foto.value.strip()
        banner = self.banner.value.strip()
        if foto and not (foto.startswith("http") or foto == "{avatar_url}"):
            await interaction.response.send_message(
                "❌ O link da foto precisa começar com http(s) ou ser {avatar_url}.", ephemeral=True
            )
            return
        if banner and not (banner.startswith("http") or banner == "{avatar_url}"):
            await interaction.response.send_message(
                "❌ O link do banner precisa começar com http(s) ou ser {avatar_url}.", ephemeral=True
            )
            return
        session["thumbnail"] = foto or None
        session["image"] = banner or None
        await self.parent_view.atualizar(interaction)


# ---------------------- SELECTS ----------------------

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
    ("Preto", "⚫", 0x23272A),
    ("Branco", "⚪", 0xFFFFFF),
]


class CorSelect(discord.ui.Select):
    def __init__(self, key: str, parent_view: "EntradaSaidaView"):
        self.key = key
        self.parent_view = parent_view
        options = [discord.SelectOption(label=nome, emoji=emoji, value=str(cor)) for nome, emoji, cor in CORES]
        super().__init__(placeholder="Escolha uma cor", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        session["color"] = int(self.values[0])
        await self.parent_view.atualizar(interaction)


class CanalSelect(discord.ui.ChannelSelect):
    def __init__(self, key: str, parent_view: "EntradaSaidaView"):
        self.key = key
        self.parent_view = parent_view
        super().__init__(
            placeholder="Selecione o canal de envio",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        session["channel_id"] = self.values[0].id
        await self.parent_view.atualizar(interaction)


# ---------------------- BOTÃO VOLTAR (pro painel de Recepção) ----------------------

class VoltarRecepcaoButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=4)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        view = RecepcaoPainelView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)


# ---------------------- PAINEL: CONFIGURAR ENTRADA / SAÍDA ----------------------

class EntradaSaidaView(BaseView):
    def __init__(self, key: str, tipo: str, dono_id: int):
        super().__init__(timeout=600)
        self.key = key
        self.tipo = tipo
        self.dono_id = dono_id
        self._atualizar_toggle_labels()

    def _atualizar_toggle_labels(self):
        session = BUILD_SESSIONS[self.key]
        self.ativar_btn.label = "🔴 Desativar" if session.get("enabled") else "🟢 Ativar"
        self.ping_btn.label = "🔕 Não marcar membro" if not session.get("ping_member") else "🔔 Marcando membro"

    async def atualizar(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.key]
        self._atualizar_toggle_labels()
        preview = montar_preview(session, interaction.user, interaction.guild)
        await interaction.response.edit_message(
            embeds=[montar_meta_embed(session, self.tipo), preview], view=self
        )

    @discord.ui.button(label="📝 Texto", style=discord.ButtonStyle.primary, row=0)
    async def texto_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TextoModal(self.key, self.tipo, self))

    @discord.ui.button(label="🖼️ Imagens", style=discord.ButtonStyle.primary, row=0)
    async def imagens_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImagensModal(self.key, self.tipo, self))

    @discord.ui.button(label="🎨 Cor", style=discord.ButtonStyle.primary, row=0)
    async def cor_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CorSelect(self.key, self))
        view.add_item(VoltarParaEditarButton(self))
        preview = montar_preview(session, interaction.user, interaction.guild)
        await interaction.response.edit_message(embeds=[montar_meta_embed(session, self.tipo), preview], view=view)

    @discord.ui.button(label="📺 Canal", style=discord.ButtonStyle.primary, row=0)
    async def canal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        view = BaseView(timeout=180)
        view.dono_id = self.dono_id
        view.add_item(CanalSelect(self.key, self))
        view.add_item(VoltarParaEditarButton(self))
        preview = montar_preview(session, interaction.user, interaction.guild)
        await interaction.response.edit_message(embeds=[montar_meta_embed(session, self.tipo), preview], view=view)

    @discord.ui.button(label="ℹ️ Variáveis", style=discord.ButtonStyle.secondary, row=1)
    async def variaveis_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        linhas = [f"`{var}` — {desc}" for var, desc in VARIAVEIS]
        await interaction.response.send_message(
            "**Variáveis disponíveis** (use no título, descrição ou rodapé):\n" + "\n".join(linhas),
            ephemeral=True,
        )

    @discord.ui.button(label="🔔 Marcando membro", style=discord.ButtonStyle.secondary, row=1)
    async def ping_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        session["ping_member"] = not session.get("ping_member")
        await self.atualizar(interaction)

    @discord.ui.button(label="🟢 Ativar", style=discord.ButtonStyle.success, row=2)
    async def ativar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        if not session.get("enabled") and not embed_valida(session):
            await interaction.response.send_message(
                "❌ Adicione ao menos um título ou descrição antes de ativar.", ephemeral=True
            )
            return
        if not session.get("enabled") and not session.get("channel_id"):
            await interaction.response.send_message(
                "❌ Escolha um canal de envio antes de ativar.", ephemeral=True
            )
            return
        session["enabled"] = not session.get("enabled")
        await self.atualizar(interaction)

    @discord.ui.button(label="💾 Salvar", style=discord.ButtonStyle.success, row=2)
    async def salvar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = BUILD_SESSIONS[self.key]
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        gconf[self.tipo] = copy.deepcopy(session)
        save_config(config)
        await interaction.response.edit_message(
            embeds=[
                montar_meta_embed(session, self.tipo, nota=f"✅ Configuração de {self.tipo} salva!"),
                montar_preview(session, interaction.user, interaction.guild),
            ],
            view=self,
        )

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=3)
    async def voltar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RecepcaoPainelView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)


class VoltarParaEditarButton(discord.ui.Button):
    """Volta da tela de Cor/Canal pra tela principal de edição de Entrada/Saída."""

    def __init__(self, parent_view: EntradaSaidaView):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        session = BUILD_SESSIONS[self.parent_view.key]
        self.parent_view._atualizar_toggle_labels()
        preview = montar_preview(session, interaction.user, interaction.guild)
        await interaction.response.edit_message(
            embeds=[montar_meta_embed(session, self.parent_view.tipo), preview], view=self.parent_view
        )


# ---------------------- PAINEL: CONFIGURAR RECEPÇÃO (entrada/saída) ----------------------

class RecepcaoPainelView(BaseView):
    def __init__(self, dono_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id

    def texto_painel(self) -> discord.Embed:
        return discord.Embed(
            title="📥 Configurar Recepção",
            description="Escolha o que quer configurar — cada um tem canal, cor, imagens e texto próprios.",
            color=0x2C2F33,
        )

    @discord.ui.button(label="➡️ Configurar Entrada", style=discord.ButtonStyle.success, row=0)
    async def entrada_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        key = _session_key(interaction.guild_id, interaction.user.id, "entrada")
        BUILD_SESSIONS[key] = carregar_sessao(interaction.guild_id, interaction.user.id, "entrada")
        view = EntradaSaidaView(key, "entrada", self.dono_id)
        session = BUILD_SESSIONS[key]
        preview = montar_preview(session, interaction.user, interaction.guild)
        await interaction.response.edit_message(embeds=[montar_meta_embed(session, "entrada"), preview], view=view)

    @discord.ui.button(label="⬅️ Configurar Saída", style=discord.ButtonStyle.danger, row=0)
    async def saida_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        key = _session_key(interaction.guild_id, interaction.user.id, "saida")
        BUILD_SESSIONS[key] = carregar_sessao(interaction.guild_id, interaction.user.id, "saida")
        view = EntradaSaidaView(key, "saida", self.dono_id)
        session = BUILD_SESSIONS[key]
        preview = montar_preview(session, interaction.user, interaction.guild)
        await interaction.response.edit_message(embeds=[montar_meta_embed(session, "saida"), preview], view=view)

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
    async def voltar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Importado aqui dentro pra evitar import circular com o cog de configuracoes
        from cogs.configuracoes import PainelConfiguracoesView

        view = PainelConfiguracoesView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)


# ---------------------- COG: EVENTOS DE ENTRADA/SAÍDA ----------------------

class Recepcao(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._enviar(member, "entrada")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._enviar(member, "saida")

    async def _enviar(self, member: discord.Member, tipo: str):
        config = load_config()
        gconf = get_guild_config(config, member.guild.id)
        secao = gconf[tipo]
        save_config(config)  # garante que o guild já fica registrado no arquivo

        if not secao.get("enabled") or not secao.get("channel_id"):
            return

        canal = member.guild.get_channel(secao["channel_id"])
        if canal is None:
            logger.warning(f"Canal de {tipo} configurado não existe mais no servidor {member.guild.id}")
            return

        embed = montar_preview(secao, member, member.guild)
        conteudo = member.mention if secao.get("ping_member") else None

        try:
            await canal.send(content=conteudo, embed=embed)
        except discord.Forbidden:
            logger.warning(f"Sem permissão para enviar embed de {tipo} no canal {canal.id}")
        except Exception as e:
            logger.error(f"Erro ao enviar embed de {tipo}", exc_info=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(Recepcao(bot))
