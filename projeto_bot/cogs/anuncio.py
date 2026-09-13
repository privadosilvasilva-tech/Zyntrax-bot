import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class Anuncio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = os.path.expanduser("~/config/anuncio_config.json")

    def carregar_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @app_commands.command(name="anuncio", description="Envia um anúncio no canal configurado")
    @app_commands.describe(mensagem="Texto do anúncio")
    @app_commands.checks.has_permissions(administrator=True)
    async def anuncio(self, interaction: discord.Interaction, mensagem: str):
        config = self.carregar_config()
        canal_id = config.get("canal_id")
        cargo_id = config.get("cargo_ping")

        if not canal_id:
            await interaction.response.send_message("❌ Canal não configurado! Use `/anuncio-config` primeiro.", ephemeral=True)
            return

        canal = self.bot.get_channel(canal_id)
        if not canal:
            await interaction.response.send_message("❌ Canal configurado não existe!", ephemeral=True)
            return

        ping = f"<@&{cargo_id}>" if cargo_id else ""

        embed = discord.Embed(
            title="📢 ANÚNCIO IMPORTANTE",
            description=mensagem,
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
        embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else "")
        embed.add_field(name="━━━━━━━━━━━━━━━━", value="", inline=False)
        embed.set_footer(text="⚡ Zyntrax Bot | Comunidade Premium", icon_url=self.bot.user.avatar.url)

        await canal.send(ping, embed=embed)
        await interaction.response.send_message(f"✅ Anúncio enviado em {canal.mention}!", ephemeral=True)

    @app_commands.command(name="anuncio-config", description="Configura canal e cargo de ping para anúncios")
    @app_commands.checks.has_permissions(administrator=True)
    async def anuncio_config(self, interaction: discord.Interaction):
        config = self.carregar_config()

        embed = discord.Embed(
            title="⚙️ Configurar Anúncio",
            description="Escolha o que configurar:",
            color=discord.Color.blurple()
        )

        view = discord.ui.View()

        async def callback_canal(interaction_btn):
            modal = ConfigModalCanal()
            await interaction_btn.response.send_modal(modal)

        async def callback_cargo(interaction_btn):
            modal = ConfigModalCargo()
            await interaction_btn.response.send_modal(modal)

        btn_canal = discord.ui.Button(label="📍 Configurar Canal", style=discord.ButtonStyle.primary)
        btn_canal.callback = callback_canal
        view.add_item(btn_canal)

        btn_cargo = discord.ui.Button(label="👥 Configurar Cargo (Ping)", style=discord.ButtonStyle.success)
        btn_cargo.callback = callback_cargo
        view.add_item(btn_cargo)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @anuncio.error
    @anuncio_config.error
    async def anuncio_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Apenas administradores podem usar esse comando.", ephemeral=True)

class ConfigModalCanal(discord.ui.Modal):
    canal_id = discord.ui.TextInput(label="ID do Canal", placeholder="Exemplo: 1234567890")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            canal_id = int(self.canal_id.value)
            config_path = os.path.expanduser("~/config/anuncio_config.json")
            with open(config_path, "r") as f:
                config = json.load(f)
            config["canal_id"] = canal_id
            with open(config_path, "w") as f:
                json.dump(config, f)
            await interaction.response.send_message(f"✅ Canal configurado: <#{canal_id}>", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)

class ConfigModalCargo(discord.ui.Modal):
    cargo_id = discord.ui.TextInput(label="ID do Cargo", placeholder="Exemplo: 1234567890")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cargo_id = int(self.cargo_id.value)
            config_path = os.path.expanduser("~/config/anuncio_config.json")
            with open(config_path, "r") as f:
                config = json.load(f)
            config["cargo_ping"] = cargo_id
            with open(config_path, "w") as f:
                json.dump(config, f)
            await interaction.response.send_message(f"✅ Cargo configurado: <@&{cargo_id}>", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Anuncio(bot))
