import discord
from discord import app_commands
from discord.ext import commands
import logging

from cogs._utils_moderacao import (
    aplicar_rodape, tem_permissao, checar_permissao, pode_moderar,
    parse_duracao, formatar_duracao, registrar_caso, get_caso,
    get_casos_membro, get_casos_recentes, desativar_casos_ativos,
    enviar_log_moderacao, ConfirmarAcaoView, get_staff_roles, set_staff_roles,
    load_mod_config, save_mod_config, get_guild_mod_config,
)

logger = logging.getLogger("bot.moderacao_comandos")


def tag(usuario: discord.abc.User) -> str:
    return f"{usuario.name}" if usuario.discriminator == "0" else f"{usuario.name}#{usuario.discriminator}"


class ModeracaoComandos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            msg = str(error) or "❌ Você não tem permissão para usar esse comando."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return
        logger.error("Erro em comando de moderação", exc_info=error)
        msg = "❌ Ocorreu um erro inesperado ao executar esse comando."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    # ═════════════════════════════════════════════════════════════
    # 🛡️ PUNIÇÕES PRINCIPAIS
    # ═════════════════════════════════════════════════════════════

    @app_commands.command(name="ban", description="Bane permanentemente um membro do servidor")
    @app_commands.describe(membro="Membro a ser banido", motivo="Motivo do banimento")
    @checar_permissao("ban_members")
    async def ban(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não especificado"):
        ok, erro = pode_moderar(interaction.user, membro, interaction.guild.me)
        if not ok:
            return await interaction.response.send_message(erro, ephemeral=True)

        embed = discord.Embed(
            title="🔨 Confirmar Banimento",
            description=f"Tem certeza que deseja banir **{membro.mention}** permanentemente?",
            color=0xE74C3C,
        )
        embed.add_field(name="📝 Motivo", value=motivo, inline=False)
        aplicar_rodape(embed)

        view = ConfirmarAcaoView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.mensagem = await interaction.original_response()
        await view.wait()
        if not view.confirmado:
            return await view.interacao_resposta.response.edit_message(
                content="❌ Banimento cancelado.", embed=None, view=None
            ) if view.interacao_resposta else None

        try:
            await membro.send(f"🔨 Você foi banido de **{interaction.guild.name}**.\n📝 Motivo: {motivo}")
        except discord.HTTPException:
            pass

        await interaction.guild.ban(membro, reason=f"{tag(interaction.user)}: {motivo}", delete_message_seconds=0)
        caso = registrar_caso(interaction.guild.id, "ban", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        resultado = discord.Embed(description=f"✅ **{membro.mention}** foi banido. Caso `#{caso['id']}`.", color=0x2ECC71)
        aplicar_rodape(resultado)
        await view.interacao_resposta.response.edit_message(embed=resultado, view=None)

    @app_commands.command(name="tempban", description="Bane um membro por um tempo determinado")
    @app_commands.describe(membro="Membro a ser banido", duracao="Ex: 1d, 12h, 30m", motivo="Motivo do banimento")
    @checar_permissao("ban_members")
    async def tempban(self, interaction: discord.Interaction, membro: discord.Member, duracao: str, motivo: str = "Não especificado"):
        ok, erro = pode_moderar(interaction.user, membro, interaction.guild.me)
        if not ok:
            return await interaction.response.send_message(erro, ephemeral=True)

        segundos = parse_duracao(duracao)
        if segundos is None:
            return await interaction.response.send_message(
                "❌ Duração inválida. Use algo como `30m`, `2h`, `1d`.", ephemeral=True
            )

        embed = discord.Embed(
            title="⏳🔨 Confirmar Ban Temporário",
            description=f"Banir **{membro.mention}** por **{formatar_duracao(segundos)}**?",
            color=0xE74C3C,
        )
        embed.add_field(name="📝 Motivo", value=motivo, inline=False)
        aplicar_rodape(embed)

        view = ConfirmarAcaoView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.mensagem = await interaction.original_response()
        await view.wait()
        if not view.confirmado:
            return await view.interacao_resposta.response.edit_message(
                content="❌ Ação cancelada.", embed=None, view=None
            ) if view.interacao_resposta else None

        try:
            await membro.send(f"⏳ Você foi banido temporariamente de **{interaction.guild.name}** por {formatar_duracao(segundos)}.\n📝 Motivo: {motivo}")
        except discord.HTTPException:
            pass

        await interaction.guild.ban(membro, reason=f"{tag(interaction.user)}: {motivo} (temp: {formatar_duracao(segundos)})", delete_message_seconds=0)
        caso = registrar_caso(interaction.guild.id, "tempban", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo, segundos)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        self.bot.loop.create_task(self._agendar_unban(interaction.guild.id, membro.id, segundos, caso["id"]))

        resultado = discord.Embed(description=f"✅ **{membro.mention}** banido por {formatar_duracao(segundos)}. Caso `#{caso['id']}`.", color=0x2ECC71)
        aplicar_rodape(resultado)
        await view.interacao_resposta.response.edit_message(embed=resultado, view=None)

    async def _agendar_unban(self, guild_id: int, user_id: int, segundos: int, caso_id: int):
        import asyncio
        await asyncio.sleep(segundos)
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        try:
            await guild.unban(discord.Object(id=user_id), reason=f"Ban temporário expirado (caso #{caso_id})")
            desativar_casos_ativos(guild_id, user_id, ["tempban"])
        except discord.HTTPException:
            pass

    @app_commands.command(name="unban", description="Remove o banimento de um usuário pelo ID")
    @app_commands.describe(user_id="ID do usuário a desbanir", motivo="Motivo do desbanimento")
    @checar_permissao("ban_members")
    async def unban(self, interaction: discord.Interaction, user_id: str, motivo: str = "Não especificado"):
        if not user_id.isdigit():
            return await interaction.response.send_message("❌ Informe um ID de usuário válido.", ephemeral=True)

        try:
            usuario = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(usuario, reason=f"{tag(interaction.user)}: {motivo}")
        except discord.NotFound:
            return await interaction.response.send_message("❌ Esse usuário não está banido ou não existe.", ephemeral=True)

        desativar_casos_ativos(interaction.guild.id, int(user_id), ["ban", "tempban"])
        caso = registrar_caso(interaction.guild.id, "unban", int(user_id), tag(usuario), interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        embed = discord.Embed(description=f"✅ **{tag(usuario)}** foi desbanido. Caso `#{caso['id']}`.", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kick", description="Expulsa um membro do servidor")
    @app_commands.describe(membro="Membro a ser expulso", motivo="Motivo da expulsão")
    @checar_permissao("kick_members")
    async def kick(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não especificado"):
        ok, erro = pode_moderar(interaction.user, membro, interaction.guild.me)
        if not ok:
            return await interaction.response.send_message(erro, ephemeral=True)

        embed = discord.Embed(
            title="👢 Confirmar Expulsão",
            description=f"Expulsar **{membro.mention}** do servidor?",
            color=0xE67E22,
        )
        embed.add_field(name="📝 Motivo", value=motivo, inline=False)
        aplicar_rodape(embed)

        view = ConfirmarAcaoView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.mensagem = await interaction.original_response()
        await view.wait()
        if not view.confirmado:
            return await view.interacao_resposta.response.edit_message(
                content="❌ Expulsão cancelada.", embed=None, view=None
            ) if view.interacao_resposta else None

        try:
            await membro.send(f"👢 Você foi expulso de **{interaction.guild.name}**.\n📝 Motivo: {motivo}")
        except discord.HTTPException:
            pass

        await membro.kick(reason=f"{tag(interaction.user)}: {motivo}")
        caso = registrar_caso(interaction.guild.id, "kick", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        resultado = discord.Embed(description=f"✅ **{tag(membro)}** foi expulso. Caso `#{caso['id']}`.", color=0x2ECC71)
        aplicar_rodape(resultado)
        await view.interacao_resposta.response.edit_message(embed=resultado, view=None)

    # ── MUTE (cargo dedicado, diferente de timeout nativo) ──────

    async def _get_or_create_cargo_mutado(self, guild: discord.Guild) -> discord.Role:
        config = load_mod_config()
        gconf = get_guild_mod_config(config, guild.id)
        cargo_id = gconf.get("cargo_mutado_id")
        if cargo_id:
            cargo = guild.get_role(cargo_id)
            if cargo:
                return cargo

        cargo = await guild.create_role(name="Mutado", color=discord.Color.dark_gray(), reason="Cargo de mute criado automaticamente pelo ZyntraX")
        for canal in guild.channels:
            try:
                if isinstance(canal, discord.TextChannel):
                    await canal.set_permissions(cargo, send_messages=False, add_reactions=False)
                elif isinstance(canal, discord.VoiceChannel):
                    await canal.set_permissions(cargo, speak=False)
            except discord.HTTPException:
                continue

        gconf["cargo_mutado_id"] = cargo.id
        save_mod_config(config)
        return cargo

    @app_commands.command(name="mute", description="Silencia um membro indefinidamente (cargo de mute)")
    @app_commands.describe(membro="Membro a silenciar", motivo="Motivo do mute")
    @checar_permissao("moderate_members")
    async def mute(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não especificado"):
        ok, erro = pode_moderar(interaction.user, membro, interaction.guild.me)
        if not ok:
            return await interaction.response.send_message(erro, ephemeral=True)

        await interaction.response.defer(ephemeral=False)
        cargo = await self._get_or_create_cargo_mutado(interaction.guild)
        if cargo in membro.roles:
            return await interaction.followup.send("❌ Esse membro já está mutado.", ephemeral=True)

        await membro.add_roles(cargo, reason=f"{tag(interaction.user)}: {motivo}")
        caso = registrar_caso(interaction.guild.id, "mute", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        embed = discord.Embed(description=f"🔇 **{membro.mention}** foi mutado. Caso `#{caso['id']}`.", color=0xF1C40F)
        embed.add_field(name="📝 Motivo", value=motivo)
        aplicar_rodape(embed)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tempmute", description="Silencia um membro por tempo determinado")
    @app_commands.describe(membro="Membro a silenciar", duracao="Ex: 30m, 2h, 1d", motivo="Motivo do mute")
    @checar_permissao("moderate_members")
    async def tempmute(self, interaction: discord.Interaction, membro: discord.Member, duracao: str, motivo: str = "Não especificado"):
        ok, erro = pode_moderar(interaction.user, membro, interaction.guild.me)
        if not ok:
            return await interaction.response.send_message(erro, ephemeral=True)

        segundos = parse_duracao(duracao)
        if segundos is None:
            return await interaction.response.send_message("❌ Duração inválida. Use algo como `30m`, `2h`, `1d`.", ephemeral=True)

        await interaction.response.defer(ephemeral=False)
        cargo = await self._get_or_create_cargo_mutado(interaction.guild)
        if cargo in membro.roles:
            return await interaction.followup.send("❌ Esse membro já está mutado.", ephemeral=True)

        await membro.add_roles(cargo, reason=f"{tag(interaction.user)}: {motivo}")
        caso = registrar_caso(interaction.guild.id, "mute", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo, segundos)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)
        self.bot.loop.create_task(self._agendar_unmute(interaction.guild.id, membro.id, segundos))

        embed = discord.Embed(description=f"🔇 **{membro.mention}** mutado por {formatar_duracao(segundos)}. Caso `#{caso['id']}`.", color=0xF1C40F)
        aplicar_rodape(embed)
        await interaction.followup.send(embed=embed)

    async def _agendar_unmute(self, guild_id: int, user_id: int, segundos: int):
        import asyncio
        await asyncio.sleep(segundos)
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        membro = guild.get_member(user_id)
        config = load_mod_config()
        gconf = get_guild_mod_config(config, guild_id)
        cargo_id = gconf.get("cargo_mutado_id")
        if membro and cargo_id:
            cargo = guild.get_role(cargo_id)
            if cargo and cargo in membro.roles:
                try:
                    await membro.remove_roles(cargo, reason="Mute temporário expirado")
                except discord.HTTPException:
                    pass
        desativar_casos_ativos(guild_id, user_id, ["mute"])

    @app_commands.command(name="unmute", description="Remove o silenciamento de um membro")
    @app_commands.describe(membro="Membro a desmutar", motivo="Motivo")
    @checar_permissao("moderate_members")
    async def unmute(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não especificado"):
        config = load_mod_config()
        gconf = get_guild_mod_config(config, interaction.guild.id)
        cargo_id = gconf.get("cargo_mutado_id")
        cargo = interaction.guild.get_role(cargo_id) if cargo_id else None

        if not cargo or cargo not in membro.roles:
            return await interaction.response.send_message("❌ Esse membro não está mutado.", ephemeral=True)

        await membro.remove_roles(cargo, reason=f"{tag(interaction.user)}: {motivo}")
        desativar_casos_ativos(interaction.guild.id, membro.id, ["mute"])
        caso = registrar_caso(interaction.guild.id, "unmute", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        embed = discord.Embed(description=f"🔊 **{membro.mention}** foi desmutado. Caso `#{caso['id']}`.", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    # ── TIMEOUT (nativo do Discord) ──────────────────────────────

    @app_commands.command(name="timeout", description="Coloca um membro em timeout (silêncio nativo do Discord)")
    @app_commands.describe(membro="Membro", duracao="Ex: 10m, 1h, 1d (máx. 28d)", motivo="Motivo")
    @checar_permissao("moderate_members")
    async def timeout(self, interaction: discord.Interaction, membro: discord.Member, duracao: str, motivo: str = "Não especificado"):
        ok, erro = pode_moderar(interaction.user, membro, interaction.guild.me)
        if not ok:
            return await interaction.response.send_message(erro, ephemeral=True)

        segundos = parse_duracao(duracao)
        if segundos is None or segundos > 28 * 86400:
            return await interaction.response.send_message("❌ Duração inválida (máximo 28 dias).", ephemeral=True)

        import datetime
        await membro.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=segundos), reason=f"{tag(interaction.user)}: {motivo}")
        caso = registrar_caso(interaction.guild.id, "timeout", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo, segundos)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        embed = discord.Embed(description=f"⏱️ **{membro.mention}** em timeout por {formatar_duracao(segundos)}. Caso `#{caso['id']}`.", color=0xF1C40F)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="untimeout", description="Remove o timeout de um membro")
    @app_commands.describe(membro="Membro", motivo="Motivo")
    @checar_permissao("moderate_members")
    async def untimeout(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não especificado"):
        if not membro.is_timed_out():
            return await interaction.response.send_message("❌ Esse membro não está em timeout.", ephemeral=True)

        await membro.timeout(None, reason=f"{tag(interaction.user)}: {motivo}")
        desativar_casos_ativos(interaction.guild.id, membro.id, ["timeout"])
        caso = registrar_caso(interaction.guild.id, "untimeout", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        embed = discord.Embed(description=f"✅ Timeout de **{membro.mention}** removido. Caso `#{caso['id']}`.", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    # ═════════════════════════════════════════════════════════════
    # ⚠️ ADVERTÊNCIAS
    # ═════════════════════════════════════════════════════════════

    @app_commands.command(name="warn", description="Aplica uma advertência a um membro")
    @app_commands.describe(membro="Membro", motivo="Motivo da advertência")
    @checar_permissao("kick_members")
    async def warn(self, interaction: discord.Interaction, membro: discord.Member, motivo: str):
        ok, erro = pode_moderar(interaction.user, membro, interaction.guild.me)
        if not ok:
            return await interaction.response.send_message(erro, ephemeral=True)

        caso = registrar_caso(interaction.guild.id, "warn", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo)
        total = len([c for c in get_casos_membro(interaction.guild.id, membro.id) if c["tipo"] == "warn" and c["ativo"]])
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        try:
            await membro.send(f"⚠️ Você recebeu uma advertência em **{interaction.guild.name}**.\n📝 Motivo: {motivo}\n📊 Total de advertências ativas: {total}")
        except discord.HTTPException:
            pass

        embed = discord.Embed(description=f"⚠️ **{membro.mention}** advertido. Caso `#{caso['id']}` — {total} advertência(s) ativa(s).", color=0xF39C12)
        embed.add_field(name="📝 Motivo", value=motivo)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unwarn", description="Remove uma advertência específica pelo número do caso")
    @app_commands.describe(caso_id="Número do caso da advertência")
    @checar_permissao("kick_members")
    async def unwarn(self, interaction: discord.Interaction, caso_id: int):
        caso = get_caso(interaction.guild.id, caso_id)
        if not caso or caso["tipo"] != "warn":
            return await interaction.response.send_message("❌ Caso de advertência não encontrado.", ephemeral=True)

        caso["ativo"] = False
        from cogs._utils_moderacao import load_casos, save_casos
        data = load_casos()
        for c in data[str(interaction.guild.id)]["casos"]:
            if c["id"] == caso_id:
                c["ativo"] = False
        save_casos(data)

        embed = discord.Embed(description=f"✅ Advertência `#{caso_id}` removida.", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warnings", description="Mostra as advertências ativas de um membro")
    @app_commands.describe(membro="Membro")
    @checar_permissao("kick_members")
    async def warnings(self, interaction: discord.Interaction, membro: discord.Member):
        casos = [c for c in get_casos_membro(interaction.guild.id, membro.id) if c["tipo"] == "warn" and c["ativo"]]
        embed = discord.Embed(title=f"⚠️ Advertências de {tag(membro)}", color=0xF39C12)
        if not casos:
            embed.description = "Nenhuma advertência ativa."
        else:
            for c in casos[-10:]:
                embed.add_field(
                    name=f"Caso #{c['id']} — <t:{c['timestamp']}:R>",
                    value=f"📝 {c['motivo']}\n🛡️ Por: {c['moderador_tag']}",
                    inline=False,
                )
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="history", description="Mostra o histórico completo de punições de um membro")
    @app_commands.describe(membro="Membro")
    @checar_permissao("kick_members")
    async def history(self, interaction: discord.Interaction, membro: discord.Member):
        casos = get_casos_membro(interaction.guild.id, membro.id)
        embed = discord.Embed(title=f"📋 Histórico de {tag(membro)}", color=0x7289DA)
        if not casos:
            embed.description = "Nenhuma ação de moderação registrada."
        else:
            for c in casos[-15:]:
                status = "🟢 Ativo" if c["ativo"] else "⚪ Encerrado"
                embed.add_field(
                    name=f"Caso #{c['id']} — {c['tipo'].upper()} ({status})",
                    value=f"📝 {c['motivo']}\n🛡️ {c['moderador_tag']} • <t:{c['timestamp']}:R>",
                    inline=False,
                )
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    # ═════════════════════════════════════════════════════════════
    # 🚨 MODERAÇÃO RÁPIDA DE MENSAGENS E CANAIS
    # ═════════════════════════════════════════════════════════════

    @app_commands.command(name="clear", description="Apaga uma quantidade de mensagens do canal")
    @app_commands.describe(quantidade="Quantidade de mensagens a apagar (1-100)")
    @checar_permissao("manage_messages")
    async def clear(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        apagadas = await interaction.channel.purge(limit=quantidade)
        caso = registrar_caso(interaction.guild.id, "clear", interaction.channel.id, interaction.channel.name, interaction.user.id, tag(interaction.user), f"{len(apagadas)} mensagens")
        await enviar_log_moderacao(self.bot, interaction.guild, caso, extra_desc=f"Canal: {interaction.channel.mention}")
        await interaction.followup.send(f"🧹 {len(apagadas)} mensagem(ns) apagada(s).", ephemeral=True)

    @app_commands.command(name="purge", description="Limpeza avançada de mensagens com filtros")
    @app_commands.describe(
        quantidade="Quantidade de mensagens a analisar (1-200)",
        membro="Apagar só mensagens desse membro (opcional)",
        contem="Apagar só mensagens que contenham esse texto (opcional)",
        apenas_bots="Apagar só mensagens de bots (opcional)",
    )
    @checar_permissao("manage_messages")
    async def purge(
        self, interaction: discord.Interaction,
        quantidade: app_commands.Range[int, 1, 200],
        membro: discord.Member = None,
        contem: str = None,
        apenas_bots: bool = False,
    ):
        await interaction.response.defer(ephemeral=True)

        def checar(msg: discord.Message) -> bool:
            if membro and msg.author.id != membro.id:
                return False
            if contem and contem.lower() not in msg.content.lower():
                return False
            if apenas_bots and not msg.author.bot:
                return False
            return True

        apagadas = await interaction.channel.purge(limit=quantidade, check=checar)
        filtros = []
        if membro:
            filtros.append(f"membro: {tag(membro)}")
        if contem:
            filtros.append(f"contém: '{contem}'")
        if apenas_bots:
            filtros.append("apenas bots")
        motivo = f"{len(apagadas)} mensagens" + (f" ({', '.join(filtros)})" if filtros else "")

        caso = registrar_caso(interaction.guild.id, "purge", interaction.channel.id, interaction.channel.name, interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso, extra_desc=f"Canal: {interaction.channel.mention}")
        await interaction.followup.send(f"🧹 {len(apagadas)} mensagem(ns) apagada(s) com os filtros aplicados.", ephemeral=True)

    @app_commands.command(name="lock", description="Bloqueia o canal atual (ou outro) para @everyone")
    @app_commands.describe(canal="Canal a bloquear (padrão: canal atual)", motivo="Motivo")
    @checar_permissao("manage_channels")
    async def lock(self, interaction: discord.Interaction, canal: discord.TextChannel = None, motivo: str = "Não especificado"):
        canal = canal or interaction.channel
        await canal.set_permissions(interaction.guild.default_role, send_messages=False, reason=f"{tag(interaction.user)}: {motivo}")
        caso = registrar_caso(interaction.guild.id, "lock", canal.id, canal.name, interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        embed = discord.Embed(description=f"🔒 {canal.mention} foi bloqueado.", color=0x992D22)
        embed.add_field(name="📝 Motivo", value=motivo)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unlock", description="Desbloqueia o canal atual (ou outro) para @everyone")
    @app_commands.describe(canal="Canal a desbloquear (padrão: canal atual)")
    @checar_permissao("manage_channels")
    async def unlock(self, interaction: discord.Interaction, canal: discord.TextChannel = None):
        canal = canal or interaction.channel
        await canal.set_permissions(interaction.guild.default_role, send_messages=None, reason=f"{tag(interaction.user)}: unlock")
        caso = registrar_caso(interaction.guild.id, "unlock", canal.id, canal.name, interaction.user.id, tag(interaction.user), "Desbloqueio manual")
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        embed = discord.Embed(description=f"🔓 {canal.mention} foi desbloqueado.", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lockdown", description="Bloqueia todos os canais de texto do servidor")
    @app_commands.describe(motivo="Motivo do lockdown geral")
    @checar_permissao("manage_channels")
    async def lockdown(self, interaction: discord.Interaction, motivo: str = "Não especificado"):
        await interaction.response.defer()
        contagem = 0
        for canal in interaction.guild.text_channels:
            try:
                await canal.set_permissions(interaction.guild.default_role, send_messages=False, reason=f"Lockdown geral: {tag(interaction.user)}")
                contagem += 1
            except discord.HTTPException:
                continue

        caso = registrar_caso(interaction.guild.id, "lock", interaction.guild.id, "TODO O SERVIDOR", interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso, extra_desc=f"{contagem} canais bloqueados")

        embed = discord.Embed(description=f"🔒 Lockdown ativado em {contagem} canal(is).", color=0x992D22)
        aplicar_rodape(embed)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="unlockdown", description="Desbloqueia todos os canais de texto do servidor")
    @checar_permissao("manage_channels")
    async def unlockdown(self, interaction: discord.Interaction):
        await interaction.response.defer()
        contagem = 0
        for canal in interaction.guild.text_channels:
            try:
                await canal.set_permissions(interaction.guild.default_role, send_messages=None, reason=f"Fim do lockdown: {tag(interaction.user)}")
                contagem += 1
            except discord.HTTPException:
                continue

        embed = discord.Embed(description=f"🔓 Lockdown removido de {contagem} canal(is).", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="slowmode", description="Define o modo lento de um canal")
    @app_commands.describe(segundos="Intervalo em segundos (0 desativa)", canal="Canal (padrão: canal atual)")
    @checar_permissao("manage_channels")
    async def slowmode(self, interaction: discord.Interaction, segundos: app_commands.Range[int, 0, 21600], canal: discord.TextChannel = None):
        canal = canal or interaction.channel
        await canal.edit(slowmode_delay=segundos, reason=f"{tag(interaction.user)}: slowmode")

        caso = registrar_caso(interaction.guild.id, "slowmode", canal.id, canal.name, interaction.user.id, tag(interaction.user), f"{segundos}s")
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        texto = "desativado" if segundos == 0 else f"definido para {segundos}s"
        embed = discord.Embed(description=f"🐌 Modo lento de {canal.mention} {texto}.", color=0x3498DB)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    # ═════════════════════════════════════════════════════════════
    # 👤 GERENCIAMENTO DE MEMBROS
    # ═════════════════════════════════════════════════════════════

    @app_commands.command(name="role", description="Adiciona ou remove um cargo de um membro")
    @app_commands.describe(membro="Membro", cargo="Cargo a alternar")
    @checar_permissao("manage_roles")
    async def role(self, interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
        if cargo >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Meu cargo precisa estar acima desse cargo.", ephemeral=True)
        if interaction.user.id != interaction.guild.owner_id and cargo >= interaction.user.top_role:
            return await interaction.response.send_message("❌ Você não pode gerenciar um cargo igual ou superior ao seu.", ephemeral=True)

        if cargo in membro.roles:
            await membro.remove_roles(cargo, reason=f"{tag(interaction.user)}: /role")
            acao, cor = "removido de", 0xE74C3C
        else:
            await membro.add_roles(cargo, reason=f"{tag(interaction.user)}: /role")
            acao, cor = "adicionado a", 0x2ECC71

        caso = registrar_caso(interaction.guild.id, "role", membro.id, tag(membro), interaction.user.id, tag(interaction.user), f"Cargo {cargo.name} {acao.split()[0]}")
        await enviar_log_moderacao(self.bot, interaction.guild, caso)

        embed = discord.Embed(description=f"🎭 Cargo {cargo.mention} {acao} **{membro.mention}**.", color=cor)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    # ═════════════════════════════════════════════════════════════
    # 🔎 INVESTIGAÇÃO
    # ═════════════════════════════════════════════════════════════

    @app_commands.command(name="userinfo", description="Mostra informações detalhadas de um membro")
    @app_commands.describe(membro="Membro (padrão: você mesmo)")
    async def userinfo(self, interaction: discord.Interaction, membro: discord.Member = None):
        membro = membro or interaction.user
        cargos = [r.mention for r in reversed(membro.roles) if r.name != "@everyone"]

        embed = discord.Embed(title=f"👤 {tag(membro)}", color=membro.color if membro.color.value else 0x7289DA)
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="🆔 ID", value=membro.id, inline=True)
        embed.add_field(name="📅 Conta criada", value=f"<t:{int(membro.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="📥 Entrou em", value=f"<t:{int(membro.joined_at.timestamp())}:R>" if membro.joined_at else "Desconhecido", inline=True)
        embed.add_field(name=f"🎭 Cargos ({len(cargos)})", value=" ".join(cargos[:15]) if cargos else "Nenhum", inline=False)
        if membro.is_timed_out():
            embed.add_field(name="⏱️ Timeout até", value=f"<t:{int(membro.timed_out_until.timestamp())}:R>", inline=True)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Mostra informações do servidor")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"🏠 {guild.name}", color=0x7289DA)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Dono", value=f"<@{guild.owner_id}>", inline=True)
        embed.add_field(name="👥 Membros", value=guild.member_count, inline=True)
        embed.add_field(name="📅 Criado em", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="🎭 Cargos", value=len(guild.roles), inline=True)
        embed.add_field(name="📁 Canais", value=len(guild.channels), inline=True)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Mostra o avatar de um membro")
    @app_commands.describe(membro="Membro (padrão: você mesmo)")
    async def avatar(self, interaction: discord.Interaction, membro: discord.Member = None):
        membro = membro or interaction.user
        embed = discord.Embed(title=f"🖼️ Avatar de {tag(membro)}", color=0x7289DA)
        embed.set_image(url=membro.display_avatar.url)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="banner", description="Mostra o banner de um membro")
    @app_commands.describe(membro="Membro (padrão: você mesmo)")
    async def banner(self, interaction: discord.Interaction, membro: discord.Member = None):
        membro = membro or interaction.user
        usuario = await self.bot.fetch_user(membro.id)
        if not usuario.banner:
            return await interaction.response.send_message("❌ Esse membro não tem banner definido.", ephemeral=True)

        embed = discord.Embed(title=f"🖼️ Banner de {tag(membro)}", color=0x7289DA)
        embed.set_image(url=usuario.banner.url)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="case", description="Consulta uma punição específica pelo número do caso")
    @app_commands.describe(caso_id="Número do caso")
    @checar_permissao("kick_members")
    async def case(self, interaction: discord.Interaction, caso_id: int):
        caso = get_caso(interaction.guild.id, caso_id)
        if not caso:
            return await interaction.response.send_message("❌ Caso não encontrado.", ephemeral=True)

        embed = discord.Embed(title=f"📋 Caso #{caso['id']} — {caso['tipo'].upper()}", color=0x7289DA)
        embed.add_field(name="👤 Alvo", value=f"{caso['alvo_tag']} (`{caso['alvo_id']}`)", inline=True)
        embed.add_field(name="🛡️ Moderador", value=f"{caso['moderador_tag']}", inline=True)
        embed.add_field(name="📊 Status", value="🟢 Ativo" if caso["ativo"] else "⚪ Encerrado", inline=True)
        embed.add_field(name="📝 Motivo", value=caso["motivo"], inline=False)
        embed.add_field(name="🕐 Data", value=f"<t:{caso['timestamp']}:F>", inline=False)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="modlogs", description="Lista os casos de moderação mais recentes do servidor")
    @app_commands.describe(quantidade="Quantos casos mostrar (padrão 10)")
    @checar_permissao("kick_members")
    async def modlogs(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 25] = 10):
        casos = get_casos_recentes(interaction.guild.id, quantidade)
        embed = discord.Embed(title="📊 Últimos Casos de Moderação", color=0x7289DA)
        if not casos:
            embed.description = "Nenhum caso registrado ainda."
        else:
            for c in casos:
                status = "🟢" if c["ativo"] else "⚪"
                embed.add_field(
                    name=f"{status} #{c['id']} — {c['tipo'].upper()}",
                    value=f"Alvo: {c['alvo_tag']} • Por: {c['moderador_tag']} • <t:{c['timestamp']}:R>",
                    inline=False,
                )
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    # ═════════════════════════════════════════════════════════════
    # ⭐ EXTRAS: DENÚNCIAS
    # ═════════════════════════════════════════════════════════════

    @app_commands.command(name="report", description="Denuncia um membro para a staff analisar")
    @app_commands.describe(membro="Membro denunciado", motivo="Descreva o que aconteceu")
    async def report(self, interaction: discord.Interaction, membro: discord.Member, motivo: str):
        caso = registrar_caso(interaction.guild.id, "report", membro.id, tag(membro), interaction.user.id, tag(interaction.user), motivo)
        await enviar_log_moderacao(self.bot, interaction.guild, caso, extra_desc="📨 Nova denúncia recebida — aguardando análise da staff.")

        embed = discord.Embed(description="✅ Sua denúncia foi enviada para a staff. Obrigado por ajudar a manter o servidor seguro.", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ═════════════════════════════════════════════════════════════
    # ⚙️ CONFIGURAÇÃO DE PERMISSÕES (quem pode usar os comandos acima)
    # ═════════════════════════════════════════════════════════════

    permissoes_group = app_commands.Group(name="permissoes", description="Gerencia quais cargos têm acesso aos comandos de moderação")

    @permissoes_group.command(name="adicionar", description="Adiciona um cargo à whitelist de staff de moderação")
    @app_commands.describe(cargo="Cargo que poderá usar todos os comandos de moderação")
    @app_commands.checks.has_permissions(administrator=True)
    async def permissoes_adicionar(self, interaction: discord.Interaction, cargo: discord.Role):
        roles = get_staff_roles(interaction.guild.id)
        if cargo.id in roles:
            return await interaction.response.send_message("❌ Esse cargo já está na whitelist de staff.", ephemeral=True)
        roles.append(cargo.id)
        set_staff_roles(interaction.guild.id, roles)

        embed = discord.Embed(description=f"✅ {cargo.mention} agora pode usar os comandos de moderação.", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @permissoes_group.command(name="remover", description="Remove um cargo da whitelist de staff de moderação")
    @app_commands.describe(cargo="Cargo a remover da whitelist")
    @app_commands.checks.has_permissions(administrator=True)
    async def permissoes_remover(self, interaction: discord.Interaction, cargo: discord.Role):
        roles = get_staff_roles(interaction.guild.id)
        if cargo.id not in roles:
            return await interaction.response.send_message("❌ Esse cargo não está na whitelist de staff.", ephemeral=True)
        roles.remove(cargo.id)
        set_staff_roles(interaction.guild.id, roles)

        embed = discord.Embed(description=f"✅ {cargo.mention} não tem mais acesso automático aos comandos de moderação.", color=0x2ECC71)
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed)

    @permissoes_group.command(name="listar", description="Lista os cargos com acesso aos comandos de moderação")
    @app_commands.checks.has_permissions(administrator=True)
    async def permissoes_listar(self, interaction: discord.Interaction):
        roles = get_staff_roles(interaction.guild.id)
        mencoes = [f"<@&{r}>" for r in roles if interaction.guild.get_role(r)]
        embed = discord.Embed(
            title="🛡️ Cargos de Staff (Moderação)",
            description="\n".join(mencoes) if mencoes else "Nenhum cargo configurado — apenas Administradores e quem já possui a permissão nativa do Discord podem usar os comandos.",
            color=0x7289DA,
        )
        aplicar_rodape(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModeracaoComandos(bot))
