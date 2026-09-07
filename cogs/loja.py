import asyncio
import json
import logging
import os
import uuid
from datetime import date, datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from cogs._utils_select import ChannelSelectComAutocomplete, RoleSelectComAutocomplete
from cogs.carteira import creditar_saldo, debitar_saldo, formatar_reais, obter_saldo

logger = logging.getLogger("bot.loja")

CONFIG_FILE = "config/loja_config.json"
TAG_NIX = "Desenvolvido por Nix"

VARIAVEIS = {
    "👤 Usuário": [
        "{usuario}", "{usuario_id}", "{usuario_mencao}", "{usuario_tag}",
        "{usuario_avatar}", "{usuario_criado_em}", "{usuario_entrou_em}", "{usuario_cargo_principal}",
    ],
    "🏠 Servidor": [
        "{servidor}", "{servidor_id}", "{servidor_membros}", "{servidor_dono}",
        "{servidor_icone}", "{servidor_boosts}", "{servidor_criado_em}", "{servidor_canais_total}",
    ],
    "📦 Produto": [
        "{produto}", "{produto_id}", "{produto_descricao}", "{produto_tipo}",
        "{produto_preco}", "{produto_preco_original}", "{produto_desconto_max}", "{produto_cargo}",
    ],
    "💰 Preço/Desconto": ["{preco_final}", "{desconto_valor}", "{desconto_percentual_aplicado}"],
    "🎟️ Cupom": ["{cupom_codigo}", "{cupom_percentual}", "{cupom_validade}", "{cupom_status}"],
    "🧾 Compra": [
        "{compra_id}", "{compra_data}", "{compra_hora}", "{compra_data_hora}",
        "{compra_canal}", "{compra_avaliacao}", "{compra_metodo}",
    ],
    "🛒 Loja": ["{loja_titulo}", "{loja_descricao}", "{loja_tipo}", "{loja_canal_logs}"],
    "🪙 Carteira": ["{saldo_atual}", "{saldo_antes}", "{saldo_depois}"],
    "👮 Staff": ["{staff_cargos}", "{staff_responsavel}"],
    "🕐 Sistema": ["{data}", "{hora}", "{data_hora}", "{ano}", "{mes}", "{dia}", "{tag_sistema}"],
}


# ----------------------------------------------------------------------------
# Persistência
# ----------------------------------------------------------------------------

def carregar() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler loja_config.json, recriando: {e}")
    return {}


