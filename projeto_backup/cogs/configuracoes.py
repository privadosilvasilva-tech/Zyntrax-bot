import discord
from discord import app_commands
from discord.ext import commands

# =====================================================================
# PAINEL CENTRAL DE CONFIGURAÇÕES
# Ponto único de entrada pra tudo que não tem comando próprio ainda
# (o /embed continua separado, do jeito que já está).
# Pra adicionar uma nova seção no futuro: cria o botão aqui no
# PainelConfiguracoesView apontando pra view do sistema novo.
# =====================================================================


class PainelConfiguracoesView(discord.ui.View):
    def __init__(self, dono_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id

    def texto_painel(self) -> str:
        return (
            "⚙️ **Configurações do Servidor**\n"
            "Escolha abaixo o que você quer configurar."
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="📥 Configurar Recepção", style=discord.ButtonStyle.primary, row=0)
    async def recepcao_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Importado aqui dentro pra evitar import circular com o cog de recepcao
        from cogs.recepcao import RecepcaoPainelView

        view = RecepcaoPainelView(self.dono_id)
        await interaction.response.edit_message(content=view.texto_painel(), embed=None, view=view)

    @discord.ui.button(label="📋 Configurar Formulários", style=discord.ButtonStyle.primary, row=0)
    async def formularios_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.formularios import FormulariosPainelView

        view = FormulariosPainelView(self.dono_id)
        texto = await view.texto_painel(interaction.guild_id)
        await interaction.response.edit_message(content=texto, embed=None, view=view)

    @discord.ui.button(label="✅ Configurar Verificação", style=discord.ButtonStyle.primary, row=1)
    async def verificacao_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.verificacao import abrir_painel_verificacao, montar_meta_texto, montar_preview

        _, view, sessao = abrir_painel_verificacao(interaction.guild_id, interaction.user.id)
        await interaction.response.edit_message(
            content=montar_meta_texto(sessao),
            embed=montar_preview(sessao, interaction.guild),
            view=view,
        )

    @discord.ui.button(label="🧾 Configurar Logs", style=discord.ButtonStyle.primary, row=1)
    async def logs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.logs import LogsView

        view = LogsView(interaction.guild)
        await interaction.response.edit_message(
            content="🧾 **Logs do Servidor**\nEscolha o que você quer fazer abaixo.",
            embed=None,
            view=view,
        )


class Configuracoes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="configuracoes", description="Abrir o painel central de configurações do servidor")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def configuracoes_cmd(self, interaction: discord.Interaction):
        view = PainelConfiguracoesView(interaction.user.id)
        await interaction.response.send_message(content=view.texto_painel(), view=view)

    @configuracoes_cmd.error
    async def configuracoes_cmd_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você precisa ser administrador para usar as configurações."
        elif isinstance(error, app_commands.NoPrivateMessage):
            msg = "❌ Esse comando só pode ser usado dentro de um servidor."
        else:
            msg = "❌ Ocorreu um erro inesperado ao executar o comando."

        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Configuracoes(bot))
