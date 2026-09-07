import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging

from cogs._utils_select import RoleSelectComAutocomplete, ChannelSelectComAutocomplete
from cogs._utils_moderacao import aplicar_rodape

logger = logging.getLogger("bot.rolepainel")
CONFIG_FILE = "config/rolepainel_config.json"
MAX_CARGOS = 25  # limite de botões do Discord numa única mensagem (5 linhas x 5)


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(data: dict) -> None:
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_guild_config(config: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {
            "canal_id": None,
            "titulo": "🎭 Escolha seus Cargos",
            "descricao": "Clique no botão do cargo que deseja receber.\nClique novamente para remover.",
            "cor": 0x5865F2,
            "cargos": [],  # [{"emoji": "🎮", "cargo_id": 123}]
            "canal_publicado_id": None,
            "mensagem_id": None,
        }
    return config[gid]


# ─────────────────────────────────────────────────────────────────
# VIEW PERSISTENTE PUBLICADA NO CANAL (botões que dão/removem cargo)
# ─────────────────────────────────────────────────────────────────

def _fazer_callback_toggle(role_id: int):
    async def callback(interaction: discord.Interaction):
        role = interaction.guild.get_role(role_id)
        if role is None:
            return await interaction.response.send_message(
                "❌ Esse cargo não existe mais. Avise a staff.", ephemeral=True
            )
        membro = interaction.user
        if not isinstance(membro, discord.Member):
            return
        try:
            if role in membro.roles:
                await membro.remove_roles(role, reason="Painel de cargos")
                await interaction.response.send_message(f"➖ Cargo {role.mention} removido.", ephemeral=True)
            else:
                await membro.add_roles(role, reason="Painel de cargos")
                await interaction.response.send_message(f"➕ Cargo {role.mention} adicionado!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para gerenciar esse cargo (verifique a hierarquia de cargos do bot).",
                ephemeral=True,
            )
    return callback


def construir_view_publicada(guild_id: int, cargos: list[dict]) -> discord.ui.View:
    """Reconstrói a view persistente com um botão por par cargo+emoji. Chamada ao publicar E ao reiniciar o bot."""
    view = discord.ui.View(timeout=None)
    for par in cargos[:MAX_CARGOS]:
        role_id = par["cargo_id"]
        try:
            emoji = discord.PartialEmoji.from_str(par["emoji"])
        except Exception:
            emoji = None
        botao = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=par.get("nome_cargo", "Cargo")[:80],
            emoji=emoji,
            custom_id=f"rolepainel:{guild_id}:{role_id}",
        )
        botao.callback = _fazer_callback_toggle(role_id)
        view.add_item(botao)
    return view


async def publicar_painel(bot: commands.Bot, guild: discord.Guild, guild_id: int) -> tuple[bool, str]:
    config = load_config()
    gconf = get_guild_config(config, guild_id)

    if not gconf["canal_id"]:
        return False, "❌ Escolha um canal antes de publicar."
    if not gconf["cargos"]:
        return False, "❌ Adicione ao menos um cargo antes de publicar."

    canal = guild.get_channel(gconf["canal_id"])
    if canal is None:
        return False, "❌ O canal configurado não existe mais. Escolha outro."

    embed = discord.Embed(title=gconf["titulo"], description=gconf["descricao"], color=gconf["cor"])
    linhas = []
    for par in gconf["cargos"]:
        role = guild.get_role(par["cargo_id"])
        if role:
            linhas.append(f"{par['emoji']} — {role.mention}")
    if linhas:
        embed.add_field(name="📋 Cargos disponíveis", value="\n".join(linhas), inline=False)
    aplicar_rodape(embed)

    view = construir_view_publicada(guild_id, gconf["cargos"])

    mensagem = None
    if gconf.get("mensagem_id") and gconf.get("canal_publicado_id") == canal.id:
        try:
            mensagem = await canal.fetch_message(gconf["mensagem_id"])
            await mensagem.edit(embed=embed, view=view)
        except discord.NotFound:
            mensagem = None
        except discord.HTTPException:
            mensagem = None

    if mensagem is None:
        try:
            mensagem = await canal.send(embed=embed, view=view)
        except discord.Forbidden:
            return False, f"❌ Não tenho permissão para enviar mensagens em {canal.mention}."

    gconf["canal_publicado_id"] = canal.id
    gconf["mensagem_id"] = mensagem.id
    save_config(config)
    bot.add_view(view, message_id=mensagem.id)
    return True, f"✅ Painel publicado/atualizado em {canal.mention}!"