def salvar(dados: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def cupom_padrao() -> dict:
    return {"codigo": None, "percentual": 0.0, "validade": None, "ativo": False}


def loja_padrao() -> dict:
    return {
        "canal_painel": None,
        "mensagem_painel": None,
        "titulo": "🛒 Loja",
        "descricao": "Bem-vindo à nossa loja!",
        "cupom": cupom_padrao(),
        "produtos": [],
        "canal_logs": None,
        "cargos_staff": [],
    }


def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {"real": loja_padrao(), "ficticio": loja_padrao()}
    config[gid].setdefault("real", loja_padrao())
    config[gid].setdefault("ficticio", loja_padrao())
    return config[gid]


def cupom_valido(cupom: dict) -> bool:
    if not cupom or not cupom.get("ativo") or not cupom.get("codigo"):
        return False
    validade = cupom.get("validade")
    if validade:
        try:
            data_val = datetime.fromisoformat(validade).date()
            if date.today() > data_val:
                return False
        except ValueError:
            pass
    return True


def substituir_variaveis(texto: str, **ctx) -> str:
    """Substitui variáveis {chave} em textos customizáveis da loja."""
    if not texto:
        return texto
    agora = datetime.now()
    mapa = {"{tag_sistema}": TAG_NIX, "{data}": agora.strftime("%d/%m/%Y"), "{hora}": agora.strftime("%H:%M"),
            "{data_hora}": agora.strftime("%d/%m/%Y %H:%M"), "{ano}": str(agora.year),
            "{mes}": str(agora.month), "{dia}": str(agora.day)}

    membro = ctx.get("membro")
    if membro:
        mapa.update({
            "{usuario}": membro.display_name,
            "{usuario_id}": str(membro.id),
            "{usuario_mencao}": membro.mention,
            "{usuario_tag}": str(membro),
            "{usuario_avatar}": str(membro.display_avatar.url),
            "{usuario_criado_em}": membro.created_at.strftime("%d/%m/%Y"),
            "{usuario_entrou_em}": membro.joined_at.strftime("%d/%m/%Y") if getattr(membro, "joined_at", None) else "—",
            "{usuario_cargo_principal}": membro.top_role.mention if getattr(membro, "top_role", None) else "—",
        })

    guild = ctx.get("guild")
    if guild:
        mapa.update({
            "{servidor}": guild.name,
            "{servidor_id}": str(guild.id),
            "{servidor_membros}": str(guild.member_count),
            "{servidor_dono}": str(guild.owner) if guild.owner else "—",
            "{servidor_icone}": str(guild.icon.url) if guild.icon else "",
            "{servidor_boosts}": str(guild.premium_subscription_count or 0),
            "{servidor_criado_em}": guild.created_at.strftime("%d/%m/%Y"),
            "{servidor_canais_total}": str(len(guild.channels)),
        })

    produto = ctx.get("produto")
    if produto:
        mapa.update({
            "{produto}": produto.get("nome", ""),
            "{produto_id}": produto.get("id", ""),
            "{produto_descricao}": produto.get("descricao", ""),
            "{produto_tipo}": "Cargo" if produto.get("tipo") == "cargo" else "Plano",
            "{produto_preco}": formatar_reais(produto.get("valor", 0)),
            "{produto_preco_original}": formatar_reais(produto.get("valor", 0)),
            "{produto_desconto_max}": f"{produto.get('desconto_max', 0):.0f}%",
            "{produto_cargo}": f"<@&{produto['cargo_id']}>" if produto.get("cargo_id") else "—",
        })

    if ctx.get("preco_final") is not None:
        mapa["{preco_final}"] = formatar_reais(ctx["preco_final"])
    if ctx.get("desconto_valor") is not None:
        mapa["{desconto_valor}"] = formatar_reais(ctx["desconto_valor"])
    if ctx.get("desconto_percentual") is not None:
        mapa["{desconto_percentual_aplicado}"] = f"{ctx['desconto_percentual']:.0f}%"

    cupom = ctx.get("cupom")
    if cupom:
        mapa.update({
            "{cupom_codigo}": cupom.get("codigo") or "—",
            "{cupom_percentual}": f"{cupom.get('percentual', 0):.0f}%",
            "{cupom_validade}": cupom.get("validade") or "Sem validade",
            "{cupom_status}": "Ativo" if cupom_valido(cupom) else "Inativo",
        })

    if ctx.get("compra_id"):
        mapa["{compra_id}"] = ctx["compra_id"]
    if ctx.get("canal"):
        mapa["{compra_canal}"] = ctx["canal"].mention
    if ctx.get("avaliacao"):
        mapa["{compra_avaliacao}"] = ctx["avaliacao"]
    mapa["{compra_data}"] = agora.strftime("%d/%m/%Y")
    mapa["{compra_hora}"] = agora.strftime("%H:%M")
    mapa["{compra_data_hora}"] = agora.strftime("%d/%m/%Y %H:%M")
    mapa["{compra_metodo}"] = "💳 Pix" if ctx.get("tipo") == "real" else "🪙 Moeda fictícia"

    loja = ctx.get("loja")
    if loja:
        mapa.update({
            "{loja_titulo}": loja.get("titulo", ""),
            "{loja_descricao}": loja.get("descricao", ""),
            "{loja_tipo}": "💳 Real (Pix)" if ctx.get("tipo") == "real" else "🪙 Fictícia",
            "{loja_canal_logs}": f"<#{loja['canal_logs']}>" if loja.get("canal_logs") else "—",
        })

    if ctx.get("saldo_atual") is not None:
        mapa["{saldo_atual}"] = formatar_reais(ctx["saldo_atual"])
    if ctx.get("saldo_antes") is not None:
        mapa["{saldo_antes}"] = formatar_reais(ctx["saldo_antes"])
    if ctx.get("saldo_depois") is not None:
        mapa["{saldo_depois}"] = formatar_reais(ctx["saldo_depois"])

    if ctx.get("cargos_staff_texto"):
        mapa["{staff_cargos}"] = ctx["cargos_staff_texto"]
    if ctx.get("staff_responsavel"):
        mapa["{staff_responsavel}"] = ctx["staff_responsavel"]

    for chave, valor in mapa.items():
        texto = texto.replace(chave, str(valor))
    return texto


def variaveis_embed() -> discord.Embed:
    e = discord.Embed(
        title="📋 Variáveis Disponíveis",
        description="Use essas variáveis no título, descrição e mensagens da loja — elas são substituídas automaticamente.",
        color=0x3498DB,
    )
    for categoria, chaves in VARIAVEIS.items():
        e.add_field(name=categoria, value=" ".join(f"`{c}`" for c in chaves), inline=False)
    e.set_footer(text=TAG_NIX)
    return e


def montar_embed_publico(loja: dict, tipo: str, guild: discord.Guild) -> discord.Embed:
    titulo = substituir_variaveis(loja.get("titulo") or "🛒 Loja", guild=guild, loja=loja, tipo=tipo)
    descricao = substituir_variaveis(loja.get("descricao") or "", guild=guild, loja=loja, tipo=tipo)
    e = discord.Embed(title=titulo, description=descricao, color=0x00B4D8 if tipo == "real" else 0xF1C40F)
    for p in loja["produtos"]:
        tipo_label = "🏷️ Cargo" if p["tipo"] == "cargo" else "📋 Plano"
        e.add_field(
            name=f"{p['nome']} — {formatar_reais(p['valor'])}",
            value=f"{tipo_label}\n{p.get('descricao') or 'Sem descrição'}",
            inline=False,
        )
    if cupom_valido(loja["cupom"]):
        e.add_field(
            name="🎟️ Cupom disponível",
            value=f"Use o código `{loja['cupom']['codigo']}` e ganhe {loja['cupom']['percentual']:.0f}% de desconto!",
            inline=False,
        )
    metodo = "💳 Pagamento via Pix (confirmado pela equipe)" if tipo == "real" else "🪙 Pago com a moeda fictícia do servidor"
    e.set_footer(text=f"{metodo} • {TAG_NIX}")
    return e


# ----------------------------------------------------------------------------
# Modais
# ----------------------------------------------------------------------------

class TituloDescricaoModal(discord.ui.Modal, title="Título e Descrição da Loja"):
    titulo = discord.ui.TextInput(label="Título da loja", max_length=100)
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, max_length=500, required=False)

    def __init__(self, tipo_loja: str, loja_atual: dict):
        super().__init__()
        self.tipo_loja = tipo_loja
        self.titulo.default = loja_atual.get("titulo", "")
        self.descricao.default = loja_atual.get("descricao", "")

    async def on_submit(self, interaction: discord.Interaction):
        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo_loja]
        loja["titulo"] = self.titulo.value.strip()
        loja["descricao"] = (self.descricao.value or "").strip()
        salvar(config)
        await interaction.response.send_message("✅ Título e descrição atualizados.", ephemeral=True)


