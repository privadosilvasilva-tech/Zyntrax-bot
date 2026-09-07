import json
import logging
import os
import random
from datetime import date, datetime, time as dtime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.carteira import formatar_reais

logger = logging.getLogger("bot.feriados")

CONFIG_FILE = "config/feriados_config.json"
CRIADOS_FILE = "config/feriados_criados.json"
TAG_NIX = "Desenvolvido por Nix"

VALOR_MAX_PERMITIDO = 2000.0

FERIADOS_FIXOS = [
    (1, 1, "🎉 Ano Novo"),
    (2, 14, "💘 Dia dos Namorados (Internacional)"),
    (4, 21, "🇧🇷 Tiradentes"),
    (5, 1, "💪 Dia do Trabalho"),
    (6, 12, "💑 Dia dos Namorados"),
    (9, 7, "🇧🇷 Independência do Brasil"),
    (10, 12, "🙏 N. Sra. Aparecida / Dia das Crianças"),
    (10, 31, "🎃 Halloween"),
    (11, 2, "🕯️ Finados"),
    (11, 15, "🇧🇷 Proclamação da República"),
    (11, 20, "✊🏿 Consciência Negra"),
    (12, 25, "🎄 Natal"),
    (12, 31, "🎊 Véspera de Ano Novo"),
]


# ----------------------------------------------------------------------------
# Cálculo de datas móveis (Páscoa e derivados) — funciona pra qualquer ano,
# sem precisar atualizar a lista todo ano.
# ----------------------------------------------------------------------------

def calcular_pascoa(ano: int) -> date:
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def _segundo_domingo(ano: int, mes: int) -> date:
    primeiro_dia = date(ano, mes, 1)
    primeiro_domingo = primeiro_dia + timedelta(days=(6 - primeiro_dia.weekday()) % 7)
    return primeiro_domingo + timedelta(days=7)


def feriados_do_ano(ano: int) -> list:
    lista = list(FERIADOS_FIXOS)

    pascoa = calcular_pascoa(ano)
    carnaval = pascoa - timedelta(days=47)
    sexta_santa = pascoa - timedelta(days=2)
    corpus_christi = pascoa + timedelta(days=60)
    lista.append((carnaval.month, carnaval.day, "🎭 Carnaval"))
    lista.append((sexta_santa.month, sexta_santa.day, "✝️ Sexta-feira Santa"))
    lista.append((corpus_christi.month, corpus_christi.day, "🍞 Corpus Christi"))

    dia_maes = _segundo_domingo(ano, 5)
    dia_pais = _segundo_domingo(ano, 8)
    lista.append((dia_maes.month, dia_maes.day, "🌷 Dia das Mães"))
    lista.append((dia_pais.month, dia_pais.day, "👔 Dia dos Pais"))

    return lista


# ----------------------------------------------------------------------------
# Persistência
# ----------------------------------------------------------------------------

def _carregar(arquivo: str) -> dict:
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler {arquivo}, recriando: {e}")
    return {}


