import json
import logging
import os
import random
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs._utils_select import ChannelSelectComAutocomplete, RoleSelectComAutocomplete, UserSelectComAutocomplete
from cogs.carteira import creditar_saldo, debitar_saldo, formatar_reais, obter_saldo, usuario_pode_gerenciar

logger = logging.getLogger("bot.sorteios")

CONFIG_FILE = "config/sorteios_config.json"
ATIVOS_FILE = "config/sorteios_ativos.json"
TAG_NIX = "Desenvolvido por Nix"

NOME_TIPO = {
    "sorteio": ("🎉 Sorteio", 0xF1C40F),
    "evento": ("🎊 Evento", 0xE67E22),
}


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


def carregar_config() -> dict:
    return _carregar(CONFIG_FILE)


def salvar_config(dados: dict) -> None:
    _salvar(CONFIG_FILE, dados)


def carregar_ativos() -> dict:
    return _carregar(ATIVOS_FILE)


def salvar_ativos(dados: dict) -> None:
    _salvar(ATIVOS_FILE, dados)


def config_padrao() -> dict:
    return {"canal_inicio": None, "canal_resultado": None, "cargo_ping": None, "cargos_elegiveis": []}


def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {"sorteio": config_padrao(), "evento": config_padrao()}
    config[gid].setdefault("sorteio", config_padrao())
    config[gid].setdefault("evento", config_padrao())
    return config[gid]


# ----------------------------------------------------------------------------
# Views de participação (persistente)
# ----------------------------------------------------------------------------

class ParticiparView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Participar!", style=discord.ButtonStyle.success, custom_id="sorteio_evento_participar")
    async def participar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ativos = carregar_ativos()
        record = ativos.get(str(interaction.message.id))
        if not record or record.get("finalizado"):
            await interaction.response.send_message("❌ Esse sorteio/evento já foi encerrado.", ephemeral=True)
            return

        cargos_elegiveis = record.get("cargos_elegiveis") or []
        if cargos_elegiveis:
            role_ids_usuario = {r.id for r in interaction.user.roles}
            if not role_ids_usuario & set(cargos_elegiveis):
                cargos_txt = ", ".join(f"<@&{rid}>" for rid in cargos_elegiveis)
                await interaction.response.send_message(
                    f"❌ Você precisa ter um destes cargos para participar: {cargos_txt}", ephemeral=True
                )
                return

        participantes = record.setdefault("participantes", [])
        if interaction.user.id in participantes:
            participantes.remove(interaction.user.id)
            msg_txt = "❌ Você saiu da participação."
        else:
            participantes.append(interaction.user.id)
            msg_txt = "✅ Você está participando! Boa sorte 🍀"
        ativos[str(interaction.message.id)] = record
        salvar_ativos(ativos)

        try:
            embed = interaction.message.embeds[0]
            for i, field in enumerate(embed.fields):
                if field.name == "👤 Participantes":
                    embed.set_field_at(i, name="👤 Participantes", value=str(len(participantes)), inline=False)
                    break
            await interaction.message.edit(embed=embed)
        except (IndexError, discord.HTTPException):
            pass

        await interaction.response.send_message(msg_txt, ephemeral=True)


# ----------------------------------------------------------------------------
# Painel de configuração (canais, ping, elegibilidade)
# ----------------------------------------------------------------------------