class CupomModal(discord.ui.Modal, title="Configurar Cupom de Desconto"):
    codigo = discord.ui.TextInput(label="Código do cupom", max_length=30)
    percentual = discord.ui.TextInput(label="Percentual de desconto (ex: 10)", max_length=5)
    validade = discord.ui.TextInput(label="Validade (DD/MM/AAAA, opcional)", required=False, max_length=10)

    def __init__(self, tipo_loja: str):
        super().__init__()
        self.tipo_loja = tipo_loja

    async def on_submit(self, interaction: discord.Interaction):
        try:
            perc = float(self.percentual.value.replace(",", "."))
        except ValueError:
            await interaction.response.send_message("❌ Percentual inválido.", ephemeral=True)
            return

        validade_iso = None
        if self.validade.value:
            try:
                dt = datetime.strptime(self.validade.value.strip(), "%d/%m/%Y")
                validade_iso = dt.date().isoformat()
            except ValueError:
                await interaction.response.send_message("❌ Data inválida. Use o formato DD/MM/AAAA.", ephemeral=True)
                return

        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo_loja]
        loja["cupom"] = {
            "codigo": self.codigo.value.strip().upper(),
            "percentual": max(0.0, min(100.0, perc)),
            "validade": validade_iso,
            "ativo": True,
        }
        salvar(config)
        await interaction.response.send_message(
            f"✅ Cupom `{loja['cupom']['codigo']}` configurado ({loja['cupom']['percentual']:.0f}% de desconto"
            f"{f', válido até {self.validade.value}' if validade_iso else ''}).",
            ephemeral=True,
        )


class ProdutoModal(discord.ui.Modal, title="Novo Produto"):
    nome = discord.ui.TextInput(label="Nome do produto", max_length=80)
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, max_length=300, required=False)
    valor = discord.ui.TextInput(label="Valor (ex: 19.90)", max_length=15)
    desconto_max = discord.ui.TextInput(label="Desconto máximo em % (0 se nenhum)", max_length=5, default="0")
    tipo_produto = discord.ui.TextInput(label='Tipo: "cargo" ou "plano"', max_length=10, default="plano")

    def __init__(self, tipo_loja: str):
        super().__init__()
        self.tipo_loja = tipo_loja

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor_f = float(self.valor.value.replace(",", "."))
            desconto_f = float(self.desconto_max.value.replace(",", ".")) if self.desconto_max.value else 0.0
        except ValueError:
            await interaction.response.send_message("❌ Valor ou desconto inválido. Use números (ex: 19.90).", ephemeral=True)
            return

        tipo_p = self.tipo_produto.value.strip().lower()
        if tipo_p not in ("cargo", "plano"):
            await interaction.response.send_message('❌ O tipo precisa ser "cargo" ou "plano".', ephemeral=True)
            return
        if valor_f <= 0:
            await interaction.response.send_message("❌ O valor precisa ser maior que zero.", ephemeral=True)
            return

        produto = {
            "id": uuid.uuid4().hex[:8],
            "tipo": tipo_p,
            "nome": self.nome.value.strip(),
            "descricao": (self.descricao.value or "").strip(),
            "valor": valor_f,
            "desconto_max": max(0.0, min(100.0, desconto_f)),
            "cargo_id": None,
        }

        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo_loja]
        loja["produtos"].append(produto)
        salvar(config)

        if tipo_p == "cargo":
            async def vincular_cargo(inter: discord.Interaction, role_id: int):
                cfg = carregar()
                lj = get_guild_config(cfg, inter.guild_id)[self.tipo_loja]
                for p in lj["produtos"]:
                    if p["id"] == produto["id"]:
                        p["cargo_id"] = role_id
                salvar(cfg)
                role = inter.guild.get_role(role_id)
                await inter.response.send_message(
                    f"✅ Produto vinculado ao cargo {role.mention if role else role_id}.", ephemeral=True
                )

            view = discord.ui.View(timeout=180)
            view.add_item(RoleSelectComAutocomplete(callback=vincular_cargo))
            await interaction.response.send_message(
                f"✅ Produto **{produto['nome']}** criado! Agora selecione qual cargo será entregue ao comprador:",
                view=view,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(f"✅ Produto **{produto['nome']}** criado com sucesso!", ephemeral=True)


class CupomCompraModal(discord.ui.Modal, title="Aplicar Cupom (opcional)"):
    codigo = discord.ui.TextInput(label="Código do cupom (deixe vazio se não tiver)", required=False, max_length=30)

    def __init__(self, cog: "Loja", tipo: str, produto: dict):
        super().__init__()
        self.cog = cog
        self.tipo = tipo
        self.produto = produto

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.processar_compra(interaction, self.tipo, self.produto, self.codigo.value.strip() or None)


# ----------------------------------------------------------------------------
# Views de gerenciamento de produtos
# ----------------------------------------------------------------------------

class RemoverProdutoSelect(discord.ui.Select):
    def __init__(self, tipo_loja: str, produtos: list):
        options = [
            discord.SelectOption(label=p["nome"][:100], description=f"{formatar_reais(p['valor'])} • ID {p['id']}", value=p["id"])
            for p in produtos[:25]
        ]
        super().__init__(placeholder="Selecione o produto para remover", options=options)
        self.tipo_loja = tipo_loja

    async def callback(self, interaction: discord.Interaction):
        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo_loja]
        loja["produtos"] = [p for p in loja["produtos"] if p["id"] != self.values[0]]
        salvar(config)
        await interaction.response.edit_message(content="✅ Produto removido.", view=None)


