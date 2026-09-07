import json
import logging
import os
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("bot.carteira")

DATA_FILE = "config/carteira_data.json"
SALDO_INICIAL = 100.0
REWARD_VALOR = 150.0
TAG_NIX = "Desenvolvido por Nix"


def carregar() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler carteira_data.json, recriando: {e}")
    return {}


def salvar(dados: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def guild_data(dados: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in dados:
        dados[gid] = {"usuarios": {}, "autorizados": []}
    dados[gid].setdefault("usuarios", {})
    dados[gid].setdefault("autorizados", [])
    return dados[gid]


def usuario_data(gdata: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in gdata["usuarios"]:
        gdata["usuarios"][uid] = {
            "saldo": SALDO_INICIAL,
            "ultimo_reward": None,
            "transacoes": [],
        }
    return gdata["usuarios"][uid]


def registrar_transacao(udata: dict, tipo: str, valor: float, detalhe: str = "") -> None:
    udata["transacoes"].append(
        {
            "tipo": tipo,
            "valor": valor,
            "detalhe": detalhe,
            "data": datetime.now(timezone.utc).isoformat(),
        }
    )
    udata["transacoes"] = udata["transacoes"][-50:]


def formatar_reais(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def usuario_pode_gerenciar(interaction: discord.Interaction) -> bool:
    """Dono do servidor, administradores, ou quem foi autorizado via /dinheiro autorizar."""
    if interaction.guild.owner_id == interaction.user.id:
        return True
    if interaction.user.guild_permissions.administrator:
        return True
    dados = carregar()
    gdata = guild_data(dados, interaction.guild_id)
    role_ids = {r.id for r in interaction.user.roles}
    return interaction.user.id in gdata["autorizados"] or any(
        rid in gdata["autorizados"] for rid in role_ids
    )


def debitar_saldo(guild_id: int, user_id: int, valor: float, detalhe: str = "") -> bool:
    """Debita valor do saldo fictício de um usuário. Retorna False se saldo insuficiente."""
    dados = carregar()
    gdata = guild_data(dados, guild_id)
    udata = usuario_data(gdata, user_id)
    if udata["saldo"] < valor:
        return False
    udata["saldo"] -= valor
    registrar_transacao(udata, "Compra na loja", -valor, detalhe)
    salvar(dados)
    return True


def creditar_saldo(guild_id: int, user_id: int, valor: float, tipo: str, detalhe: str = "") -> float:
    dados = carregar()
    gdata = guild_data(dados, guild_id)
    udata = usuario_data(gdata, user_id)
    udata["saldo"] += valor
    registrar_transacao(udata, tipo, valor, detalhe)
    salvar(dados)
    return udata["saldo"]


def obter_saldo(guild_id: int, user_id: int) -> float:
    dados = carregar()
    gdata = guild_data(dados, guild_id)
    udata = usuario_data(gdata, user_id)
    salvar(dados)
    return udata["saldo"]


class Carteira(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="saldo", description="Ver o saldo de dinheiro fictício de um usuário")
    @app_commands.describe(usuario="Usuário para consultar (padrão: você mesmo)")
    async def saldo_cmd(self, interaction: discord.Interaction, usuario: discord.Member = None):
        alvo = usuario or interaction.user
        dados = carregar()
        gdata = guild_data(dados, interaction.guild_id)
        udata = usuario_data(gdata, alvo.id)
        salvar(dados)

        embed = discord.Embed(title="🪙 Carteira", color=0xF1C40F)
        embed.set_author(name=alvo.display_name, icon_url=alvo.display_avatar.url)
        embed.add_field(name="💰 Saldo atual", value=formatar_reais(udata["saldo"]), inline=False)

        ultimas = list(reversed(udata["transacoes"][-5:]))
        if ultimas:
            linhas = []
            for t in ultimas:
                sinal = "+" if t["valor"] >= 0 else ""
                data_fmt = t["data"][:16].replace("T", " ")
                linhas.append(f"`{data_fmt}` **{t['tipo']}** {sinal}{formatar_reais(t['valor'])}")
            embed.add_field(name="📜 Últimas transações", value="\n".join(linhas), inline=False)
        else:
            embed.add_field(name="📜 Últimas transações", value="Nenhuma transação ainda.", inline=False)

        embed.set_footer(text=TAG_NIX)
        await interaction.response.send_message(embed=embed, ephemeral=(alvo.id != interaction.user.id))

    @app_commands.command(name="reward", description="Resgatar sua recompensa diária de dinheiro fictício")
    async def reward_cmd(self, interaction: discord.Interaction):
        dados = carregar()
        gdata = guild_data(dados, interaction.guild_id)
        udata = usuario_data(gdata, interaction.user.id)

        agora = datetime.now(timezone.utc)
        if udata["ultimo_reward"]:
            ultimo = datetime.fromisoformat(udata["ultimo_reward"])
            if agora - ultimo < timedelta(hours=24):
                proximo = ultimo + timedelta(hours=24)
                restante = proximo - agora
                horas, resto = divmod(int(restante.total_seconds()), 3600)
                minutos = resto // 60
                await interaction.response.send_message(
                    f"⏳ Você já resgatou sua recompensa hoje. Tente novamente em **{horas}h {minutos}min**.",
                    ephemeral=True,
                )
                return

        udata["saldo"] += REWARD_VALOR
        udata["ultimo_reward"] = agora.isoformat()
        registrar_transacao(udata, "Reward diário", REWARD_VALOR, "Recompensa diária")
        salvar(dados)

        embed = discord.Embed(
            title="🎁 Recompensa Resgatada!",
            description=f"Você recebeu **{formatar_reais(REWARD_VALOR)}**!\nSaldo atual: **{formatar_reais(udata['saldo'])}**",
            color=0x2ECC71,
        )
        embed.set_footer(text=TAG_NIX)
        await interaction.response.send_message(embed=embed)

    dinheiro_group = app_commands.Group(
        name="dinheiro", description="Gerenciar dinheiro fictício (requer autorização)"
    )

    @dinheiro_group.command(name="adicionar", description="Adicionar dinheiro fictício a um usuário")
    @app_commands.describe(usuario="Usuário", valor="Valor a adicionar")
    async def dinheiro_adicionar(self, interaction: discord.Interaction, usuario: discord.Member, valor: float):
        if not usuario_pode_gerenciar(interaction):
            await interaction.response.send_message(
                "❌ Você não tem autorização para mexer no dinheiro fictício.", ephemeral=True
            )
            return
        if valor <= 0:
            await interaction.response.send_message("❌ O valor precisa ser maior que zero.", ephemeral=True)
            return

        novo_saldo = creditar_saldo(interaction.guild_id, usuario.id, valor, "Adição (admin)", f"Por {interaction.user.display_name}")
        await interaction.response.send_message(
            f"✅ Adicionado **{formatar_reais(valor)}** para {usuario.mention}. Novo saldo: **{formatar_reais(novo_saldo)}**"
        )

    @dinheiro_group.command(name="remover", description="Remover dinheiro fictício de um usuário")
    @app_commands.describe(usuario="Usuário", valor="Valor a remover")
    async def dinheiro_remover(self, interaction: discord.Interaction, usuario: discord.Member, valor: float):
        if not usuario_pode_gerenciar(interaction):
            await interaction.response.send_message(
                "❌ Você não tem autorização para mexer no dinheiro fictício.", ephemeral=True
            )
            return
        if valor <= 0:
            await interaction.response.send_message("❌ O valor precisa ser maior que zero.", ephemeral=True)
            return

        dados = carregar()
        gdata = guild_data(dados, interaction.guild_id)
        udata = usuario_data(gdata, usuario.id)
        valor_removido = min(valor, udata["saldo"])
        udata["saldo"] = max(0.0, udata["saldo"] - valor)
        registrar_transacao(udata, "Remoção (admin)", -valor_removido, f"Por {interaction.user.display_name}")
        salvar(dados)

        await interaction.response.send_message(
            f"✅ Removido **{formatar_reais(valor_removido)}** de {usuario.mention}. Novo saldo: **{formatar_reais(udata['saldo'])}**"
        )

    @dinheiro_group.command(name="transferir", description="Transferir dinheiro fictício para outro usuário")
    @app_commands.describe(usuario="Destinatário", valor="Valor a transferir")
    async def dinheiro_transferir(self, interaction: discord.Interaction, usuario: discord.Member, valor: float):
        if usuario.id == interaction.user.id:
            await interaction.response.send_message("❌ Você não pode transferir para si mesmo.", ephemeral=True)
            return
        if usuario.bot:
            await interaction.response.send_message("❌ Você não pode transferir para um bot.", ephemeral=True)
            return
        if valor <= 0:
            await interaction.response.send_message("❌ O valor precisa ser maior que zero.", ephemeral=True)
            return

        dados = carregar()
        gdata = guild_data(dados, interaction.guild_id)
        origem = usuario_data(gdata, interaction.user.id)

        if origem["saldo"] < valor:
            await interaction.response.send_message(
                f"❌ Saldo insuficiente. Seu saldo atual é **{formatar_reais(origem['saldo'])}**.", ephemeral=True
            )
            return

        destino = usuario_data(gdata, usuario.id)
        origem["saldo"] -= valor
        destino["saldo"] += valor
        registrar_transacao(origem, "Transferência enviada", -valor, f"Para {usuario.display_name}")
        registrar_transacao(destino, "Transferência recebida", valor, f"De {interaction.user.display_name}")
        salvar(dados)

        await interaction.response.send_message(
            f"✅ Você transferiu **{formatar_reais(valor)}** para {usuario.mention}. "
            f"Seu novo saldo: **{formatar_reais(origem['saldo'])}**"
        )

    @dinheiro_group.command(
        name="autorizar",
        description="Autorizar um usuário ou cargo a gerenciar o dinheiro fictício (apenas dono do servidor)",
    )
    @app_commands.describe(usuario="Usuário a autorizar (opcional)", cargo="Cargo a autorizar (opcional)")
    async def dinheiro_autorizar(
        self, interaction: discord.Interaction, usuario: discord.Member = None, cargo: discord.Role = None
    ):
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Apenas o dono do servidor pode autorizar alguém a gerenciar o dinheiro fictício.", ephemeral=True
            )
            return
        if not usuario and not cargo:
            await interaction.response.send_message(
                "❌ Informe um usuário ou um cargo para autorizar.", ephemeral=True
            )
            return

        dados = carregar()
        gdata = guild_data(dados, interaction.guild_id)
        alvo_id = usuario.id if usuario else cargo.id
        if alvo_id in gdata["autorizados"]:
            await interaction.response.send_message("⚠️ Esse alvo já está autorizado.", ephemeral=True)
            return

        gdata["autorizados"].append(alvo_id)
        salvar(dados)

        alvo_nome = usuario.mention if usuario else cargo.mention
        await interaction.response.send_message(f"✅ {alvo_nome} agora pode usar `/dinheiro adicionar` e `/dinheiro remover`.")

    @dinheiro_group.command(
        name="revogar", description="Remover a autorização de um usuário ou cargo (apenas dono do servidor)"
    )
    @app_commands.describe(usuario="Usuário a revogar (opcional)", cargo="Cargo a revogar (opcional)")
    async def dinheiro_revogar(
        self, interaction: discord.Interaction, usuario: discord.Member = None, cargo: discord.Role = None
    ):
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Apenas o dono do servidor pode revogar autorizações.", ephemeral=True
            )
            return
        if not usuario and not cargo:
            await interaction.response.send_message(
                "❌ Informe um usuário ou um cargo para revogar.", ephemeral=True
            )
            return

        dados = carregar()
        gdata = guild_data(dados, interaction.guild_id)
        alvo_id = usuario.id if usuario else cargo.id
        if alvo_id not in gdata["autorizados"]:
            await interaction.response.send_message("⚠️ Esse alvo não está autorizado.", ephemeral=True)
            return

        gdata["autorizados"].remove(alvo_id)
        salvar(dados)
        await interaction.response.send_message("✅ Autorização revogada.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Carteira(bot))
