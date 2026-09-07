import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging
import unicodedata
import re

logger = logging.getLogger("bot.filtro_palavras")
CONFIG_FILE = "config/moderacao_config.json"

PALAVRAS_PADRAO = {
    "ofensas": [
        "idiota", "imbecil", "burro", "burra", "otário", "otária", "babaca",
        "besta", "anta", "animal", "asno", "asna", "cretino", "cretina",
        "estúpido", "estúpida", "ignorante", "inútil", "nojento", "nojenta",
        "ridículo", "ridícula", "palhaço", "palhaça", "patético", "patética",
        "fracassado", "fracassada", "loser", "trouxa", "tonto", "tonta",
        "lerdo", "lerda", "tapado", "tapada", "mané", "vacilão", "vacilona",
        "zé ruela", "zé ninguém", "moleque", "moleca"
    ],
    "palavroes": [
        "porra", "caralho", "merda", "bosta", "cacete", "foda", "fodase",
        "fuder", "fudeu", "puta", "puto", "putaria", "viado", "cu", "cuzão",
        "cuzona", "buceta", "pica", "pau", "rola", "xota", "merdinha",
        "porra nenhuma", "vai se foder", "vai tomar no cu", "vai à merda",
        "filho da puta", "filha da puta", "desgraçado", "desgraçada"
    ],
    "assedio": [
        "se mata", "vai se matar", "morre", "tomara que morra",
        "bem que podia morrer", "some daqui", "ninguém te quer",
        "ninguém gosta de você", "você é um lixo", "você não serve pra nada",
        "vou acabar com você", "vou te pegar", "vou atrás de você",
        "vou te matar", "eu vou te matar", "merece morrer"
    ]
}

def normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

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
            "filtro_palavras": {
                "enabled": False,
                "ofensas": PALAVRAS_PADRAO["ofensas"].copy(),
                "palavroes": PALAVRAS_PADRAO["palavroes"].copy(),
                "assedio": PALAVRAS_PADRAO["assedio"].copy(),
                "customizadas": [],
                "aviso": "Essa palavra não é permitida aqui."
            }
        }
    if "filtro_palavras" not in config[gid]:
        config[gid]["filtro_palavras"] = {
            "enabled": False,
            "ofensas": PALAVRAS_PADRAO["ofensas"].copy(),
            "palavroes": PALAVRAS_PADRAO["palavroes"].copy(),
            "assedio": PALAVRAS_PADRAO["assedio"].copy(),
            "customizadas": [],
            "aviso": "Essa palavra não é permitida aqui."
        }
    return config[gid]["filtro_palavras"]

