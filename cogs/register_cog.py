# register_cog.py
# Description: Cog para gerenciar o sistema de registro de membros
# Date of Creation: 14/03/2025
# Created by: CodeProjects
# Modified by: Grok (xAI) & CodeProjects
# Date of Modification: 19/03/2025
# Reason of Modification: Adição de personalização da embed com /person_register corrigido
# Version: 2.3
# Developer Of Version: Grok (xAI), CodeProjects, RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
import os
import json
from datetime import datetime

class RegisterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data"

    # Garante que a pasta do servidor exista
    def ensure_guild_directory(self, guild_id: str):
        guild_dir = os.path.join(self.data_dir, guild_id)
        if not os.path.exists(guild_dir):
            os.makedirs(guild_dir)

    # Carrega a configuração de registro do servidor
    def load_config(self, guild_id: str):
        self.ensure_guild_directory(guild_id)
        config_file = os.path.join(self.data_dir, guild_id, "register_config.json")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                return json.load(f)
        return {}

    # Salva a configuração de registro do servidor
    def save_config(self, guild_id: str, config: dict):
        self.ensure_guild_directory(guild_id)
        config_file = os.path.join(self.data_dir, guild_id, "register_config.json")
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)

    # Comando slash para configurar o sistema de registro
    @nextcord.slash_command(
        name="config_register",
        description="Configure o sistema de registro."
    )
    async def config_register(
        self,
        interaction: Interaction,
        role: nextcord.Role = SlashOption(description="Cargo a ser atribuído após o registro")
    ):
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)

        config["role_id"] = role.id
        self.save_config(guild_id, config)

        await interaction.response.send_message(
            f"Sistema de registro configurado!\n"
            f"Cargo de registro: {role.mention}",
            ephemeral=True
        )

    # Classe para o Modal de personalização da embed de registro
    class PersonalizeRegisterModal(nextcord.ui.Modal):
        def __init__(self, parent_cog):
            super().__init__("Personalizar Embed de Registro")
            self.parent_cog = parent_cog

            # Campos do modal
            self.embed_title = nextcord.ui.TextInput(
                label="Título da Embed",
                default_value="🚀 Bem-vindo ao Registro!",
                required=True,
                max_length=256
            )
            self.add_item(self.embed_title)

            self.embed_description = nextcord.ui.TextInput(
                label="Descrição da Embed",
                default_value=(
                    "Olá! Para liberar o acesso completo ao servidor, registre-se agora.\n"
                    "Aqui está tudo o que você precisa saber:\n\n"
                    "➜ **Passo Único:** Clique no botão abaixo para se registrar.\n"
                    "➜ **Benefícios:** Acesso aos canais principais e participação na comunidade!\n"
                    "➜ **Aviso:** Sem registro, seu acesso será limitado."
                ),
                required=True,
                max_length=2000,
                style=nextcord.TextInputStyle.paragraph
            )
            self.add_item(self.embed_description)

            self.embed_image_url = nextcord.ui.TextInput(
                label="URL da Imagem Principal",
                default_value="https://imgur.com/OiwK8ZC.png",
                required=False,
                max_length=500
            )
            self.add_item(self.embed_image_url)

            self.embed_thumbnail_url = nextcord.ui.TextInput(
                label="URL do Thumbnail",
                default_value="https://imgur.com/zH8pL7z.png",
                required=False,
                max_length=500
            )
            self.add_item(self.embed_thumbnail_url)

            self.embed_footer = nextcord.ui.TextInput(
                label="Texto do Footer",
                default_value="Sistema de Registro Automático - by CodeProjects",
                required=True,
                max_length=2048
            )
            self.add_item(self.embed_footer)

        async def callback(self, interaction: Interaction):
            guild_id = str(interaction.guild.id)
            config = self.parent_cog.load_config(guild_id)

            # Salva as configurações do modal no config
            config["embed_title"] = self.embed_title.value
            config["embed_description"] = self.embed_description.value
            config["embed_image_url"] = self.embed_image_url.value or ""
            config["embed_thumbnail_url"] = self.embed_thumbnail_url.value or ""
            config["embed_footer"] = self.embed_footer.value

            self.parent_cog.save_config(guild_id, config)

            await interaction.response.send_message(
                "Embed de registro personalizada com sucesso! Use /create_register_embed para aplicá-la.",
                ephemeral=True
            )

    # Comando slash para personalizar a embed de registro
    @nextcord.slash_command(
        name="person_register",
        description="Personalize a embed de registro do servidor."
    )
    async def person_register(self, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Você precisa ser administrador para usar este comando!",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(self.PersonalizeRegisterModal(self))

    # Comando slash para criar a embed com o botão de registro
    @nextcord.slash_command(
        name="create_register_embed",
        description="Cria uma embed com o botão de registro."
    )
    async def create_register_embed(
        self,
        interaction: Interaction,
        channel: nextcord.TextChannel = SlashOption(description="Canal onde a embed será enviada")
    ):
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)

        # Usa configurações personalizadas ou valores padrão
        embed_title = config.get("embed_title", "🚀 Bem-vindo ao Registro!")
        embed_description = config.get("embed_description", (
            "Olá! Para liberar o acesso completo ao servidor, registre-se agora.\n"
            "Aqui está tudo o que você precisa saber:\n\n"
            "➜ **Passo Único:** Clique no botão abaixo para se registrar.\n"
            "➜ **Benefícios:** Acesso aos canais principais e participação na comunidade!\n"
            "➜ **Aviso:** Sem registro, seu acesso será limitado."
        ))
        embed_image_url = config.get("embed_image_url", "https://imgur.com/OiwK8ZC.png")
        embed_thumbnail_url = config.get("embed_thumbnail_url", "https://imgur.com/zH8pL7z.png")
        embed_footer = config.get("embed_footer", "Sistema de Registro Automático - by CodeProjects")

        # Cor da embed (43, 45, 49 em RGB)
        embed_color = nextcord.Color.from_rgb(43, 45, 49)

        # Criar a embed
        embed = nextcord.Embed(
            title=embed_title,
            description=embed_description,
            color=embed_color
        )
        embed.add_field(
            name="📌 Instruções",
            value="Clique em 'Registrar-se' e receba seu cargo automaticamente!",
            inline=False
        )
        if embed_image_url:
            embed.set_image(url=embed_image_url)
        if embed_thumbnail_url:
            embed.set_thumbnail(url=embed_thumbnail_url)
        embed.set_footer(text=embed_footer)

        # Adiciona o botão à view
        view = nextcord.ui.View(timeout=None)
        button = nextcord.ui.Button(
            label="Registrar-se",
            style=nextcord.ButtonStyle.secondary,  # Botão cinza
            emoji="<:logo2:1350090849903710208>"  # Emoji personalizado
        )

        # Função de callback para o botão
        async def button_callback(interaction_button: Interaction):
            guild_id = str(interaction_button.guild.id)
            register_config = self.load_config(guild_id)

            # Carrega o cargo inicial do sistema de boas-vindas
            welcome_config_file = os.path.join(self.data_dir, guild_id, "welcome_config.json")
            if not os.path.exists(welcome_config_file):
                await interaction_button.response.send_message(
                    "Erro: O sistema de boas-vindas não está configurado. Contate um administrador.",
                    ephemeral=True
                )
                return

            with open(welcome_config_file, "r") as f:
                welcome_config = json.load(f)

            initial_role_id = welcome_config.get("role_id")
            role_id = register_config.get("role_id")

            if not role_id or not initial_role_id:
                await interaction_button.response.send_message(
                    "Erro: O sistema de registro ou boas-vindas não está configurado corretamente. Contate um administrador.",
                    ephemeral=True
                )
                return

            role = interaction_button.guild.get_role(role_id)
            initial_role = interaction_button.guild.get_role(initial_role_id)

            if not role or not initial_role:
                await interaction_button.response.send_message(
                    "Erro: Um dos cargos configurados não foi encontrado. Contate um administrador.",
                    ephemeral=True
                )
                return

            member = interaction_button.user

            # Verifica se o membro já tem o cargo de registro
            if role in member.roles:
                await interaction_button.response.send_message(
                    "Você já está registrado! Aproveite o servidor! 😊",
                    ephemeral=True
                )
                return

            # Remove o cargo inicial e adiciona o cargo de registro
            try:
                await member.remove_roles(initial_role, reason="Removendo cargo inicial após registro")
                await member.add_roles(role, reason="Registro no servidor")
            except Exception as e:
                await interaction_button.response.send_message(
                    f"Erro ao processar o registro: {e}",
                    ephemeral=True
                )
                return

            await interaction_button.response.send_message(
                f"Registro concluído! Bem-vindo(a) ao {interaction_button.guild.name}, {member.mention}! 🎉",
                ephemeral=True
            )

        button.callback = button_callback
        view.add_item(button)

        # Envia a embed com o botão
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"Embed de registro enviada com sucesso para {channel.mention}!",
            ephemeral=True
        )

def setup(bot):
    bot.add_cog(RegisterCog(bot))