# cogs/TicketCog.py
# Description: Sistema de tickets personalizado com transcrição em HTML estilizada e visualização online via Flask
# Date of Creation: 29/04/2025
# Created by: Grok (xAI)
# Version: 5.3
# Developer Of Version: Grok (xAI)

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui
import sqlite3
import json
from datetime import datetime
import pytz
import asyncio
from typing import Dict, Optional
import logging
import os
import html
from io import BytesIO
import uuid

logger = logging.getLogger("DataBit.TicketCog")

class TicketCog(commands.Cog):
    def __init__(self, bot):
        logger.info("Inicializando TicketCog")
        self.bot = bot
        self.db_path = "ticket_system.db"
        self.transcript_base_url = "https://databit-v1.discloud.app/transcripts"
        try:
            self.init_database()
            self.active_tickets: Dict[str, Dict] = {}
            self.br_tz = pytz.timezone("America/Sao_Paulo")
            self.load_active_tickets()
            os.makedirs("transcripts", exist_ok=True)
            logger.info("TicketCog inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar TicketCog: {e}", exc_info=True)
            raise

    def init_database(self):
        """Inicializa o banco de dados SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    guild_id TEXT,
                    user_id TEXT,
                    category TEXT,
                    created_at TEXT,
                    assumed_by TEXT,
                    last_activity TEXT,
                    status TEXT,
                    data TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ticket_config (
                    guild_id TEXT PRIMARY KEY,
                    config TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ticket_categories (
                    guild_id TEXT,
                    category_id TEXT,
                    name TEXT,
                    description TEXT,
                    emoji TEXT,
                    PRIMARY KEY (guild_id, category_id)
                )
            """)
            conn.commit()

    def load_categories(self, guild_id: str) -> Dict[str, Dict]:
        """Carrega as categorias de tickets do SQLite para um servidor."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT category_id, name, description, emoji FROM ticket_categories WHERE guild_id = ?", (guild_id,))
                categories = {}
                for row in cursor.fetchall():
                    categories[row[0]] = {
                        "name": row[1],
                        "desc": row[2],
                        "emoji": row[3]
                    }
                logger.info(f"Carregadas {len(categories)} categorias para guild_id {guild_id}")
                return categories
        except Exception as e:
            logger.error(f"Erro ao carregar categorias para guild_id {guild_id}: {e}", exc_info=True)
            return {}

    def save_category(self, guild_id: str, category_id: str, name: str, description: str, emoji: Optional[str]):
        """Salva uma nova categoria no SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO ticket_categories (guild_id, category_id, name, description, emoji)
                    VALUES (?, ?, ?, ?, ?)
                """, (guild_id, category_id, name, description, emoji))
                conn.commit()
                logger.info(f"Categoria {category_id} salva para guild_id {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar categoria {category_id} para guild_id {guild_id}: {e}", exc_info=True)

    def update_category(self, guild_id: str, category_id: str, name: Optional[str] = None, description: Optional[str] = None, emoji: Optional[str] = None):
        """Atualiza uma categoria existente no SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, description, emoji FROM ticket_categories WHERE guild_id = ? AND category_id = ?", (guild_id, category_id))
                current = cursor.fetchone()
                if not current:
                    return False
                new_name = name if name is not None else current[0]
                new_description = description if description is not None else current[1]
                new_emoji = emoji if emoji is not None else current[2]
                cursor.execute("""
                    UPDATE ticket_categories
                    SET name = ?, description = ?, emoji = ?
                    WHERE guild_id = ? AND category_id = ?
                """, (new_name, new_description, new_emoji, guild_id, category_id))
                conn.commit()
                logger.info(f"Categoria {category_id} atualizada para guild_id {guild_id}")
                return True
        except Exception as e:
            logger.error(f"Erro ao atualizar categoria {category_id} para guild_id {guild_id}: {e}", exc_info=True)
            return False

    def delete_category(self, guild_id: str, category_id: str):
        """Remove uma categoria do SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ticket_categories WHERE guild_id = ? AND category_id = ?", (guild_id, category_id))
                conn.commit()
                logger.info(f"Categoria {category_id} removida para guild_id {guild_id}")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Erro ao remover categoria {category_id} para guild_id {guild_id}: {e}", exc_info=True)
            return False

    def load_active_tickets(self):
        """Carrega tickets com status 'aberto' do SQLite para o cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ticket_id, user_id, category, created_at, assumed_by, last_activity, status FROM tickets WHERE status = 'aberto'")
                tickets = cursor.fetchall()
                for ticket in tickets:
                    ticket_key = ticket[0]
                    self.active_tickets[ticket_key] = {
                        "user_id": ticket[1],
                        "category": ticket[2],
                        "created_at": datetime.fromisoformat(ticket[3]),
                        "assumed_by": ticket[4],
                        "last_activity": datetime.fromisoformat(ticket[5]),
                        "status": ticket[6]
                    }
                logger.info(f"Carregados {len(self.active_tickets)} tickets ativos do SQLite")
        except Exception as e:
            logger.error(f"Erro ao carregar tickets ativos: {e}", exc_info=True)

    def load_config(self, guild_id: str) -> dict:
        """Carrega a configuração de tickets do SQLite."""
        default_config = {
            "categoria_tickets": None,
            "canal_menu": None,
            "cargo_suporte": None,
            "canal_avaliacoes": None,
            "canal_logs": None,
            "canal_transcripts": None,
            "embed_color_rgb": [43, 45, 49],
            "tempo_notificacao_horas": 24,
            "tempo_fechamento_horas": 48,
            "menu_message_id": None,
            "embed_menu": {
                "title": "<:logo2:1350090849903710208> Ticket's System",
                "description": (
                    "Bem-vindo ao nosso sistema de tickets! 🎟\n\n"
                    "Selecione uma categoria abaixo para abrir um ticket.\n"
                    "Um canal privado será criado, e nossa equipe entrará em contato.\n\n"
                    "Estamos aqui para ajudar! 😊"
                ),
                "thumbnail": "https://imgur.com/FI0J8Aw.png",
                "image": "https://imgur.com/OZ95Zry.png",
                "footer": "Tickets System - by CodeProjects"
            },
            "embed_panel": {
                "title": "<:open:1350167913591734363> Novo Ticket Aberto!",
                "thumbnail": "https://imgur.com/FI0J8Aw.png",
                "image": "https://imgur.com/iTQBsLh.png"
            },
            "embed_assumed": {
                "title": "Ticket Assumido",
                "thumbnail": "",
                "image": "",
                "footer": ""
            },
            "embed_inactivity": {
                "title": "🚨 Aviso de Inatividade",
                "thumbnail": "",
                "image": "",
                "footer": ""
            },
            "embed_evaluation": {
                "title": "📝 Avalie o Atendimento",
                "description": "Como você avalia o atendimento recebido?",
                "thumbnail": "",
                "image": "",
                "footer": ""
            }
        }
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT config FROM ticket_config WHERE guild_id = ?", (guild_id,))
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                return default_config
        except Exception as e:
            logger.error(f"Erro ao carregar ticket_config de {guild_id}: {e}", exc_info=True)
            return default_config

    def save_config(self, guild_id: str, config: dict):
        """Salva a configuração de tickets no SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO ticket_config (guild_id, config)
                    VALUES (?, ?)
                """, (guild_id, json.dumps(config)))
                conn.commit()
                logger.info(f"Configuração de tickets salva para {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar ticket_config de {guild_id}: {e}", exc_info=True)

    def load_ticket(self, guild_id: str, ticket_id: str) -> dict:
        """Carrega um ticket específico do SQLite."""
        ticket_key = f"{guild_id}_{ticket_id}"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT data FROM tickets WHERE ticket_id = ?", (ticket_key,))
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                return {}
        except Exception as e:
            logger.error(f"Erro ao carregar ticket {ticket_key}: {e}", exc_info=True)
            return {}

    def save_ticket(self, guild_id: str, ticket_id: str, data: dict):
        """Salva um ticket no SQLite."""
        ticket_key = f"{guild_id}_{ticket_id}"
        data = data.copy()
        data["ticket_id"] = ticket_key
        data["guild_id"] = guild_id
        if "created_at" not in data:
            data["created_at"] = datetime.now(self.br_tz)
        if "last_activity" not in data:
            data["last_activity"] = data["created_at"]

        # Converter datetime para string antes de salvar
        if isinstance(data["created_at"], datetime):
            data["created_at"] = data["created_at"].isoformat()
        if isinstance(data["last_activity"], datetime):
            data["last_activity"] = data["last_activity"].isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO tickets (
                        ticket_id, guild_id, user_id, category, created_at, assumed_by, last_activity, status, data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticket_key,
                    guild_id,
                    data["user_id"],
                    data["category"],
                    data["created_at"],
                    data.get("assumed_by"),
                    data["last_activity"],
                    data["status"],
                    json.dumps(data)
                ))
                conn.commit()
                logger.info(f"Ticket salvo: {ticket_key}")
        except Exception as e:
            logger.error(f"Erro ao salvar ticket {ticket_key}: {e}", exc_info=True)

    async def generate_transcript(self, channel: nextcord.TextChannel, ticket_data: dict) -> tuple[str, str]:
        """Gera um transcript em HTML do canal do ticket com Tailwind CSS."""
        guild_id = str(channel.guild.id)
        categories = self.load_categories(guild_id)
        category_name = categories.get(ticket_data["category"], {"name": "Desconhecida"})["name"]

        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            messages.append({
                "author": message.author,
                "content": message.content,
                "timestamp": message.created_at.astimezone(self.br_tz),
                "attachments": [attachment.url for attachment in message.attachments]
            })

        html_content = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcrição do Ticket #{ticket_id}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            background-color: #36393f;
        }}
    </style>
