# cogs/opcionais/member_management.py
# Description: Sistema para registro de nicknames e notificação de ausência no Discord, com interface personalizável
# Date of Creation: 23/04/2025
# Created by: Grok (xAI), CodeProjects, RedeGamer
# Version: 1.0
# Developer Of Version: Grok (xAI), CodeProjects, RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction, ui
import logging
from datetime import datetime, timedelta
import pytz
import sqlite3
import json
import re
from uuid import uuid4

# Configuração de logging
logger = logging.getLogger("DataBit.MemberManagementCog")
logger.setLevel(logging.INFO)

class MemberManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Conexão SQLite do main.py
        self.br_tz = pytz.timezone("America/Sao_Paulo")
        self.default_config = {
            "enabled": False,
            "guild_id": None,
            "register_channel_id": None,
            "register_message_id": None,
            "absence_channel_id": None,
            "absence_message_id": None,
            "embed_config": {
                "register": {
                    "title": "Registro de Membro",
                    "description": "Clique no botão abaixo para registrar seu nickname, ID e sigla do servidor.",
                    "color": [43, 45, 49],  # RGB
                    "thumbnail": "https://cdn-icons-png.flaticon.com/512/149/149071.png",
                    "footer": "Sistema de Registro - RedeGamer",
                },
                "absence": {
                    "title": "Informar Ausência",
                    "description": "Clique no botão abaixo para registrar uma ausência.",
                    "color": [43, 45, 49],
                    "thumbnail": "https://cdn-icons-png.flaticon.com/512/3659/3659796.png",
                    "footer": "Sistema de Ausência - RedeGamer",
                },
                "confirmation": {
                    "title": "Confirmação",
                    "description": "Registro realizado com sucesso!",
                    "color": [0, 255, 0],
                    "thumbnail": None,
                    "footer": "Atualizado em {timestamp}",
                }
            },
            "button_config": {
                "register": {"label": "Registrar", "emoji": "📝", "style": "blurple"},
                "absence": {"label": "Informar Ausência", "emoji": "🔔", "style": "blurple"},
                "list_absences": {"label": "Ver Ausências Ativas", "emoji": "📋", "style": "grey"},
                "customize": {"label": "Personalizar Embeds", "emoji": "🎨", "style": "green"},
                "close": {"label": "Fechar", "emoji": "❌", "style": "red"}
            }
        }
        self.update_absences.start()

    def cog_unload(self):
        self.update_absences.cancel()
        logger.info("MemberManagementCog descarregada")

    def init_db(self):
        """Inicializa as tabelas no banco de dados."""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS member_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT FALSE,
                    register_channel_id TEXT,
                    register_message_id TEXT,
                    absence_channel_id TEXT,
                    absence_message_id TEXT,
                    embed_config TEXT,
                    button_config TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS member_registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    sigla TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    UNIQUE(guild_id, user_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS member_absences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    status TEXT DEFAULT 'ativa',
                    timestamp TEXT NOT NULL
                )
            """)
            self.db.commit()
            logger.info("Tabelas member_config, member_registrations e member_absences criadas ou já existentes")
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {e}")

    def load_config(self, guild_id: str) -> dict:
        """Carrega a configuração do sistema para a guild."""
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT * FROM member_config WHERE guild_id = ?",
                (guild_id,)
            )
            result = cursor.fetchone()
            if result:
                config = dict(result)
                config["embed_config"] = json.loads(config["embed_config"]) if config["embed_config"] else self.default_config["embed_config"]
                config["button_config"] = json.loads(config["button_config"]) if config["button_config"] else self.default_config["button_config"]
                return config
            return {**self.default_config, "guild_id": guild_id}
        except Exception as e:
            logger.error(f"Erro ao carregar member_config de {guild_id}: {e}")
            return {**self.default_config, "guild_id": guild_id}

    def save_config(self, guild_id: str, config: dict):
        """Salva a configuração do sistema."""
        try:
            cursor = self.db.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO member_config (
                    guild_id, enabled, register_channel_id, register_message_id,
                    absence_channel_id, absence_message_id, embed_config, button_config
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    config.get("enabled", self.default_config["enabled"]),
                    config.get("register_channel_id"),
                    config.get("register_message_id"),
                    config.get("absence_channel_id"),
                    config.get("absence_message_id"),
                    json.dumps(config.get("embed_config", self.default_config["embed_config"])),
                    json.dumps(config.get("button_config", self.default_config["button_config"]))
                )
            )
            self.db.commit()
            logger.info(f"Configuração salva para {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar member_config de {guild_id}: {e}")

    def validate_nickname(self, nickname: str) -> bool:
        """Valida o formato do nickname."""
        return bool(re.match(r"^[a-zA-Z0-9_]{1,32}$", nickname))

    def validate_id(self, player_id: str) -> bool:
        """Valida o formato do ID (numérico ou alfanumérico)."""
        return bool(re.match(r"^[a-zA-Z0-9]{1,20}$", player_id))

    def validate_sigla(self, sigla: str) -> bool:
        """Valida o formato da sigla."""
        return bool(re.match(r"^[a-zA-Z0-9]{1,5}$", sigla))

    def validate_date(self, date_str: str) -> bool:
        """Valida o formato da data (DD/MM/YYYY)."""
        try:
            datetime.strptime(date_str, "%d/%m/%Y")
            return True
        except ValueError:
            return False

    async def send_or_update_message(self, config: dict, guild_id: str, channel_id: str, message_id: str, embed_key: str, view):
        """Envia ou atualiza uma mensagem fixa no canal."""
        try:
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                logger.error(f"Guild {guild_id} não encontrada")
                return False

            channel = guild.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Canal {channel_id} não encontrado na guild {guild_id}")
                return False

            if not channel.permissions_for(guild.me).send_messages:
                logger.error(f"Sem permissão para enviar mensagens no canal {channel_id}")
                return False

            embed_config = config["embed_config"][embed_key]
            embed = nextcord.Embed(
                title=embed_config["title"],
                description=embed_config["description"],
                color=nextcord.Color.from_rgb(*embed_config["color"]),
                timestamp=datetime.now(self.br_tz)
            )
            if embed_config["thumbnail"]:
                embed.set_thumbnail(url=embed_config["thumbnail"])
            if embed_config["footer"]:
                embed.set_footer(text=embed_config["footer"])

            if message_id:
                try:
                    message = await channel.fetch_message(int(message_id))
                    await message.edit(embed=embed, view=view)
                    logger.info(f"Mensagem {embed_key} atualizada em {guild_id}/{channel_id}")
                except nextcord.NotFound:
                    logger.warning(f"Mensagem {message_id} não encontrada, enviando nova")
                    message = await channel.send(embed=embed, view=view)
                    config[f"{embed_key}_message_id"] = str(message.id)
                    self.save_config(guild_id, config)
            else:
                message = await channel.send(embed=embed, view=view)
                config[f"{embed_key}_message_id"] = str(message.id)
                self.save_config(guild_id, config)
                logger.info(f"Nova mensagem {embed_key} enviada para {guild_id}/{channel_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar/atualizar mensagem {embed_key} em {guild_id}/{channel_id}: {e}")
            return False

    class RegisterNicknameModal(ui.Modal):
        def __init__(self, cog, guild_id: str):
            super().__init__("Registrar Nickname")
            self.cog = cog
            self.guild_id = guild_id

            self.nickname = ui.TextInput(
                label="Nickname",
                placeholder="Ex: Jogador123",
                required=True,
                max_length=32
            )
            self.add_item(self.nickname)

            self.player_id = ui.TextInput(
                label="ID do Jogador",
                placeholder="Ex: 123456 ou ABC123",
                required=True,
                max_length=20
            )
            self.add_item(self.player_id)

            self.sigla = ui.TextInput(
                label="Sigla do Servidor",
                placeholder="Ex: RPG",
                required=True,
                max_length=5
            )
            self.add_item(self.sigla)

        async def callback(self, interaction: Interaction):
            try:
                if not self.cog.validate_nickname(self.nickname.value):
                    await interaction.response.send_message(
                        "Nickname inválido! Use apenas letras, números e sublinhado (máx. 32 caracteres).",
                        ephemeral=True
                    )
                    return
                if not self.cog.validate_id(self.player_id.value):
                    await interaction.response.send_message(
                        "ID inválido! Use letras ou números (máx. 20 caracteres).",
                        ephemeral=True
                    )
                    return
                if not self.cog.validate_sigla(self.sigla.value):
                    await interaction.response.send_message(
                        "Sigla inválida! Use letras ou números (máx. 5 caracteres).",
                        ephemeral=True
                    )
                    return

                cursor = self.cog.db.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO member_registrations (
                        guild_id, user_id, nickname, player_id, sigla, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.guild_id,
                        str(interaction.user.id),
                        self.nickname.value,
                        self.player_id.value,
                        self.sigla.value,
                        datetime.now(self.cog.br_tz).isoformat()
                    )
                )
                self.cog.db.commit()

                config = self.cog.load_config(self.guild_id)
                embed_config = config["embed_config"]["confirmation"]
                embed = nextcord.Embed(
                    title=embed_config["title"],
                    description=f"**Nickname:** {self.nickname.value}\n**ID:** {self.player_id.value}\n**Sigla:** {self.sigla.value}",
                    color=nextcord.Color.from_rgb(*embed_config["color"]),
                    timestamp=datetime.now(self.cog.br_tz)
                )
                if embed_config["thumbnail"]:
                    embed.set_thumbnail(url=embed_config["thumbnail"])
                embed.set_footer(text=embed_config["footer"].format(timestamp=datetime.now(self.cog.br_tz).strftime("%d/%m/%Y %H:%M")))

                channel = interaction.guild.get_channel(int(config["register_channel_id"]))
                if channel and channel.permissions_for(interaction.guild.me).send_messages:
                    await channel.send(embed=embed)
                await interaction.response.send_message("Registro concluído com sucesso!", ephemeral=True)
                logger.info(f"Nickname registrado por {interaction.user.id} em {self.guild_id}")
            except Exception as e:
                logger.error(f"Erro ao registrar nickname em {self.guild_id}/{interaction.user.id}: {e}")
                await interaction.response.send_message("Erro ao registrar. Tente novamente.", ephemeral=True)

    class ReportAbsenceModal(ui.Modal):
        def __init__(self, cog, guild_id: str):
            super().__init__("Informar Ausência")
            self.cog = cog
            self.guild_id = guild_id

            self.reason = ui.TextInput(
                label="Motivo da Ausência",
                placeholder="Ex: Viagem, trabalho, etc.",
                style=nextcord.TextInputStyle.paragraph,
                required=True,
                max_length=500
            )
            self.add_item(self.reason)

            self.start_date = ui.TextInput(
                label="Data de Início (DD/MM/YYYY)",
                placeholder="Ex: 01/01/2025",
                required=True,
                max_length=10
            )
            self.add_item(self.start_date)

            self.end_date = ui.TextInput(
                label="Data de Retorno (DD/MM/YYYY)",
                placeholder="Ex: 10/01/2025",
                required=True,
                max_length=10
            )
            self.add_item(self.end_date)

        async def callback(self, interaction: Interaction):
            try:
                if not self.cog.validate_date(self.start_date.value):
                    await interaction.response.send_message(
                        "Data de início inválida! Use o formato DD/MM/YYYY.",
                        ephemeral=True
                    )
                    return
                if not self.cog.validate_date(self.end_date.value):
                    await interaction.response.send_message(
                        "Data de retorno inválida! Use o formato DD/MM/YYYY.",
                        ephemeral=True
                    )
                    return

                start_date = datetime.strptime(self.start_date.value, "%d/%m/%Y")
                end_date = datetime.strptime(self.end_date.value, "%d/%m/%Y")
                if end_date < start_date:
                    await interaction.response.send_message(
                        "A data de retorno deve ser posterior à data de início.",
                        ephemeral=True
                    )
                    return

                cursor = self.cog.db.cursor()
                cursor.execute(
                    """
                    INSERT INTO member_absences (
                        guild_id, user_id, reason, start_date, end_date, status, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.guild_id,
                        str(interaction.user.id),
                        self.reason.value,
                        self.start_date.value,
                        self.end_date.value,
                        "ativa",
                        datetime.now(self.cog.br_tz).isoformat()
                    )
                )
                self.cog.db.commit()

                config = self.cog.load_config(self.guild_id)
                embed_config = config["embed_config"]["confirmation"]
                embed = nextcord.Embed(
                    title=embed_config["title"],
                    description=f"**Motivo:** {self.reason.value}\n**Início:** {self.start_date.value}\n**Retorno:** {self.end_date.value}",
                    color=nextcord.Color.from_rgb(*embed_config["color"]),
                    timestamp=datetime.now(self.cog.br_tz)
                )
                if embed_config["thumbnail"]:
                    embed.set_thumbnail(url=embed_config["thumbnail"])
                embed.set_footer(text=embed_config["footer"].format(timestamp=datetime.now(self.cog.br_tz).strftime("%d/%m/%Y %H:%M")))

                channel = interaction.guild.get_channel(int(config["absence_channel_id"]))
                if channel and channel.permissions_for(interaction.guild.me).send_messages:
                    await channel.send(embed=embed)
                await interaction.response.send_message("Ausência registrada com sucesso!", ephemeral=True)
                logger.info(f"Ausência registrada por {interaction.user.id} em {self.guild_id}")
            except Exception as e:
                logger.error(f"Erro ao registrar ausência em {self.guild_id}/{interaction.user.id}: {e}")
                await interaction.response.send_message("Erro ao registrar ausência. Tente novamente.", ephemeral=True)

    class RegisterNicknameView(ui.View):
        def __init__(self, cog, guild_id: str):
            super().__init__(timeout=None)
            self.cog = cog
            self.guild_id = guild_id

        @ui.button(label="Registrar", style=nextcord.ButtonStyle.blurple, emoji="📝", custom_id="register_nickname")
        async def register_button(self, button: ui.Button, interaction: Interaction):
            config = self.cog.load_config(self.guild_id)
            button.label = config["button_config"]["register"]["label"]
            button.emoji = config["button_config"]["register"]["emoji"]
            button.style = getattr(nextcord.ButtonStyle, config["button_config"]["register"]["style"])
            modal = self.cog.RegisterNicknameModal(self.cog, self.guild_id)
            await interaction.response.send_modal(modal)

    class ReportAbsenceView(ui.View):
        def __init__(self, cog, guild_id: str):
            super().__init__(timeout=None)
            self.cog = cog
            self.guild_id = guild_id

        @ui.button(label="Informar Ausência", style=nextcord.ButtonStyle.blurple, emoji="🔔", custom_id="report_absence")
        async def absence_button(self, button: ui.Button, interaction: Interaction):
            config = self.cog.load_config(self.guild_id)
            button.label = config["button_config"]["absence"]["label"]
            button.emoji = config["button_config"]["absence"]["emoji"]
            button.style = getattr(nextcord.ButtonStyle, config["button_config"]["absence"]["style"])
            modal = self.cog.ReportAbsenceModal(self.cog, self.guild_id)
            await interaction.response.send_modal(modal)

        @ui.button(label="Ver Ausências Ativas", style=nextcord.ButtonStyle.grey, emoji="📋", custom_id="list_absences")
        async def list_absences_button(self, button: ui.Button, interaction: Interaction):
            config = self.cog.load_config(self.guild_id)
            button.label = config["button_config"]["list_absences"]["label"]
            button.emoji = config["button_config"]["list_absences"]["emoji"]
            button.style = getattr(nextcord.ButtonStyle, config["button_config"]["list_absences"]["style"])

            cursor = self.cog.db.cursor()
            cursor.execute(
                "SELECT user_id, reason, start_date, end_date FROM member_absences WHERE guild_id = ? AND status = ?",
                (self.guild_id, "ativa")
            )
            absences = cursor.fetchall()

            if not absences:
                await interaction.response.send_message("Nenhuma ausência ativa registrada.", ephemeral=True)
                return

            embed = nextcord.Embed(
                title="Ausências Ativas",
                description="Lista de ausências ativas no servidor.",
                color=nextcord.Color.from_rgb(*config["embed_config"]["confirmation"]["color"]),
                timestamp=datetime.now(self.cog.br_tz)
            )
            for absence in absences:
                user = interaction.guild.get_member(int(absence["user_id"]))
                embed.add_field(
                    name=f"{user.display_name if user else 'Usuário Desconhecido'}",
                    value=f"**Motivo:** {absence['reason']}\n**Início:** {absence['start_date']}\n**Retorno:** {absence['end_date']}",
                    inline=False
                )
            embed.set_footer(text=config["embed_config"]["confirmation"]["footer"].format(timestamp=datetime.now(self.cog.br_tz).strftime("%d/%m/%Y %H:%M")))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    class CustomizeEmbedModal(ui.Modal):
        def __init__(self, cog, guild_id: str, embed_type: str):
            super().__init__(f"Personalizar Embed: {embed_type.capitalize()}")
            self.cog = cog
            self.guild_id = guild_id
            self.embed_type = embed_type
            self.config = cog.load_config(guild_id)
            embed_config = self.config["embed_config"][embed_type]

            self.title_input = ui.TextInput(
                label="Título do Embed",
                default_value=embed_config["title"],
                required=True,
                max_length=256
            )
            self.add_item(self.title_input)

            self.description_input = ui.TextInput(
                label="Descrição do Embed",
                default_value=embed_config["description"],
                style=nextcord.TextInputStyle.paragraph,
                required=True,
                max_length=2000
            )
            self.add_item(self.description_input)

            self.color_input = ui.TextInput(
                label="Cor do Embed (R,G,B)",
                placeholder="Ex: 255,0,0 para vermelho",
                default_value=",".join(map(str, embed_config["color"])),
                required=True,
                max_length=20
            )
            self.add_item(self.color_input)

            self.thumbnail_input = ui.TextInput(
                label="URL do Thumbnail (Opcional)",
                default_value=embed_config["thumbnail"],
                required=False,
                max_length=512
            )
            self.add_item(self.thumbnail_input)

            self.footer_input = ui.TextInput(
                label="Footer do Embed (Opcional)",
                default_value=embed_config["footer"],
                required=False,
                max_length=2048
            )
            self.add_item(self.footer_input)

        async def callback(self, interaction: Interaction):
            try:
                color_match = re.match(r"(\d{1,3}),(\d{1,3}),(\d{1,3})", self.color_input.value)
                if not color_match or not all(0 <= int(x) <= 255 for x in color_match.groups()):
                    await interaction.response.send_message(
                        "Cor inválida! Use formato R,G,B (ex: 255,0,0).",
                        ephemeral=True
                    )
                    return

                self.config["embed_config"][self.embed_type].update({
                    "title": self.title_input.value,
                    "description": self.description_input.value,
                    "color": [int(x) for x in color_match.groups()],
                    "thumbnail": self.thumbnail_input.value or None,
                    "footer": self.footer_input.value or None
                })
                self.cog.save_config(self.guild_id, self.config)
                await interaction.response.send_message("Embed personalizado com sucesso!", ephemeral=True)
            except Exception as e:
                logger.error(f"Erro ao personalizar embed {self.embed_type} em {self.guild_id}: {e}")
                await interaction.response.send_message("Erro ao salvar personalização.", ephemeral=True)

    class ConfigView(ui.View):
        def __init__(self, cog, guild_id: str):
            super().__init__(timeout=None)
            self.cog = cog
            self.guild_id = guild_id
            self.config = cog.load_config(guild_id)

        async def update_embed(self, interaction: Interaction, embed: nextcord.Embed):
            try:
                await interaction.message.edit(embed=embed, view=self)
            except Exception as e:
                logger.error(f"Erro ao atualizar embed de configuração em {self.guild_id}: {e}")

        @ui.button(label="Ativar/Desativar", style=nextcord.ButtonStyle.grey, emoji="🔄", row=0)
        async def toggle_button(self, button: ui.Button, interaction: Interaction):
            self.config["enabled"] = not self.config["enabled"]
            self.cog.save_config(self.guild_id, self.config)
            embed = self.create_config_embed()
            button.label = self.config["button_config"]["close"]["label"]
            button.emoji = self.config["button_config"]["close"]["emoji"]
            button.style = getattr(nextcord.ButtonStyle, self.config["button_config"]["close"]["style"])
            await self.update_embed(interaction, embed)

        @ui.select(
            placeholder="Canal de Registro",
            options=[nextcord.SelectOption(label="Escolha um canal", value="placeholder", emoji="📝")],
            custom_id="register_channel_select",
            row=1
        )
        async def register_channel_select(self, select: ui.Select, interaction: Interaction):
            channels = [c for c in interaction.guild.text_channels if c.permissions_for(interaction.guild.me).send_messages]
            select.options = [
                nextcord.SelectOption(label=c.name, value=str(c.id), emoji="📝")
                for c in channels[:25]
            ]
            if interaction.data["values"][0] != "placeholder":
                channel_id = interaction.data["values"][0]
                channel = interaction.guild.get_channel(int(channel_id))
                if not channel:
                    await interaction.response.send_message("Canal inválido!", ephemeral=True)
                    return
                if not channel.permissions_for(interaction.guild.me).send_messages:
                    await interaction.response.send_message(
                        "Não tenho permissão para enviar mensagens nesse canal!", ephemeral=True
                    )
                    return
                self.config["register_channel_id"] = channel_id
                self.cog.save_config(self.guild_id, self.config)
                await self.cog.send_or_update_message(
                    self.config, self.guild_id, channel_id, self.config.get("register_message_id"), "register", self.cog.RegisterNicknameView(self.cog, self.guild_id)
                )
                embed = self.create_config_embed()
                await self.update_embed(interaction, embed)
            else:
                await interaction.response.defer()

        @ui.select(
            placeholder="Canal de Ausência",
            options=[nextcord.SelectOption(label="Escolha um canal", value="placeholder", emoji="🔔")],
            custom_id="absence_channel_select",
            row=2
        )
        async def absence_channel_select(self, select: ui.Select, interaction: Interaction):
            channels = [c for c in interaction.guild.text_channels if c.permissions_for(interaction.guild.me).send_messages]
            select.options = [
                nextcord.SelectOption(label=c.name, value=str(c.id), emoji="🔔")
                for c in channels[:25]
            ]
            if interaction.data["values"][0] != "placeholder":
                channel_id = interaction.data["values"][0]
                channel = interaction.guild.get_channel(int(channel_id))
                if not channel:
                    await interaction.response.send_message("Canal inválido!", ephemeral=True)
                    return
                if not channel.permissions_for(interaction.guild.me).send_messages:
                    await interaction.response.send_message(
                        "Não tenho permissão para enviar mensagens nesse canal!", ephemeral=True
                    )
                    return
                self.config["absence_channel_id"] = channel_id
                self.cog.save_config(self.guild_id, self.config)
                await self.cog.send_or_update_message(
                    self.config, self.guild_id, channel_id, self.config.get("absence_message_id"), "absence", self.cog.ReportAbsenceView(self.cog, self.guild_id)
                )
                embed = self.create_config_embed()
                await self.update_embed(interaction, embed)
            else:
                await interaction.response.defer()

        @ui.button(label="Personalizar Embeds", style=nextcord.ButtonStyle.green, emoji="🎨", row=3)
        async def customize_embed_button(self, button: ui.Button, interaction: Interaction):
            config = self.cog.load_config(self.guild_id)
            select = ui.Select(
                placeholder="Escolha o tipo de embed",
                options=[
                    nextcord.SelectOption(label="Registro", value="register", emoji="📝"),
                    nextcord.SelectOption(label="Ausência", value="absence", emoji="🔔"),
                    nextcord.SelectOption(label="Confirmação", value="confirmation", emoji="✅")
                ],
                custom_id="embed_type_select"
            )
            async def select_callback(interaction: Interaction):
                embed_type = interaction.data["values"][0]
                modal = self.cog.CustomizeEmbedModal(self.cog, self.guild_id, embed_type)
                await interaction.response.send_modal(modal)
            select.callback = select_callback
            view = ui.View()
            view.add_item(select)
            await interaction.response.send_message("Selecione o tipo de embed para personalizar:", view=view, ephemeral=True)

        @ui.button(label="Fechar", style=nextcord.ButtonStyle.red, emoji="❌", row=3)
        async def close_button(self, button: ui.Button, interaction: Interaction):
            if not self.config["enabled"]:
                await interaction.response.send_message(
                    "O sistema não está ativado. Clique em 'Ativar/Desativar' antes de fechar.",
                    ephemeral=True
                )
                return
            if not self.config["register_channel_id"] or not self.config["absence_channel_id"]:
                await interaction.response.send_message(
                    "Configure os canais de registro e ausência antes de fechar.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                "Configuração concluída! Os sistemas de registro e ausência estão ativos.",
                ephemeral=True
            )
            try:
                await interaction.message.delete()
            except Exception as e:
                logger.error(f"Erro ao deletar mensagem de configuração em {self.guild_id}: {e}")

        def create_config_embed(self):
            embed = nextcord.Embed(
                title="Configuração do Sistema de Membros",
                description="Configure os sistemas de registro de nicknames e notificação de ausência.",
                color=nextcord.Color.from_rgb(*self.config["embed_config"]["register"]["color"]),
                timestamp=datetime.now(self.cog.br_tz)
            )
            embed.add_field(
                name="Status",
                value=f"**Ativado:** {'Sim' if self.config['enabled'] else 'Não'}",
                inline=True
            )
            embed.add_field(
                name="Canal de Registro",
                value=f"<#{self.config['register_channel_id']}>" if self.config["register_channel_id"] else "Não configurado",
                inline=True
            )
            embed.add_field(
                name="Canal de Ausência",
                value=f"<#{self.config['absence_channel_id']}>" if self.config["absence_channel_id"] else "Não configurado",
                inline=True
            )
            embed.set_footer(text="Member Management - by CodeProjects")
            return embed

    @tasks.loop(hours=24)
    async def update_absences(self):
        """Marca ausências expiradas como inativas."""
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT id, guild_id, end_date FROM member_absences WHERE status = ?", ("ativa",))
            absences = cursor.fetchall()
            now = datetime.now(self.br_tz)

            for absence in absences:
                end_date = datetime.strptime(absence["end_date"], "%d/%m/%Y")
                if now.date() > end_date.date():
                    cursor.execute(
                        "UPDATE member_absences SET status = ? WHERE id = ?",
                        ("expirada", absence["id"])
                    )
                    logger.info(f"Ausência {absence['id']} em {absence['guild_id']} marcada como expirada")
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro no loop update_absences: {e}")

    @update_absences.before_loop
    async def before_update_absences(self):
        await self.bot.wait_until_ready()
        self.init_db()

    @nextcord.slash_command(name="config_member_system", description="Configura o sistema de registro e ausência.")
    @commands.has_permissions(administrator=True)
    async def config_member_system(self, interaction: Interaction):
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)
        view = self.ConfigView(self, guild_id)
        embed = view.create_config_embed()

        try:
            await interaction.response.send_message(embed=embed, view=view)
            logger.info(f"Configuração member_system iniciada por {interaction.user.id} em {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao enviar configuração member_system em {guild_id}: {e}")
            await interaction.response.send_message(
                "Erro ao iniciar a configuração. Tente novamente.", ephemeral=True
            )

    @nextcord.slash_command(name="reset_member_system", description="Reseta a configuração do sistema de membros.")
    @commands.has_permissions(administrator=True)
    async def reset_member_system(self, interaction: Interaction):
        guild_id = str(interaction.guild.id)
        try:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM member_config WHERE guild_id = ?", (guild_id,))
            self.db.commit()
            logger.info(f"Configuração resetada para {guild_id}")
            await interaction.response.send_message(
                "Configuração do sistema de membros resetada com sucesso! Use /config_member_system para configurar novamente.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Erro ao resetar configuração de {guild_id}: {e}")
            await interaction.response.send_message(
                "Erro ao resetar configuração. Verifique os logs.", ephemeral=True
            )

def setup(bot):
    bot.add_cog(MemberManagementCog(bot))