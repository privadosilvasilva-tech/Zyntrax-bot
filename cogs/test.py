import discord
from discord import app_commands
from discord.ext import commands
import platform
import resource
import time
from datetime import datetime, timezone


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Marca o horário de início assim que o cog é carregado (na inicialização do bot)
        if not hasattr(bot, "launch_time"):
            bot.launch_time = datetime.now(timezone.utc)

    def _formatar_uptime(self) -> str:
        delta = datetime.now(timezone.utc) - self.bot.launch_time
        dias, resto = divmod(int(delta.total_seconds()), 86400)
        horas, resto = divmod(resto, 3600)
        minutos, segundos = divmod(resto, 60)

        partes = []
        if dias:
            partes.append(f"{dias}d")
        if horas:
            partes.append(f"{horas}h")
        if minutos:
            partes.append(f"{minutos}m")
        partes.append(f"{segundos}s")
        return " ".join(partes)

    def _cor_por_latencia(self, ms: int) -> discord.Color:
        if ms < 100:
            return discord.Color.green()
        if ms < 300:
            return discord.Color.gold()
        return discord.Color.red()

    def _status_por_latencia(self, ms: int) -> str:
        if ms < 100:
            return "🟢 Excelente"
        if ms < 300:
            return "🟡 Instável"
        return "🔴 Ruim"

    def _memoria_mb(self) -> float:
        # ru_maxrss vem em KB no Linux/Android (Termux)
        uso_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(uso_kb / 1024, 1)

    @app_commands.command(name="ping", description="Mostra o status e as estatísticas do bot")
    async def ping(self, interaction: discord.Interaction):
        inicio = time.perf_counter()
        await interaction.response.defer(thinking=True)
        latencia_resposta = round((time.perf_counter() - inicio) * 1000)

        latencia_ws = round(self.bot.latency * 1000)
        cor = self._cor_por_latencia(latencia_ws)

        total_membros = sum(g.member_count or 0 for g in self.bot.guilds)

        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**{self._status_por_latencia(latencia_ws)}**",
            color=cor,
            timestamp=datetime.now(timezone.utc),
        )

        embed.add_field(name="📡 Latência WebSocket", value=f"`{latencia_ws}ms`", inline=True)
        embed.add_field(name="⚡ Tempo de Resposta", value=f"`{latencia_resposta}ms`", inline=True)
        embed.add_field(name="⏱️ Uptime", value=self._formatar_uptime(), inline=True)

        embed.add_field(name="🌐 Servidores", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="👥 Membros (total)", value=f"`{total_membros}`", inline=True)
        embed.add_field(name="💾 Memória (RSS)", value=f"`{self._memoria_mb()} MB`", inline=True)

        embed.add_field(
            name="🧩 Versões",
            value=(
                f"discord.py `{discord.__version__}`\n"
                f"Python `{platform.python_version()}`"
            ),
            inline=False,
        )

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Solicitado por {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Test(bot))
