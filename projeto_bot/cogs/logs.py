import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

CONFIG_FILE = "config/logs_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"logs": {}, "authorized_users": {}}

def save_config(data):
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class LogTypeSelect(discord.ui.Select):
    def __init__(self, canal_id):
        self.canal_id = canal_id
        options = [
            discord.SelectOption(label="🗑️ Mensagens Deletadas", value="deletadas"),
            discord.SelectOption(label="✏️ Mensagens Editadas", value="editadas"),
            discord.SelectOption(label="⛔ Membros Banidos", value="bans"),
            discord.SelectOption(label="👋 Membros Saem", value="membros"),
        ]
        super().__init__(placeholder="Selecione os tipos de log", options=options, min_values=1, max_values=4)
    
    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild_id)
        
        if guild_id not in config["logs"]:
            config["logs"][guild_id] = {}
        
        config["logs"][guild_id][self.canal_id] = self.values
        save_config(config)
        
        embed = discord.Embed(
            title="✅ Canal Configurado",
            description=f"Canal <#{self.canal_id}> configurado com sucesso!",
            color=discord.Color.green()
        )
        embed.add_field(name="Tipos de Log", value=", ".join(self.values), inline=False)
        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LogTypeView(discord.ui.View):
    def __init__(self, canal_id):
        super().__init__()
        self.add_item(LogTypeSelect(canal_id))