def _salvar(arquivo: str, dados: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def config_padrao() -> dict:
    return {"ativo": False, "valor_min": 100.0, "valor_max": 500.0, "duracao_horas": 24}


def obter_config_guild(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = config_padrao()
    config[gid].setdefault("valor_max", 500.0)
    if config[gid]["valor_max"] > VALOR_MAX_PERMITIDO:
        config[gid]["valor_max"] = VALOR_MAX_PERMITIDO
    return config[gid]


# ----------------------------------------------------------------------------
# Painel de configuração
# ----------------------------------------------------------------------------

class ValoresFeriadoModal(discord.ui.Modal, title="Configurar valores do sorteio de feriado"):
    valor_min_input = discord.ui.TextInput(label="Valor mínimo do prêmio (R$)", default="100.00", max_length=15)
    valor_max_input = discord.ui.TextInput(label="Valor máximo do prêmio (R$) — até 2000", default="500.00", max_length=15)
    duracao_input = discord.ui.TextInput(label="Duração em horas", default="24", max_length=5)

    def __init__(self, dono_id: int):
        super().__init__()
        self.dono_id = dono_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            vmin = float(self.valor_min_input.value.replace(",", "."))
            vmax = float(self.valor_max_input.value.replace(",", "."))
            horas = float(self.duracao_input.value.replace(",", "."))
        except ValueError:
            await interaction.response.send_message("❌ Use apenas números nos valores e na duração.", ephemeral=True)
            return
        if vmin <= 0 or vmax <= 0 or horas <= 0:
            await interaction.response.send_message("❌ Os valores e a duração precisam ser maiores que zero.", ephemeral=True)
            return
        if vmax > VALOR_MAX_PERMITIDO:
            await interaction.response.send_message(
                f"❌ O valor máximo dos sorteios automáticos de feriado não pode passar de {formatar_reais(VALOR_MAX_PERMITIDO)}.",
                ephemeral=True,
            )
            return
        if vmin > vmax:
            await interaction.response.send_message("❌ O valor mínimo não pode ser maior que o máximo.", ephemeral=True)
            return

        config = _carregar(CONFIG_FILE)
        cfg = obter_config_guild(config, interaction.guild_id)
        cfg["valor_min"] = vmin
        cfg["valor_max"] = vmax
        cfg["duracao_horas"] = horas
        _salvar(CONFIG_FILE, config)

        view = FeriadosConfigView(self.dono_id)
        await interaction.response.edit_message(embed=view.embed(interaction.guild), view=view)


class FeriadosConfigView(discord.ui.View):
    def __init__(self, dono_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True)
            return False
        return True

    def embed(self, guild: discord.Guild) -> discord.Embed:
        config = _carregar(CONFIG_FILE)
        cfg = obter_config_guild(config, guild.id)
        status = "✅ Ativado" if cfg["ativo"] else "❌ Desativado"

        e = discord.Embed(title="🎉 Sorteios Automáticos de Feriado", color=0xF1C40F)
        e.description = (
            "No dia de um feriado ou data comemorativa, o bot cria sozinho um sorteio no servidor "
            "— sem tirar dinheiro de ninguém, é uma comemoração por conta da casa."
        )
        e.add_field(name="Status", value=status, inline=True)
        e.add_field(
            name="💰 Faixa de valor do prêmio",
            value=f"{formatar_reais(cfg['valor_min'])} — {formatar_reais(cfg['valor_max'])}",
            inline=True,
        )
        e.add_field(name="⏰ Duração", value=f"{cfg['duracao_horas']:g}h", inline=True)
        e.add_field(
            name="ℹ️ Canal e cargo de ping",
            value="Usa a mesma configuração do `/sorteio-config` (canal de início, canal de resultado, cargo de ping e cargos elegíveis).",
            inline=False,
        )
        e.set_footer(text=f"💡 Valor máximo permitido: {formatar_reais(VALOR_MAX_PERMITIDO)} • {TAG_NIX}")
        return e

    @discord.ui.button(label="🔀 Ativar/Desativar", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = _carregar(CONFIG_FILE)
        cfg = obter_config_guild(config, interaction.guild_id)
        cfg["ativo"] = not cfg["ativo"]
        _salvar(CONFIG_FILE, config)
        await interaction.response.edit_message(embed=self.embed(interaction.guild), view=self)

    @discord.ui.button(label="💰 Definir Valores e Duração", style=discord.ButtonStyle.success, row=0)
    async def valores_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ValoresFeriadoModal(self.dono_id))


# ----------------------------------------------------------------------------
# Cog
# ----------------------------------------------------------------------------

class Feriados(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.verificar_feriados.start()

    def cog_unload(self):
        self.verificar_feriados.cancel()

    @tasks.loop(time=dtime(hour=12, tzinfo=timezone.utc))
    async def verificar_feriados(self):
        hoje = datetime.now(timezone.utc).date()
        feriados_hoje = [f for f in feriados_do_ano(hoje.year) if f[0] == hoje.month and f[1] == hoje.day]
        if not feriados_hoje:
            return

        sorteios_cog = self.bot.get_cog("SorteiosEventos")
        if not sorteios_cog:
            logger.warning("Cog de sorteios não encontrado — feriado automático não pôde ser criado.")
            return

        config = _carregar(CONFIG_FILE)
        criados = _carregar(CRIADOS_FILE)

        for guild in self.bot.guilds:
            gcfg = config.get(str(guild.id))
            if not gcfg or not gcfg.get("ativo"):
                continue

            registro_guild = criados.setdefault(str(guild.id), {})
            for mes, dia, nome in feriados_hoje:
                chave = f"{mes:02d}-{dia:02d}"
                if registro_guild.get(chave) == hoje.year:
                    continue  # já criado nesse ano pra essa data

                valor = round(random.uniform(gcfg["valor_min"], min(gcfg["valor_max"], VALOR_MAX_PERMITIDO)), 2)
                try:
                    ok, _ = await sorteios_cog.criar_sorteio_automatico(
                        guild, f"{nome} — Sorteio Especial", valor, gcfg.get("duracao_horas", 24)
                    )
                except Exception:
                    logger.exception(f"Falha ao criar sorteio automático de feriado em {guild.id}")
                    ok = False

                if ok:
                    registro_guild[chave] = hoje.year

        _salvar(CRIADOS_FILE, criados)

    @verificar_feriados.before_loop
    async def before_verificar_feriados(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="feriados-config", description="Configurar sorteios automáticos de feriado (até R$ 2.000)")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def feriados_config_cmd(self, interaction: discord.Interaction):
        view = FeriadosConfigView(interaction.user.id)
        await interaction.response.send_message(embed=view.embed(interaction.guild), view=view, ephemeral=True)

    @app_commands.command(name="feriados-listar", description="Ver as próximas datas de feriado/sorteio automático")
    async def feriados_listar_cmd(self, interaction: discord.Interaction):
        hoje = datetime.now(timezone.utc).date()
        todos = [(date(hoje.year, m, d), nome) for m, d, nome in feriados_do_ano(hoje.year)]
        todos += [(date(hoje.year + 1, m, d), nome) for m, d, nome in feriados_do_ano(hoje.year + 1)]
        futuros = sorted((dt, nome) for dt, nome in todos if dt >= hoje)[:8]

        e = discord.Embed(title="📅 Próximas Datas Comemorativas", color=0xF1C40F)
        if futuros:
            linhas = []
            for dt, nome in futuros:
                ts = int(datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).timestamp())
                linhas.append(f"<t:{ts}:D> — {nome}")
            e.description = "\n".join(linhas)
        else:
            e.description = "Nenhuma data encontrada."
        e.set_footer(text=TAG_NIX)
        await interaction.response.send_message(embed=e, ephemeral=True)

    async def _erro_permissao(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você precisa ser administrador para usar esse comando."
        elif isinstance(error, app_commands.NoPrivateMessage):
            msg = "❌ Esse comando só pode ser usado dentro de um servidor."
        else:
            msg = "❌ Ocorreu um erro inesperado ao executar o comando."
            logger.exception("Erro em comando de feriados", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    @feriados_config_cmd.error
    async def feriados_config_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await self._erro_permissao(interaction, error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Feriados(bot))