class VoltarFiltroButton(discord.ui.Button):
    def __init__(self, dono_id: int):
        super().__init__(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=2)
        self.dono_id = dono_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.moderacao import abrir_painel_moderacao
        embed, view = abrir_painel_moderacao(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

class PainelFiltroView(discord.ui.View):
    def __init__(self, dono_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id
        self.guild_id = guild_id
        
        config = load_config()
        gconf = get_guild_config(config, guild_id)
        self.ofensas = set(gconf.get("ofensas", []))
        self.palavroes = set(gconf.get("palavroes", []))
        self.assedio = set(gconf.get("assedio", []))
        self.customizadas = set(gconf.get("customizadas", []))
        self.enabled = gconf.get("enabled", False)
        self.categoria_selecionada = "ofensas"
        self.add_item(VoltarFiltroButton(dono_id))

    def montar_embed(self) -> discord.Embed:
        status = "🟢 Ativado" if self.enabled else "🔴 Desativado"
        total = len(self.ofensas) + len(self.palavroes) + len(self.assedio) + len(self.customizadas)
        
        embed = discord.Embed(
            title="🚫 CONFIGURAR FILTRO DE PALAVRAS",
            description="Bloqueie palavras por categoria com normalização inteligente",
            color=0xE74C3C,
        )
        
        embed.add_field(name="📊 Status", value=status, inline=True)
        embed.add_field(name="📝 Total de Palavras", value=f"`{total}`", inline=True)
        embed.add_field(name="　", value="　", inline=True)
        
        embed.add_field(
            name="🟢 OFENSAS COMUNS",
            value=f"> `{len(self.ofensas)}` palavras\n> Palavras leves (ex: idiota, burro)",
            inline=False
        )
        
        embed.add_field(
            name="🟠 PALAVRÕES E OBSCENIDADES",
            value=f"> `{len(self.palavroes)}` palavras\n> Palavras fortes (ex: porra, merda)",
            inline=False
        )
        
        embed.add_field(
            name="🔴 ASSÉDIO E AGRESSÃO",
            value=f"> `{len(self.assedio)}` palavras\n> Ameaças e assédio (ex: vou te matar)",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ CUSTOMIZADAS",
            value=f"> `{len(self.customizadas)}` palavras personalizadas",
            inline=False
        )
        
        embed.add_field(
            name="🔐 NORMALIZAÇÃO ATIVA",
            value="> • Remove acentos (á→a)\n> • Remove pontuação intercalada\n> • Ignora maiúsculas\n> • Remove espaços extras",
            inline=False
        )
        
        embed.set_footer(text="💡 Selecione uma categoria abaixo")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        embed = self.montar_embed()
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="🟢 Ofensas", style=discord.ButtonStyle.primary, row=0)
    async def ofensas_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.categoria_selecionada = "ofensas"
        await self.abrir_categoria(interaction, "OFENSAS COMUNS", self.ofensas)

    @discord.ui.button(label="🟠 Palavrões", style=discord.ButtonStyle.primary, row=0)
    async def palavroes_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.categoria_selecionada = "palavroes"
        await self.abrir_categoria(interaction, "PALAVRÕES E OBSCENIDADES", self.palavroes)

    @discord.ui.button(label="🔴 Assédio", style=discord.ButtonStyle.primary, row=0)
    async def assedio_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.categoria_selecionada = "assedio"
        await self.abrir_categoria(interaction, "ASSÉDIO E AGRESSÃO", self.assedio)

    @discord.ui.button(label="🛡️ Customizadas", style=discord.ButtonStyle.primary, row=1)
    async def customizadas_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.categoria_selecionada = "customizadas"
        await self.abrir_categoria(interaction, "PALAVRAS CUSTOMIZADAS", self.customizadas)

    async def abrir_categoria(self, interaction: discord.Interaction, titulo: str, palavras_set: set):
        embed = discord.Embed(
            title=f"🚫 {titulo}",
            description=f"Gerenciando `{len(palavras_set)}` palavras",
            color=0xE74C3C,
        )
        
        if palavras_set:
            lista = ", ".join(sorted(list(palavras_set))[:15])
            if len(palavras_set) > 15:
                lista += f"\n... e mais {len(palavras_set) - 15}"
            embed.add_field(name="📝 Palavras", value=f"`{lista}`", inline=False)
        
        view = discord.ui.View()
        
        adicionar_btn = discord.ui.Button(label="➕ Adicionar", style=discord.ButtonStyle.success, row=0)
        remover_btn = discord.ui.Button(label="❌ Remover", style=discord.ButtonStyle.danger, row=0)
        voltar_btn = discord.ui.Button(label="◀️ Voltar", style=discord.ButtonStyle.secondary, row=1)
        
        async def adicionar_callback(interaction: discord.Interaction):
            modal = ModalAdicionarPalavra(self, self.categoria_selecionada)
            await interaction.response.send_modal(modal)
        
        async def remover_callback(interaction: discord.Interaction):
            if not palavras_set:
                await interaction.response.send_message("❌ Nenhuma palavra para remover", ephemeral=True)
                return
            
            select = discord.ui.Select(
                placeholder="Selecione a palavra para remover",
                options=[discord.SelectOption(label=p[:100], value=p) for p in sorted(list(palavras_set))[:25]]
            )
            
            async def select_callback(interaction: discord.Interaction):
                palavras_set.discard(select.values[0])
                await interaction.response.defer()
                await self.atualizar(interaction)
            
            select.callback = select_callback
            view2 = discord.ui.View()
            view2.add_item(select)
            await interaction.response.send_message("Escolha a palavra para remover:", view=view2, ephemeral=True)
        
        async def voltar_callback(interaction: discord.Interaction):
            await self.atualizar(interaction)
        
        adicionar_btn.callback = adicionar_callback
        remover_btn.callback = remover_callback
        voltar_btn.callback = voltar_callback
        
        view.add_item(adicionar_btn)
        view.add_item(remover_btn)
        view.add_item(voltar_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🟢 Ativar", style=discord.ButtonStyle.success, row=1)
    async def ativar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.enabled = not self.enabled
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["enabled"] = self.enabled
        save_config(config)
        await self.atualizar(interaction)

    @discord.ui.button(label="💾 Salvar", style=discord.ButtonStyle.success, row=1)
    async def salvar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        gconf = get_guild_config(config, self.guild_id)
        gconf["ofensas"] = list(self.ofensas)
        gconf["palavroes"] = list(self.palavroes)
        gconf["assedio"] = list(self.assedio)
        gconf["customizadas"] = list(self.customizadas)
        gconf["enabled"] = self.enabled
        save_config(config)
        await interaction.response.send_message("✅ Configuração salva com sucesso!", ephemeral=True)

class ModalAdicionarPalavra(discord.ui.Modal, title="Adicionar Palavra"):
    palavra = discord.ui.TextInput(label="Palavra a bloquear", placeholder="Digite a palavra", max_length=100)
    
    def __init__(self, view: PainelFiltroView, categoria: str):
        super().__init__()
        self.view = view
        self.categoria = categoria

    async def on_submit(self, interaction: discord.Interaction):
        palavra = self.palavra.value.lower().strip()
        if palavra:
            if self.categoria == "ofensas":
                self.view.ofensas.add(palavra)
            elif self.categoria == "palavroes":
                self.view.palavroes.add(palavra)
            elif self.categoria == "assedio":
                self.view.assedio.add(palavra)
            elif self.categoria == "customizadas":
                self.view.customizadas.add(palavra)
            
            await interaction.response.defer()
            await self.view.atualizar(interaction)

def abrir_painel_filtro(dono_id: int, guild_id: int) -> tuple[discord.Embed, PainelFiltroView]:
    view = PainelFiltroView(dono_id, guild_id)
    embed = view.montar_embed()
    return embed, view

class FitroPalavras(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        config = load_config()
        gconf = get_guild_config(config, message.guild.id)
        
        if not gconf.get("enabled"):
            return
        
        texto_normalizado = normalizar_texto(message.content)
        
        todas_palavras = (
            gconf.get("ofensas", []) +
            gconf.get("palavroes", []) +
            gconf.get("assedio", []) +
            gconf.get("customizadas", [])
        )
        
        for palavra in todas_palavras:
            palavra_normalizada = normalizar_texto(palavra)
            
            if re.search(rf'\b{re.escape(palavra_normalizada)}\b', texto_normalizado):
                try:
                    await message.delete()
                    aviso = gconf.get("aviso", "Essa palavra não é permitida aqui.")
                    await message.author.send(f"⚠️ {aviso}")
                    logger.info(f"Mensagem deletada de {message.author} por conter palavra bloqueada")
                except discord.Forbidden:
                    logger.warning(f"Sem permissão para deletar mensagem de {message.author}")
                return

async def setup(bot: commands.Bot):
    await bot.add_cog(FitroPalavras(bot))