class RemoverProdutoView(discord.ui.View):
    def __init__(self, tipo_loja: str, produtos: list):
        super().__init__(timeout=180)
        self.add_item(RemoverProdutoSelect(tipo_loja, produtos))


class ProdutosView(discord.ui.View):
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
        config = carregar()
        loja = get_guild_config(config, guild.id)[self.tipo]
        produtos = loja["produtos"]
        e = discord.Embed(
            title=f"📦 Produtos — {'Loja Real (Pix)' if self.tipo == 'real' else 'Loja Fictícia'}",
            color=0x9B59B6,
        )
        if not produtos:
            e.description = "Nenhum produto cadastrado ainda. Clique em ➕ Adicionar Produto."
        else:
            for p in produtos:
                tipo_label = "🏷️ Cargo" if p["tipo"] == "cargo" else "📋 Plano"
                e.add_field(
                    name=f"{p['nome']} ({tipo_label})",
                    value=(
                        f"💰 {formatar_reais(p['valor'])} • desconto máx: {p.get('desconto_max', 0):.0f}%\n"
                        f"{(p.get('descricao') or 'Sem descrição')[:150]}\nID: `{p['id']}`"
                    ),
                    inline=False,
                )
        e.set_footer(text=TAG_NIX)
        return e

    @discord.ui.button(label="➕ Adicionar Produto", style=discord.ButtonStyle.success, row=0)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ProdutoModal(self.tipo))

    @discord.ui.button(label="🗑️ Remover Produto", style=discord.ButtonStyle.danger, row=0)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo]
        if not loja["produtos"]:
            await interaction.response.send_message("❌ Não há produtos para remover.", ephemeral=True)
            return
        view = RemoverProdutoView(self.tipo, loja["produtos"])
        await interaction.response.send_message("Selecione o produto que deseja remover:", view=view, ephemeral=True)

    @discord.ui.button(label="🔙 Voltar", style=discord.ButtonStyle.secondary, row=1)
    async def voltar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LojaConfigView(self.dono_id, self.tipo)
        await interaction.response.edit_message(embed=view.embed(interaction.guild), view=view)


class CupomGerenciarView(discord.ui.View):
    def __init__(self, dono_id: int, tipo_loja: str):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.tipo_loja = tipo_loja

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✏️ Criar/Editar Cupom", style=discord.ButtonStyle.primary, row=0)
    async def criar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CupomModal(self.tipo_loja))

    @discord.ui.button(label="⏸️ Desativar Cupom", style=discord.ButtonStyle.secondary, row=0)
    async def desativar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo_loja]
        loja["cupom"]["ativo"] = False
        salvar(config)
        await interaction.response.send_message("⏸️ Cupom desativado.", ephemeral=True)

    @discord.ui.button(label="🗑️ Excluir Cupom", style=discord.ButtonStyle.danger, row=0)
    async def excluir_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo_loja]
        loja["cupom"] = cupom_padrao()
        salvar(config)
        await interaction.response.send_message("🗑️ Cupom excluído.", ephemeral=True)


# ----------------------------------------------------------------------------
# Painel principal de configuração
# ----------------------------------------------------------------------------