</head>
<body class="min-h-screen flex flex-col items-center justify-center">
    <div class="w-full max-w-3xl bg-gray-800 rounded-lg shadow-lg p-6">
        <div class="text-center mb-6">
            <h1 class="text-2xl font-bold text-white">Transcrição do Ticket #{ticket_id}</h1>
            <p class="text-gray-400">Categoria: {category}</p>
            <p class="text-gray-400">Aberto por: {user_name} | Fechado em: {closed_at}</p>
        </div>
        <div class="space-y-4">
"""

        # Criar dicionário com valores para formatação
        format_data = {
            "ticket_id": channel.id,
            "category": category_name,
            "user_name": self.bot.get_user(int(ticket_data["user_id"])).name,
            "closed_at": datetime.now(self.br_tz).strftime("%d/%m/%Y %H:%M")
        }

        # Usar format_map para evitar KeyError em chaves não fornecidas
        html_content = html_content.format_map(format_data)

        for msg in messages:
            avatar_url = msg["author"].avatar.url if msg["author"].avatar else "https://discord.com/assets/1f0bfc0865d324c25817.png"
            content = html.escape(msg["content"]) if msg["content"] else ""
            timestamp = msg["timestamp"].strftime("%d/%m/%Y %H:%M")
            attachments = "".join([f'<a href="{url}" class="text-blue-400 hover:underline">{os.path.basename(url)}</a><br>' for url in msg["attachments"]])

            html_content += f"""
            <div class="flex items-start space-x-3">
                <img src="{avatar_url}" alt="Avatar" class="w-10 h-10 rounded-full">
                <div class="flex-1">
                    <div class="flex items-center space-x-2">
                        <span class="font-semibold text-white">{html.escape(msg["author"].name)}</span>
                        <span class="text-xs text-gray-500">{timestamp}</span>
                    </div>
                    <p class="text-gray-200">{content}</p>
                    {attachments}
                </div>
            </div>
            """

        html_content += """
        </div>
    </div>
