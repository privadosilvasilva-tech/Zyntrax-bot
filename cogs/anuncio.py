import discord
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

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def anuncio(self, ctx, *, mensagem):
        config = self.carregar_config()
        canal_id = config.get("canal_id")
        cargo_id = config.get("cargo_ping")

        if not canal_id:
            await ctx.send("❌ Canal não configurado! Use `/anuncio-config` primeiro.")
            return

        canal = self.bot.get_channel(canal_id)
        if not canal:
            await ctx.send("❌ Canal configurado não existe!")
            return

        ping = f"<@&{cargo_id}>" if cargo_id else ""

        embed = discord.Embed(
            title="📢 ANÚNCIO IMPORTANTE",
            description=mensagem,
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else "")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else "")
        embed.add_field(name="━━━━━━━━━━━━━━━━", value="", inline=False)
        embed.set_footer(text="⚡ Zyntrax Bot | Comunidade Premium", icon_url=self.bot.user.avatar.url)

        await canal.send(ping, embed=embed)
        await ctx.send(f"✅ Anúncio enviado em {canal.mention}!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def anuncio_config(self, ctx):
        config = self.carregar_config()

        embed = discord.Embed(
            title="⚙️ Configurar Anúncio",
            description="Escolha o que configurar:",
            color=discord.Color.blurple()
        )

        view = discord.ui.View()

        async def callback_canal(interaction):
            modal = ConfigModalCanal()
            await interaction.response.send_modal(modal)

        async def callback_cargo(interaction):
            modal = ConfigModalCargo()
            await interaction.response.send_modal(modal)

        btn_canal = discord.ui.Button(label="📍 Configurar Canal", style=discord.ButtonStyle.primary)
        btn_canal.callback = callback_canal
        view.add_item(btn_canal)

        btn_cargo = discord.ui.Button(label="👥 Configurar Cargo (Ping)", style=discord.ButtonStyle.success)
        btn_cargo.callback = callback_cargo
        view.add_item(btn_cargo)

        await ctx.send(embed=embed, view=view)

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
