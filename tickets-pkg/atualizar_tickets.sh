#!/data/data/com.termux/files/usr/bin/bash
# =====================================================================
# Zyntrax SmartDesk — Atualizacao: canal do painel, canal de logs
# (aberto/fechado/transcript) e ajustes no painel de configuracoes.
# Rode este script dentro da pasta raiz do projeto (~/zyntrax-bot).
# =====================================================================

set -e

if [ ! -f "bot.py" ]; then
  echo "❌ Rode este script dentro da pasta raiz do projeto (onde fica o bot.py)."
  exit 1
fi

mkdir -p cogs config

echo "📦 Atualizando o sistema de Tickets (Zyntrax SmartDesk)..."

echo "  -> escrevendo cogs/tickets.py"
cat > cogs/tickets.py << 'ZYNTRAX_EOF_COGS_TICKETS.PY'
import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import io
import logging
import os
import re
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("bot.tickets")

CONFIG_FILE = "config/tickets_config.json"
DATA_FILE = "config/tickets_data.json"

# =====================================================================
# CONSTANTES
# =====================================================================

STATUS_INFO = {
    "aguardando": ("🟡", "Aguardando atendimento", 0xF1C40F),
    "em_atendimento": ("🔵", "Em atendimento", 0x3498DB),
    "aguardando_usuario": ("🟣", "Aguardando usuário", 0x9B59B6),
    "em_analise": ("🟠", "Em análise", 0xE67E22),
    "resolvido": ("🟢", "Resolvido", 0x2ECC71),
    "encerrado": ("⚫", "Encerrado", 0x2C2F33),
}

PRIORIDADE_INFO = {
    "baixa": ("🟢", "Baixa"),
    "normal": ("🟡", "Normal"),
    "alta": ("🟠", "Alta"),
    "critico": ("🔴", "Crítico"),
}

COR_TICKETS = 0x5865F2


# =====================================================================
# PERSISTÊNCIA
# =====================================================================

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config de tickets, recriando: {e}")
    return {}


def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def guild_config_padrao() -> dict:
    return {
        "canal_painel": None,
        "mensagem_painel": None,
        "canal_logs": None,
        "categoria_discord_padrao": None,
        "limite_por_usuario": 2,
        "cooldown_minutos": 5,
        "aviso_sem_resposta_minutos": 15,
        "proximo_numero": 1,
        "categorias": {},
    }


def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = guild_config_padrao()
    else:
        for chave, valor in guild_config_padrao().items():
            config[gid].setdefault(chave, valor)
        # migração: versões antigas usavam "canal_transcripts" para só o transcript
        if config[gid].get("canal_transcripts") and not config[gid].get("canal_logs"):
            config[gid]["canal_logs"] = config[gid]["canal_transcripts"]
    return config[gid]


def categoria_padrao(nome: str, emoji: str, descricao: str) -> dict:
    return {
        "nome": nome,
        "emoji": emoji,
        "descricao": descricao,
        "ativo": True,
        "categoria_discord_id": None,
        "cargos_responsaveis": [],
        "prioridade_padrao": "normal",
        "perguntas": [],
    }


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler dados de tickets, recriando: {e}")
    return {}


