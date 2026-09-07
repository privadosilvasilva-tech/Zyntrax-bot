import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
BASE_DIR = Path(__file__).resolve().parent
COGS_DIR = BASE_DIR / "cogs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class ZyntraxBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.load_cogs()
        try:
            synced = await self.tree.sync()
            logger.info(f"{len(synced)} comando(s) sincronizado(s)")
            for cmd in synced:
                logger.info(f"   - /{cmd.name}")
        except Exception:
            logger.exception("Falha ao sincronizar comandos")

    async def load_cogs(self):
        COGS_DIR.mkdir(exist_ok=True)
        for arquivo in sorted(COGS_DIR.glob("*.py")):
            nome = arquivo.stem
            if nome.startswith("_"):
                continue
            try:
                await self.load_extension(f"cogs.{nome}")
                logger.info(f"Cog carregado: {nome}")
            except Exception:
                logger.exception(f"Falha ao carregar cog: {nome}")

    async def on_ready(self):
        logger.info(f"Conectado como {self.user} (ID: {self.user.id})")
        logger.info(f"Em {len(self.guilds)} servidor(es)")
        try:
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name="/logs | /ping")
            )
        except Exception:
            logger.exception("Falha ao definir presença")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error("Erro em comando de prefixo", exc_info=error)


async def main():
    if not TOKEN:
        logger.critical("DISCORD_TOKEN não encontrado. Configure o arquivo .env (veja .env.example)")
        sys.exit(1)

    bot = ZyntraxBot()

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        # Handler global: qualquer erro não tratado em slash command cai aqui
        # em vez de deixar a interação travada até o Discord mostrar "não respondeu a tempo".
        logger.error("Erro em comando de aplicação", exc_info=error)
        msg = "❌ Ocorreu um erro inesperado ao executar esse comando."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot encerrado manualmente.")
