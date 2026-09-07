"""
Utilitários compartilhados pelo sistema de comandos de moderação (cogs/moderacao_comandos.py).
Prefixado com "_" de propósito: o bot.py ignora arquivos que começam com "_" ao carregar cogs,
então este módulo nunca é carregado como extensão, só importado.
"""
import re
import json
import os
import time
import discord
from discord import app_commands
from typing import Optional

# ─────────────────────────────────────────────────────────────────
# TAG PADRÃO DE RODAPÉ (usar em TODOS os embeds do sistema de moderação)
# ─────────────────────────────────────────────────────────────────

FOOTER_TEXT = "Desenvolvido por Nix • [🚀] • Zyntra / #Support561"

def aplicar_rodape(embed: discord.Embed) -> discord.Embed:
    """Aplica a tag padrão no rodapé do embed, preservando ícone se já houver um."""
    embed.set_footer(text=FOOTER_TEXT)
    return embed

# ─────────────────────────────────────────────────────────────────
# ARQUIVOS DE DADOS
# ─────────────────────────────────────────────────────────────────

MOD_CONFIG_FILE = "config/moderacao_config.json"
CASOS_FILE = "config/casos.json"

def _load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def _save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_mod_config() -> dict:
    return _load_json(MOD_CONFIG_FILE)

def save_mod_config(data: dict) -> None:
    _save_json(MOD_CONFIG_FILE, data)

def get_guild_mod_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {}
    return config[gid]

# ─────────────────────────────────────────────────────────────────
# PERMISSÕES: staff whitelist + permissão nativa do Discord
# ─────────────────────────────────────────────────────────────────

def get_staff_roles(guild_id: int) -> list[int]:
    config = load_mod_config()
    gconf = get_guild_mod_config(config, guild_id)
    return gconf.get("staff_roles", [])

def set_staff_roles(guild_id: int, roles: list[int]) -> None:
    config = load_mod_config()
    gconf = get_guild_mod_config(config, guild_id)
    gconf["staff_roles"] = roles
    save_mod_config(config)

def tem_permissao(member: discord.Member, permissao_nativa: str) -> bool:
    """
    Retorna True se o membro pode usar um comando de moderação que exige `permissao_nativa`
    (ex: 'ban_members', 'kick_members', 'manage_messages', 'manage_channels',
    'manage_roles', 'moderate_members').

    Regras (qualquer uma libera o acesso):
    - É Administrador do servidor
    - Possui a permissão nativa do Discord exigida
    - Possui um cargo configurado na whitelist de staff (/permissoes)
    """
    if member.guild_permissions.administrator:
        return True
    if getattr(member.guild_permissions, permissao_nativa, False):
        return True
    staff_roles = set(get_staff_roles(member.guild.id))
    if staff_roles and any(r.id in staff_roles for r in member.roles):
        return True
    return False