def save_data(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_guild_data(data: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    data.setdefault(gid, {"tickets": {}, "cooldowns": {}})
    data[gid].setdefault("tickets", {})
    data[gid].setdefault("cooldowns", {})
    return data[gid]


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


def formatar_duracao(segundos: float) -> str:
    segundos = int(segundos)
    if segundos < 60:
        return f"{segundos}s"
    minutos, segundos = divmod(segundos, 60)
    if minutos < 60:
        return f"{minutos}m {segundos}s"
    horas, minutos = divmod(minutos, 60)
    if horas < 24:
        return f"{horas}h {minutos}m"
    dias, horas = divmod(horas, 24)
    return f"{dias}d {horas}h"


def slugify(nome: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")
    return slug[:20] or "geral"


def eh_staff_do_ticket(membro: discord.Member, categoria_conf: dict) -> bool:
    if membro.guild_permissions.manage_channels or membro.guild_permissions.administrator:
        return True
    cargos = set(categoria_conf.get("cargos_responsaveis", []))
    return any(cargo.id in cargos for cargo in membro.roles)


def localizar_ticket(data: dict, guild_id: int, channel_id: int) -> tuple[str, dict] | tuple[None, None]:
    gdata = get_guild_data(data, guild_id)
    for chave, ticket in gdata["tickets"].items():
        if ticket.get("canal_id") == channel_id:
            return chave, ticket
    return None, None


# =====================================================================
# EMBEDS
# =====================================================================

def montar_embed_ticket(ticket: dict, categoria_conf: dict | None) -> discord.Embed:
    status_emoji, status_label, status_cor = STATUS_INFO[ticket["status"]]
    prio_emoji, prio_label = PRIORIDADE_INFO[ticket["prioridade"]]

    embed = discord.Embed(
        title=f"🎫 Ticket #{ticket['numero']:04d} — {ticket['categoria_nome']}",
        color=status_cor,
    )
    embed.add_field(name="👤 Autor", value=f"<@{ticket['autor_id']}>", inline=True)
    embed.add_field(name="📂 Categoria", value=f"{ticket['categoria_emoji']} {ticket['categoria_nome']}", inline=True)
    embed.add_field(name="⚡ Prioridade", value=f"{prio_emoji} {prio_label}", inline=True)
    embed.add_field(name="📌 Status", value=f"{status_emoji} {status_label}", inline=True)
    atendente = f"<@{ticket['atendente_id']}>" if ticket.get("atendente_id") else "*Ninguém ainda*"
    embed.add_field(name="👨‍💻 Atendente", value=atendente, inline=True)
    embed.add_field(name="🕐 Aberto em", value=f"<t:{int(parse_iso(ticket['criado_em']).timestamp())}:R>", inline=True)

    for pergunta, resposta in ticket.get("respostas", {}).items():
        embed.add_field(name=f"📝 {pergunta[:250]}", value=(resposta or "—")[:1000], inline=False)

    embed.set_footer(text=f"Ticket #{ticket['numero']:04d}")
    return embed


async def atualizar_embed_ticket(channel: discord.TextChannel, ticket: dict, categoria_conf: dict | None) -> None:
    msg_id = ticket.get("mensagem_info_id")
    if not msg_id:
        return
    try:
        msg = await channel.fetch_message(msg_id)
        await msg.edit(embed=montar_embed_ticket(ticket, categoria_conf))
    except (discord.NotFound, discord.HTTPException):
        pass


# =====================================================================
# MODAIS — GESTÃO DE CATEGORIAS (painel de configurações)
# =====================================================================

class NovaCategoriaModal(discord.ui.Modal, title="Nova Categoria de Atendimento"):
    nome = discord.ui.TextInput(label="Nome da categoria", placeholder="Ex: Suporte", max_length=50)
    emoji = discord.ui.TextInput(label="Emoji", placeholder="Ex: 🛠️", max_length=10)
    descricao = discord.ui.TextInput(
        label="Descrição curta", placeholder="Aparece no menu de abertura", max_length=100, required=False
    )

    def __init__(self, dono_id: int):
        super().__init__()
        self.dono_id = dono_id

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        chave = f"{slugify(str(self.nome))}-{uuid.uuid4().hex[:4]}"
        gconf["categorias"][chave] = categoria_padrao(str(self.nome), str(self.emoji), str(self.descricao or ""))
        save_config(config)

        view = CategoriaEditView(self.dono_id, chave)
        await interaction.response.edit_message(embed=view.texto_painel(gconf["categorias"][chave]), view=view)


class TextosCategoriaModal(discord.ui.Modal, title="Editar Categoria"):
    def __init__(self, dono_id: int, chave: str, categoria: dict):
        super().__init__()
        self.dono_id = dono_id
        self.chave = chave
        self.nome = discord.ui.TextInput(label="Nome", default=categoria["nome"], max_length=50)
        self.emoji = discord.ui.TextInput(label="Emoji", default=categoria["emoji"], max_length=10)
        self.descricao = discord.ui.TextInput(
            label="Descrição curta", default=categoria.get("descricao", ""), max_length=100, required=False
        )
        self.add_item(self.nome)
        self.add_item(self.emoji)
        self.add_item(self.descricao)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        cat = gconf["categorias"].get(self.chave)
        if not cat:
            await interaction.response.send_message("❌ Categoria não encontrada mais.", ephemeral=True)
            return
        cat["nome"] = str(self.nome)
        cat["emoji"] = str(self.emoji)
        cat["descricao"] = str(self.descricao or "")
        save_config(config)
        view = CategoriaEditView(self.dono_id, self.chave)
        await interaction.response.edit_message(embed=view.texto_painel(cat), view=view)


class PerguntasCategoriaModal(discord.ui.Modal, title="Formulário do Atendimento (até 5 perguntas)"):
    def __init__(self, dono_id: int, chave: str, categoria: dict):
        super().__init__()
        self.dono_id = dono_id
        self.chave = chave
        perguntas_atuais = categoria.get("perguntas", [])
        self.campos = []
        for i in range(5):
            valor_atual = perguntas_atuais[i] if i < len(perguntas_atuais) else ""
            campo = discord.ui.TextInput(
                label=f"Pergunta {i + 1} (em branco = não usar)",
                default=valor_atual,
                max_length=150,
                required=False,
            )
            self.campos.append(campo)
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        cat = gconf["categorias"].get(self.chave)
        if not cat:
            await interaction.response.send_message("❌ Categoria não encontrada mais.", ephemeral=True)
            return
        cat["perguntas"] = [str(c).strip() for c in self.campos if str(c).strip()]
        save_config(config)
        view = CategoriaEditView(self.dono_id, self.chave)
        await interaction.response.edit_message(embed=view.texto_painel(cat), view=view)


class LimitesModal(discord.ui.Modal, title="Limites e Cooldown"):
    limite = discord.ui.TextInput(label="Limite de tickets abertos por usuário", max_length=3)
    cooldown = discord.ui.TextInput(label="Cooldown entre aberturas (minutos)", max_length=4)
    aviso_sla = discord.ui.TextInput(label="Avisar sem resposta após (minutos)", max_length=4)

    def __init__(self, dono_id: int, gconf: dict):
        super().__init__()
        self.dono_id = dono_id
        self.limite.default = str(gconf.get("limite_por_usuario", 2))
        self.cooldown.default = str(gconf.get("cooldown_minutos", 5))
        self.aviso_sla.default = str(gconf.get("aviso_sem_resposta_minutos", 15))

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        try:
            gconf["limite_por_usuario"] = max(1, int(str(self.limite)))
            gconf["cooldown_minutos"] = max(0, int(str(self.cooldown)))
            gconf["aviso_sem_resposta_minutos"] = max(1, int(str(self.aviso_sla)))
        except ValueError:
            await interaction.response.send_message("❌ Use apenas números nos campos.", ephemeral=True)
            return
        save_config(config)
        view = TicketsPainelView(self.dono_id)
        await interaction.response.edit_message(embed=await view.texto_painel(interaction.guild_id), view=view)


# =====================================================================
# PAINEL DE CONFIGURAÇÕES — CATEGORIA (editar uma categoria específica)
# =====================================================================

class CategoriaEditView(discord.ui.View):
    def __init__(self, dono_id: int, chave: str):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.chave = chave

    def texto_painel(self, categoria: dict) -> discord.Embed:
        prio_emoji, prio_label = PRIORIDADE_INFO[categoria.get("prioridade_padrao", "normal")]
        embed = discord.Embed(
            title=f"{categoria['emoji']} {categoria['nome']}",
            description=categoria.get("descricao") or "*(sem descrição)*",
            color=COR_TICKETS,
        )
        embed.add_field(name="Status", value="✅ Ativa" if categoria.get("ativo", True) else "⛔ Desativada", inline=True)
        embed.add_field(name="Prioridade padrão", value=f"{prio_emoji} {prio_label}", inline=True)
        destino = f"<#{categoria['categoria_discord_id']}>" if categoria.get("categoria_discord_id") else "*(usa a padrão do servidor)*"
        embed.add_field(name="Categoria de destino", value=destino, inline=True)
        cargos = categoria.get("cargos_responsaveis", [])
        embed.add_field(
            name="👥 Equipe responsável",
            value=", ".join(f"<@&{c}>" for c in cargos) if cargos else "*(nenhum cargo definido)*",
            inline=False,
        )
        perguntas = categoria.get("perguntas", [])
        embed.add_field(
            name="📝 Perguntas do formulário",
            value="\n".join(f"{i + 1}. {p}" for i, p in enumerate(perguntas)) if perguntas else "*(sem perguntas — o ticket abre direto)*",
            inline=False,
        )
        embed.set_footer(text="💡 Configure tudo abaixo antes de publicar o painel de atendimento")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True)
            return False
        return True

    def _cat(self, guild_id: int) -> tuple[dict, dict]:
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        return config, gconf["categorias"].get(self.chave)

    @discord.ui.button(label="✏️ Nome/Emoji/Descrição", style=discord.ButtonStyle.primary, row=0)
    async def editar_textos(self, interaction: discord.Interaction, button: discord.ui.Button):
        _, cat = self._cat(interaction.guild_id)
        await interaction.response.send_modal(TextosCategoriaModal(self.dono_id, self.chave, cat))

    @discord.ui.button(label="📝 Formulário", style=discord.ButtonStyle.primary, row=0)
    async def editar_perguntas(self, interaction: discord.Interaction, button: discord.ui.Button):
        _, cat = self._cat(interaction.guild_id)
        await interaction.response.send_modal(PerguntasCategoriaModal(self.dono_id, self.chave, cat))

    @discord.ui.button(label="🔀 Trocar prioridade padrão", style=discord.ButtonStyle.secondary, row=1)
    async def trocar_prioridade(self, interaction: discord.Interaction, button: discord.ui.Button):
        config, cat = self._cat(interaction.guild_id)
        ordem = list(PRIORIDADE_INFO.keys())
        atual = ordem.index(cat.get("prioridade_padrao", "normal"))
        cat["prioridade_padrao"] = ordem[(atual + 1) % len(ordem)]
        save_config(config)
        await interaction.response.edit_message(embed=self.texto_painel(cat), view=self)

    @discord.ui.button(label="✅/⛔ Ativar/Desativar", style=discord.ButtonStyle.secondary, row=1)
    async def alternar_ativo(self, interaction: discord.Interaction, button: discord.ui.Button):
        config, cat = self._cat(interaction.guild_id)
        cat["ativo"] = not cat.get("ativo", True)
        save_config(config)
        await interaction.response.edit_message(embed=self.texto_painel(cat), view=self)

    @discord.ui.button(label="🗑️ Excluir Categoria", style=discord.ButtonStyle.danger, row=1)
    async def excluir(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        gconf["categorias"].pop(self.chave, None)
        save_config(config)
        view = TicketsPainelView(self.dono_id)
        await interaction.response.edit_message(embed=await view.texto_painel(interaction.guild_id), view=view)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.category],
                        placeholder="📁 Categoria do Discord de destino", row=2)
    async def escolher_categoria_discord(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        config, cat = self._cat(interaction.guild_id)
        cat["categoria_discord_id"] = select.values[0].id
        save_config(config)
        await interaction.response.edit_message(embed=self.texto_painel(cat), view=self)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="👥 Equipe responsável (substitui a lista atual)",
                        min_values=1, max_values=5, row=3)
    async def escolher_cargos(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        config, cat = self._cat(interaction.guild_id)
        cat["cargos_responsaveis"] = [role.id for role in select.values]
        save_config(config)
        await interaction.response.edit_message(embed=self.texto_painel(cat), view=self)

    @discord.ui.button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=4)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TicketsPainelView(self.dono_id)
        await interaction.response.edit_message(embed=await view.texto_painel(interaction.guild_id), view=view)


class ListaCategoriasSelect(discord.ui.Select):
    def __init__(self, categorias: dict, dono_id: int):
        options = [
            discord.SelectOption(label=cat["nome"][:100], value=chave, emoji=cat["emoji"] or None,
                                  description=(cat.get("descricao") or "")[:100] or None)
            for chave, cat in list(categorias.items())[:25]
        ]
        super().__init__(placeholder="✏️ Escolha uma categoria para editar", options=options)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        chave = self.values[0]
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        cat = gconf["categorias"].get(chave)
        if not cat:
            await interaction.response.send_message("❌ Categoria não encontrada mais.", ephemeral=True)
            return
        view = CategoriaEditView(self.dono_id, chave)
        await interaction.response.edit_message(embed=view.texto_painel(cat), view=view)


# =====================================================================
# PAINEL DE CONFIGURAÇÕES — VISÃO GERAL DE TICKETS
# =====================================================================

class TicketsPainelView(discord.ui.View):
    def __init__(self, dono_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id

    async def texto_painel(self, guild_id: int) -> discord.Embed:
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        save_config(config)

        embed = discord.Embed(
            title="🎫 CENTRAL DE ATENDIMENTO — Tickets",
            description="Configure o SmartDesk do seu servidor: categorias, formulários, equipe e limites.",
            color=COR_TICKETS,
        )
        painel_txt = f"<#{gconf['canal_painel']}>" if gconf.get("canal_painel") else "*(não definido)*"
        logs_txt = f"<#{gconf['canal_logs']}>" if gconf.get("canal_logs") else "*(não definido)*"
        padrao_txt = f"<#{gconf['categoria_discord_padrao']}>" if gconf.get("categoria_discord_padrao") else "*(não definida)*"

        embed.add_field(name="📍 Canal do painel público", value=painel_txt, inline=True)
        embed.add_field(name="🗂️ Canal de logs (aberto/fechado/transcript)", value=logs_txt, inline=True)
        embed.add_field(name="📁 Categoria padrão do Discord", value=padrao_txt, inline=True)
        embed.add_field(
            name="⚙️ Limites",
            value=(
                f"Máx. {gconf['limite_por_usuario']} ticket(s) simultâneo(s) por usuário\n"
                f"Cooldown de {gconf['cooldown_minutos']} min entre aberturas\n"
                f"Aviso de SLA após {gconf['aviso_sem_resposta_minutos']} min sem resposta"
            ),
            inline=False,
        )

        categorias = gconf["categorias"]
        if categorias:
            linhas = [
                f"{cat['emoji']} **{cat['nome']}** — {'✅ ativa' if cat.get('ativo', True) else '⛔ desativada'}"
                for cat in categorias.values()
            ]
            embed.add_field(name=f"📂 Categorias ({len(categorias)})", value="\n".join(linhas)[:1024], inline=False)
        else:
            embed.add_field(name="📂 Categorias", value="*(nenhuma categoria criada ainda)*", inline=False)

        embed.set_footer(text="💡 Crie ao menos uma categoria e defina o canal do painel antes de publicar")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="➕ Nova Categoria", style=discord.ButtonStyle.success, row=0)
    async def nova_categoria(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NovaCategoriaModal(self.dono_id))

    @discord.ui.button(label="✏️ Gerenciar Categorias", style=discord.ButtonStyle.primary, row=0)
    async def gerenciar_categorias(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        if not gconf["categorias"]:
            await interaction.response.send_message("⚠️ Nenhuma categoria criada ainda.", ephemeral=True)
            return
        view = discord.ui.View(timeout=180)
        view.add_item(ListaCategoriasSelect(gconf["categorias"], self.dono_id))
        voltar = discord.ui.Button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)

        async def voltar_cb(inter: discord.Interaction):
            painel = TicketsPainelView(self.dono_id)
            await inter.response.edit_message(embed=await painel.texto_painel(inter.guild_id), view=painel)

        voltar.callback = voltar_cb
        view.add_item(voltar)
        await interaction.response.edit_message(embed=await self.texto_painel(interaction.guild_id), view=view)

    @discord.ui.button(label="⚙️ Limites e Cooldown", style=discord.ButtonStyle.secondary, row=0)
    async def limites(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        await interaction.response.send_modal(LimitesModal(self.dono_id, gconf))

    @discord.ui.button(label="📊 Dashboard", style=discord.ButtonStyle.secondary, row=0)
    async def dashboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = montar_dashboard(interaction.guild_id)
        voltar_view = discord.ui.View(timeout=180)
        voltar = discord.ui.Button(label="◀️ Voltar", style=discord.ButtonStyle.secondary)

        async def voltar_cb(inter: discord.Interaction):
            painel = TicketsPainelView(self.dono_id)
            await inter.response.edit_message(embed=await painel.texto_painel(inter.guild_id), view=painel)

        voltar.callback = voltar_cb
        voltar_view.add_item(voltar)
        await interaction.response.edit_message(embed=embed, view=voltar_view)

    @discord.ui.button(label="🚀 Publicar Painel no Canal Selecionado", style=discord.ButtonStyle.success, row=1)
    async def publicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        categorias_ativas = {k: v for k, v in gconf["categorias"].items() if v.get("ativo", True)}
        if not categorias_ativas:
            await interaction.response.send_message("⚠️ Crie e ative ao menos uma categoria antes de publicar.", ephemeral=True)
            return
        if not gconf.get("canal_painel"):
            await interaction.response.send_message(
                "⚠️ Selecione primeiro o canal do painel no menu **📍 Canal do Painel** abaixo.", ephemeral=True
            )
            return
        canal_destino = interaction.guild.get_channel(gconf["canal_painel"])
        if not canal_destino:
            await interaction.response.send_message("❌ O canal selecionado não existe mais. Escolha outro.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎫 Central de Atendimento",
            description="Selecione abaixo o tipo de atendimento que você precisa. Um formulário rápido vai aparecer antes de abrir seu ticket.",
            color=COR_TICKETS,
        )
        view = PainelAberturaView(interaction.guild_id, categorias_ativas)
        try:
            msg = await canal_destino.send(embed=embed, view=view)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ Não tenho permissão para enviar mensagens em {canal_destino.mention}.", ephemeral=True)
            return

        gconf["mensagem_painel"] = msg.id
        save_config(config)
        await interaction.response.edit_message(embed=await self.texto_painel(interaction.guild_id), view=self)
        await interaction.followup.send(f"✅ Painel publicado em {canal_destino.mention}!", ephemeral=True)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                        placeholder="📍 Canal do Painel (onde os membros abrem tickets)", row=2)
    async def escolher_canal_painel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        gconf["canal_painel"] = select.values[0].id
        save_config(config)
        await interaction.response.edit_message(embed=await self.texto_painel(interaction.guild_id), view=self)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                        placeholder="🗂️ Canal de Logs (aberto/fechado/transcript)", row=3)
    async def escolher_canal_logs(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        gconf["canal_logs"] = select.values[0].id
        save_config(config)
        await interaction.response.edit_message(embed=await self.texto_painel(interaction.guild_id), view=self)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.category],
                        placeholder="📁 Categoria padrão do Discord (fallback)", row=4)
    async def escolher_categoria_padrao(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        gconf["categoria_discord_padrao"] = select.values[0].id
        save_config(config)
        await interaction.response.edit_message(embed=await self.texto_painel(interaction.guild_id), view=self)


# =====================================================================
# PAINEL PÚBLICO — ABERTURA DE ATENDIMENTO
# =====================================================================

class AberturaSelect(discord.ui.Select):
    def __init__(self, guild_id: int, categorias: dict):
        options = [
            discord.SelectOption(label=cat["nome"][:100], value=chave, emoji=cat["emoji"] or None,
                                  description=(cat.get("descricao") or "")[:100] or None)
            for chave, cat in list(categorias.items())[:25]
        ]
        super().__init__(
            placeholder="🎯 Escolha o tipo de atendimento",
            options=options,
            custom_id=f"ticket_abrir_select:{guild_id}",
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        chave = self.values[0]
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        categoria = gconf["categorias"].get(chave)
        if not categoria or not categoria.get("ativo", True):
            await interaction.response.send_message("❌ Esse tipo de atendimento não está mais disponível.", ephemeral=True)
            return

        data = load_data()
        gdata = get_guild_data(data, self.guild_id)

        abertos = [t for t in gdata["tickets"].values() if t["autor_id"] == interaction.user.id and t["status"] != "encerrado"]
        if len(abertos) >= gconf["limite_por_usuario"]:
            await interaction.response.send_message(
                f"⚠️ Você já tem {len(abertos)} ticket(s) em aberto. Finalize antes de abrir outro.", ephemeral=True
            )
            return

        ultima = parse_iso(gdata["cooldowns"].get(str(interaction.user.id)))
        if ultima:
            passado = (datetime.now(timezone.utc) - ultima).total_seconds() / 60
            if passado < gconf["cooldown_minutos"]:
                restante = round(gconf["cooldown_minutos"] - passado, 1)
                await interaction.response.send_message(f"⏳ Aguarde mais {restante} min antes de abrir outro ticket.", ephemeral=True)
                return

        perguntas = categoria.get("perguntas", [])
        if perguntas:
            await interaction.response.send_modal(AberturaModal(self.guild_id, chave, perguntas))
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            canal = await criar_ticket(interaction, chave, {})
            if canal:
                await interaction.followup.send(f"✅ Atendimento aberto em {canal.mention}!", ephemeral=True)


class PainelAberturaView(discord.ui.View):
    def __init__(self, guild_id: int, categorias: dict):
        super().__init__(timeout=None)
        self.add_item(AberturaSelect(guild_id, categorias))


class AberturaModal(discord.ui.Modal, title="Antes de abrir seu atendimento..."):
    def __init__(self, guild_id: int, categoria_chave: str, perguntas: list[str]):
        super().__init__()
        self.guild_id = guild_id
        self.categoria_chave = categoria_chave
        self.campos = []
        for pergunta in perguntas[:5]:
            campo = discord.ui.TextInput(label=pergunta[:45], style=discord.TextStyle.paragraph, max_length=500, required=True)
            self.campos.append((pergunta, campo))
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        respostas = {pergunta: str(campo) for pergunta, campo in self.campos}
        canal = await criar_ticket(interaction, self.categoria_chave, respostas)
        if canal:
            await interaction.followup.send(f"✅ Atendimento aberto em {canal.mention}!", ephemeral=True)


async def criar_ticket(interaction: discord.Interaction, categoria_chave: str, respostas: dict) -> discord.TextChannel | None:
    guild = interaction.guild
    config = load_config()
    gconf = get_guild_config(config, guild.id)
    categoria = gconf["categorias"].get(categoria_chave)
    if not categoria:
        await interaction.followup.send("❌ Essa categoria não existe mais.", ephemeral=True)
        return None

    numero = gconf.get("proximo_numero", 1)
    gconf["proximo_numero"] = numero + 1

    categoria_discord_id = categoria.get("categoria_discord_id") or gconf.get("categoria_discord_padrao")
    categoria_discord = guild.get_channel(categoria_discord_id) if categoria_discord_id else None
    if not isinstance(categoria_discord, discord.CategoryChannel):
        categoria_discord = None

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    for cargo_id in categoria.get("cargos_responsaveis", []):
        cargo = guild.get_role(cargo_id)
        if cargo:
            overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

    try:
        canal = await guild.create_text_channel(
            name=f"ticket-{numero:04d}-{slugify(categoria['nome'])}",
            category=categoria_discord,
            overwrites=overwrites,
            reason=f"Ticket #{numero:04d} aberto por {interaction.user}",
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ Não tenho permissão para criar canais aqui. Avise um administrador.", ephemeral=True)
        return None

    chave_ticket = f"{numero:04d}"
    ticket = {
        "numero": numero,
        "canal_id": canal.id,
        "categoria_id": categoria_chave,
        "categoria_nome": categoria["nome"],
        "categoria_emoji": categoria["emoji"],
        "autor_id": interaction.user.id,
        "prioridade": categoria.get("prioridade_padrao", "normal"),
        "status": "aguardando",
        "atendente_id": None,
        "respostas": respostas,
        "criado_em": agora_iso(),
        "primeira_resposta_staff_em": None,
        "fechado_em": None,
        "resultado": None,
        "motivo_fechamento": None,
        "avaliacao": None,
        "comentario_avaliacao": None,
        "avisado_sem_resposta": False,
        "mensagem_info_id": None,
    }

    data = load_data()
    gdata = get_guild_data(data, guild.id)
    gdata["tickets"][chave_ticket] = ticket
    gdata["cooldowns"][str(interaction.user.id)] = agora_iso()
    save_data(data)
    save_config(config)

    mencoes = " ".join(f"<@&{cid}>" for cid in categoria.get("cargos_responsaveis", []))
    embed = montar_embed_ticket(ticket, categoria)
    msg = await canal.send(
        content=f"{interaction.user.mention} {mencoes}".strip(),
        embed=embed,
        view=TicketControlView(guild.id, chave_ticket),
    )

    ticket["mensagem_info_id"] = msg.id
    save_data(data)

    await enviar_log_evento(
        guild, gconf,
        titulo=f"🟢 Ticket Aberto — #{ticket['numero']:04d}",
        cor=STATUS_INFO["aguardando"][2],
        ticket=ticket,
        canal=canal,
    )
    return canal


# =====================================================================
# CONTROLE DO TICKET (dentro do canal)
# =====================================================================

class ResultadoModal(discord.ui.Modal):
    def __init__(self, guild_id: int, chave: str, resultado: str):
        titulo = "Marcar como Resolvido" if resultado == "resolvido" else "Encerrar Atendimento"
        super().__init__(title=titulo)
        self.guild_id = guild_id
        self.chave = chave
        self.resultado = resultado
        self.solucao = discord.ui.TextInput(
            label="Resumo / solução aplicada", style=discord.TextStyle.paragraph, max_length=500, required=False
        )
        self.add_item(self.solucao)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        gdata = get_guild_data(data, self.guild_id)
        ticket = gdata["tickets"].get(self.chave)
        if not ticket:
            await interaction.response.send_message("❌ Este ticket não existe mais nos registros.", ephemeral=True)
            return

        ticket["status"] = "encerrado"
        ticket["resultado"] = self.resultado
        ticket["motivo_fechamento"] = str(self.solucao) or None
        ticket["fechado_em"] = agora_iso()
        save_data(data)

        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        categoria = gconf["categorias"].get(ticket["categoria_id"])

        await interaction.response.defer()
        canal = interaction.channel
        await atualizar_embed_ticket(canal, ticket, categoria)

        duracao = (datetime.fromisoformat(ticket["fechado_em"]) - parse_iso(ticket["criado_em"])).total_seconds()
        resumo = discord.Embed(
            title=f"📋 Resumo do Atendimento — Ticket #{ticket['numero']:04d}",
            color=STATUS_INFO["encerrado"][2],
        )
        primeira_pergunta = next(iter(ticket.get("respostas", {}).items()), None)
        resumo.add_field(name="Problema relatado", value=(primeira_pergunta[1] if primeira_pergunta else "*(sem formulário)*")[:1000], inline=False)
        resumo.add_field(name="Solução / resumo", value=ticket["motivo_fechamento"] or "*(não informado)*", inline=False)
        resumo.add_field(name="Resultado", value="✅ Resolvido" if self.resultado == "resolvido" else "🔒 Encerrado sem resolução", inline=True)
        atendente_txt = f"<@{ticket['atendente_id']}>" if ticket.get("atendente_id") else "*(ninguém assumiu)*"
        resumo.add_field(name="Atendente", value=atendente_txt, inline=True)
        resumo.add_field(name="Duração total", value=formatar_duracao(duracao), inline=True)
        await canal.send(embed=resumo)

        await enviar_log_evento(
            interaction.guild, gconf,
            titulo=f"🔒 Ticket Encerrado — #{ticket['numero']:04d}",
            cor=STATUS_INFO["encerrado"][2],
            ticket=ticket,
            canal=canal,
            campos_extra=[
                ("Resultado", "✅ Resolvido" if self.resultado == "resolvido" else "🔒 Sem resolução"),
                ("Duração", formatar_duracao(duracao)),
            ],
        )
        await enviar_transcript(interaction.guild, canal, ticket, gconf)

        try:
            overwrites = canal.overwrites
            overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            autor = interaction.guild.get_member(ticket["autor_id"])
            if autor:
                overwrites[autor] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)
            await canal.edit(overwrites=overwrites)
        except discord.HTTPException:
            pass

        avaliacao_view = AvaliacaoView(self.guild_id, self.chave, ticket["autor_id"])
        try:
            await canal.send(
                f"<@{ticket['autor_id']}> ⭐ Como foi seu atendimento? Sua avaliação ajuda a equipe a melhorar!",
                view=avaliacao_view,
            )
        except discord.HTTPException:
            pass


class StatusSelect(discord.ui.Select):
    OPCOES = ["aguardando", "em_atendimento", "aguardando_usuario", "em_analise", "resolvido"]

    def __init__(self, guild_id: int, chave: str):
        options = [
            discord.SelectOption(label=STATUS_INFO[s][1], value=s, emoji=STATUS_INFO[s][0]) for s in self.OPCOES
        ]
        super().__init__(placeholder="📌 Mudar status", options=options, custom_id=f"ticket_status:{guild_id}:{chave}")
        self.guild_id = guild_id
        self.chave = chave

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        data = load_data()
        gdata = get_guild_data(data, self.guild_id)
        ticket = gdata["tickets"].get(self.chave)
        if not ticket:
            await interaction.response.send_message("❌ Ticket não encontrado nos registros.", ephemeral=True)
            return
        categoria = gconf["categorias"].get(ticket["categoria_id"])
        if not eh_staff_do_ticket(interaction.user, categoria or {}):
            await interaction.response.send_message("❌ Apenas a equipe responsável pode mudar o status.", ephemeral=True)
            return
        ticket["status"] = self.values[0]
        save_data(data)
        await atualizar_embed_ticket(interaction.channel, ticket, categoria)
        await interaction.response.send_message(f"📌 Status atualizado para **{STATUS_INFO[self.values[0]][1]}**.", ephemeral=True)


class PrioridadeSelect(discord.ui.Select):
    def __init__(self, guild_id: int, chave: str):
        options = [
            discord.SelectOption(label=label, value=chave_p, emoji=emoji) for chave_p, (emoji, label) in PRIORIDADE_INFO.items()
        ]
        super().__init__(placeholder="⚡ Mudar prioridade", options=options, custom_id=f"ticket_prioridade:{guild_id}:{chave}")
        self.guild_id = guild_id
        self.chave = chave

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        data = load_data()
        gdata = get_guild_data(data, self.guild_id)
        ticket = gdata["tickets"].get(self.chave)
        if not ticket:
            await interaction.response.send_message("❌ Ticket não encontrado nos registros.", ephemeral=True)
            return
        categoria = gconf["categorias"].get(ticket["categoria_id"])
        if not eh_staff_do_ticket(interaction.user, categoria or {}):
            await interaction.response.send_message("❌ Apenas a equipe responsável pode mudar a prioridade.", ephemeral=True)
            return
        ticket["prioridade"] = self.values[0]
        save_data(data)
        await atualizar_embed_ticket(interaction.channel, ticket, categoria)
        await interaction.response.send_message(f"⚡ Prioridade atualizada para **{PRIORIDADE_INFO[self.values[0]][1]}**.", ephemeral=True)


class TicketControlView(discord.ui.View):
    def __init__(self, guild_id: int, chave: str):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.chave = chave

        assumir = discord.ui.Button(label="🟢 Assumir", style=discord.ButtonStyle.success, row=0,
                                     custom_id=f"ticket_assumir:{guild_id}:{chave}")
        assumir.callback = self.assumir_cb
        self.add_item(assumir)

        resolver = discord.ui.Button(label="✅ Resolver", style=discord.ButtonStyle.primary, row=0,
                                      custom_id=f"ticket_resolver:{guild_id}:{chave}")
        resolver.callback = self.resolver_cb
        self.add_item(resolver)

        encerrar = discord.ui.Button(label="🔒 Encerrar", style=discord.ButtonStyle.danger, row=0,
                                      custom_id=f"ticket_encerrar:{guild_id}:{chave}")
        encerrar.callback = self.encerrar_cb
        self.add_item(encerrar)

        self.add_item(StatusSelect(guild_id, chave))
        self.add_item(PrioridadeSelect(guild_id, chave))

    def _carregar(self, guild_id: int, chave: str):
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        data = load_data()
        gdata = get_guild_data(data, guild_id)
        ticket = gdata["tickets"].get(chave)
        categoria = gconf["categorias"].get(ticket["categoria_id"]) if ticket else None
        return data, ticket, categoria

    async def assumir_cb(self, interaction: discord.Interaction):
        data, ticket, categoria = self._carregar(self.guild_id, self.chave)
        if not ticket:
            await interaction.response.send_message("❌ Ticket não encontrado nos registros.", ephemeral=True)
            return
        if ticket["status"] == "encerrado":
            await interaction.response.send_message("⚠️ Este ticket já foi encerrado.", ephemeral=True)
            return
        if not eh_staff_do_ticket(interaction.user, categoria or {}):
            await interaction.response.send_message("❌ Apenas a equipe responsável pode assumir este ticket.", ephemeral=True)
            return
        ticket["atendente_id"] = interaction.user.id
        if ticket["status"] == "aguardando":
            ticket["status"] = "em_atendimento"
        if not ticket.get("primeira_resposta_staff_em"):
            ticket["primeira_resposta_staff_em"] = agora_iso()
        save_data(data)
        await atualizar_embed_ticket(interaction.channel, ticket, categoria)
        await interaction.response.send_message(f"🟢 {interaction.user.mention} assumiu este atendimento.")

    async def resolver_cb(self, interaction: discord.Interaction):
        _, ticket, categoria = self._carregar(self.guild_id, self.chave)
        if not ticket or ticket["status"] == "encerrado":
            await interaction.response.send_message("⚠️ Este ticket já está encerrado.", ephemeral=True)
            return
        if not eh_staff_do_ticket(interaction.user, categoria or {}):
            await interaction.response.send_message("❌ Apenas a equipe responsável pode fechar este ticket.", ephemeral=True)
            return
        await interaction.response.send_modal(ResultadoModal(self.guild_id, self.chave, "resolvido"))

    async def encerrar_cb(self, interaction: discord.Interaction):
        _, ticket, categoria = self._carregar(self.guild_id, self.chave)
        if not ticket or ticket["status"] == "encerrado":
            await interaction.response.send_message("⚠️ Este ticket já está encerrado.", ephemeral=True)
            return
        if not eh_staff_do_ticket(interaction.user, categoria or {}):
            await interaction.response.send_message("❌ Apenas a equipe responsável pode fechar este ticket.", ephemeral=True)
            return
        await interaction.response.send_modal(ResultadoModal(self.guild_id, self.chave, "cancelado"))


# =====================================================================
# TRANSCRIPT
# =====================================================================

async def enviar_log_evento(
    guild: discord.Guild, gconf: dict, titulo: str, cor: int, ticket: dict,
    canal: discord.TextChannel, campos_extra: list[tuple[str, str]] | None = None,
) -> None:
    """Envia um embed curto pro canal de logs quando um ticket é aberto ou encerrado."""
    canal_logs_id = gconf.get("canal_logs")
    if not canal_logs_id:
        return
    destino = guild.get_channel(canal_logs_id)
    if not destino:
        return

    prio_emoji, prio_label = PRIORIDADE_INFO[ticket["prioridade"]]
    embed = discord.Embed(title=titulo, color=cor)
    embed.add_field(name="Canal", value=canal.mention, inline=True)
    embed.add_field(name="Autor", value=f"<@{ticket['autor_id']}>", inline=True)
    embed.add_field(name="Categoria", value=f"{ticket['categoria_emoji']} {ticket['categoria_nome']}", inline=True)
    embed.add_field(name="Prioridade", value=f"{prio_emoji} {prio_label}", inline=True)
    for nome, valor in campos_extra or []:
        embed.add_field(name=nome, value=valor, inline=True)

    try:
        await destino.send(embed=embed)
    except discord.HTTPException:
        logger.exception("Falha ao enviar log de evento de ticket")


async def enviar_transcript(guild: discord.Guild, canal: discord.TextChannel, ticket: dict, gconf: dict) -> None:
    canal_logs_id = gconf.get("canal_logs")
    if not canal_logs_id:
        return
    destino = guild.get_channel(canal_logs_id)
    if not destino:
        return

    linhas = []
    try:
        async for msg in canal.history(limit=2000, oldest_first=True):
            hora = msg.created_at.strftime("%d/%m %H:%M")
            conteudo = msg.content or "[sem texto — embed/anexo]"
            linhas.append(f"[{hora}] {msg.author}: {conteudo}")
    except discord.HTTPException:
        linhas.append("(não foi possível carregar todo o histórico)")

    texto = "\n".join(linhas) if linhas else "(sem mensagens)"
    arquivo = discord.File(io.BytesIO(texto.encode("utf-8")), filename=f"ticket-{ticket['numero']:04d}.txt")

    embed = discord.Embed(
        title=f"🗂️ Transcript — Ticket #{ticket['numero']:04d}",
        color=COR_TICKETS,
    )
    embed.add_field(name="Autor", value=f"<@{ticket['autor_id']}>", inline=True)
    embed.add_field(name="Categoria", value=f"{ticket['categoria_emoji']} {ticket['categoria_nome']}", inline=True)
    atendente = f"<@{ticket['atendente_id']}>" if ticket.get("atendente_id") else "*(ninguém)*"
    embed.add_field(name="Atendente", value=atendente, inline=True)

    try:
        await destino.send(embed=embed, file=arquivo)
    except discord.HTTPException:
        logger.exception("Falha ao enviar transcript")


# =====================================================================
# AVALIAÇÃO
# =====================================================================

class ComentarioModal(discord.ui.Modal, title="Deixe um comentário (opcional)"):
    comentario = discord.ui.TextInput(label="Comentário", style=discord.TextStyle.paragraph, max_length=300)

    def __init__(self, guild_id: int, chave: str):
        super().__init__()
        self.guild_id = guild_id
        self.chave = chave

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        gdata = get_guild_data(data, self.guild_id)
        ticket = gdata["tickets"].get(self.chave)
        if ticket:
            ticket["comentario_avaliacao"] = str(self.comentario)
            save_data(data)
        await interaction.response.send_message("💬 Comentário registrado, obrigado!", ephemeral=True)


class AvaliacaoView(discord.ui.View):
    def __init__(self, guild_id: int, chave: str, autor_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.chave = chave
        self.autor_id = autor_id

        for estrelas in range(1, 6):
            botao = discord.ui.Button(
                label="⭐" * estrelas, style=discord.ButtonStyle.secondary, row=0,
                custom_id=f"ticket_avaliar:{guild_id}:{chave}:{estrelas}",
            )
            botao.callback = self._callback_estrela(estrelas)
            self.add_item(botao)

        comentar = discord.ui.Button(label="💬 Comentar (opcional)", style=discord.ButtonStyle.secondary, row=1,
                                      custom_id=f"ticket_comentar:{guild_id}:{chave}")
        comentar.callback = self.comentar_cb
        self.add_item(comentar)

    def _callback_estrela(self, estrelas: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.autor_id:
                await interaction.response.send_message("❌ Só quem abriu o ticket pode avaliar.", ephemeral=True)
                return
            data = load_data()
            gdata = get_guild_data(data, self.guild_id)
            ticket = gdata["tickets"].get(self.chave)
            if not ticket:
                await interaction.response.send_message("❌ Ticket não encontrado nos registros.", ephemeral=True)
                return
            ticket["avaliacao"] = estrelas
            save_data(data)
            await interaction.response.send_message(f"⭐ Obrigado pela avaliação de {estrelas} estrela(s)!", ephemeral=True)
        return callback

    async def comentar_cb(self, interaction: discord.Interaction):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message("❌ Só quem abriu o ticket pode comentar.", ephemeral=True)
            return
        await interaction.response.send_modal(ComentarioModal(self.guild_id, self.chave))


# =====================================================================
# DASHBOARD
# =====================================================================

def montar_dashboard(guild_id: int) -> discord.Embed:
    data = load_data()
    gdata = get_guild_data(data, guild_id)
    tickets = list(gdata["tickets"].values())

    embed = discord.Embed(title="📊 Dashboard de Atendimento", color=COR_TICKETS)

    if not tickets:
        embed.description = "Ainda não há tickets registrados neste servidor."
        return embed

    por_status = {chave: 0 for chave in STATUS_INFO}
    for t in tickets:
        por_status[t["status"]] = por_status.get(t["status"], 0) + 1

    ativos = sum(v for k, v in por_status.items() if k != "encerrado")
    embed.add_field(
        name="🎫 Visão Geral",
        value=(
            f"📈 Total: {len(tickets)}\n"
            f"🟢 Ativos: {ativos}\n"
            + "\n".join(f"{STATUS_INFO[k][0]} {STATUS_INFO[k][1]}: {v}" for k, v in por_status.items() if v)
        ),
        inline=True,
    )

    tempos_resposta = []
    tempos_resolucao = []
    avaliacoes = []
    ranking: dict[int, dict] = {}

    for t in tickets:
        criado = parse_iso(t["criado_em"])
        primeira = parse_iso(t.get("primeira_resposta_staff_em"))
        if criado and primeira:
            tempos_resposta.append((primeira - criado).total_seconds())
        fechado = parse_iso(t.get("fechado_em"))
        if criado and fechado:
            tempos_resolucao.append((fechado - criado).total_seconds())
        if t.get("avaliacao"):
            avaliacoes.append(t["avaliacao"])
        if t.get("atendente_id"):
            r = ranking.setdefault(t["atendente_id"], {"resolvidos": 0, "soma_nota": 0, "qtd_nota": 0})
            if t["status"] == "encerrado":
                r["resolvidos"] += 1
            if t.get("avaliacao"):
                r["soma_nota"] += t["avaliacao"]
                r["qtd_nota"] += 1

    tempo_resp_txt = formatar_duracao(sum(tempos_resposta) / len(tempos_resposta)) if tempos_resposta else "—"
    tempo_resol_txt = formatar_duracao(sum(tempos_resolucao) / len(tempos_resolucao)) if tempos_resolucao else "—"
    nota_media = round(sum(avaliacoes) / len(avaliacoes), 1) if avaliacoes else None

    embed.add_field(
        name="⏱️ Tempos",
        value=(
            f"Primeira resposta (média): {tempo_resp_txt}\n"
            f"Resolução (média): {tempo_resol_txt}"
        ),
        inline=True,
    )
    embed.add_field(
        name="⭐ Satisfação",
        value=(f"Nota média: {nota_media} ⭐\nAvaliações: {len(avaliacoes)}" if nota_media else "Ainda sem avaliações"),
        inline=True,
    )

    if ranking:
        top = sorted(ranking.items(), key=lambda kv: kv[1]["resolvidos"], reverse=True)[:5]
        linhas = []
        for uid, r in top:
            nota = round(r["soma_nota"] / r["qtd_nota"], 1) if r["qtd_nota"] else "—"
            linhas.append(f"<@{uid}> — {r['resolvidos']} resolvido(s), nota média {nota}")
        embed.add_field(name="🏆 Ranking da Equipe", value="\n".join(linhas), inline=False)

    return embed


# =====================================================================
# COG
# =====================================================================

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        config = load_config()
        for gid_str, gconf in config.items():
            gid = int(gid_str)
            categorias_ativas = {k: v for k, v in gconf.get("categorias", {}).items() if v.get("ativo", True)}
            if gconf.get("canal_painel") and categorias_ativas:
                try:
                    self.bot.add_view(PainelAberturaView(gid, categorias_ativas))
                except Exception:
                    logger.exception(f"Falha ao registrar painel de abertura de tickets (guild {gid})")

        data = load_data()
        for gid_str, gdata in data.items():
            gid = int(gid_str)
            for chave, ticket in gdata.get("tickets", {}).items():
                try:
                    if ticket["status"] != "encerrado":
                        self.bot.add_view(TicketControlView(gid, chave))
                    elif ticket.get("avaliacao") is None:
                        self.bot.add_view(AvaliacaoView(gid, chave, ticket["autor_id"]))
                except Exception:
                    logger.exception(f"Falha ao registrar view persistente do ticket #{chave} (guild {gid})")

        if not self.checar_sla.is_running():
            self.checar_sla.start()

    async def cog_unload(self):
        self.checar_sla.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        data = load_data()
        chave, ticket = localizar_ticket(data, message.guild.id, message.channel.id)
        if not ticket or ticket["status"] == "encerrado" or ticket.get("primeira_resposta_staff_em"):
            return
        if message.author.id == ticket["autor_id"]:
            return

        config = load_config()
        gconf = get_guild_config(config, message.guild.id)
        categoria = gconf["categorias"].get(ticket["categoria_id"], {})
        if not eh_staff_do_ticket(message.author, categoria):
            return

        ticket["primeira_resposta_staff_em"] = agora_iso()
        if ticket["status"] == "aguardando":
            ticket["status"] = "em_atendimento"
        save_data(data)
        await atualizar_embed_ticket(message.channel, ticket, categoria)

    @tasks.loop(minutes=1)
    async def checar_sla(self):
        data = load_data()
        config = load_config()
        alterado = False
        for gid_str, gdata in data.items():
            gconf = config.get(gid_str)
            if not gconf:
                continue
            guild = self.bot.get_guild(int(gid_str))
            if not guild:
                continue
            limite_min = gconf.get("aviso_sem_resposta_minutos", 15)
            for chave, ticket in gdata.get("tickets", {}).items():
                if ticket["status"] != "aguardando" or ticket.get("primeira_resposta_staff_em") or ticket.get("avisado_sem_resposta"):
                    continue
                criado = parse_iso(ticket["criado_em"])
                if not criado:
                    continue
                minutos = (datetime.now(timezone.utc) - criado).total_seconds() / 60
                if minutos < limite_min:
                    continue
                canal = guild.get_channel(ticket["canal_id"])
                if not canal:
                    continue
                categoria = gconf["categorias"].get(ticket["categoria_id"], {})
                mencoes = " ".join(f"<@&{cid}>" for cid in categoria.get("cargos_responsaveis", []))
                try:
                    await canal.send(f"⏰ {mencoes} este ticket está aguardando atendimento há mais de {limite_min} minutos!")
                except discord.HTTPException:
                    pass
                ticket["avisado_sem_resposta"] = True
                alterado = True
        if alterado:
            save_data(data)

    @checar_sla.before_loop
    async def antes_checar_sla(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="ticket-dashboard", description="Ver estatísticas do sistema de tickets")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def ticket_dashboard_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=montar_dashboard(interaction.guild_id))


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
ZYNTRAX_EOF_COGS_TICKETS.PY

echo "🔎 Verificando sintaxe..."
python3 -m py_compile cogs/*.py && echo "✅ Sintaxe OK"

echo "✅ Atualizacao aplicada com sucesso!"
echo "   Reinicie o bot (pkill -f bot.py && python3 bot.py)."
echo "   No /configuracoes -> 🎫 Tickets, selecione o Canal do Painel e o Canal de Logs, depois clique em Publicar."
