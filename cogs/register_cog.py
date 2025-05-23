# register_cog.py
# Description: Cog para gerenciar o sistema de registro de membros
# Date of Creation: 14/03/2025
# Created by: CodeProjects
# Modified by: Grok (xAI), CodeProjects, RedeGamer
# Date of Modification: 23/04/2025
# Reason of Modification: Migração de JSON para SQLite, remoção de gerenciamento de arquivos, correção de referência a default_config
# Version: 3.0.1
# Developer Of Version: Grok (xAI), CodeProjects, RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
import json
import logging
import aiohttp
import asyncio
from datetime import datetime
import hashlib

# Configuração de logging
logger = logging.getLogger("DataBit.RegisterCog")
logger.setLevel(logging.INFO)

class RegisterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Usa a conexão SQLite fornecida pelo main.py
        self.session = None
        self.default_config = {
            "role_id": None,
            "embed_title": "🚀 Bem-vindo ao Registro!",
            "embed_description": (
                "Olá! Para liberar o acesso completo ao servidor, registre-se agora.\n"
                "Aqui está tudo o que você precisa saber:\n\n"
                "➜ **Passo Único:** Clique no botão abaixo para se registrar.\n"
                "➜ **Benefícios:** Acesso aos canais principais e participação na comunidade!\n"
                "➜ **Aviso:** Sem registro, seu acesso será limitado."
            ),
            "embed_image_url": "",
            "embed_thumbnail_url": "",
            "embed_footer": "Sistema de Registro Automático - by CodeProjects"
        }

    def load_config(self, guild_id: str) -> dict:
        """Carrega a configuração de registro do banco de dados."""
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM register_config WHERE guild_id = ?", (guild_id,))
            result = cursor.fetchone()
            if result:
                config = dict(result)
                return {**self.default_config, **config}
            return self.default_config
        except Exception as e:
            logger.error(f"Erro ao carregar register_config de {guild_id}: {e}")
            return self.default_config

    def save_config(self, guild_id: str, config: dict):
        """Salva a configuração de registro no banco de dados."""
        try:
            cursor = self.db.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO register_config (
                    guild_id, role_id, embed_title, embed_description,
                    embed_image_url, embed_thumbnail_url, embed_footer
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    config.get("role_id"),
                    config.get("embed_title", self.default_config["embed_title"]),
                    config.get("embed_description", self.default_config["embed_description"]),
                    config.get("embed_image_url", ""),
                    config.get("embed_thumbnail_url", ""),
                    config.get("embed_footer", self.default_config["embed_footer"])
                )
            )
            self.db.commit()
            logger.info(f"Configuração salva para servidor {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar register_config de {guild_id}: {e}")

    async def validate_url(self, url: str) -> bool:
        """Valida se a URL é acessível e retorna uma imagem."""
        if not url:
            return True
        if not self.session:
            self.session = aiohttp.ClientSession(headers={"User-Agent": "DataBitBot/3.0"})
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200 and resp.headers.get("Content-Type", "").startswith("image/"):
                    return True
                logger.warning(f"URL inválida ou não é imagem: {url}, status: {resp.status}")
                return False
        except Exception as e:
            logger.error(f"Erro ao validar URL {url}: {e}")
            return False

    @nextcord.slash_command(
        name="config_register",
        description="Configure o sistema de registro."
    )
    async def config_register(
        self,
        interaction: Interaction,
        role: nextcord.Role = SlashOption(description="Cargo a ser atribuído após o registro")
    ):
        """Configura o sistema de registro com o cargo especificado."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Você precisa ser administrador para usar este comando!",
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)

        config["role_id"] = role.id
        self.save_config(guild_id, config)

        await interaction.response.send_message(
            f"Sistema de registro configurado!\n"
            f"Cargo de registro: {role.mention}",
            ephemeral=True
        )
        logger.info(f"Sistema de registro configurado por {interaction.user.id} em {guild_id}, cargo: {role.id}")

    class PersonalizeRegisterModal(nextcord.ui.Modal):
        def __init__(self, parent_cog):
            super().__init__("Personalizar Embed de Registro", timeout=300)
            self.parent_cog = parent_cog

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
                default_value="",
                placeholder="Ex.: https://cdn.discordapp.com/attachments/.../image.png",
                required=False,
                max_length=500
            )
            self.add_item(self.embed_image_url)

            self.embed_thumbnail_url = nextcord.ui.TextInput(
                label="URL do Thumbnail",
                default_value="",
                placeholder="Ex.: https://cdn.discordapp.com/attachments/.../thumbnail.png",
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

            # Valida URLs
            image_valid = await self.parent_cog.validate_url(self.embed_image_url.value)
            thumbnail_valid = await self.parent_cog.validate_url(self.embed_thumbnail_url.value)

            if not (image_valid and thumbnail_valid):
                await interaction.response.send_message(
                    "Uma ou mais URLs fornecidas são inválidas ou inacessíveis. Verifique e tente novamente.",
                    ephemeral=True
                )
                return

            # Salva as configurações
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
            logger.info(f"Embed de registro personalizada por {interaction.user.id} em {guild_id}")

    @nextcord.slash_command(
        name="person_register",
        description="Personalize a embed de registro do servidor."
    )
    async def person_register(
        self,
        interaction: Interaction,
        image_file: nextcord.Attachment = SlashOption(description="Upload de imagem principal", required=False),
        thumbnail_file: nextcord.Attachment = SlashOption(description="Upload de thumbnail", required=False)
    ):
        """Personaliza a embed de registro com modal ou upload de imagens."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Você precisa ser administrador para usar este comando!",
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)

        # Processa upload de imagens
        if image_file:
            try:
                if not image_file.content_type.startswith("image/"):
                    await interaction.response.send_message(
                        "O arquivo de imagem principal deve ser uma imagem (PNG/JPG)!",
                        ephemeral=True
                    )
                    return
                file_data = await image_file.read()
                file_hash = hashlib.md5(file_data).hexdigest()
                config["embed_image_url"] = f"attachment://{file_hash}.png"
                logger.info(f"Imagem principal carregada via upload para {guild_id}")
            except Exception as e:
                logger.error(f"Erro ao processar upload de imagem principal para {guild_id}: {e}")
                await interaction.response.send_message(
                    "Erro ao processar a imagem principal carregada. Tente novamente.",
                    ephemeral=True
                )
                return

        if thumbnail_file:
            try:
                if not thumbnail_file.content_type.startswith("image/"):
                    await interaction.response.send_message(
                        "O arquivo de thumbnail deve ser uma imagem (PNG/JPG)!",
                        ephemeral=True
                    )
                    return
                file_data = await thumbnail_file.read()
                file_hash = hashlib.md5(file_data).hexdigest()
                config["embed_thumbnail_url"] = f"attachment://{file_hash}.png"
                logger.info(f"Thumbnail carregado via upload para {guild_id}")
            except Exception as e:
                logger.error(f"Erro ao processar upload de thumbnail para {guild_id}: {e}")
                await interaction.response.send_message(
                    "Erro ao processar o thumbnail carregado. Tente novamente.",
                    ephemeral=True
                )
                return

        if image_file or thumbnail_file:
            self.save_config(guild_id, config)
            await interaction.response.send_message(
                "Imagens carregadas com sucesso! Use /create_register_embed para aplicar ou /person_register para personalizar a embed.",
                ephemeral=True
            )
            logger.info(f"Imagens carregadas por {interaction.user.id} em {guild_id}")
        else:
            await interaction.response.send_modal(self.PersonalizeRegisterModal(self))

    @nextcord.slash_command(
        name="create_register_embed",
        description="Cria uma embed com o botão de registro."
    )
    async def create_register_embed(
        self,
        interaction: Interaction,
        channel: nextcord.TextChannel = SlashOption(description="Canal onde a embed será enviada")
    ):
        """Cria e envia a embed de registro com botão."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Você precisa ser administrador para usar este comando!",
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)

        # Usa configurações personalizadas ou valores padrão
        embed_title = config.get("embed_title", self.default_config["embed_title"])
        embed_description = config.get("embed_description", self.default_config["embed_description"])
        embed_image_url = config.get("embed_image_url", "")
        embed_thumbnail_url = config.get("embed_thumbnail_url", "")
        embed_footer = config.get("embed_footer", self.default_config["embed_footer"])

        # Valida URLs (ignora attachment://)
        files = []
        if embed_image_url and not embed_image_url.startswith("attachment://"):
            if not await self.validate_url(embed_image_url):
                embed_image_url = ""
        if embed_thumbnail_url and not embed_thumbnail_url.startswith("attachment://"):
            if not await self.validate_url(embed_thumbnail_url):
                embed_thumbnail_url = ""

        # Cor da embed
        embed_color = nextcord.Color.from_rgb(43, 45, 49)

        # Cria a embed
        embed = nextcord.Embed(
            title=embed_title,
            description=embed_description,
            color=embed_color,
            timestamp=datetime.utcnow()
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
            style=nextcord.ButtonStyle.secondary,
            emoji="<:logo2:1350090849903710208>"
        )

        async def button_callback(interaction_button: Interaction):
            guild_id = str(interaction_button.guild.id)
            register_config = self.load_config(guild_id)

            # Carrega o cargo inicial do sistema de boas-vindas do banco
            try:
                cursor = self.db.cursor()
                cursor.execute("SELECT role_id FROM welcome_config WHERE guild_id = ?", (guild_id,))
                result = cursor.fetchone()
                initial_role_id = result["role_id"] if result else None
            except Exception as e:
                await interaction_button.response.send_message(
                    "Erro: Não foi possível carregar a configuração de boas-vindas. Contate um administrador.",
                    ephemeral=True
                )
                logger.error(f"Erro ao carregar welcome_config de {guild_id}: {e}")
                return

            role_id = register_config.get("role_id")

            if not role_id or not initial_role_id:
                await interaction_button.response.send_message(
                    "Erro: O sistema de registro ou boas-vindas não está configurado corretamente. Contate um administrador.",
                    ephemeral=True
                )
                logger.error(f"Configuração incompleta em {guild_id}: role_id={role_id}, initial_role_id={initial_role_id}")
                return

            role = interaction_button.guild.get_role(role_id)
            initial_role = interaction_button.guild.get_role(initial_role_id)

            if not role or not initial_role:
                await interaction_button.response.send_message(
                    "Erro: Um dos cargos configurados não foi encontrado. Contate um administrador.",
                    ephemeral=True
                )
                logger.error(f"Cargo não encontrado em {guild_id}: role={role_id}, initial_role={initial_role_id}")
                return

            member = interaction_button.user

            if role in member.roles:
                await interaction_button.response.send_message(
                    "Você já está registrado! Aproveite o servidor! 😊",
                    ephemeral=True
                )
                logger.info(f"Membro {member.id} já registrado em {guild_id}")
                return

            # Tenta remover e adicionar cargos com retry para rate limits
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await member.remove_roles(initial_role, reason="Removendo cargo inicial após registro")
                    await member.add_roles(role, reason="Registro no servidor")
                    break
                except nextcord.HTTPException as e:
                    if e.status == 429:
                        retry_after = e.retry_after or 5
                        logger.warning(f"Rate limit ao modificar cargos para {member.id} em {guild_id}. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_after}s")
                        await asyncio.sleep(retry_after + attempt * 2)
                    else:
                        await interaction_button.response.send_message(
                            f"Erro ao processar o registro: {e}",
                            ephemeral=True
                        )
                        logger.error(f"Erro ao modificar cargos para {member.id} em {guild_id}: {e}")
                        return
                except Exception as e:
                    await interaction_button.response.send_message(
                        f"Erro ao processar o registro: {e}",
                        ephemeral=True
                    )
                    logger.error(f"Erro inesperado ao modificar cargos para {member.id} em {guild_id}: {e}")
                    return
            else:
                await interaction_button.response.send_message(
                    "Erro: Não foi possível processar o registro devido a limites de requisições. Tente novamente mais tarde.",
                    ephemeral=True
                )
                logger.error(f"Falha após {max_retries} tentativas para {member.id} em {guild_id}")
                return

            await interaction_button.response.send_message(
                f"Registro concluído! Bem-vindo(a) ao {interaction_button.guild.name}, {member.mention}! 🎉",
                ephemeral=True
            )
            logger.info(f"Registro concluído para {member.id} em {guild_id}")

        button.callback = button_callback
        view.add_item(button)

        # Envia a embed com o botão e anexos, se houver
        try:
            if files:
                await channel.send(embed=embed, view=view, files=files)
                logger.info(f"Embed de registro enviada com {len(files)} anexos por {interaction.user.id} para {channel.id} em {guild_id}")
            else:
                await channel.send(embed=embed, view=view)
                logger.info(f"Embed de registro enviada sem anexos por {interaction.user.id} para {channel.id} em {guild_id}")
            await interaction.response.send_message(
                f"Embed de registro enviada com sucesso para {channel.mention}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Erro ao enviar a embed para {channel.mention}: {e}",
                ephemeral=True
            )
            logger.error(f"Erro ao enviar embed para {channel.id} em {guild_id}: {e}")

    async def close(self):
        """Fecha a sessão HTTP."""
        if self.session:
            await self.session.close()
            self.session = None

def setup(bot):
    bot.add_cog(RegisterCog(bot))