</body>
</html>
"""

        transcript_filename = f"ticket_{channel.id}_{datetime.now(self.br_tz).strftime('%Y%m%d_%H%M%S')}.html"
        transcript_path = f"transcripts/{transcript_filename}"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return transcript_path, transcript_filename

    async def send_transcript(self, config: dict, ticket_data: dict, channel: nextcord.TextChannel):
        """Envia o transcript para o canal de logs com botões para visualização e download."""
        try:
            transcript_path, transcript_filename = await self.generate_transcript(channel, ticket_data)
            if config.get("canal_transcripts"):
                transcripts_channel = self.bot.get_channel(config["canal_transcripts"])
                if transcripts_channel:
                    guild_id = str(channel.guild.id)
                    categories = self.load_categories(guild_id)
                    category_name = categories.get(ticket_data["category"], {"name": "Desconhecida"})["name"]
                    embed = nextcord.Embed(
                        title="Nova Transcrição de Ticket",
                        description=(
                            f"**Ticket ID:** {channel.id}\n"
                            f"**Categoria:** {category_name}\n"
                            f"**Aberto por:** {self.bot.get_user(int(ticket_data['user_id'])).mention}\n"
                            f"**Fechado em:** {datetime.now(self.br_tz).strftime('%d/%m/%Y %H:%M')}"
                        ),
                        color=nextcord.Color.from_rgb(*config["embed_color_rgb"]),
                        timestamp=datetime.now(self.br_tz)
                    )

                    view = ui.View(timeout=None)

                    # Botão Ver Transcript Online
                    online_button = ui.Button(
                        label="Ver Transcript Online",
                        style=nextcord.ButtonStyle.link,
                        url=f"{self.transcript_base_url}/{transcript_filename}",
                        emoji="🌐"
                    )
                    view.add_item(online_button)

                    # Botão Download Transcript
                    with open(transcript_path, "rb") as f:
                        file = nextcord.File(BytesIO(f.read()), filename=transcript_filename)
                        download_button = ui.Button(
                            label="Download Transcript",
                            style=nextcord.ButtonStyle.grey,
                            emoji="📥"
                        )
                        async def download_callback(interaction: Interaction):
                            with open(transcript_path, "rb") as f:
                                file = nextcord.File(BytesIO(f.read()), filename=transcript_filename)
                                await interaction.response.send_message(file=file, ephemeral=True)
                        download_button.callback = download_callback
                        view.add_item(download_button)

                    await transcripts_channel.send(embed=embed, view=view, file=file)
                    logger.info(f"Transcrição enviada para o canal {transcripts_channel.id}")
        except Exception as e:
            logger.error(f"Erro ao gerar/enviar transcrição para o ticket {channel.id}: {e}", exc_info=True)

    async def update_menu_embed(self, guild_id: str):
        """Atualiza o menu de tickets existente com as categorias atuais."""
        config = self.load_config(guild_id)
        if not config.get("canal_menu") or not config.get("menu_message_id"):
            return
        channel = self.bot.get_channel(config["canal_menu"])
        if not channel:
            return
        try:
            message = await channel.fetch_message(config["menu_message_id"])
            embed_config = config["embed_menu"]
            embed = nextcord.Embed(
                title=embed_config["title"],
                description=embed_config["description"],
                color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
            )
            if embed_config["thumbnail"]:
                embed.set_thumbnail(url=embed_config["thumbnail"])
            if embed_config["image"]:
                embed.set_image(url=embed_config["image"])
            if embed_config["footer"]:
                embed.set_footer(text=embed_config["footer"])

            categories = self.load_categories(guild_id)
            if not categories:
                await message.edit(embed=embed, view=None, content="Nenhuma categoria configurada. Use /add_category para adicionar categorias.")
                return

            options = [
                nextcord.SelectOption(label=cat["name"], value=cat_id, emoji=cat["emoji"] or "<:seta:1350166397040463922>", description=cat["desc"])
                for cat_id, cat in categories.items()
            ]
            select = ui.Select(placeholder="Selecione uma categoria...", options=options)

            async def select_callback(interaction: Interaction):
                category_id = interaction.data["values"][0]
                ticket_channel = await self.create_ticket_channel(interaction, guild_id, category_id)
                if ticket_channel:
                    await interaction.response.send_message(f"Ticket criado: {ticket_channel.mention}", ephemeral=True)
                else:
                    await interaction.response.send_message("Erro ao criar o ticket. Contate um administrador.", ephemeral=True)

            select.callback = select_callback
            view = ui.View(timeout=None)
            view.add_item(select)

            await message.edit(embed=embed, view=view, content=None)
            logger.info(f"Menu de tickets atualizado em {channel.id}")
        except nextcord.errors.NotFound:
            # Se a mensagem não for encontrada, recriar o menu
            logger.warning(f"Mensagem do menu {config['menu_message_id']} não encontrada. Recriando o menu.")
            await self.create_menu_embed(guild_id, channel)
        except Exception as e:
            logger.error(f"Erro ao atualizar menu de tickets para guild_id {guild_id}: {e}", exc_info=True)

    async def create_menu_embed(self, guild_id: str, channel: nextcord.TextChannel):
        """Cria ou atualiza o menu de tickets no canal especificado."""
        config = self.load_config(guild_id)
        embed_config = config["embed_menu"]
        embed = nextcord.Embed(
            title=embed_config["title"],
            description=embed_config["description"],
            color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
        )
        if embed_config["thumbnail"]:
            embed.set_thumbnail(url=embed_config["thumbnail"])
        if embed_config["image"]:
            embed.set_image(url=embed_config["image"])
        if embed_config["footer"]:
            embed.set_footer(text=embed_config["footer"])

        categories = self.load_categories(guild_id)
        if not categories:
            message = await channel.send(embed=embed, content="Nenhuma categoria configurada. Use /add_category para adicionar categorias.")
            config["canal_menu"] = channel.id
            config["menu_message_id"] = message.id
            self.save_config(guild_id, config)
            return

        options = [
            nextcord.SelectOption(label=cat["name"], value=cat_id, emoji=cat["emoji"] or "<:seta:1350166397040463922>", description=cat["desc"])
            for cat_id, cat in categories.items()
        ]
        select = ui.Select(placeholder="Selecione uma categoria...", options=options)

        async def select_callback(interaction: Interaction):
            category_id = interaction.data["values"][0]
            ticket_channel = await self.create_ticket_channel(interaction, guild_id, category_id)
            if ticket_channel:
                await interaction.response.send_message(f"Ticket criado: {ticket_channel.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("Erro ao criar o ticket. Contate um administrador.", ephemeral=True)

        select.callback = select_callback
        view = ui.View(timeout=None)
        view.add_item(select)

        message = await channel.send(embed=embed, view=view)
        config["canal_menu"] = channel.id
        config["menu_message_id"] = message.id
        self.save_config(guild_id, config)

    async def create_ticket_channel(self, interaction: Interaction, guild_id: str, category_id: str):
        """Cria um canal de ticket com base na categoria selecionada."""
        config = self.load_config(guild_id)
        categories = self.load_categories(guild_id)
        if category_id not in categories:
            await interaction.response.send_message("Categoria inválida!", ephemeral=True)
            return None

        category_channel = interaction.guild.get_channel(config["categoria_tickets"])
        if not category_channel or not isinstance(category_channel, nextcord.CategoryChannel):
            await interaction.response.send_message("Categoria de tickets não configurada ou inválida!", ephemeral=True)
            return None

        # Criar canal de ticket
        ticket_channel = await interaction.guild.create_text_channel(
            f"🎫・ticket-{interaction.user.name}",
            category=category_channel,
            overwrites={
                interaction.guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
                interaction.user: nextcord.PermissionOverwrite(view_channel=True, send_messages=True),
                self.bot.user: nextcord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
                interaction.guild.get_role(config["cargo_suporte"]): nextcord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
        )

        # Registrar dados do ticket
        ticket_key = f"{guild_id}_{ticket_channel.id}"
        created_at = datetime.now(self.br_tz)
        self.active_tickets[ticket_key] = {
            "user_id": str(interaction.user.id),
            "category": category_id,
            "created_at": created_at,
            "assumed_by": None,
            "assumed_at": None,
            "last_activity": created_at,
            "status": "aberto"
        }
        self.save_ticket(guild_id, str(ticket_channel.id), self.active_tickets[ticket_key])
        
        # Log detalhado
        logger.info(
            f"Novo ticket criado: {ticket_channel.id} por {interaction.user} (ID: {interaction.user.id}). "
            f"Categoria: {categories[category_id]['name']}. "
            f"Criado em: {created_at.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        # Enviar log para o canal de logs
        if config["canal_logs"]:
            logs_channel = self.bot.get_channel(config["canal_logs"])
            if logs_channel:
                log_embed = nextcord.Embed(
                    title="🎫 Novo Ticket Aberto",
                    color=nextcord.Color.green(),
                    timestamp=created_at
                )
                log_embed.add_field(
                    name="👤 Usuário",
                    value=f"{interaction.user.mention}\nID: {interaction.user.id}",
                    inline=True
                )
                log_embed.add_field(
                    name="🎟️ Ticket",
                    value=f"ID: {ticket_channel.id}\nCategoria: {categories[category_id]['name']}",
                    inline=True
                )
                log_embed.add_field(
                    name="⏱️ Criado em",
                    value=created_at.strftime("%d/%m/%Y %H:%M:%S"),
                    inline=False
                )
                await logs_channel.send(embed=log_embed)

        await self.create_ticket_panel(ticket_channel, interaction.user, config, ticket_key)
        return ticket_channel

    async def create_ticket_panel(self, channel: nextcord.TextChannel, user: nextcord.Member, config: dict, ticket_key: str):
        """Cria o painel de controle do ticket."""
        ticket_data = self.active_tickets[ticket_key]
        guild_id = str(channel.guild.id)
        categories = self.load_categories(guild_id)
        category = categories.get(ticket_data["category"], {"name": "Desconhecida"})
        created_at = ticket_data["created_at"].strftime("%d/%m/%Y %H:%M")
        embed_config = config["embed_panel"]

        embed = nextcord.Embed(
            title=embed_config["title"],
            description=(
                f"<:readd:1350154929746215037> **Quem Abriu:** {user.mention}\n"
                f"<:readd:1350154929746215037> **Categoria:** {category['name']}\n"
                f"<:readd:1350154929746215037> **Data e Hora da Abertura:** {created_at}\n"
                f"<:readd:1350154929746215037> **Atendente Responsável:** Nenhum"
            ),
            color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
        )
        if embed_config["thumbnail"]:
            embed.set_thumbnail(url=embed_config["thumbnail"])
        if embed_config["image"]:
            embed.set_image(url=embed_config["image"])

        view = ui.View(timeout=None)

        assume_button = ui.Button(label="Assumir Ticket", style=nextcord.ButtonStyle.green, emoji="<:accept:1350169522077962324>")
        assume_button.callback = lambda i: self.assume_ticket(i, channel, user, config, ticket_key, embed, view)
        view.add_item(assume_button)

        close_button = ui.Button(label="Encerrar Ticket", style=nextcord.ButtonStyle.red, emoji="<:rejects:1350169812751614064>")
        close_button.callback = lambda i: self.close_ticket(i, channel, user, config, ticket_key, embed, view)
        view.add_item(close_button)

        notify_button = ui.Button(label="Notificar", style=nextcord.ButtonStyle.grey, emoji="<:notify:1350170693978951820>")
        notify_button.callback = lambda i: self.notify_inactivity(i, channel, user, config, ticket_key, embed, view)
        view.add_item(notify_button)

        await channel.send(embed=embed, view=view)
        asyncio.create_task(self.monitor_inactivity(channel, user, config, ticket_key))

    async def assume_ticket(self, interaction: Interaction, channel, user, config, ticket_key, embed, view):
        """Permite que um atendente assuma o ticket."""
        ticket_data = self.active_tickets[ticket_key]
        if ticket_data["assumed_by"]:
            await interaction.response.send_message("Este ticket já foi assumido!", ephemeral=True)
            return
        if config["cargo_suporte"] not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("Apenas atendentes podem assumir tickets!", ephemeral=True)
            return

        ticket_data["assumed_by"] = str(interaction.user.id)
        ticket_data["last_activity"] = datetime.now(self.br_tz)
        self.save_ticket(str(channel.guild.id), str(channel.id), ticket_data)
        guild_id = str(channel.guild.id)
        categories = self.load_categories(guild_id)
        category = categories.get(ticket_data["category"], {"name": "Desconhecida"})
        created_at = ticket_data["created_at"].strftime("%d/%m/%Y %H:%M")
        embed_config = config["embed_assumed"]
        embed.description = (
            f"<:readd:1350154929746215037> **Quem Abriu:** {user.mention}\n"
            f"<:readd:1350154929746215037> **Categoria:** {category['name']}\n"
            f"<:readd:1350154929746215037> **Data e Hora da Abertura:** {created_at}\n"
            f"<:readd:1350154929746215037> **Atendente Responsável:** {interaction.user.mention}"
        )
        await channel.send(f"{user.mention}, seu ticket foi assumido por {interaction.user.mention}!")
        await interaction.message.edit(embed=embed, view=view)

        assumed_embed = nextcord.Embed(
            title=embed_config["title"],
            description=f"Seu ticket no canal {channel.mention} foi assumido por {interaction.user.mention}.",
            color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
        )
        if embed_config["thumbnail"]:
            assumed_embed.set_thumbnail(url=embed_config["thumbnail"])
        if embed_config["image"]:
            assumed_embed.set_image(url=embed_config["image"])
        if embed_config["footer"]:
            assumed_embed.set_footer(text=embed_config["footer"])

        try:
            await user.send(embed=assumed_embed)
        except nextcord.Forbidden:
            await channel.send(f"Não consegui notificar {user.mention} por DM (bloqueada).")
        await interaction.response.send_message("Ticket assumido!", ephemeral=True)

    async def close_ticket(self, interaction: Interaction, channel, user, config, ticket_key, embed, view):
        """Encerra o ticket e deleta o canal."""
        ticket_data = self.active_tickets[ticket_key]
        if ticket_data.get("status") == "fechado":
            await interaction.response.send_message("Este ticket já está fechado!", ephemeral=True)
            return

        # Registrar quem fechou o ticket
        closed_by = str(interaction.user.id)
        closed_at = datetime.now(self.br_tz)
        
        # Atualizar dados do ticket
        ticket_data["status"] = "fechado"
        ticket_data["closed_by"] = closed_by
        ticket_data["closed_at"] = closed_at.isoformat()
        
        self.save_ticket(str(channel.guild.id), str(channel.id), ticket_data)
        
        # Log detalhado
        logger.info(
            f"Ticket {channel.id} fechado por {interaction.user} (ID: {closed_by}). "
            f"Aberto por: {ticket_data['user_id']}, Assumido por: {ticket_data.get('assumed_by', 'Ninguém')}. "
            f"Tempo aberto: {(closed_at - ticket_data['created_at']).total_seconds()/3600:.2f} horas."
        )

        await interaction.response.send_message("Ticket será encerrado e deletado em 5 segundos...", ephemeral=True)
        await interaction.message.edit(view=None)
        await channel.edit(name=f"closed-ticket-{user.name}")

        # Enviar log completo para o canal de logs
        if config["canal_logs"]:
            logs_channel = self.bot.get_channel(config["canal_logs"])
            if logs_channel:
                guild_id = str(channel.guild.id)
                categories = self.load_categories(guild_id)
                category_name = categories.get(ticket_data["category"], {"name": "Desconhecida"})["name"]
                
                # Embed de log detalhado
                log_embed = nextcord.Embed(
                    title="📝 Ticket Encerrado - Relatório Completo",
                    color=nextcord.Color.from_rgb(*config["embed_color_rgb"]),
                    timestamp=closed_at
                )
                
                # Informações básicas
                opener = self.bot.get_user(int(ticket_data["user_id"]))
                log_embed.add_field(
                    name="👤 Usuário",
                    value=f"{opener.mention}\nID: {opener.id}",
                    inline=True
                )
                
                # Informações do ticket
                created_at = ticket_data["created_at"].strftime("%d/%m/%Y %H:%M:%S") if isinstance(ticket_data["created_at"], datetime) else ticket_data["created_at"]
                closed_at_str = closed_at.strftime("%d/%m/%Y %H:%M:%S")
                log_embed.add_field(
                    name="🎟️ Ticket",
                    value=f"ID: {channel.id}\nCategoria: {category_name}",
                    inline=True
                )
                log_embed.add_field(
                    name="⏱️ Tempo",
                    value=f"Aberto em: {created_at}\nFechado em: {closed_at_str}",
                    inline=False
                )
                
                # Informações de atendimento
                if ticket_data.get("assumed_by"):
                    staff = self.bot.get_user(int(ticket_data["assumed_by"]))
                    assumed_at = ticket_data.get("assumed_at", "Desconhecido")
                    if isinstance(assumed_at, str):
                        try:
                            assumed_at = datetime.fromisoformat(assumed_at).strftime("%d/%m/%Y %H:%M:%S")
                        except:
                            assumed_at = "Desconhecido"
                    
                    log_embed.add_field(
                        name="🛎️ Atendimento",
                        value=f"Atendente: {staff.mention}\nAssumido em: {assumed_at}",
                        inline=True
                    )
                
                # Quem fechou
                closer = interaction.user
                log_embed.add_field(
                    name="🔒 Fechado por",
                    value=f"{closer.mention}\nID: {closer.id}",
                    inline=True
                )
                
                # Estatísticas
                if isinstance(ticket_data["created_at"], datetime):
                    duration = (closed_at - ticket_data["created_at"]).total_seconds()
                    hours, remainder = divmod(duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                else:
                    duration_str = "Desconhecido"
                
                log_embed.add_field(
                    name="📊 Estatísticas",
                    value=f"Duração total: {duration_str}\nMensagens: {len([m async for m in channel.history(limit=None)])}",
                    inline=False
                )
                
                await logs_channel.send(embed=log_embed)

        await self.send_transcript(config, ticket_data, channel)
        await self.request_evaluation(user, config, ticket_data, channel)
        del self.active_tickets[ticket_key]
        await asyncio.sleep(5)
        await channel.delete()

    async def notify_inactivity(self, interaction: Interaction, channel, user, config, ticket_key, embed, view):
        """Notifica o usuário sobre inatividade no ticket."""
        ticket_data = self.active_tickets[ticket_key]
        if ticket_data["assumed_by"] and str(interaction.user.id) != ticket_data["assumed_by"]:
            await interaction.response.send_message("Apenas o atendente responsável pode notificar!", ephemeral=True)
            return

        embed_config = config["embed_inactivity"]
        inactivity_embed = nextcord.Embed(
            title=embed_config["title"],
            description=f"Seu ticket em {channel.mention} está inativo há muito tempo. Responda em até {config['tempo_fechamento_horas'] - config['tempo_notificacao_horas']} horas ou ele será encerrado automaticamente.",
            color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
        )
        if embed_config["thumbnail"]:
            inactivity_embed.set_thumbnail(url=embed_config["thumbnail"])
        if embed_config["image"]:
            inactivity_embed.set_image(url=embed_config["image"])
        if embed_config["footer"]:
            inactivity_embed.set_footer(text=embed_config["footer"])

        try:
            await user.send(embed=inactivity_embed)
            await channel.send(f"{user.mention} foi notificado sobre a inatividade.")
        except nextcord.Forbidden:
            await channel.send(f"Não consegui notificar {user.mention} por DM (bloqueada).")
        await interaction.response.send_message("Notificação enviada!", ephemeral=True)

    async def monitor_inactivity(self, channel: nextcord.TextChannel, user: nextcord.Member, config: dict, ticket_key: str):
        """Monitora a inatividade do ticket e fecha automaticamente se necessário."""
        while ticket_key in self.active_tickets:
            await asyncio.sleep(3600)  # Verificar a cada hora
            ticket_data = self.active_tickets.get(ticket_key, {})
            last_activity = ticket_data["last_activity"]
            hours_inactive = (datetime.now(self.br_tz) - last_activity).total_seconds() / 3600
            
            # Log de verificação de inatividade
            logger.debug(
                f"Verificando inatividade do ticket {channel.id}. "
                f"Horas inativo: {hours_inactive:.2f}/{config['tempo_fechamento_horas']}. "
                f"Última atividade: {last_activity.strftime('%d/%m/%Y %H:%M:%S')}"
            )

            if hours_inactive >= config["tempo_notificacao_horas"]:
                # Log de notificação de inatividade
                logger.info(
                    f"Ticket {channel.id} inativo por {hours_inactive:.2f} horas. "
                    f"Notificando usuário {user} (ID: {user.id})."
                )
                await channel.send(f"{user.mention}, seu ticket está inativo há {int(hours_inactive)} horas. Responda ou ele será fechado em breve!")
                
            if hours_inactive >= config["tempo_fechamento_horas"]:
                # Registrar fechamento por inatividade
                closed_at = datetime.now(self.br_tz)
                ticket_data["status"] = "fechado"
                ticket_data["closed_by"] = "auto"
                ticket_data["closed_at"] = closed_at.isoformat()
                self.save_ticket(str(channel.guild.id), str(channel.id), ticket_data)
                
                # Log detalhado
                logger.info(
                    f"Ticket {channel.id} fechado automaticamente por inatividade. "
                    f"Aberto por: {ticket_data['user_id']}, Assumido por: {ticket_data.get('assumed_by', 'Ninguém')}. "
                    f"Tempo inativo: {hours_inactive:.2f} horas. "
                    f"Tempo total aberto: {(closed_at - ticket_data['created_at']).total_seconds()/3600:.2f} horas."
                )

                # Enviar log completo para o canal de logs
                if config["canal_logs"]:
                    logs_channel = self.bot.get_channel(config["canal_logs"])
                    if logs_channel:
                        guild_id = str(channel.guild.id)
                        categories = self.load_categories(guild_id)
                        category_name = categories.get(ticket_data["category"], {"name": "Desconhecida"})["name"]
                        
                        log_embed = nextcord.Embed(
                            title="⏳ Ticket Encerrado por Inatividade",
                            color=nextcord.Color.orange(),
                            timestamp=closed_at
                        )
                        
                        opener = self.bot.get_user(int(ticket_data["user_id"]))
                        log_embed.add_field(
                            name="👤 Usuário",
                            value=f"{opener.mention}\nID: {opener.id}",
                            inline=True
                        )
                        
                        created_at = ticket_data["created_at"].strftime("%d/%m/%Y %H:%M:%S") if isinstance(ticket_data["created_at"], datetime) else ticket_data["created_at"]
                        log_embed.add_field(
                            name="🎟️ Ticket",
                            value=f"ID: {channel.id}\nCategoria: {category_name}",
                            inline=True
                        )
                        
                        if ticket_data.get("assumed_by"):
                            staff = self.bot.get_user(int(ticket_data["assumed_by"]))
                            log_embed.add_field(
                                name="🛎️ Atendente",
                                value=f"{staff.mention}\nID: {staff.id}",
                                inline=True
                            )
                        
                        log_embed.add_field(
                            name="⏱️ Tempo",
                            value=f"Aberto em: {created_at}\nFechado em: {closed_at.strftime('%d/%m/%Y %H:%M:%S')}",
                            inline=False
                        )
                        
                        log_embed.add_field(
                            name="📊 Estatísticas",
                            value=(
                                f"Tempo inativo: {hours_inactive:.1f} horas\n"
                                f"Tempo total: {(closed_at - ticket_data['created_at']).total_seconds()/3600:.1f} horas\n"
                                f"Mensagens: {len([m async for m in channel.history(limit=None)])}"
                            ),
                            inline=False
                        )
                        
                        await logs_channel.send(embed=log_embed)

                await channel.send("Ticket fechado automaticamente por inatividade e será deletado em 5 segundos.")
                await self.send_transcript(config, ticket_data, channel)
                await self.request_evaluation(user, config, ticket_data, channel)
                del self.active_tickets[ticket_key]
                await asyncio.sleep(5)
                await channel.delete()
                break

    async def request_evaluation(self, user: nextcord.Member, config: dict, ticket_data: dict, channel: nextcord.TextChannel):
        """Solicita uma avaliação do atendimento."""
        embed_config = config["embed_evaluation"]
        embed = nextcord.Embed(
            title=embed_config["title"],
            description=embed_config["description"],
            color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
        )
        if embed_config["thumbnail"]:
            embed.set_thumbnail(url=embed_config["thumbnail"])
        if embed_config["image"]:
            embed.set_image(url=embed_config["image"])
        if embed_config["footer"]:
            embed.set_footer(text=embed_config["footer"])

        view = ui.View(timeout=None)
        select = ui.Select(
            placeholder="Selecione uma nota...",
            options=[
                nextcord.SelectOption(label="😞 Péssimo", value="1", emoji="😞"),
                nextcord.SelectOption(label="😕 Ruim", value="2", emoji="😕"),
                nextcord.SelectOption(label="😐 Regular", value="3", emoji="😐"),
                nextcord.SelectOption(label="😊 Bom", value="4", emoji="😊"),
                nextcord.SelectOption(label="😍 Excelente", value="5", emoji="😍")
            ]
        )

        async def select_callback(interaction: Interaction):
            rating = interaction.data["values"][0]
            rating_text = {
                "1": "Péssimo",
                "2": "Ruim",
                "3": "Regular",
                "4": "Bom",
                "5": "Excelente"
            }.get(rating, "Desconhecido")
            
            # Log da avaliação
            logger.info(
                f"Avaliação recebida para ticket {channel.id}. "
                f"Usuário: {user} (ID: {user.id}). "
                f"Nota: {rating}/5 ({rating_text}). "
                f"Atendente: {ticket_data.get('assumed_by', 'Nenhum')}"
            )

            if config["canal_avaliacoes"]:
                avaliacoes_channel = self.bot.get_channel(config["canal_avaliacoes"])
                if avaliacoes_channel:
                    guild_id = str(channel.guild.id)
                    categories = self.load_categories(guild_id)
                    category_name = categories.get(ticket_data["category"], {"name": "Desconhecida"})["name"]
                    
                    # Embed detalhada da avaliação
                    evaluation_embed = nextcord.Embed(
                        title="⭐ Nova Avaliação de Atendimento",
                        color={
                            "1": nextcord.Color.red(),
                            "2": nextcord.Color.orange(),
                            "3": nextcord.Color.gold(),
                            "4": nextcord.Color.green(),
                            "5": nextcord.Color.blue()
                        }.get(rating, nextcord.Color.default()),
                        timestamp=datetime.now(self.br_tz)
                    )
                    
                    evaluation_embed.add_field(
                        name="👤 Usuário",
                        value=f"{user.mention}\nID: {user.id}",
                        inline=True
                    )
                    
                    if ticket_data.get("assumed_by"):
                        staff = self.bot.get_user(int(ticket_data["assumed_by"]))
                        evaluation_embed.add_field(
                            name="🛎️ Atendente",
                            value=f"{staff.mention}\nID: {staff.id}",
                            inline=True
                        )
                    
                    evaluation_embed.add_field(
                        name="🎟️ Ticket",
                        value=f"ID: {channel.id}\nCategoria: {category_name}",
                        inline=True
                    )
                    
                    evaluation_embed.add_field(
                        name="⭐ Avaliação",
                        value=f"{'⭐' * int(rating)} ({rating}/5)\n{rating_text}",
                        inline=False
                    )
                    
                    # Adicionar informações temporais
                    created_at = ticket_data["created_at"].strftime("%d/%m/%Y %H:%M") if isinstance(ticket_data["created_at"], datetime) else ticket_data["created_at"]
                    closed_at = ticket_data.get("closed_at", "Desconhecido")
                    if isinstance(closed_at, str) and closed_at != "Desconhecido":
                        try:
                            closed_at = datetime.fromisoformat(closed_at).strftime("%d/%m/%Y %H:%M")
                        except:
                            closed_at = "Desconhecido"
                    
                    evaluation_embed.add_field(
                        name="⏱️ Tempo",
                        value=f"Aberto em: {created_at}\nFechado em: {closed_at}",
                        inline=False
                    )
                    
                    await avaliacoes_channel.send(embed=evaluation_embed)
            
            await interaction.response.send_message("Obrigado pela avaliação!", ephemeral=True)

        select.callback = select_callback
        view.add_item(select)
        try:
            await user.send(embed=embed, view=view)
        except nextcord.Forbidden:
            await channel.send(f"{user.mention}, avalie o atendimento aqui (DM bloqueada):", embed=embed, view=view)

    class AddCategoryModal(nextcord.ui.Modal):
        """Modal para adicionar uma nova categoria."""
        def __init__(self, parent_cog):
            super().__init__("Adicionar Nova Categoria de Ticket")
            self.parent_cog = parent_cog

            self.name = nextcord.ui.TextInput(
                label="Nome da Categoria",
                placeholder="Ex.: Suporte Técnico",
                required=True,
                max_length=100
            )
            self.add_item(self.name)

            self.description = nextcord.ui.TextInput(
                label="Descrição da Categoria",
                placeholder="Ex.: Ajuda com problemas técnicos",
                required=True,
                max_length=100,
                style=nextcord.TextInputStyle.paragraph
            )
            self.add_item(self.description)

            self.emoji = nextcord.ui.TextInput(
                label="Emoji (opcional)",
                placeholder="Ex.: 🎟️ ou <:nome:ID>",
                required=False,
                max_length=100
            )
            self.add_item(self.emoji)

        async def callback(self, interaction: Interaction):
            guild_id = str(interaction.guild.id)
            category_id = str(uuid.uuid4())
            self.parent_cog.save_category(
                guild_id,
                category_id,
                self.name.value,
                self.description.value,
                self.emoji.value or None
            )
            await self.parent_cog.update_menu_embed(guild_id)
            await interaction.response.send_message(
                f"Categoria '{self.name.value}' adicionada com sucesso! O menu foi atualizado.",
                ephemeral=True
            )

    class EditCategoryModal(nextcord.ui.Modal):
        """Modal para editar uma categoria existente."""
        def __init__(self, parent_cog, category_id, current_name, current_description, current_emoji):
            super().__init__(f"Editar Categoria: {current_name}")
            self.parent_cog = parent_cog
            self.category_id = category_id

            self.name = nextcord.ui.TextInput(
                label="Nome da Categoria",
                default_value=current_name,
                required=True,
                max_length=100
            )
            self.add_item(self.name)

            self.description = nextcord.ui.TextInput(
                label="Descrição da Categoria",
                default_value=current_description,
                required=True,
                max_length=100,
                style=nextcord.TextInputStyle.paragraph
            )
            self.add_item(self.description)

            self.emoji = nextcord.ui.TextInput(
                label="Emoji (opcional)",
                default_value=current_emoji or "",
                required=False,
                max_length=100
            )
            self.add_item(self.emoji)

        async def callback(self, interaction: Interaction):
            guild_id = str(interaction.guild.id)
            success = self.parent_cog.update_category(
                guild_id,
                self.category_id,
                self.name.value,
                self.description.value,
                self.emoji.value or None
            )
            if success:
                await self.parent_cog.update_menu_embed(guild_id)
                await interaction.response.send_message(
                    f"Categoria '{self.name.value}' atualizada com sucesso! O menu foi atualizado.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Erro: Categoria não encontrada!",
                    ephemeral=True
                )

    @nextcord.slash_command(name="add_category", description="Adiciona uma nova categoria de ticket.")
    @commands.has_permissions(administrator=True)
    async def add_category(self, interaction: Interaction):
        """Comando para adicionar uma nova categoria."""
        await interaction.response.send_modal(self.AddCategoryModal(self))

    @nextcord.slash_command(name="list_categories", description="Lista todas as categorias de tickets.")
    @commands.has_permissions(administrator=True)
    async def list_categories(self, interaction: Interaction):
        """Comando para listar todas as categorias."""
        guild_id = str(interaction.guild.id)
        categories = self.load_categories(guild_id)
        if not categories:
            await interaction.response.send_message("Nenhuma categoria configurada!", ephemeral=True)
            return

        embed = nextcord.Embed(
            title="Categorias de Tickets",
            description="Lista de todas as categorias configuradas:",
            color=nextcord.Color.from_rgb(43, 45, 49)
        )
        for cat_id, cat in categories.items():
            emoji = cat["emoji"] or "<:seta:1350166397040463922>"
            embed.add_field(
                name=f"{emoji} {cat['name']}",
                value=f"**ID:** {cat_id}\n**Descrição:** {cat['desc']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="edit_category", description="Edita uma categoria de ticket existente.")
    @commands.has_permissions(administrator=True)
    async def edit_category(self, interaction: Interaction):
        """Comando para editar uma categoria existente."""
        guild_id = str(interaction.guild.id)
        categories = self.load_categories(guild_id)
        if not categories:
            await interaction.response.send_message("Nenhuma categoria configurada! Use /add_category primeiro.", ephemeral=True)
            return

        options = [
            nextcord.SelectOption(label=cat["name"], value=cat_id, description=cat["desc"], emoji=cat["emoji"] or "<:seta:1350166397040463922WAR>")
            for cat_id, cat in categories.items()
        ]
        select = ui.Select(placeholder="Selecione uma categoria para editar...", options=options)

        async def select_callback(interaction: Interaction):
            category_id = interaction.data["values"][0]
            cat = categories[category_id]
            await interaction.response.send_modal(
                self.EditCategoryModal(self, category_id, cat["name"], cat["desc"], cat["emoji"])
            )

        select.callback = select_callback
        view = ui.View(timeout=None)
        view.add_item(select)
        await interaction.response.send_message("Selecione a categoria para editar:", view=view, ephemeral=True)

    @nextcord.slash_command(name="remove_category", description="Remove uma categoria de ticket.")
    @commands.has_permissions(administrator=True)
    async def remove_category(self, interaction: Interaction):
        """Comando para remover uma categoria."""
        guild_id = str(interaction.guild.id)
        categories = self.load_categories(guild_id)
        if not categories:
            await interaction.response.send_message("Nenhuma categoria configurada!", ephemeral=True)
            return

        options = [
            nextcord.SelectOption(label=cat["name"], value=cat_id, description=cat["desc"], emoji=cat["emoji"] or "<:seta:1350166397040463922>")
            for cat_id, cat in categories.items()
        ]
        select = ui.Select(placeholder="Selecione uma categoria para remover...", options=options)

        async def select_callback(interaction: Interaction):
            category_id = interaction.data["values"][0]
            if self.delete_category(guild_id, category_id):
                await self.update_menu_embed(guild_id)
                await interaction.response.send_message(
                    f"Categoria removida com sucesso! O menu foi atualizado.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Erro: Categoria não encontrada!",
                    ephemeral=True
                )

        select.callback = select_callback
        view = ui.View(timeout=None)
        view.add_item(select)
        await interaction.response.send_message("Selecione a categoria para remover:", view=view, ephemeral=True)

    class PersonalizeEmbedModal(nextcord.ui.Modal):
        """Modal para personalizar embeds."""
        def __init__(self, parent_cog, embed_key):
            super().__init__(f"Personalizar Embed: {embed_key.replace('embed_', '').capitalize()}")
            self.parent_cog = parent_cog
            self.embed_key = embed_key
            config = self.parent_cog.load_config(str(parent_cog.bot.guilds[0].id))
            embed_config = config[self.embed_key]

            self.embed_title = nextcord.ui.TextInput(
                label="Título da Embed",
                default_value=embed_config["title"],
                required=True,
                max_length=256
            )
            self.add_item(self.embed_title)

            self.embed_description = nextcord.ui.TextInput(
                label="Descrição da Embed",
                default_value=embed_config.get("description", ""),
                required=self.embed_key in ["embed_menu", "embed_evaluation"],
                max_length=2000,
                style=nextcord.TextInputStyle.paragraph
            )
            self.add_item(self.embed_description)

            self.embed_thumbnail = nextcord.ui.TextInput(
                label="URL do Thumbnail",
                default_value=embed_config["thumbnail"],
                required=False,
                max_length=500
            )
            self.add_item(self.embed_thumbnail)

            self.embed_image = nextcord.ui.TextInput(
                label="URL da Imagem",
                default_value=embed_config["image"],
                required=False,
                max_length=500
            )
            self.add_item(self.embed_image)

            self.embed_footer = nextcord.ui.TextInput(
                label="Texto do Footer",
                default_value=embed_config.get("footer", ""),
                required=False,
                max_length=2048
            )
            self.add_item(self.embed_footer)

        async def callback(self, interaction: Interaction):
            guild_id = str(interaction.guild.id)
            config = self.parent_cog.load_config(guild_id)

            config[self.embed_key] = {
                "title": self.embed_title.value,
                "description": self.embed_description.value or "",
                "thumbnail": self.embed_thumbnail.value or "",
                "image": self.embed_image.value or "",
                "footer": self.embed_footer.value or ""
            }
            self.parent_cog.save_config(guild_id, config)

            await interaction.response.send_message(
                f"Embed '{self.embed_key.replace('embed_', '').capitalize()}' personalizada com sucesso!",
                ephemeral=True
            )

    @nextcord.slash_command(name="person_tickets", description="Personalize as embeds do sistema de tickets.")
    @commands.has_permissions(administrator=True)
    async def person_tickets(self, interaction: Interaction):
        """Comando para personalizar embeds do sistema de tickets."""
        embed = nextcord.Embed(
            title="Personalização de Embeds - Tickets",
            description="Escolha uma embed para personalizar clicando nos botões abaixo:",
            color=nextcord.Color.from_rgb(43, 45, 49)
        )
        embed.add_field(
            name="Embeds Disponíveis",
            value=(
                "1. **Menu**: Embed do menu de tickets.\n"
                "2. **Painel**: Embed enviada no canal do ticket.\n"
                "3. **Assumido**: Notificação de ticket assumido (DM).\n"
                "4. **Inatividade**: Aviso de inatividade (DM).\n"
                "5. **Avaliação**: Solicitação de avaliação (DM ou canal)."
            ),
            inline=False
        )

        view = ui.View(timeout=None)
        embeds_to_edit = ["embed_menu", "embed_panel", "embed_assumed", "embed_inactivity", "embed_evaluation"]
        for embed_key in embeds_to_edit:
            button = ui.Button(
                label=embed_key.replace("embed_", "").capitalize(),
                style=nextcord.ButtonStyle.secondary,
                emoji="<:add:1350154819419246677>"
            )
            async def button_callback(interaction, key=embed_key):
                await interaction.response.send_modal(self.PersonalizeEmbedModal(self, key))
            button.callback = button_callback
            view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @nextcord.slash_command(name="config_tickets", description="Configura o sistema de tickets.")
    @commands.has_permissions(administrator=True)
    async def config_tickets(
        self,
        interaction: Interaction,
        categoria: nextcord.CategoryChannel = SlashOption(description="Categoria onde os tickets serão criados", required=True),
        canal_menu: nextcord.TextChannel = SlashOption(description="Canal do menu de tickets", required=True),
        cargo_suporte: nextcord.Role = SlashOption(description="Cargo responsável por atender", required=True),
        canal_avaliacoes: nextcord.TextChannel = SlashOption(description="Canal de avaliações", required=True),
        canal_logs: nextcord.TextChannel = SlashOption(description="Canal de logs", required=True),
        canal_transcripts: nextcord.TextChannel = SlashOption(description="Canal de logs de transcrição", required=True),
        cor_r: int = SlashOption(description="Cor R (0-255)", default=43, min_value=0, max_value=255),
        cor_g: int = SlashOption(description="Cor G (0-255)", default=45, min_value=0, max_value=255),
        cor_b: int = SlashOption(description="Cor B (0-255)", default=49, min_value=0, max_value=255),
        tempo_notificacao: int = SlashOption(description="Horas para notificar inatividade", default=24, min_value=1, max_value=168),
        tempo_fechamento: int = SlashOption(description="Horas para fechar ticket inativo", default=48, min_value=2, max_value=168)
    ):
        """Comando para configurar o sistema de tickets."""
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)
        config.update({
            "categoria_tickets": categoria.id,
            "canal_menu": canal_menu.id,
            "cargo_suporte": cargo_suporte.id,
            "canal_avaliacoes": canal_avaliacoes.id,
            "canal_logs": canal_logs.id,
            "canal_transcripts": canal_transcripts.id,
            "embed_color_rgb": [cor_r, cor_g, cor_b],
            "tempo_notificacao_horas": tempo_notificacao,
            "tempo_fechamento_horas": tempo_fechamento
        })
        self.save_config(guild_id, config)
        await interaction.response.send_message(
            f"✅ Sistema configurado!\n"
            f"**Categoria:** {categoria.name}\n**Canal do Menu:** {canal_menu.mention}\n"
            f"**Cargo:** {cargo_suporte.mention}\n**Avaliações:** {canal_avaliacoes.mention}\n"
            f"**Logs:** {canal_logs.mention}\n**Transcrições:** {canal_transcripts.mention}\n"
            f"**Cor RGB:** {cor_r},{cor_g},{cor_b}\n"
            f"**Notificação:** {tempo_notificacao}h\n**Fechamento:** {tempo_fechamento}h",
            ephemeral=True
        )

    @nextcord.slash_command(name="create_ticket_menu", description="Cria o menu de tickets no canal configurado.")
    @commands.has_permissions(administrator=True)
    async def create_ticket_menu(self, interaction: Interaction):
        """Comando para criar o menu de tickets."""
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)
        if not config["canal_menu"]:
            await interaction.response.send_message("O sistema não foi configurado. Use /config_tickets primeiro!", ephemeral=True)
            return
        channel = self.bot.get_channel(config["canal_menu"])
        await self.create_menu_embed(guild_id, channel)
        await interaction.response.send_message(f"Menu de tickets criado em {channel.mention}!", ephemeral=True)

def setup(bot):
    logger.info("Chamando setup para TicketCog")
    try:
        bot.add_cog(TicketCog(bot))
        logger.info("TicketCog adicionada ao bot")
    except Exception as e:
        logger.error(f"Erro ao adicionar TicketCog: {e}", exc_info=True)
        raise