class LojaConfigView(discord.ui.View):
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
        config = carregar()
        loja = get_guild_config(config, guild.id)[self.tipo]
        nome_tipo = "💳 Loja Real (Pix)" if self.tipo == "real" else "🪙 Loja Fictícia"
        e = discord.Embed(title=f"🛒 Configurar {nome_tipo}", color=0x00B4D8 if self.tipo == "real" else 0xF1C40F)

        canal_painel = guild.get_channel(loja["canal_painel"]) if loja.get("canal_painel") else None
        canal_logs = guild.get_channel(loja["canal_logs"]) if loja.get("canal_logs") else None
        cargos = [guild.get_role(rid) for rid in loja.get("cargos_staff", [])]
        cargos = [c.mention for c in cargos if c]
        cupom = loja["cupom"]

        e.add_field(name="📺 Canal do painel", value=canal_painel.mention if canal_painel else "Não configurado", inline=True)
        e.add_field(name="🧾 Canal de logs", value=canal_logs.mention if canal_logs else "Não configurado", inline=True)
        e.add_field(name="📦 Produtos cadastrados", value=str(len(loja["produtos"])), inline=True)
        e.add_field(name="👮 Cargos de atendimento", value=", ".join(cargos) if cargos else "Nenhum", inline=False)
        e.add_field(name="✏️ Título", value=loja.get("titulo") or "—", inline=True)
        e.add_field(name="📄 Descrição", value=(loja.get("descricao") or "—")[:200], inline=False)

        if cupom.get("codigo"):
            status = "🟢 Ativo" if cupom_valido(cupom) else "🔴 Inativo/Expirado"
            e.add_field(
                name="🎟️ Cupom",
                value=f"`{cupom['codigo']}` — {cupom['percentual']:.0f}% — validade: {cupom.get('validade') or 'sem validade'} — {status}",
                inline=False,
            )
        else:
            e.add_field(name="🎟️ Cupom", value="Nenhum cupom configurado", inline=False)

        e.set_footer(text=TAG_NIX)
        return e

    @discord.ui.button(label="📺 Canal do Painel", style=discord.ButtonStyle.primary, row=0)
    async def canal_painel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def salvar_canal(inter: discord.Interaction, channel_id: int):
            cfg = carregar()
            lj = get_guild_config(cfg, inter.guild_id)[self.tipo]
            lj["canal_painel"] = channel_id
            salvar(cfg)
            canal = inter.guild.get_channel(channel_id)
            await inter.response.send_message(f"✅ Canal do painel definido: {canal.mention if canal else channel_id}", ephemeral=True)

        view = discord.ui.View(timeout=180)
        view.add_item(ChannelSelectComAutocomplete(callback=salvar_canal))
        await interaction.response.send_message("Selecione o canal onde o painel da loja será publicado:", view=view, ephemeral=True)

    @discord.ui.button(label="✏️ Título/Descrição", style=discord.ButtonStyle.primary, row=0)
    async def titulo_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo]
        await interaction.response.send_modal(TituloDescricaoModal(self.tipo, loja))

    @discord.ui.button(label="🎟️ Cupom", style=discord.ButtonStyle.primary, row=0)
    async def cupom_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CupomGerenciarView(self.dono_id, self.tipo)
        await interaction.response.send_message("Gerencie o cupom de desconto da loja:", view=view, ephemeral=True)

    @discord.ui.button(label="📦 Produtos", style=discord.ButtonStyle.primary, row=1)
    async def produtos_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ProdutosView(self.dono_id, self.tipo)
        await interaction.response.edit_message(embed=view.embed(interaction.guild), view=view)

    @discord.ui.button(label="🧾 Canal de Logs", style=discord.ButtonStyle.primary, row=1)
    async def canal_logs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def salvar_canal(inter: discord.Interaction, channel_id: int):
            cfg = carregar()
            lj = get_guild_config(cfg, inter.guild_id)[self.tipo]
            lj["canal_logs"] = channel_id
            salvar(cfg)
            canal = inter.guild.get_channel(channel_id)
            await inter.response.send_message(f"✅ Canal de logs definido: {canal.mention if canal else channel_id}", ephemeral=True)

        view = discord.ui.View(timeout=180)
        view.add_item(ChannelSelectComAutocomplete(callback=salvar_canal))
        await interaction.response.send_message("Selecione o canal onde os logs de compras serão enviados:", view=view, ephemeral=True)

    @discord.ui.button(label="👮 Cargos de Atendimento", style=discord.ButtonStyle.primary, row=1)
    async def cargos_staff_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def adicionar_cargo(inter: discord.Interaction, role_id: int):
            cfg = carregar()
            lj = get_guild_config(cfg, inter.guild_id)[self.tipo]
            if role_id not in lj["cargos_staff"]:
                lj["cargos_staff"].append(role_id)
            salvar(cfg)
            role = inter.guild.get_role(role_id)
            await inter.response.send_message(
                f"✅ Cargo {role.mention if role else role_id} agora tem acesso aos canais e compras da loja.", ephemeral=True
            )

        view = discord.ui.View(timeout=180)
        view.add_item(RoleSelectComAutocomplete(callback=adicionar_cargo, min_values=1, max_values=5))
        await interaction.response.send_message(
            "Selecione os cargos que terão acesso aos canais privados de compra e ao histórico de compras:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="📋 Variáveis Disponíveis", style=discord.ButtonStyle.secondary, row=2)
    async def variaveis_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=variaveis_embed(), ephemeral=True)

    @discord.ui.button(label="✅ Publicar Painel da Loja", style=discord.ButtonStyle.success, row=2)
    async def publicar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo]

        if not loja.get("canal_painel"):
            await interaction.response.send_message("❌ Configure primeiro o canal do painel.", ephemeral=True)
            return
        if not loja["produtos"]:
            await interaction.response.send_message("❌ Cadastre pelo menos um produto antes de publicar.", ephemeral=True)
            return

        canal = interaction.guild.get_channel(loja["canal_painel"])
        if not canal:
            await interaction.response.send_message("❌ O canal configurado não foi encontrado.", ephemeral=True)
            return

        embed = montar_embed_publico(loja, self.tipo, interaction.guild)
        view = LojaPainelPublicoView(self.tipo, loja["produtos"])
        mensagem = await canal.send(embed=embed, view=view)

        loja["mensagem_painel"] = mensagem.id
        salvar(config)

        interaction.client.add_view(view, message_id=mensagem.id)
        await interaction.response.send_message(f"✅ Painel publicado em {canal.mention}!", ephemeral=True)

    @discord.ui.button(label="🔙 Voltar", style=discord.ButtonStyle.secondary, row=3)
    async def voltar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LojaEscolhaView(self.dono_id)
        await interaction.response.edit_message(embed=view.embed(), view=view)