class SorteioEventoConfigView(discord.ui.View):
    def __init__(self, dono_id: int, tipo: str):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.tipo = tipo

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True)
            return False
        return True

    def embed(self, guild: discord.Guild) -> discord.Embed:
        config = carregar_config()
        cfg = get_guild_config(config, guild.id)[self.tipo]
        nome, cor = NOME_TIPO[self.tipo]

        canal_inicio = guild.get_channel(cfg["canal_inicio"]) if cfg.get("canal_inicio") else None
        canal_resultado = guild.get_channel(cfg["canal_resultado"]) if cfg.get("canal_resultado") else None
        cargo_ping = guild.get_role(cfg["cargo_ping"]) if cfg.get("cargo_ping") else None
        cargos_elegiveis = [guild.get_role(rid) for rid in cfg.get("cargos_elegiveis", [])]
        cargos_elegiveis = [c.mention for c in cargos_elegiveis if c]

        e = discord.Embed(title=f"⚙️ Configurar {nome}", color=cor)
        e.add_field(name="📺 Canal de Início", value=canal_inicio.mention if canal_inicio else "Não configurado", inline=True)
        e.add_field(name="🏆 Canal de Resultados", value=canal_resultado.mention if canal_resultado else "Não configurado", inline=True)
        e.add_field(name="🔔 Cargo de Ping", value=cargo_ping.mention if cargo_ping else "Nenhum", inline=True)
        e.add_field(
            name="👥 Cargos Elegíveis",
            value=", ".join(cargos_elegiveis) if cargos_elegiveis else "Todos podem participar",
            inline=False,
        )
        e.set_footer(text=TAG_NIX)
        return e

    @discord.ui.button(label="📺 Canal de Início", style=discord.ButtonStyle.primary, row=0)
    async def canal_inicio_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def salvar_canal(inter: discord.Interaction, channel_id: int):
            cfg = carregar_config()
            get_guild_config(cfg, inter.guild_id)[self.tipo]["canal_inicio"] = channel_id
            salvar_config(cfg)
            canal = inter.guild.get_channel(channel_id)
            await inter.response.send_message(f"✅ Canal de início definido: {canal.mention if canal else channel_id}", ephemeral=True)

        view = discord.ui.View(timeout=180)
        view.add_item(ChannelSelectComAutocomplete(callback=salvar_canal))
        await interaction.response.send_message("Selecione o canal onde os sorteios/eventos serão anunciados ao iniciar:", view=view, ephemeral=True)

    @discord.ui.button(label="🏆 Canal de Resultados", style=discord.ButtonStyle.primary, row=0)
    async def canal_resultado_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def salvar_canal(inter: discord.Interaction, channel_id: int):
            cfg = carregar_config()
            get_guild_config(cfg, inter.guild_id)[self.tipo]["canal_resultado"] = channel_id
            salvar_config(cfg)
            canal = inter.guild.get_channel(channel_id)
            await inter.response.send_message(f"✅ Canal de resultados definido: {canal.mention if canal else channel_id}", ephemeral=True)

        view = discord.ui.View(timeout=180)
        view.add_item(ChannelSelectComAutocomplete(callback=salvar_canal))
        await interaction.response.send_message("Selecione o canal onde os resultados serão anunciados:", view=view, ephemeral=True)

    @discord.ui.button(label="🔔 Cargo de Ping", style=discord.ButtonStyle.primary, row=1)
    async def cargo_ping_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def salvar_cargo(inter: discord.Interaction, role_id: int):
            cfg = carregar_config()
            get_guild_config(cfg, inter.guild_id)[self.tipo]["cargo_ping"] = role_id
            salvar_config(cfg)
            role = inter.guild.get_role(role_id)
            await inter.response.send_message(f"✅ Cargo de ping definido: {role.mention if role else role_id}", ephemeral=True)

        view = discord.ui.View(timeout=180)
        view.add_item(RoleSelectComAutocomplete(callback=salvar_cargo))
        await interaction.response.send_message("Selecione o cargo que será marcado quando um sorteio/evento começar:", view=view, ephemeral=True)

    @discord.ui.button(label="👥 Cargos Elegíveis", style=discord.ButtonStyle.primary, row=1)
    async def cargos_elegiveis_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def adicionar_cargo(inter: discord.Interaction, role_id: int):
            cfg = carregar_config()
            lista = get_guild_config(cfg, inter.guild_id)[self.tipo].setdefault("cargos_elegiveis", [])
            if role_id not in lista:
                lista.append(role_id)
            salvar_config(cfg)
            role = inter.guild.get_role(role_id)
            await inter.response.send_message(f"✅ Cargo adicionado à lista de elegíveis: {role.mention if role else role_id}", ephemeral=True)

        view = discord.ui.View(timeout=180)
        view.add_item(RoleSelectComAutocomplete(callback=adicionar_cargo, min_values=1, max_values=5))
        await interaction.response.send_message(
            "Selecione até 5 cargos que podem participar (deixe sem configurar para liberar a todos):",
            view=view, ephemeral=True,
        )

    @discord.ui.button(label="🗑️ Limpar Cargos Elegíveis", style=discord.ButtonStyle.danger, row=2)
    async def limpar_cargos_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = carregar_config()
        get_guild_config(cfg, interaction.guild_id)[self.tipo]["cargos_elegiveis"] = []
        salvar_config(cfg)
        await interaction.response.send_message("🗑️ Lista de cargos elegíveis limpa. Agora todos podem participar.", ephemeral=True)


