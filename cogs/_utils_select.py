import discord
from typing import Callable

class RoleSelectComAutocomplete(discord.ui.RoleSelect):
    """RoleSelect nativo do Discord com autocomplete automático"""
    def __init__(self, callback: Callable, min_values: int = 1, max_values: int = 1):
        self.user_callback = callback
        super().__init__(
            min_values=min_values,
            max_values=max_values,
            placeholder="🔍 Digite para filtrar cargos"
        )
    
    async def callback(self, interaction: discord.Interaction):
        for role in self.values:
            await self.user_callback(interaction, role.id)

class UserSelectComAutocomplete(discord.ui.UserSelect):
    """UserSelect nativo do Discord com busca digitando e escolhas ilimitadas"""
    def __init__(self, callback: Callable, min_values: int = 1, max_values: int = 1):
        self.user_callback = callback
        super().__init__(
            min_values=min_values,
            max_values=max_values,
            placeholder="🔍 Digite para buscar um membro"
        )

    async def callback(self, interaction: discord.Interaction):
        for user in self.values:
            await self.user_callback(interaction, user.id)

class ChannelSelectComAutocomplete(discord.ui.ChannelSelect):
    """ChannelSelect nativo do Discord com autocomplete automático"""
    def __init__(self, callback: Callable, min_values: int = 1, max_values: int = 1):
        self.user_callback = callback
        super().__init__(
            min_values=min_values,
            max_values=max_values,
            channel_types=[discord.ChannelType.text],
            placeholder="🔍 Digite para filtrar canais"
        )
    
    async def callback(self, interaction: discord.Interaction):
        for channel in self.values:
            await self.user_callback(interaction, channel.id)