# ─────────────────────────────────────────────────────────────────
# PAINEL DE CONFIGURAÇÃO (dentro de /configuracoes, separado do resto)
# ─────────────────────────────────────────────────────────────────

class VoltarRolePainelButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.configuracoes import PainelConfiguracoesView
        view = PainelConfiguracoesView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)


class PainelCargosView(discord.ui.View):
    def __init__(self, dono_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True
            )
            return False
        return True

    def montar_embed(self, guild: discord.Guild) -> discord.Embed:
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)

        canal_txt = f"<#{gconf['canal_id']}>" if gconf["canal_id"] else "Não configurado"
        publicado_txt = "🟢 Publicado" if gconf.get("mensagem_id") else "🔴 Ainda não publicado"

        embed = discord.Embed(
            title="🎭 PAINEL DE CARGOS POR EMOJI",
            description="Configure aqui os cargos que os membros podem escolher clicando num botão.\nEsse sistema é independente das configurações do Discord.",
            color=0x5865F2,
        )
        embed.add_field(name="📢 Canal", value=canal_txt, inline=True)
        embed.add_field(name="📊 Status", value=publicado_txt, inline=True)
        embed.add_field(name="　", value="　", inline=True)

        if gconf["cargos"]:
            linhas = []
            for par in gconf["cargos"]:
                role = guild.get_role(par["cargo_id"])
                nome = role.mention if role else f"`{par['cargo_id']}` (cargo apagado)"
                linhas.append(f"{par['emoji']} → {nome}")
            embed.add_field(name=f"🎭 Cargos configurados ({len(gconf['cargos'])}/{MAX_CARGOS})", value="\n".join(linhas), inline=False)
        else:
            embed.add_field(name="🎭 Cargos configurados", value="Nenhum cargo adicionado ainda.", inline=False)

        embed.set_footer(text="💡 Adicione cargos, escolha o canal e depois clique em Publicar")
        return embed

    @discord.ui.button(label="➕ Adicionar Cargo", style=discord.ButtonStyle.success, row=0)
    async def adicionar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        if len(gconf["cargos"]) >= MAX_CARGOS:
            return await interaction.response.send_message(
                f"❌ Limite de {MAX_CARGOS} cargos atingido (limite de botões do Discord por mensagem).", ephemeral=True
            )

        view = AdicionarCargoView(self.dono_id, self.guild_id, interaction.message)
        embed = discord.Embed(
            title="➕ Adicionar Cargo ao Painel",
            description="Selecione o cargo que deseja adicionar. Depois será pedido o emoji correspondente.",
            color=0x5865F2,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="➖ Remover Cargo", style=discord.ButtonStyle.danger, row=0)
    async def remover_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        if not gconf["cargos"]:
            return await interaction.response.send_message("❌ Não há cargos configurados para remover.", ephemeral=True)

        view = RemoverCargoView(self.dono_id, self.guild_id, gconf["cargos"], interaction.guild)
        embed = discord.Embed(title="➖ Remover Cargo", description="Selecione qual cargo deseja remover do painel.", color=0xE74C3C)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📢 Escolher Canal", style=discord.ButtonStyle.primary, row=1)
    async def canal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=180)

        async def canal_escolhido(inter: discord.Interaction, canal_id: int):
            config = load_config()
            gconf = get_guild_config(config, self.guild_id)
            gconf["canal_id"] = canal_id
            save_config(config)
            embed = self.montar_embed(inter.guild)
            await inter.response.edit_message(embed=embed, view=self)

        view.add_item(ChannelSelectComAutocomplete(canal_escolhido))
        view.add_item(VoltarSubPainelButton(self.dono_id, self.guild_id))
        embed = discord.Embed(title="📢 Escolher Canal do Painel", description="Selecione o canal onde o painel de cargos será publicado.", color=0x5865F2)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="✏️ Editar Textos", style=discord.ButtonStyle.secondary, row=1)
    async def editar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditarTextoModal(self.guild_id, interaction.message))

    @discord.ui.button(label="📤 Publicar Painel", style=discord.ButtonStyle.success, row=2)
    async def publicar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        ok, msg = await publicar_painel(interaction.client, interaction.guild, self.guild_id)
        await interaction.followup.send(msg, ephemeral=True)
        if ok:
            try:
                await interaction.edit_original_response(embed=self.montar_embed(interaction.guild), view=self)
            except discord.HTTPException:
                pass

    def voltar_item(self):
        self.add_item(VoltarRolePainelButton(self.dono_id))


