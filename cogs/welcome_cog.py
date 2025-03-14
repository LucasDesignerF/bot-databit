# welcome_cog.py
# Description: Cog para gerenciar boas-vindas de novos membros com imagem personalizada
# Date of Creation: 12/03/2025
# Created by: CodeProjects
# Modified by: Grok (xAI) & CodeProjects
# Date of Modification: 14/03/2025
# Reason of Modification: Ajuste de fonte com linha comentada para tamanho
# Version: 2.3
# Developer Of Version: Grok (xAI), CodeProjects, RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
import os
import json
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data"
        self.font_dir = "fonts"  # Crie uma pasta 'fonts' e adicione 'Montserrat-ExtraBold.ttf'

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

    # Função para criar a imagem de boas-vindas
    async def create_welcome_image(self, member):
        # Configurações da imagem
        img_width, img_height = 800, 300

        # Baixa o fundo personalizado
        background_url = "https://static.vecteezy.com/ti/vetor-gratis/p1/3809900-digital-binario-codigo-dados-fundo-computador-numeros-conceito-tecnologico-vetor.jpg"
        async with aiohttp.ClientSession() as session:
            async with session.get(background_url) as resp:
                bg_data = await resp.read()
        background = Image.open(io.BytesIO(bg_data)).convert("RGBA")
        background = background.resize((img_width, img_height), Image.LANCZOS)
        draw = ImageDraw.Draw(background)

        # Baixa o avatar do membro
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.avatar.url)) as resp:
                avatar_data = await resp.read()
        avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
        avatar = avatar.resize((150, 150), Image.LANCZOS)

        # Máscara circular para o avatar
        mask = Image.new("L", (150, 150), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 150, 150), fill=255)
        avatar.putalpha(mask)

        # Contorno do avatar
        avatar_x = (img_width - 150) // 2
        avatar_y = 50
        draw.ellipse(
            [avatar_x - 10, avatar_y - 10, avatar_x + 160, avatar_y + 160],
            outline=(255, 255, 255, 255),  # Contorno branco
            width=5  # Largura do contorno
        )
        background.paste(avatar, (avatar_x, avatar_y), avatar)

        # Carrega a fonte Montserrat ExtraBold (baixe do Google Fonts)
        try:
            # Ajuste o tamanho da fonte aqui (aumente ou diminua o valor 50 conforme necessário)
            welcome_font = ImageFont.truetype(os.path.join(self.font_dir, "Montserrat-ExtraBold.otf"), 50)
        except:
            welcome_font = ImageFont.load_default()

        # Texto de boas-vindas
        welcome_text = f"Bem-vindo {member.name} #{member.guild.member_count}!"
        text_bbox = draw.textbbox((0, 0), welcome_text, font=welcome_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Centraliza o texto embaixo do avatar
        text_x = (img_width - text_width) // 2
        text_y = avatar_y + 150 + 20  # 20px abaixo do avatar pra dar espaço
        draw.text((text_x, text_y), welcome_text, font=welcome_font, fill=(255, 255, 255, 255))

        # Salva a imagem em um buffer
        buffer = io.BytesIO()
        background.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

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

        # Gera e envia a imagem de boas-vindas
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                welcome_image = await self.create_welcome_image(member)
                file = nextcord.File(welcome_image, filename="welcome.png")
                welcome_message = f"Bem-vindo(a) ao servidor, {member.mention}! 🎉"
                await channel.send(welcome_message, file=file)

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