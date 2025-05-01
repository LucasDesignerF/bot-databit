# welcome_cog.py
# Description: Cog para gerenciar boas-vindas de novos membros com embed personalizável
# Date of Creation: 12/03/2025
# Created by: CodeProjects
# Modified by: Grok (xAI), CodeProjects, RedeGamer
# Date of Modification: 01/05/2025
# Reason of Modification: Melhorada validação de URLs de imagens para aceitar qualquer serviço de hospedagem
# Version: 4.1
# Developer Of Version: Grok (xAI), CodeProjects, RedeGamer

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
import sqlite3
import logging
import json
import aiohttp
import asyncio

# Configuração de logging
logger = logging.getLogger("DataBit.WelcomeCog")
logger.setLevel(logging.INFO)

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Conexão SQLite fornecida pelo main.py
        self.session = None

    def load_config(self, guild_id: str) -> dict:
        """Carrega a configuração de boas-vindas do banco de dados."""
        default_config = {
            "role_id": None,
            "channel_id": None,
            "embed_title": "Bem-vindo(a) ao {guild}!",
            "embed_description": "Olá {member}, seja bem-vindo(a)! Você é o membro #{count}!",
            "embed_color": [0, 0, 255],  # Azul padrão
            "embed_image": "",
            "embed_footer": "Esperamos que você aproveite!",
            "embed_fields": [],  # Lista de campos: [{"name": "", "value": "", "inline": true}]
            "dm_message": "Olá {member}, bem-vindo(a) ao **{guild}**! 🎉"
        }
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM welcome_config WHERE guild_id = ?", (guild_id,))
            result = cursor.fetchone()
            if result:
                config = dict(result)
                config["embed_color"] = json.loads(config["embed_color"])
                config["embed_fields"] = json.loads(config["embed_fields"])
                return config
            return default_config
        except Exception as e:
            logger.error(f"Erro ao carregar welcome_config de {guild_id}: {e}")
            return default_config

    def save_config(self, guild_id: str, config: dict):
        """Salva a configuração de boas-vindas no banco de dados."""
        try:
            cursor = self.db.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO welcome_config (
                    guild_id, role_id, channel_id, embed_title, embed_description,
                    embed_color, embed_image, embed_footer, embed_fields, dm_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    config.get("role_id"),
                    config.get("channel_id"),
                    config.get("embed_title", "Bem-vindo(a) ao {guild}!"),
                    config.get("embed_description", "Olá {member}, seja bem-vindo(a)! Você é o membro #{count}!"),
                    json.dumps(config.get("embed_color", [0, 0, 255])),
                    config.get("embed_image", ""),
                    config.get("embed_footer", "Esperamos que você aproveite!"),
                    json.dumps(config.get("embed_fields", [])),
                    config.get("dm_message", "Olá {member}, bem-vindo(a) ao **{guild}**! 🎉")
                )
            )
            self.db.commit()
            logger.info(f"Configuração salva para servidor {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar welcome_config de {guild_id}: {e}")

    async def resolve_imgur_url(self, url: str) -> str:
        """Resolve URLs do Imgur para a imagem direta, se aplicável."""
        if url.startswith("https://imgur.com"):
            img_id = url.split("/")[-1].split(".")[0]
            direct_url = f"https://i.imgur.com/{img_id}.png"
            logger.debug(f"URL do Imgur simplificada: {url} -> {direct_url}")
            return direct_url
        return url

    async def validate_image_url(self, url: str, max_retries: int = 3) -> bool:
        """Valida se a URL aponta para uma imagem válida."""
        if not url:
            return True
        if not self.session:
            self.session = aiohttp.ClientSession(headers={"User-Agent": "DataBitBot/4.1"})
        
        for attempt in range(max_retries):
            try:
                async with self.session.get(
                    url,
                    allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "").lower()
                        if content_type.startswith("image/"):
                            logger.debug(f"URL validada como imagem: {url} (Content-Type: {content_type})")
                            return True
                        # Fallback: verificar extensão se Content-Type não for claro
                        if not content_type or content_type == "application/octet-stream":
                            if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                logger.debug(f"URL validada por extensão: {url}")
                                return True
                            # Tentar baixar uma pequena amostra para verificar
                            sample = await resp.read(1024)  # Baixa apenas 1KB
                            if sample.startswith(b'\x89PNG') or sample.startswith(b'\xff\xd8') or sample.startswith(b'GIF89a'):
                                logger.debug(f"URL validada por amostra de conteúdo: {url}")
                                return True
                        logger.warning(f"URL {url} não é uma imagem (Content-Type: {content_type})")
                        return False
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 5))
                        logger.warning(f"Erro 429 ao validar {url}. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_after}s")
                        await asyncio.sleep(retry_after)
                    else:
                        logger.warning(f"Erro HTTP {resp.status} ao validar {url}")
                        return False
            except aiohttp.ClientError as e:
                logger.error(f"Erro na tentativa {attempt+1}/{max_retries} para validar {url}: {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2)  # Pequena espera antes de tentar novamente
        return False

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Evento disparado quando um membro entra no servidor."""
        if member.bot:
            return
        guild_id = str(member.guild.id)
        config = self.load_config(guild_id)

        # Atribuir cargo, se configurado
        role_id = config.get("role_id")
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Cargo de boas-vindas")
                    logger.info(f"Cargo {role_id} atribuído a {member.id} em {guild_id}")
                except Exception as e:
                    logger.error(f"Erro ao atribuir cargo a {member.id} em {guild_id}: {e}")

        # Enviar embed no canal
        channel_id = config.get("channel_id")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                try:
                    embed = nextcord.Embed()
                    # Configurar título
                    embed.title = config["embed_title"].format(
                        member=member.name, guild=member.guild.name, count=member.guild.member_count
                    )
                    # Configurar descrição
                    embed.description = config["embed_description"].format(
                        member=member.name, guild=member.guild.name, count=member.guild.member_count
                    )
                    # Configurar cor
                    rgb = config["embed_color"]
                    embed.color = nextcord.Color.from_rgb(rgb[0], rgb[1], rgb[2])
                    # Configurar imagem
                    image_url = await self.resolve_imgur_url(config["embed_image"])
                    if image_url and await self.validate_image_url(image_url):
                        embed.set_image(url=image_url)
                    # Configurar thumbnail com avatar do membro
                    avatar_url = str(member.avatar.url if member.avatar else member.default_avatar.url)
                    embed.set_thumbnail(url=avatar_url)
                    # Configurar footer
                    embed.set_footer(text=config["embed_footer"].format(
                        member=member.name, guild=member.guild.name, count=member.guild.member_count
                    ))
                    # Adicionar campos
                    for field in config["embed_fields"]:
                        embed.add_field(
                            name=field["name"].format(member=member.name, guild=member.guild.name, count=member.guild.member_count),
                            value=field["value"].format(member=member.name, guild=member.guild.name, count=member.guild.member_count),
                            inline=field.get("inline", True)
                        )
                    await channel.send(embed=embed)
                    logger.info(f"Embed de boas-vindas enviada para {member.id} em {guild_id}")
                except Exception as e:
                    logger.error(f"Erro ao enviar embed de boas-vindas para {member.id} em {guild_id}: {e}")
                    await channel.send(
                        f"Bem-vindo(a) ao servidor, {member.mention}! 🎉\n"
                        f"(Erro ao gerar embed de boas-vindas. Verifique a configuração.)"
                    )

        # Enviar DM
        try:
            dm_message = config["dm_message"].format(member=member.name, guild=member.guild.name)
            await member.send(dm_message)
            logger.info(f"DM enviada para {member.id} em {guild_id}")
        except nextcord.Forbidden:
            logger.warning(f"DM bloqueada para {member.id} em {guild_id}")
        except nextcord.HTTPException as e:
            if e.status == 429:
                retry_after = e.retry_after or 5
                logger.warning(f"Rate limit em DM para {member.id}. Aguardando {retry_after}s")
                await asyncio.sleep(retry_after)
                await member.send(dm_message)
            else:
                logger.error(f"Erro ao enviar DM para {member.id} em {guild_id}: {e}")

    @nextcord.slash_command(
        name="config_welcome",
        description="Configure o sistema de boas-vindas (apenas administradores)"
    )
    async def config_welcome(
        self,
        interaction: Interaction,
        role: nextcord.Role = SlashOption(description="Cargo para novos membros", required=False),
        channel: nextcord.TextChannel = SlashOption(description="Canal de boas-vindas", required=False),
        embed_title: str = SlashOption(description="Título da embed ({member}, {guild}, {count})", required=False),
        embed_description: str = SlashOption(description="Descrição da embed ({member}, {guild}, {count})", required=False),
        embed_color: str = SlashOption(description="Cor da embed (R,G,B, ex.: 0,0,255)", required=False),
        embed_image: str = SlashOption(description="URL da imagem da embed", required=False),
        embed_footer: str = SlashOption(description="Rodapé da embed ({member}, {guild}, {count})", required=False),
        embed_fields: str = SlashOption(description="Campos da embed (JSON: [{'name': '', 'value': '', 'inline': true}])", required=False),
        dm_message: str = SlashOption(description="Mensagem de DM ({member}, {guild})", required=False)
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Você precisa ser administrador para usar este comando!",
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)

        if role:
            config["role_id"] = role.id
        if channel:
            config["channel_id"] = channel.id
        if embed_title:
            config["embed_title"] = embed_title
        if embed_description:
            config["embed_description"] = embed_description
        if embed_color:
            try:
                rgb = [int(x) for x in embed_color.split(",")]
                if len(rgb) != 3 or not all(0 <= x <= 255 for x in rgb):
                    raise ValueError
                config["embed_color"] = rgb
            except ValueError:
                await interaction.response.send_message(
                    "Cor inválida! Use o formato R,G,B (ex.: 0,0,255)",
                    ephemeral=True
                )
                return
        if embed_image:
            resolved_url = await self.resolve_imgur_url(embed_image)
            if not await self.validate_image_url(resolved_url):
                await interaction.response.send_message(
                    "URL da imagem inválida! Verifique se o link é acessível e aponta para uma imagem (ex.: PNG, JPG, GIF).",
                    ephemeral=True
                )
                return
            config["embed_image"] = resolved_url
        if embed_footer:
            config["embed_footer"] = embed_footer
        if embed_fields:
            try:
                fields = json.loads(embed_fields)
                if not isinstance(fields, list) or not all(
                    isinstance(f, dict) and "name" in f and "value" in f for f in fields
                ):
                    raise ValueError
                config["embed_fields"] = fields
            except ValueError:
                await interaction.response.send_message(
                    "Campos inválidos! Use JSON como [{'name': '', 'value': '', 'inline': true}]",
                    ephemeral=True
                )
                return
        if dm_message:
            config["dm_message"] = dm_message

        self.save_config(guild_id, config)
        response = "Sistema de boas-vindas configurado!\n"
        if role:
            response += f"Cargo: {role.mention}\n"
        if channel:
            response += f"Canal: {channel.mention}\n"
        if embed_title:
            response += f"Título: {embed_title}\n"
        if embed_description:
            response += f"Descrição: {embed_description}\n"
        if embed_color:
            response += f"Cor: {embed_color}\n"
        if embed_image:
            response += f"Imagem: {config['embed_image']}\n"
        if embed_footer:
            response += f"Rodapé: {embed_footer}\n"
        if embed_fields:
            response += f"Campos: {len(config['embed_fields'])} configurados\n"
        if dm_message:
            response += f"DM: {dm_message}\n"

        await interaction.response.send_message(response, ephemeral=True)
        logger.info(f"Configuração de boas-vindas atualizada por {interaction.user.id} em {guild_id}")

def setup(bot):
    bot.add_cog(WelcomeCog(bot))