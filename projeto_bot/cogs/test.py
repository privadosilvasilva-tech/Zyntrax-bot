import discord
from discord import app_commands
from discord.ext import commands

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ping", description="Testa se o bot está respondendo")
    async def ping(self, interaction: discord.Interaction):
        latencia = round(self.bot.latency * 1000)
        await interaction.response.send_message(f'🏓 Pong! **{latencia}ms**')

async def setup(bot):
    await bot.add_cog(Test(bot))