class VoltarSubPainelButton(discord.ui.Button):
    """Volta pro painel de cargos (não pro /configuracoes principal) a partir de uma sub-tela."""
    def __init__(self, dono_id: int, guild_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
        self.dono_id = dono_id
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        view = PainelCargosView(self.dono_id, self.guild_id)
        view.voltar_item()
        await interaction.response.edit_message(embed=view.montar_embed(interaction.guild), view=view)


class AdicionarCargoView(discord.ui.View):
    def __init__(self, dono_id: int, guild_id: int, mensagem_original: discord.Message):
        super().__init__(timeout=180)
        self.dono_id = dono_id
        self.guild_id = guild_id
        self.mensagem_original = mensagem_original
        self.add_item(RoleSelectComAutocomplete(self._role_escolhido))
        self.add_item(VoltarSubPainelButton(dono_id, guild_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.dono_id

    async def _role_escolhido(self, interaction: discord.Interaction, role_id: int):
        role = interaction.guild.get_role(role_id)
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        if any(p["cargo_id"] == role_id for p in gconf["cargos"]):
            return await interaction.response.send_message(
                f"❌ O cargo {role.mention if role else role_id} já está no painel. Remova antes de adicionar de novo.",
                ephemeral=True,
            )
        await interaction.response.send_modal(EmojiModal(self.guild_id, role_id, role.name if role else "Cargo", self.mensagem_original))


class EmojiModal(discord.ui.Modal, title="Definir Emoji do Cargo"):
    def __init__(self, guild_id: int, role_id: int, nome_cargo: str, mensagem_original: discord.Message):
        super().__init__()
        self.guild_id = guild_id
        self.role_id = role_id
        self.nome_cargo = nome_cargo
        self.mensagem_original = mensagem_original
        self.emoji_input = discord.ui.TextInput(
            label="Emoji correspondente",
            placeholder="Ex: 🎮 ou <:nome:123456789>",
            max_length=60,
            required=True,
        )
        self.add_item(self.emoji_input)

    async def on_submit(self, interaction: discord.Interaction):
        valor = self.emoji_input.value.strip()
        try:
            discord.PartialEmoji.from_str(valor)
        except Exception:
            return await interaction.response.send_message("❌ Emoji inválido. Tente novamente.", ephemeral=True)

        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["cargos"] = [p for p in gconf["cargos"] if p["cargo_id"] != self.role_id]
        gconf["cargos"].append({"emoji": valor, "cargo_id": self.role_id, "nome_cargo": self.nome_cargo})
        save_config(config)

        await interaction.response.send_message(f"✅ Cargo **{self.nome_cargo}** vinculado ao emoji {valor}.", ephemeral=True)

        dono_id = self._resolver_dono(interaction)
        view = PainelCargosView(dono_id, self.guild_id)
        view.voltar_item()
        try:
            await self.mensagem_original.edit(embed=view.montar_embed(interaction.guild), view=view)
        except discord.HTTPException:
            pass

    def _resolver_dono(self, interaction: discord.Interaction) -> int:
        try:
            if self.mensagem_original.interaction_metadata:
                return self.mensagem_original.interaction_metadata.user.id
        except AttributeError:
            pass
        return interaction.user.id


class RemoverCargoSelect(discord.ui.Select):
    def __init__(self, cargos: list[dict], guild: discord.Guild):
        options = []
        for par in cargos[:25]:
            role = guild.get_role(par["cargo_id"])
            nome = role.name if role else f"Cargo apagado ({par['cargo_id']})"
            try:
                emoji = discord.PartialEmoji.from_str(par["emoji"])
            except Exception:
                emoji = None
            options.append(discord.SelectOption(label=nome[:100], value=str(par["cargo_id"]), emoji=emoji))
        super().__init__(placeholder="🔍 Selecione o cargo a remover", options=options)

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        config = load_config()
        gconf = get_guild_config(config, interaction.guild_id)
        gconf["cargos"] = [p for p in gconf["cargos"] if p["cargo_id"] != role_id]
        save_config(config)

        for item in self.view.children:
            if isinstance(item, VoltarSubPainelButton):
                dono_id, guild_id = item.dono_id, item.guild_id
                view = PainelCargosView(dono_id, guild_id)
                view.voltar_item()
                return await interaction.response.edit_message(embed=view.montar_embed(interaction.guild), view=view)


class RemoverCargoView(discord.ui.View):
    def __init__(self, dono_id: int, guild_id: int, cargos: list[dict], guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(RemoverCargoSelect(cargos, guild))
        self.add_item(VoltarSubPainelButton(dono_id, guild_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True


class EditarTextoModal(discord.ui.Modal, title="Editar Textos do Painel"):
    def __init__(self, guild_id: int, mensagem_original: discord.Message):
        super().__init__()
        self.guild_id = guild_id
        self.mensagem_original = mensagem_original
        config = load_config()
        gconf = get_guild_config(config, guild_id)

        self.titulo_input = discord.ui.TextInput(
            label="Título", max_length=100, required=True, default=gconf["titulo"]
        )
        self.descricao_input = discord.ui.TextInput(
            label="Descrição", style=discord.TextStyle.paragraph, max_length=1000,
            required=True, default=gconf["descricao"]
        )
        self.cor_input = discord.ui.TextInput(
            label="Cor (hex, ex: 5865F2)", max_length=7, required=False, default=f"{gconf['cor']:06X}"
        )
        self.add_item(self.titulo_input)
        self.add_item(self.descricao_input)
        self.add_item(self.cor_input)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["titulo"] = self.titulo_input.value
        gconf["descricao"] = self.descricao_input.value
        if self.cor_input.value:
            try:
                gconf["cor"] = int(self.cor_input.value.strip().lstrip("#"), 16)
            except ValueError:
                pass
        save_config(config)

        try:
            dono_id = self.mensagem_original.interaction_metadata.user.id if self.mensagem_original.interaction_metadata else interaction.user.id
        except AttributeError:
            dono_id = interaction.user.id
        view = PainelCargosView(dono_id, self.guild_id)
        view.voltar_item()
        await interaction.response.edit_message(embed=view.montar_embed(interaction.guild), view=view)


def abrir_painel_cargos(dono_id: int, guild: discord.Guild) -> tuple[discord.Embed, PainelCargosView]:
    view = PainelCargosView(dono_id, guild.id)
    view.voltar_item()
    embed = view.montar_embed(guild)
    return embed, view


# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────

class RolePainel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Re-registra as views persistentes de todos os servidores já configurados
        # (necessário pra os botões continuarem funcionando depois de reiniciar o bot).
        config = load_config()
        for gid, gconf in config.items():
            if gconf.get("mensagem_id") and gconf.get("cargos"):
                try:
                    view = construir_view_publicada(int(gid), gconf["cargos"])
                    self.bot.add_view(view, message_id=gconf["mensagem_id"])
                except Exception:
                    logger.exception(f"Falha ao registrar view persistente do painel de cargos (guild {gid})")


async def setup(bot: commands.Bot):
    await bot.add_cog(RolePainel(bot))
