import discord
from discord import app_commands
from discord.ext import commands

COR_PAINEL_PRINCIPAL = 0x2F3136
COR_MEMBROS = 0x43B581
COR_APLICACOES = 0x7289DA
COR_REGISTROS = 0xFAA61A
COR_MODERACAO = 0xE74C3C


class PainelConfiguracoesView(discord.ui.View):
    def __init__(self, dono_id: int):
        super().__init__(timeout=300)
        self.dono_id = dono_id

    def texto_painel(self) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ PAINEL CENTRAL DE CONFIGURAÇÕES",
            description="Gerencie todos os aspectos do seu servidor de forma organizada e intuitiva",
            color=COR_PAINEL_PRINCIPAL,
        )
        
        embed.add_field(
            name="👥 GERENCIAMENTO DE MEMBROS",
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False
        )
        
        embed.add_field(
            name="📥 Recepção",
            value="> Personalize mensagens de boas-vindas e despedidas\n> Customize com cores, imagens e variáveis",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Auto Cargo",
            value="> Atribua cargos automaticamente a novos membros\n> Configure quais cargos serão distribuídos",
            inline=False
        )
        
        embed.add_field(
            name="✅ Verificação",
            value="> Sistema de verificação para novos usuários\n> Proteja seu servidor contra alt-accounts",
            inline=False
        )
        
        embed.add_field(
            name="📋 APLICAÇÕES E FORMULÁRIOS",
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False
        )
        
        embed.add_field(
            name="📝 Formulários",
            value="> Crie formulários de aplicação personalizados\n> Gerencie inscrições e aprovações",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ MODERAÇÃO E SEGURANÇA",
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Moderação",
            value="> Configure filtros e proteção automática\n> Gerencie infrações e logs de moderação",
            inline=False
        )
        
        embed.add_field(
            name="🎭 Cargos por Emoji",
            value="> Painel de cargos que membros escolhem clicando\n> Configure canal, cargos e emojis correspondentes",
            inline=False
        )
        
        embed.add_field(
            name="🎫 ATENDIMENTO",
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False
        )

        embed.add_field(
            name="🎫 Tickets",
            value="> Central de atendimento inteligente (SmartDesk)\n> Categorias, formulários, prioridade e dashboard",
            inline=False
        )

        embed.add_field(
            name="📊 REGISTROS E LOGS",
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False
        )
        
        embed.add_field(
            name="🧾 Logs",
            value="> Rastreie eventos e atividades do servidor\n> Registre ações importantes automaticamente",
            inline=False
        )
        
        embed.set_footer(text="💡 Clique nos botões abaixo para configurar • Apenas administradores")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu esse painel pode usar estes botões.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="📥 Recepção", style=discord.ButtonStyle.success, row=0)
    async def recepcao_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.recepcao import RecepcaoPainelView
        view = RecepcaoPainelView(self.dono_id)
        await interaction.response.edit_message(embed=view.texto_painel(), view=view)

    @discord.ui.button(label="🎯 Auto Cargo", style=discord.ButtonStyle.success, row=0)
    async def autocargo_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.autocargo import abrir_painel_autocargo
        embed, view = abrir_painel_autocargo(self.dono_id, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="✅ Verificação", style=discord.ButtonStyle.success, row=0)
    async def verificacao_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.verificacao import abrir_painel_verificacao, montar_meta_embed, montar_preview
        _, view, sessao = abrir_painel_verificacao(interaction.guild_id, interaction.user.id)
        await interaction.response.edit_message(
            embeds=[montar_meta_embed(sessao), montar_preview(sessao, interaction.guild)],
            view=view,
        )

    @discord.ui.button(label="📋 Formulários", style=discord.ButtonStyle.primary, row=1)
    async def formularios_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.formularios import FormulariosPainelView
        view = FormulariosPainelView(self.dono_id)
        embed = await view.texto_painel(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🛡️ Moderação", style=discord.ButtonStyle.danger, row=1)
    async def moderacao_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.moderacao import abrir_painel_moderacao
        embed, view = abrir_painel_moderacao(self.dono_id, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎭 Cargos por Emoji", style=discord.ButtonStyle.primary, row=2)
    async def rolepainel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.rolepainel import abrir_painel_cargos
        embed, view = abrir_painel_cargos(self.dono_id, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎫 Tickets", style=discord.ButtonStyle.success, row=2)
    async def tickets_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.tickets import TicketsPainelView
        view = TicketsPainelView(self.dono_id)
        embed = await view.texto_painel(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🧾 Logs", style=discord.ButtonStyle.secondary, row=1)
    async def logs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.logs import LogsView
        view = LogsView(interaction.guild, dono_id=self.dono_id)
        embed = discord.Embed(
            title="🧾 Logs do Servidor",
            description="Escolha o que você quer fazer abaixo.",
            color=COR_REGISTROS,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class Configuracoes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="configuracoes", description="Abrir o painel central de configurações do servidor")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def configuracoes_cmd(self, interaction: discord.Interaction):
        view = PainelConfiguracoesView(interaction.user.id)
        await interaction.response.send_message(embed=view.texto_painel(), view=view)

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