def checar_permissao(permissao_nativa: str):
    """Decorator para slash commands: exige a permissão nativa OU cargo de staff OU admin."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        if tem_permissao(interaction.user, permissao_nativa):
            return True
        raise app_commands.CheckFailure(
            f"❌ Você não tem permissão para usar esse comando. "
            f"É necessário ser Administrador, ter a permissão `{permissao_nativa}` "
            f"ou um cargo de staff configurado (`/permissoes`)."
        )
    return app_commands.check(predicate)

# ─────────────────────────────────────────────────────────────────
# HIERARQUIA: impede punir quem tem cargo igual/maior, o dono, ou o próprio bot
# ─────────────────────────────────────────────────────────────────

def pode_moderar(autor: discord.Member, alvo: discord.Member, bot_member: discord.Member) -> tuple[bool, str]:
    if alvo.id == autor.id:
        return False, "❌ Você não pode aplicar essa ação em si mesmo."
    if alvo.id == autor.guild.owner_id:
        return False, "❌ Você não pode aplicar essa ação no dono do servidor."
    if alvo.id == bot_member.id:
        return False, "❌ Eu não posso aplicar essa ação em mim mesmo."
    if alvo.bot and alvo.top_role >= bot_member.top_role:
        return False, "❌ Meu cargo precisa estar acima do cargo desse bot para essa ação."
    if autor.id != autor.guild.owner_id and alvo.top_role >= autor.top_role:
        return False, "❌ Você não pode aplicar essa ação em alguém com cargo igual ou superior ao seu."
    if alvo.top_role >= bot_member.top_role:
        return False, "❌ Meu cargo precisa estar acima do cargo desse membro para essa ação."
    return True, ""

# ─────────────────────────────────────────────────────────────────
# DURAÇÃO: converte "10m", "2h", "1d", "1d12h" etc em segundos
# ─────────────────────────────────────────────────────────────────

_UNIDADES = {"s": 1, "m": 60, "h": 3600, "d": 86400}

def parse_duracao(texto: str) -> Optional[int]:
    """Converte uma string de duração (ex: '10m', '2h30m', '1d') em segundos. None se inválida."""
    texto = texto.strip().lower().replace(" ", "")
    if not texto:
        return None
    partes = re.findall(r"(\d+)([smhd])", texto)
    if not partes:
        return None
    total = 0
    for valor, unidade in partes:
        total += int(valor) * _UNIDADES[unidade]
    return total if total > 0 else None

def formatar_duracao(segundos: int) -> str:
    dias, resto = divmod(segundos, 86400)
    horas, resto = divmod(resto, 3600)
    minutos, seg = divmod(resto, 60)
    partes = []
    if dias:
        partes.append(f"{dias}d")
    if horas:
        partes.append(f"{horas}h")
    if minutos:
        partes.append(f"{minutos}m")
    if seg and not dias and not horas:
        partes.append(f"{seg}s")
    return " ".join(partes) if partes else "0s"

# ─────────────────────────────────────────────────────────────────
# SISTEMA DE CASOS (histórico de punições)
# ─────────────────────────────────────────────────────────────────

def load_casos() -> dict:
    return _load_json(CASOS_FILE)

def save_casos(data: dict) -> None:
    _save_json(CASOS_FILE, data)

def registrar_caso(
    guild_id: int,
    tipo: str,
    alvo_id: int,
    alvo_tag: str,
    moderador_id: int,
    moderador_tag: str,
    motivo: str,
    duracao_segundos: Optional[int] = None,
) -> dict:
    """Cria um novo caso, salva em disco e retorna o registro criado (com 'id' numérico)."""
    data = load_casos()
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {"next_id": 1, "casos": []}

    caso_id = data[gid]["next_id"]
    caso = {
        "id": caso_id,
        "tipo": tipo,
        "alvo_id": alvo_id,
        "alvo_tag": alvo_tag,
        "moderador_id": moderador_id,
        "moderador_tag": moderador_tag,
        "motivo": motivo or "Não especificado",
        "timestamp": int(time.time()),
        "duracao_segundos": duracao_segundos,
        "ativo": tipo in ("warn", "mute", "timeout", "tempban"),
    }
    data[gid]["casos"].append(caso)
    data[gid]["next_id"] += 1
    save_casos(data)
    return caso

def get_caso(guild_id: int, caso_id: int) -> Optional[dict]:
    data = load_casos()
    gconf = data.get(str(guild_id), {"casos": []})
    for caso in gconf["casos"]:
        if caso["id"] == caso_id:
            return caso
    return None

def get_casos_membro(guild_id: int, membro_id: int) -> list[dict]:
    data = load_casos()
    gconf = data.get(str(guild_id), {"casos": []})
    return [c for c in gconf["casos"] if c["alvo_id"] == membro_id]

def get_casos_recentes(guild_id: int, limite: int = 10) -> list[dict]:
    data = load_casos()
    gconf = data.get(str(guild_id), {"casos": []})
    return list(reversed(gconf["casos"]))[:limite]

def desativar_casos_ativos(guild_id: int, membro_id: int, tipos: list[str]) -> None:
    """Marca como inativos os casos de certos tipos (ex: ao dar /unmute, desativa 'mute' ativos)."""
    data = load_casos()
    gid = str(guild_id)
    if gid not in data:
        return
    for caso in data[gid]["casos"]:
        if caso["alvo_id"] == membro_id and caso["tipo"] in tipos and caso["ativo"]:
            caso["ativo"] = False
    save_casos(data)

def remover_caso(guild_id: int, caso_id: int) -> bool:
    data = load_casos()
    gid = str(guild_id)
    if gid not in data:
        return False
    antes = len(data[gid]["casos"])
    data[gid]["casos"] = [c for c in data[gid]["casos"] if c["id"] != caso_id]
    save_casos(data)
    return len(data[gid]["casos"]) < antes

# ─────────────────────────────────────────────────────────────────
# LOG AUTOMÁTICO NO CANAL DE MODERAÇÃO (reaproveita config de logs_moderacao.py)
# ─────────────────────────────────────────────────────────────────

CORES_TIPO = {
    "ban": 0xE74C3C, "tempban": 0xE74C3C, "unban": 0x2ECC71,
    "kick": 0xE67E22, "mute": 0xF1C40F, "unmute": 0x2ECC71,
    "timeout": 0xF1C40F, "untimeout": 0x2ECC71,
    "warn": 0xF39C12, "unwarn": 0x2ECC71,
    "clear": 0x3498DB, "purge": 0x3498DB,
    "lock": 0x992D22, "unlock": 0x2ECC71, "slowmode": 0x3498DB,
    "role": 0x9B59B6, "report": 0xE91E63,
}

EMOJIS_TIPO = {
    "ban": "🔨", "tempban": "⏳🔨", "unban": "✅",
    "kick": "👢", "mute": "🔇", "unmute": "🔊",
    "timeout": "⏱️", "untimeout": "✅",
    "warn": "⚠️", "unwarn": "✅",
    "clear": "🧹", "purge": "🧹",
    "lock": "🔒", "unlock": "🔓", "slowmode": "🐌",
    "role": "🎭", "report": "🚨",
}

async def enviar_log_moderacao(bot: discord.Client, guild: discord.Guild, caso: dict, extra_desc: str = "") -> None:
    config = load_mod_config()
    gconf = get_guild_mod_config(config, guild.id)
    logs_conf = gconf.get("logs", {})
    if not logs_conf.get("enabled") or not logs_conf.get("channel_id"):
        return

    canal = guild.get_channel(logs_conf["channel_id"])
    if canal is None:
        return

    tipo = caso["tipo"]
    embed = discord.Embed(
        title=f"{EMOJIS_TIPO.get(tipo, '📋')} Caso #{caso['id']} — {tipo.upper()}",
        color=CORES_TIPO.get(tipo, 0x7289DA),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="👤 Alvo", value=f"{caso['alvo_tag']} (`{caso['alvo_id']}`)", inline=True)
    embed.add_field(name="🛡️ Moderador", value=f"{caso['moderador_tag']} (`{caso['moderador_id']}`)", inline=True)
    if caso.get("duracao_segundos"):
        embed.add_field(name="⏳ Duração", value=formatar_duracao(caso["duracao_segundos"]), inline=True)
    embed.add_field(name="📝 Motivo", value=caso["motivo"], inline=False)
    if extra_desc:
        embed.description = extra_desc
    aplicar_rodape(embed)

    try:
        await canal.send(embed=embed)
    except discord.HTTPException:
        pass

# ─────────────────────────────────────────────────────────────────
# VIEW DE CONFIRMAÇÃO (para ações perigosas: ban, tempban, unban, kick)
# ─────────────────────────────────────────────────────────────────

class ConfirmarAcaoView(discord.ui.View):
    """Botões Confirmar/Cancelar. Só quem executou o comando pode responder. Expira em 30s."""
    def __init__(self, autor_id: int):
        super().__init__(timeout=30)
        self.autor_id = autor_id
        self.confirmado: Optional[bool] = None
        self.interacao_resposta: Optional[discord.Interaction] = None
        self.mensagem: Optional[discord.InteractionMessage] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "❌ Apenas quem executou o comando pode confirmar essa ação.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmado = True
        self.interacao_resposta = interaction
        self.stop()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmado = False
        self.interacao_resposta = interaction
        self.stop()

    async def on_timeout(self) -> None:
        self.confirmado = False
        if self.mensagem:
            try:
                await self.mensagem.edit(content="⌛ Tempo esgotado. Ação cancelada automaticamente.", embed=None, view=None)
            except discord.HTTPException:
                pass