class LojaEscolhaView(discord.ui.View):
    def __init__(self, dono_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True)
            return False
        return True

    def embed(self) -> discord.Embed:
        e = discord.Embed(
            title="🛒 LOJA DO SERVIDOR",
            description=(
                "Escolha qual loja você quer configurar:\n\n"
                "💳 **Loja Real** — vende com Pix de verdade (confirmação manual da equipe)\n"
                "🪙 **Loja Fictícia** — vende com a moeda fictícia do servidor (débito automático)"
            ),
            color=0x9B59B6,
        )
        e.set_footer(text=TAG_NIX)
        return e

    @discord.ui.button(label="💳 Loja Real (Pix)", style=discord.ButtonStyle.success, row=0)
    async def real_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LojaConfigView(self.dono_id, "real")
        await interaction.response.edit_message(embed=view.embed(interaction.guild), view=view)

    @discord.ui.button(label="🪙 Loja Fictícia", style=discord.ButtonStyle.primary, row=0)
    async def ficticio_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LojaConfigView(self.dono_id, "ficticio")
        await interaction.response.edit_message(embed=view.embed(interaction.guild), view=view)


def abrir_painel_loja(dono_id: int):
    view = LojaEscolhaView(dono_id)
    return view.embed(), view


# ----------------------------------------------------------------------------
# Painel público / fluxo de compra
# ----------------------------------------------------------------------------

class ComprarButton(discord.ui.Button):
    def __init__(self, tipo: str, produto: dict):
        super().__init__(
            label=f"{produto['nome'][:60]} • {formatar_reais(produto['valor'])}",
            style=discord.ButtonStyle.success,
            emoji="🛒",
            custom_id=f"loja_comprar:{tipo}:{produto['id']}",
        )
        self.tipo = tipo
        self.produto_id = produto["id"]

    async def callback(self, interaction: discord.Interaction):
        config = carregar()
        loja = get_guild_config(config, interaction.guild_id)[self.tipo]
        produto = next((p for p in loja["produtos"] if p["id"] == self.produto_id), None)
        if not produto:
            await interaction.response.send_message("❌ Esse produto não está mais disponível.", ephemeral=True)
            return

        cog = interaction.client.get_cog("Loja")
        if not cog:
            await interaction.response.send_message("❌ Sistema de loja indisponível no momento.", ephemeral=True)
            return

        if cupom_valido(loja["cupom"]):
            await interaction.response.send_modal(CupomCompraModal(cog, self.tipo, produto))
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await cog.processar_compra(interaction, self.tipo, produto, None)


class LojaPainelPublicoView(discord.ui.View):
    def __init__(self, tipo: str, produtos: list):
        super().__init__(timeout=None)
        for p in produtos[:25]:
            self.add_item(ComprarButton(tipo, p))


