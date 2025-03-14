# welcome_cog.py
# Description: Cog para gerenciar boas-vindas de novos membros
# Date of Creation: 12/03/2025
# Created by: CodeProjects
# Modified by: CodeProjects
# Date of Modification: 12/03/2025
# Reason of Modification: Implementação inicial
# Version: 1.0
# Developer Of Version: CodeProjects and RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
import os
import json

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data"

    # Garante que a pasta do servidor exista
    def ensure_guild_directory(self, guild_id: str):
        guild_dir = os.path.join(self.data_dir, guild_id)
        if not os.path.exists(guild_dir):
            os.makedirs(guild_dir)

    # Carrega a configuração de boas-vindas do servidor
    def load_config(self, guild_id: str):
        self.ensure_guild_directory(guild_id)
        config_file = os.path.join(self.data_dir, guild_id, "welcome_config.json")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                return json.load(f)
        return {}

    # Salva a configuração de boas-vindas do servidor
    def save_config(self, guild_id: str, config: dict):
        self.ensure_guild_directory(guild_id)
        config_file = os.path.join(self.data_dir, guild_id, "welcome_config.json")
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)

    # Evento de entrada de membro
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = str(member.guild.id)
        config = self.load_config(guild_id)

        role_id = config.get("role_id")
        channel_id = config.get("channel_id")

        # Atribui o cargo ao membro
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role, reason="Cargo de boas-vindas configurado.")

        # Envia mensagem no canal de boas-vindas
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                welcome_message = f"Bem-vindo(a) ao servidor, {member.mention}! 🎉"
                await channel.send(welcome_message)

        # Envia mensagem na DM do membro
        try:
            dm_message = (
                f"Olá {member.name}, bem-vindo(a) ao servidor **{member.guild.name}**! 🎉\n"
                f"Esperamos que você se divirta e participe ativamente!"
            )
            await member.send(dm_message)
        except nextcord.Forbidden:
            print(f"Não foi possível enviar mensagem privada para {member.name}.")

    # Comando slash para configurar o sistema de boas-vindas
    @nextcord.slash_command(
        name="config_welcome",
        description="Configure o sistema de boas-vindas."
    )
    async def config_welcome(
        self,
        interaction: Interaction,
        role: nextcord.Role = SlashOption(description="Cargo a ser atribuído aos novos membros"),
        channel: nextcord.TextChannel = SlashOption(description="Canal onde as mensagens serão enviadas")
    ):
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)

        config["role_id"] = role.id
        config["channel_id"] = channel.id
        self.save_config(guild_id, config)

        await interaction.response.send_message(
            f"Sistema de boas-vindas configurado!\n"
            f"Cargo: {role.mention}\n"
            f"Canal: {channel.mention}",
            ephemeral=True
        )

def setup(bot):
    bot.add_cog(WelcomeCog(bot))