import discord
from discord import app_commands
from discord.ext import commands
import os
import sys

class Restart(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="restart", description="Reinicia o bot")
    @app_commands.checks.has_permissions(administrator=True)
    async def restart(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔄 Reiniciando Bot",
            description="O bot está sendo reiniciado em 2 segundos...",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

        await self.bot.close()
        os.execv(sys.executable, ['python3', 'bot.py'])

    @restart.error
    async def restart_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Apenas administradores podem usar esse comando.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Restart(bot))