class ChannelSelect(discord.ui.Select):
    def __init__(self, guild):
        self.guild = guild
        options = []
        
        for canal in guild.text_channels:
            if canal.permissions_for(guild.me).send_messages:
                options.append(
                    discord.SelectOption(label=canal.name, value=str(canal.id), emoji="💬")
                )
        
        super().__init__(placeholder="Selecione um canal para logs", options=options[:25])
    
    async def callback(self, interaction: discord.Interaction):
        canal_id = self.values[0]
        embed = discord.Embed(
            title="📋 Selecione os Tipos de Log",
            description="Escolha quais eventos serão registrados neste canal",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
        
        view = LogTypeView(canal_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self, guild):
        super().__init__()
        self.add_item(ChannelSelect(guild))

class MemberSelect(discord.ui.Select):
    def __init__(self, guild, action="auth"):
        self.action = action
        options = []
        
        for member in guild.members[:25]:
            if not member.bot:
                options.append(
                    discord.SelectOption(label=member.name, value=str(member.id), emoji="👤")
                )
        
        placeholder = "Selecione um membro para autorizar" if action == "auth" else "Selecione um membro para remover"
        super().__init__(placeholder=placeholder, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild_id)
        member_id = self.values[0]
        
        if guild_id not in config["authorized_users"]:
            config["authorized_users"][guild_id] = []
        
        if self.action == "auth":
            if member_id not in config["authorized_users"][guild_id]:
                config["authorized_users"][guild_id].append(member_id)
                save_config(config)
                embed = discord.Embed(
                    title="✅ Membro Autorizado",
                    description=f"<@{member_id}> agora pode configurar logs",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Já Autorizado",
                    description=f"<@{member_id}> já tem permissão",
                    color=discord.Color.yellow()
                )
        else:
            if member_id in config["authorized_users"][guild_id]:
                config["authorized_users"][guild_id].remove(member_id)
                save_config(config)
                embed = discord.Embed(
                    title="✅ Removido",
                    description=f"<@{member_id}> não pode mais configurar logs",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Não Autorizado",
                    description=f"<@{member_id}> não estava autorizado",
                    color=discord.Color.yellow()
                )
        
        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class MemberSelectView(discord.ui.View):
    def __init__(self, guild, action="auth"):
        super().__init__()
        self.add_item(MemberSelect(guild, action))

class LogsView(discord.ui.View):
    def __init__(self, guild):
        super().__init__()
        self.guild = guild
    
    @discord.ui.button(label="📋 Configurar Canal", style=discord.ButtonStyle.primary)
    async def config_canal(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📌 Selecione um Canal",
            description="Escolha o canal onde os logs serão enviados",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
        
        view = ChannelSelectView(self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="👤 Autorizar Membro", style=discord.ButtonStyle.success)
    async def auth_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👤 Selecione um Membro",
            description="Escolha qual membro pode configurar logs",
            color=discord.Color.green()
        )
        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
        
        view = MemberSelectView(self.guild, "auth")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🗑️ Remover Autorização", style=discord.ButtonStyle.danger)
    async def remove_auth(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🗑️ Remover Autorização",
            description="Escolha qual membro remover",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
        
        view = MemberSelectView(self.guild, "remove")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📊 Ver Configurações", style=discord.ButtonStyle.secondary)
    async def view_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        guild_config = config["logs"].get(str(interaction.guild_id), {})
        authorized = config["authorized_users"].get(str(interaction.guild_id), [])
        
        embed = discord.Embed(
            title="⚙️ Configurações Atuais",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if guild_config:
            for canal_id, tipos in guild_config.items():
                embed.add_field(
                    name=f"📌 Canal: <#{canal_id}>",
                    value=f"🎯 {', '.join(tipos)}",
                    inline=False
                )
        else:
            embed.add_field(name="Canais", value="Nenhum configurado", inline=False)
        
        if authorized:
            membros = ", ".join([f"<@{m}>" for m in authorized])
            embed.add_field(name="👥 Membros Autorizados", value=membros, inline=False)
        else:
            embed.add_field(name="👥 Membros Autorizados", value="Nenhum", inline=False)
        
        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="logs", description="Gerenciar sistema de logs")
    async def logs_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            embed = discord.Embed(
                title="❌ Sem Permissão",
                description="Apenas o dono pode usar isso",
                color=discord.Color.red()
            )
            embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 Painel de Logs",
            description="Configure os logs do seu servidor",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
        
        await interaction.response.send_message(embed=embed, view=LogsView(interaction.guild), ephemeral=True)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        
        config = load_config()
        guild_id = str(message.guild.id)
        
        if guild_id not in config["logs"]:
            return
        
        for canal_id, tipos in config["logs"][guild_id].items():
            if "deletadas" in tipos:
                try:
                    canal = self.bot.get_channel(int(canal_id))
                    if canal:
                        embed = discord.Embed(
                            title="🗑️ Mensagem Deletada",
                            color=discord.Color.red(),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="👤 Autor", value=message.author.mention, inline=False)
                        embed.add_field(name="💬 Conteúdo", value=message.content[:1024] or "Sem conteúdo", inline=False)
                        embed.add_field(name="📍 Canal", value=message.channel.mention, inline=True)
                        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
                        await canal.send(embed=embed)
                except:
                    pass
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content:
            return
        
        config = load_config()
        guild_id = str(before.guild.id)
        
        if guild_id not in config["logs"]:
            return
        
        for canal_id, tipos in config["logs"][guild_id].items():
            if "editadas" in tipos:
                try:
                    canal = self.bot.get_channel(int(canal_id))
                    if canal:
                        embed = discord.Embed(
                            title="✏️ Mensagem Editada",
                            color=discord.Color.yellow(),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="👤 Autor", value=before.author.mention, inline=False)
                        embed.add_field(name="📝 Antes", value=before.content[:1024], inline=False)
                        embed.add_field(name="📝 Depois", value=after.content[:1024], inline=False)
                        embed.add_field(name="📍 Canal", value=before.channel.mention, inline=True)
                        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
                        await canal.send(embed=embed)
                except:
                    pass
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        config = load_config()
        guild_id = str(guild.id)
        
        if guild_id not in config["logs"]:
            return
        
        for canal_id, tipos in config["logs"][guild_id].items():
            if "bans" in tipos:
                try:
                    canal = self.bot.get_channel(int(canal_id))
                    if canal:
                        embed = discord.Embed(
                            title="⛔ Membro Banido",
                            color=discord.Color.dark_red(),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="👤 Usuário", value=user.mention, inline=False)
                        embed.add_field(name="🏷️ ID", value=user.id, inline=True)
                        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
                        await canal.send(embed=embed)
                except:
                    pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = load_config()
        guild_id = str(member.guild.id)
        
        if guild_id not in config["logs"]:
            return
        
        for canal_id, tipos in config["logs"][guild_id].items():
            if "membros" in tipos:
                try:
                    canal = self.bot.get_channel(int(canal_id))
                    if canal:
                        embed = discord.Embed(
                            title="👋 Membro Saiu",
                            color=discord.Color.orange(),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="👤 Usuário", value=member.mention, inline=False)
                        embed.add_field(name="🏷️ ID", value=member.id, inline=True)
                        embed.set_footer(text="Sistema desenvolvido por Nix / Zyntrax Support")
                        await canal.send(embed=embed)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(Logs(bot))