class ConfirmarPagamentoView(discord.ui.View):
    def __init__(self, cog: "Loja", guild, canal, tipo, produto, comprador,
                 preco_final, desconto_valor, desconto_percentual, cupom_codigo, staff_role_ids):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild = guild
        self.canal = canal
        self.tipo = tipo
        self.produto = produto
        self.comprador = comprador
        self.preco_final = preco_final
        self.desconto_valor = desconto_valor
        self.desconto_percentual = desconto_percentual
        self.cupom_codigo = cupom_codigo
        self.staff_role_ids = staff_role_ids

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        role_ids = {r.id for r in interaction.user.roles}
        if role_ids & self.staff_role_ids:
            return True
        await interaction.response.send_message("❌ Apenas a equipe de atendimento pode confirmar o pagamento.", ephemeral=True)
        return False

    @discord.ui.button(label="✅ Confirmar Pagamento Pix", style=discord.ButtonStyle.success)
    async def confirmar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        button.label = "✅ Pagamento Confirmado"
        await interaction.response.edit_message(view=self)

        if self.produto["tipo"] == "cargo" and self.produto.get("cargo_id"):
            role = self.guild.get_role(self.produto["cargo_id"])
            if role:
                try:
                    await self.comprador.add_roles(role, reason="Compra confirmada na loja")
                except discord.Forbidden:
                    pass

        await interaction.followup.send(f"✅ Pagamento confirmado por {interaction.user.mention}.")
        await self.cog.iniciar_avaliacao(
            self.canal, self.guild, self.tipo, self.produto, self.comprador,
            self.preco_final, self.desconto_valor, self.desconto_percentual, self.cupom_codigo,
        )
        self.stop()


# ----------------------------------------------------------------------------
# Cog
# ----------------------------------------------------------------------------

