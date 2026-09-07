import discord
from discord.ext import commands
import os
import sys

class Restart(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def restart(self, ctx):
        embed = discord.Embed(
            title="🔄 Reiniciando Bot",
            description="O bot está sendo reiniciado em 2 segundos...",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        
        await self.bot.close()
        os.execv(sys.executable, ['python3', 'bot.py'])

async def setup(bot):
    await bot.add_cog(Restart(bot))