# ----------------------------------------------------------------------------
# Criação de sorteio/evento
# ----------------------------------------------------------------------------

class CriarSorteioModal(discord.ui.Modal):
    titulo_input = discord.ui.TextInput(label="Título", max_length=100)
    valor_input = discord.ui.TextInput(label="Valor do prêmio (R$)", max_length=15)
    vencedores_input = discord.ui.TextInput(label="Quantidade de vencedores", max_length=3, default="1")
    duracao_input = discord.ui.TextInput(label="Duração em minutos", max_length=6, default="60")

    def __init__(self, tipo: str):
        super().__init__(title="Criar Sorteio" if tipo == "sorteio" else "Criar Evento")
        self.tipo = tipo
        self.titulo_input.default = "🎉 Sorteio Especial" if tipo == "sorteio" else "🎊 Evento Especial"
        self.valor_input.placeholder = "Ex: 100.00" if tipo == "sorteio" else "Ex: 5000.00"

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor_f = float(self.valor_input.value.replace(",", "."))
            vencedores_i = int(self.vencedores_input.value)
            duracao_i = int(self.duracao_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Valor, vencedores ou duração inválidos. Use apenas números.", ephemeral=True)
            return
        if valor_f <= 0 or vencedores_i <= 0 or duracao_i <= 0:
            await interaction.response.send_message("❌ Valor, vencedores e duração precisam ser maiores que zero.", ephemeral=True)
            return

        cog = interaction.client.get_cog("SorteiosEventos")
        if not cog:
            await interaction.response.send_message("❌ Sistema de sorteios indisponível no momento.", ephemeral=True)
            return

        view = PatrocinadorView(cog, self.tipo, self.titulo_input.value.strip(), valor_f, vencedores_i, duracao_i)
        await interaction.response.send_message(
            "🏷️ Selecione o patrocinador (opcional) ou clique em pular:", view=view, ephemeral=True
        )


class PatrocinadorView(discord.ui.View):
    def __init__(self, cog: "SorteiosEventos", tipo: str, titulo: str, valor: float, vencedores: int, duracao: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.tipo = tipo
        self.titulo = titulo
        self.valor = valor
        self.vencedores = vencedores
        self.duracao = duracao
        self.add_item(UserSelectComAutocomplete(callback=self.selecionar_patrocinador))

    async def selecionar_patrocinador(self, interaction: discord.Interaction, user_id: int):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.criar_sorteio(interaction, self.tipo, self.titulo, self.valor, self.vencedores, self.duracao, user_id)

    @discord.ui.button(label="⏭️ Pular (sem patrocinador)", style=discord.ButtonStyle.secondary)
    async def pular_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.criar_sorteio(interaction, self.tipo, self.titulo, self.valor, self.vencedores, self.duracao, None)


# ----------------------------------------------------------------------------
# Cog
# ----------------------------------------------------------------------------

class SorteiosEventos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.checar_finalizacoes.start()

    def cog_unload(self):
        self.checar_finalizacoes.cancel()

    async def cog_load(self):
        self.bot.add_view(ParticiparView())

    async def criar_sorteio(self, interaction: discord.Interaction, tipo: str, titulo: str,
                             valor: float, vencedores_qtd: int, duracao_min: int, patrocinador_id):
        guild = interaction.guild
        config = carregar_config()
        cfg = get_guild_config(config, guild.id)[tipo]
        nome, cor = NOME_TIPO[tipo]

        if not cfg.get("canal_inicio"):
            await interaction.followup.send(
                f"❌ Canal de início não configurado. Use `/{tipo}-config` primeiro.", ephemeral=True
            )
            return

        canal = guild.get_channel(cfg["canal_inicio"])
        if not canal:
            await interaction.followup.send(
                f"❌ O canal de início configurado não existe mais. Use `/{tipo}-config` para escolher outro.", ephemeral=True
            )
            return

        criador = interaction.user
        rotulo_transacao = "Sorteio criado" if tipo == "sorteio" else "Evento criado"
        if not debitar_saldo(guild.id, criador.id, valor, detalhe=titulo, tipo=rotulo_transacao):
            saldo = obter_saldo(guild.id, criador.id)
            await interaction.followup.send(
                f"❌ Saldo insuficiente. Você tem **{formatar_reais(saldo)}**, mas o prêmio é de **{formatar_reais(valor)}**.",
                ephemeral=True,
            )
            return

        termina_em = datetime.now(timezone.utc) + timedelta(minutes=duracao_min)

        embed = discord.Embed(title=f"{nome} — {titulo}", color=cor)
        embed.add_field(name="💰 Prêmio", value=formatar_reais(valor), inline=True)
        embed.add_field(name="🏆 Vencedores", value=str(vencedores_qtd), inline=True)
        if patrocinador_id:
            embed.add_field(name="🏷️ Patrocinado por", value=f"<@{patrocinador_id}>", inline=True)
        if cfg.get("cargos_elegiveis"):
            cargos_txt = ", ".join(f"<@&{rid}>" for rid in cfg["cargos_elegiveis"])
            embed.add_field(name="👥 Quem pode participar", value=cargos_txt, inline=False)
        embed.add_field(name="⏰ Termina em", value=f"<t:{int(termina_em.timestamp())}:R>", inline=False)
        embed.add_field(name="👤 Participantes", value="0", inline=False)
        embed.set_footer(text=f"Criado por {criador} • {TAG_NIX}")

        role_ping = guild.get_role(cfg["cargo_ping"]) if cfg.get("cargo_ping") else None
        conteudo = role_ping.mention if role_ping else None
        allowed_mentions = discord.AllowedMentions(roles=[role_ping] if role_ping else [])

        try:
            msg = await canal.send(content=conteudo, embed=embed, view=ParticiparView(), allowed_mentions=allowed_mentions)
        except discord.Forbidden:
            creditar_saldo(guild.id, criador.id, valor, tipo="Estorno", detalhe=f"Falha ao publicar {titulo}")
            await interaction.followup.send("❌ Não tenho permissão para enviar mensagens nesse canal. Valor estornado.", ephemeral=True)
            return

        ativos = carregar_ativos()
        ativos[str(msg.id)] = {
            "guild_id": guild.id,
            "canal_id": canal.id,
            "tipo": tipo,
            "titulo": titulo,
            "valor": valor,
            "vencedores_qtd": vencedores_qtd,
            "patrocinador_id": patrocinador_id,
            "criador_id": criador.id,
            "cargos_elegiveis": cfg.get("cargos_elegiveis", []),
            "participantes": [],
            "termina_em": termina_em.isoformat(),
            "finalizado": False,
        }
        salvar_ativos(ativos)

        await interaction.followup.send(f"✅ {nome} criado com sucesso em {canal.mention}!", ephemeral=True)

    @tasks.loop(seconds=60)
    async def checar_finalizacoes(self):
        ativos = carregar_ativos()
        agora = datetime.now(timezone.utc)
        for msg_id, record in list(ativos.items()):
            if record.get("finalizado"):
                continue
            try:
                termina_em = datetime.fromisoformat(record["termina_em"])
            except (KeyError, ValueError):
                continue
            if agora >= termina_em:
                try:
                    await self.finalizar(msg_id, record)
                except Exception:
                    logger.exception(f"Falha ao finalizar sorteio/evento {msg_id}")

    @checar_finalizacoes.before_loop
    async def before_checar_finalizacoes(self):
        await self.bot.wait_until_ready()

    async def finalizar(self, msg_id: str, record: dict):
        ativos = carregar_ativos()
        record = ativos.get(msg_id, record)
        if record.get("finalizado"):
            return

        guild = self.bot.get_guild(record["guild_id"])
        tipo = record["tipo"]
        nome, cor = NOME_TIPO.get(tipo, ("🎉 Sorteio", 0xF1C40F))
        participantes = record.get("participantes", [])
        vencedores_qtd = min(record.get("vencedores_qtd", 1), len(participantes)) if participantes else 0
        vencedores_ids = random.sample(participantes, vencedores_qtd) if vencedores_qtd else []
        valor_total = record["valor"]
        valor_por_vencedor = round(valor_total / vencedores_qtd, 2) if vencedores_qtd else 0

        if guild:
            for uid in vencedores_ids:
                creditar_saldo(record["guild_id"], uid, valor_por_vencedor, tipo=f"Prêmio de {tipo}", detalhe=record["titulo"])

        embed = discord.Embed(title=f"🏆 RESULTADO — {record['titulo']}", color=cor)
        if record.get("patrocinador_id"):
            embed.add_field(name="🏷️ Patrocinado por", value=f"<@{record['patrocinador_id']}>", inline=False)
        if vencedores_ids:
            vencedores_txt = "\n".join(f"🎉 <@{uid}> — {formatar_reais(valor_por_vencedor)}" for uid in vencedores_ids)
            embed.add_field(name="🏆 Vencedor(es)", value=vencedores_txt, inline=False)
        else:
            embed.add_field(name="😢 Resultado", value="Ninguém participou desse sorteio/evento.", inline=False)
        embed.add_field(name="👥 Total de participantes", value=str(len(participantes)), inline=True)
        embed.set_footer(text=TAG_NIX)

        canal_origem = guild.get_channel(record["canal_id"]) if guild else None
        canal_resultado = None
        if guild:
            config = carregar_config()
            cfg = get_guild_config(config, guild.id)[tipo]
            if cfg.get("canal_resultado"):
                canal_resultado = guild.get_channel(cfg["canal_resultado"])

        destino = canal_resultado or canal_origem
        if destino:
            try:
                await destino.send(embed=embed)
            except discord.HTTPException:
                pass

        if canal_origem:
            try:
                msg = await canal_origem.fetch_message(int(msg_id))
                view_encerrada = discord.ui.View()
                view_encerrada.add_item(discord.ui.Button(label="🔒 Encerrado", style=discord.ButtonStyle.secondary, disabled=True))
                embed_original = msg.embeds[0] if msg.embeds else None
                if embed_original:
                    embed_original.title = f"🔒 [ENCERRADO] {embed_original.title}"
                await msg.edit(embed=embed_original, view=view_encerrada)
            except discord.HTTPException:
                pass

        record["finalizado"] = True
        record["vencedores_ids"] = vencedores_ids
        ativos[msg_id] = record
        salvar_ativos(ativos)

    # ------------------------------------------------------------------
    # Comandos soltos
    # ------------------------------------------------------------------

    @app_commands.command(name="sorteio-config", description="Configurar canais, ping e elegibilidade dos sorteios")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def sorteio_config_cmd(self, interaction: discord.Interaction):
        view = SorteioEventoConfigView(interaction.user.id, "sorteio")
        await interaction.response.send_message(embed=view.embed(interaction.guild), view=view, ephemeral=True)

    @app_commands.command(name="evento-config", description="Configurar canais, ping e elegibilidade dos eventos")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def evento_config_cmd(self, interaction: discord.Interaction):
        view = SorteioEventoConfigView(interaction.user.id, "evento")
        await interaction.response.send_message(embed=view.embed(interaction.guild), view=view, ephemeral=True)

    @app_commands.command(name="sorteio-criar", description="Criar e iniciar um sorteio pago com dinheiro fictício")
    @app_commands.guild_only()
    async def sorteio_criar_cmd(self, interaction: discord.Interaction):
        if not usuario_pode_gerenciar(interaction):
            await interaction.response.send_message("❌ Você não tem permissão para criar sorteios.", ephemeral=True)
            return
        await interaction.response.send_modal(CriarSorteioModal("sorteio"))

    @app_commands.command(name="evento-criar", description="Criar e iniciar um evento pago com dinheiro fictício")
    @app_commands.guild_only()
    async def evento_criar_cmd(self, interaction: discord.Interaction):
        if not usuario_pode_gerenciar(interaction):
            await interaction.response.send_message("❌ Você não tem permissão para criar eventos.", ephemeral=True)
            return
        await interaction.response.send_modal(CriarSorteioModal("evento"))

    async def _erro_permissao(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você precisa ser administrador para usar esse comando."
        elif isinstance(error, app_commands.NoPrivateMessage):
            msg = "❌ Esse comando só pode ser usado dentro de um servidor."
        else:
            msg = "❌ Ocorreu um erro inesperado ao executar o comando."
            logger.exception("Erro em comando de sorteios/eventos", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    @sorteio_config_cmd.error
    async def sorteio_config_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await self._erro_permissao(interaction, error)

    @evento_config_cmd.error
    async def evento_config_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await self._erro_permissao(interaction, error)

    @sorteio_criar_cmd.error
    async def sorteio_criar_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await self._erro_permissao(interaction, error)

    @evento_criar_cmd.error
    async def evento_criar_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await self._erro_permissao(interaction, error)


async def setup(bot: commands.Bot):
    await bot.add_cog(SorteiosEventos(bot))