class Loja(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        config = carregar()
        for gid, gconf in config.items():
            for tipo in ("real", "ficticio"):
                loja = gconf.get(tipo, {})
                if loja.get("canal_painel") and loja.get("mensagem_painel") and loja.get("produtos"):
                    try:
                        view = LojaPainelPublicoView(tipo, loja["produtos"])
                        self.bot.add_view(view, message_id=loja["mensagem_painel"])
                    except Exception:
                        logger.exception(f"Falha ao restaurar painel de loja ({tipo}) do servidor {gid}")

    async def processar_compra(self, interaction: discord.Interaction, tipo: str, produto: dict, codigo_cupom: str):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild
        comprador = interaction.user
        config = carregar()
        loja = get_guild_config(config, guild.id)[tipo]
        cupom = loja["cupom"]

        desconto_percentual = 0.0
        cupom_aplicado = None
        if codigo_cupom and cupom_valido(cupom) and codigo_cupom.strip().upper() == (cupom.get("codigo") or ""):
            desconto_percentual = min(cupom["percentual"], produto.get("desconto_max", 100.0))
            cupom_aplicado = cupom["codigo"]

        valor_original = produto["valor"]
        valor_final = round(valor_original * (1 - desconto_percentual / 100), 2)
        desconto_valor = round(valor_original - valor_final, 2)

        if tipo == "ficticio":
            if not debitar_saldo(guild.id, comprador.id, valor_final, detalhe=produto["nome"]):
                saldo = obter_saldo(guild.id, comprador.id)
                await interaction.followup.send(
                    f"❌ Saldo insuficiente. Você tem **{formatar_reais(saldo)}**, mas o produto custa **{formatar_reais(valor_final)}**.",
                    ephemeral=True,
                )
                return
            pago = True
            
            # Entregar cargos automático após compra fictícia
            cargos_ids = produto.get("cargos_id", [])
            if cargos_ids:
                for cargo_id in cargos_ids:
                    try:
                        cargo = guild.get_role(cargo_id)
                        if cargo:
                            await comprador.add_roles(cargo, reason=f"Compra de {produto['nome']} na loja")
                    except Exception as e:
                        logger.error(f"Erro ao dar cargo: {e}")
        else:
            pago = False

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            comprador: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        for role_id in loja.get("cargos_staff", []):
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        nome_canal_bruto = f"compra-{produto['nome']}-{comprador.name}"
        nome_canal = "".join(c for c in nome_canal_bruto if c.isalnum() or c in "-_ ").strip().replace(" ", "-").lower()[:90]
        nome_canal = nome_canal or f"compra-{produto['id']}"

        try:
            canal = await guild.create_text_channel(
                nome_canal, overwrites=overwrites, reason=f"Compra de {produto['nome']} por {comprador}"
            )
            try:
                await canal.edit(position=0)
            except discord.HTTPException:
                pass
        except discord.Forbidden:
            await interaction.followup.send("❌ Não tenho permissão para criar canais neste servidor.", ephemeral=True)
            return

        embed = discord.Embed(title=f"🛒 Compra — {produto['nome']}", color=0x2ECC71 if tipo == "ficticio" else 0x00B4D8)
        embed.add_field(name="👤 Comprador", value=comprador.mention, inline=True)
        embed.add_field(name="📦 Produto", value=produto["nome"], inline=True)
        embed.add_field(name="💰 Preço", value=formatar_reais(valor_final), inline=True)
        if desconto_percentual:
            embed.add_field(
                name="🎟️ Desconto aplicado",
                value=f"{desconto_percentual:.0f}% (cupom `{cupom_aplicado}`) — economia de {formatar_reais(desconto_valor)}",
                inline=False,
            )
        embed.add_field(
            name="📋 Status",
            value="✅ Pagamento confirmado (débito automático)" if pago else "⏳ Aguardando confirmação de pagamento Pix pela equipe",
            inline=False,
        )
        embed.set_footer(text=TAG_NIX)

        mencoes_staff = " ".join(
            guild.get_role(rid).mention for rid in loja.get("cargos_staff", []) if guild.get_role(rid)
        )

        if pago:
            if produto["tipo"] == "cargo" and produto.get("cargo_id"):
                role = guild.get_role(produto["cargo_id"])
                if role:
                    try:
                        await comprador.add_roles(role, reason="Compra na loja")
                    except discord.Forbidden:
                        pass
            await canal.send(content=f"{comprador.mention} {mencoes_staff}".strip(), embed=embed)
            await interaction.followup.send(f"✅ Compra realizada! Canal criado: {canal.mention}", ephemeral=True)
            await self.iniciar_avaliacao(
                canal, guild, tipo, produto, comprador, valor_final, desconto_valor, desconto_percentual, cupom_aplicado
            )
        else:
            view = ConfirmarPagamentoView(
                self, guild, canal, tipo, produto, comprador, valor_final, desconto_valor,
                desconto_percentual, cupom_aplicado, set(loja.get("cargos_staff", [])),
            )
            await canal.send(content=f"{comprador.mention} {mencoes_staff}".strip(), embed=embed, view=view)
            await canal.send(
                f"💳 {comprador.mention}, realize o pagamento via Pix combinado com a equipe. "
                "Um responsável vai confirmar o pagamento aqui pelo botão acima assim que o Pix cair."
            )
            await interaction.followup.send(f"✅ Canal de compra criado: {canal.mention}", ephemeral=True)

    async def iniciar_avaliacao(self, canal, guild, tipo, produto, comprador,
                                 preco_final, desconto_valor, desconto_percentual, cupom_codigo):
        await canal.send(
            f"📝 {comprador.mention}, para finalizar o atendimento, deixe abaixo um comentário/avaliação "
            "sobre a compra (obrigatório)."
        )

        def check(m: discord.Message):
            return m.channel.id == canal.id and m.author.id == comprador.id and not m.author.bot

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=1800)
            avaliacao = msg.content or "(mensagem sem texto)"
        except asyncio.TimeoutError:
            avaliacao = "(o comprador não avaliou a tempo)"

        embed = discord.Embed(
            title="✅ Compra Finalizada",
            description=f"Obrigado por escolher o produto: **{produto['nome']}** — **{guild.name}**!",
            color=0x2ECC71,
        )
        embed.set_footer(text=f"{TAG_NIX} — este canal será fechado automaticamente.")
        try:
            await canal.send(embed=embed)
        except discord.HTTPException:
            pass

        config = carregar()
        loja = get_guild_config(config, guild.id)[tipo]
        canal_logs = guild.get_channel(loja.get("canal_logs")) if loja.get("canal_logs") else None
        if canal_logs:
            log_embed = discord.Embed(title="🧾 Nova Compra Registrada", color=0x3498DB, timestamp=datetime.now(timezone.utc))
            log_embed.add_field(name="👤 Comprador", value=f"{comprador.mention} (`{comprador.id}`)", inline=False)
            log_embed.add_field(name="📦 Produto", value=produto["nome"], inline=True)
            log_embed.add_field(name="💰 Preço final", value=formatar_reais(preco_final), inline=True)
            if desconto_percentual:
                log_embed.add_field(
                    name="🎟️ Desconto",
                    value=f"{desconto_percentual:.0f}% ({formatar_reais(desconto_valor)}) — cupom `{cupom_codigo}`",
                    inline=True,
                )
            else:
                log_embed.add_field(name="🎟️ Desconto", value="Nenhum", inline=True)
            log_embed.add_field(name="🏷️ Tipo de loja", value="💳 Real (Pix)" if tipo == "real" else "🪙 Fictícia", inline=True)
            log_embed.add_field(name="🕐 Horário da compra", value=datetime.now().strftime("%d/%m/%Y %H:%M"), inline=True)
            log_embed.add_field(name="⭐ Avaliação", value=avaliacao[:1000], inline=False)
            log_embed.set_footer(text=TAG_NIX)
            try:
                await canal_logs.send(embed=log_embed)
            except discord.HTTPException:
                pass

        await asyncio.sleep(10)
        try:
            await canal.delete(reason="Compra finalizada e avaliada")
        except discord.HTTPException:
            pass

    @app_commands.command(name="loja-config", description="Abrir o painel de configuração da loja (Pix real ou fictícia)")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def loja_config_cmd(self, interaction: discord.Interaction):
        view = LojaEscolhaView(interaction.user.id)
        await interaction.response.send_message(embed=view.embed(), view=view)

    @loja_config_cmd.error
    async def loja_config_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você precisa ser administrador para configurar a loja."
        elif isinstance(error, app_commands.NoPrivateMessage):
            msg = "❌ Esse comando só pode ser usado dentro de um servidor."
        else:
            msg = "❌ Ocorreu um erro inesperado ao executar o comando."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Loja(bot))
