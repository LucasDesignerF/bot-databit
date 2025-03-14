# ticket_cog.py
# Description: Sistema de tickets personalizado para múltiplos servidores
# Date of Creation: 20/03/2025
# Created by: Grok (xAI) & CodeProjects
# Version: 6.0
# Developer Of Version: Grok (xAI), CodeProjects, RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui
import os
import json
from datetime import datetime
import pytz
import asyncio
from typing import Dict, Optional

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data"
        self.ticket_categories = {
            "suporte_tecnico": {"name": "Suporte Técnico", "desc": "Ajuda com problemas técnicos"},
            "compras": {"name": "Compras", "desc": "Dúvidas ou problemas com compras"},
            "parcerias": {"name": "Parcerias", "desc": "Propostas e informações sobre parcerias"},
            "trabalhe_conosco": {"name": "Trabalhe Conosco", "desc": "Oportunidades de trabalho"}
        }
        self.active_tickets: Dict[str, Dict] = {}  # Cache de tickets ativos
        self.br_tz = pytz.timezone("America/Sao_Paulo")

    # Utilitários
    def ensure_guild_directory(self, guild_id: str):
        os.makedirs(os.path.join(self.data_dir, guild_id), exist_ok=True)

    def load_config(self, guild_id: str) -> dict:
        self.ensure_guild_directory(guild_id)
        config_file = os.path.join(self.data_dir, guild_id, "tickets.json")
        default_config = {
            "categoria_tickets": None,
            "canal_menu": None,
            "cargo_suporte": None,
            "canal_avaliacoes": None,
            "canal_logs": None,
            "embed_color_rgb": [43, 45, 49],
            "tempo_notificacao_horas": 24,
            "tempo_fechamento_horas": 48,
            "menu_message_id": None
        }
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return {**default_config, **config}
        return default_config

    def save_config(self, guild_id: str, config: dict):
        with open(os.path.join(self.data_dir, guild_id, "tickets.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    def load_ticket(self, guild_id: str, ticket_id: str) -> dict:
        ticket_file = os.path.join(self.data_dir, guild_id, f"ticket_{ticket_id}.json")
        if os.path.exists(ticket_file):
            with open(ticket_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_ticket(self, guild_id: str, ticket_id: str, data: dict):
        # Converte objetos datetime para strings antes de salvar
        data = data.copy()
        if "created_at" in data and isinstance(data["created_at"], datetime):
            data["created_at"] = data["created_at"].isoformat()
        if "last_activity" in data and isinstance(data["last_activity"], datetime):
            data["last_activity"] = data["last_activity"].isoformat()

        with open(os.path.join(self.data_dir, guild_id, f"ticket_{ticket_id}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    # Embed do Menu
    async def create_menu_embed(self, guild_id: str, channel: nextcord.TextChannel):
        config = self.load_config(guild_id)
        embed = nextcord.Embed(
            title="<:logo2:1350090849903710208> Ticket's System",
            description=(
                "Bem-vindo ao nosso sistema de tickets! 🎟\n\n"
                "Aqui você pode abrir um ticket para receber suporte técnico, resolver problemas com compras, "
                "discutir parcerias ou até mesmo se candidatar a oportunidades de trabalho.\n\n"
                "**Como funciona?**\n"
                "1. Selecione uma categoria abaixo.\n"
                "2. Um canal privado será criado para você.\n"
                "3. Nossa equipe entrará em contato o mais rápido possível.\n\n"
                "Estamos aqui para ajudar! 😊"
            ),
            color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
        )
        embed.set_thumbnail(url="https://imgur.com/FI0J8Aw.png")
        embed.set_image(url="https://imgur.com/OZ95Zry.png")

        options = [
            nextcord.SelectOption(label=cat["name"], value=cat_id, emoji="<:seta:1350166397040463922>", description=cat["desc"])
            for cat_id, cat in self.ticket_categories.items()
        ]
        select = ui.Select(placeholder="Selecione uma categoria...", options=options)

        async def select_callback(interaction: Interaction):
            category_id = interaction.data["values"][0]
            category = self.ticket_categories[category_id]
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
        config = self.load_config(guild_id)
        category_channel = interaction.guild.get_channel(config["categoria_tickets"])
        if not category_channel or not isinstance(category_channel, nextcord.CategoryChannel):
            return None

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

        ticket_key = f"{guild_id}_{ticket_channel.id}"
        self.active_tickets[ticket_key] = {
            "user_id": interaction.user.id,
            "category": category_id,
            "created_at": datetime.now(self.br_tz),
            "assumed_by": None,
            "last_activity": datetime.now(self.br_tz),
            "status": "aberto"
        }
        await self.create_ticket_panel(ticket_channel, interaction.user, config, ticket_key)
        return ticket_channel

    # Painel do Ticket
    async def create_ticket_panel(self, channel: nextcord.TextChannel, user: nextcord.Member, config: dict, ticket_key: str):
        ticket_data = self.active_tickets[ticket_key]
        category = self.ticket_categories[ticket_data["category"]]
        created_at = ticket_data["created_at"].strftime("%d/%m/%Y %H:%M")

        embed = nextcord.Embed(
            title="<:open:1350167913591734363> Novo Ticket Aberto!",
            description=(
                f"<:readd:1350154929746215037> **Quem Abriu:** {user.mention}\n"
                f"<:readd:1350154929746215037> **Categoria:** {category['name']}\n"
                f"<:readd:1350154929746215037> **Data e Hora da Abertura:** {created_at}\n"
                f"<:readd:1350154929746215037> **Atendente Responsável:** Nenhum"
            ),
            color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
        )
        embed.set_thumbnail(url="https://imgur.com/FI0J8Aw.png")
        embed.set_image(url="https://imgur.com/iTQBsLh.png")

        view = ui.View(timeout=None)
        
        # Botão para assumir ticket
        assume_button = ui.Button(label="Assumir Ticket", style=nextcord.ButtonStyle.green, emoji="<:accept:1350169522077962324>")
        assume_button.callback = lambda i: self.assume_ticket(i, channel, user, config, ticket_key, embed, view)
        view.add_item(assume_button)

        # Botão para encerrar ticket
        close_button = ui.Button(label="Encerrar Ticket", style=nextcord.ButtonStyle.red, emoji="<:rejects:1350169812751614064>")
        close_button.callback = lambda i: self.close_ticket(i, channel, user, config, ticket_key, embed, view)
        view.add_item(close_button)

        # Botão para notificar inatividade
        notify_button = ui.Button(label="Notificar", style=nextcord.ButtonStyle.grey, emoji="<:notify:1350170693978951820>")
        notify_button.callback = lambda i: self.notify_inactivity(i, channel, user, config, ticket_key, embed, view)
        view.add_item(notify_button)

        await channel.send(embed=embed, view=view)
        asyncio.create_task(self.monitor_inactivity(channel, user, config, ticket_key))

    async def assume_ticket(self, interaction: Interaction, channel, user, config, ticket_key, embed, view):
        ticket_data = self.active_tickets[ticket_key]
        if ticket_data["assumed_by"]:
            await interaction.response.send_message("Este ticket já foi assumido!", ephemeral=True)
            return
        if config["cargo_suporte"] not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("Apenas atendentes podem assumir tickets!", ephemeral=True)
            return

        ticket_data["assumed_by"] = interaction.user.id
        ticket_data["last_activity"] = datetime.now(self.br_tz)
        category = self.ticket_categories[ticket_data["category"]]
        created_at = ticket_data["created_at"].strftime("%d/%m/%Y %H:%M")
        embed.description = (
            f"<:readd:1350154929746215037> **Quem Abriu:** {user.mention}\n"
            f"<:readd:1350154929746215037> **Categoria:** {category['name']}\n"
            f"<:readd:1350154929746215037> **Data e Hora da Abertura:** {created_at}\n"
            f"<:readd:1350154929746215037> **Atendente Responsável:** {interaction.user.mention}"
        )
        await channel.send(f"{user.mention}, seu ticket foi assumido por {interaction.user.mention}!")
        await interaction.message.edit(embed=embed, view=view)

        try:
            await user.send(embed=nextcord.Embed(
                title="Ticket Assumido",
                description=f"Seu ticket no canal {channel.mention} foi assumido por {interaction.user.mention}.",
                color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
            ))
        except nextcord.Forbidden:
            await channel.send(f"Não consegui notificar {user.mention} por DM (bloqueada).")
        await interaction.response.send_message("Ticket assumido!", ephemeral=True)

    async def close_ticket(self, interaction: Interaction, channel, user, config, ticket_key, embed, view):
        ticket_data = self.active_tickets[ticket_key]
        if ticket_data.get("status") == "fechado":
            await interaction.response.send_message("Este ticket já está fechado!", ephemeral=True)
            return

        # Responde à interação imediatamente
        await interaction.response.send_message("Ticket será encerrado em 5 segundos...", ephemeral=True)

        ticket_data["status"] = "fechado"
        await interaction.message.edit(view=None)  # Remove os botões
        await asyncio.sleep(5)
        await channel.edit(name=f"closed-ticket-{user.name}")

        self.save_ticket(str(channel.guild.id), str(channel.id), ticket_data)
        if config["canal_logs"]:
            logs_channel = self.bot.get_channel(config["canal_logs"])
            if logs_channel:
                await logs_channel.send(embed=nextcord.Embed(
                    title="Ticket Encerrado",
                    description=f"**Usuário:** {user.mention}\n**Categoria:** {self.ticket_categories[ticket_data['category']]['name']}\n**Canal:** {channel.mention}",
                    color=nextcord.Color.from_rgb(*config["embed_color_rgb"]),
                    timestamp=datetime.now(self.br_tz)
                ))

        await self.request_evaluation(user, config, ticket_data, channel)
        del self.active_tickets[ticket_key]

    async def notify_inactivity(self, interaction: Interaction, channel, user, config, ticket_key, embed, view):
        ticket_data = self.active_tickets[ticket_key]
        if ticket_data["assumed_by"] and interaction.user.id != ticket_data["assumed_by"]:
            await interaction.response.send_message("Apenas o atendente responsável pode notificar!", ephemeral=True)
            return

        try:
            await user.send(embed=nextcord.Embed(
                title="🚨 Aviso de Inatividade",
                description=f"Seu ticket em {channel.mention} está inativo há muito tempo. Responda em até {config['tempo_fechamento_horas'] - config['tempo_notificacao_horas']} horas ou ele será encerrado automaticamente.",
                color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
            ))
            await channel.send(f"{user.mention} foi notificado sobre a inatividade.")
        except nextcord.Forbidden:
            await channel.send(f"Não consegui notificar {user.mention} por DM (bloqueada).")
        await interaction.response.send_message("Notificação enviada!", ephemeral=True)

    async def monitor_inactivity(self, channel: nextcord.TextChannel, user: nextcord.Member, config: dict, ticket_key: str):
        while ticket_key in self.active_tickets:
            await asyncio.sleep(3600)  # Verifica a cada hora
            ticket_data = self.active_tickets.get(ticket_key, {})
            last_activity = ticket_data["last_activity"]
            if (datetime.now(self.br_tz) - last_activity).total_seconds() / 3600 >= config["tempo_notificacao_horas"]:
                await channel.send(f"{user.mention}, seu ticket está inativo há {config['tempo_notificacao_horas']} horas. Responda ou ele será fechado em breve!")
            if (datetime.now(self.br_tz) - last_activity).total_seconds() / 3600 >= config["tempo_fechamento_horas"]:
                await channel.send("Ticket fechado automaticamente por inatividade.")
                ticket_data["status"] = "fechado"
                await channel.edit(name=f"closed-ticket-{user.name}")
                self.save_ticket(str(channel.guild.id), str(channel.id), ticket_data)
                await self.request_evaluation(user, config, ticket_data, channel)
                del self.active_tickets[ticket_key]
                break

    async def request_evaluation(self, user: nextcord.Member, config: dict, ticket_data: dict, channel: nextcord.TextChannel):
        embed = nextcord.Embed(
            title="📝 Avalie o Atendimento",
            description="Como você avalia o atendimento recebido?",
            color=nextcord.Color.from_rgb(*config["embed_color_rgb"])
        )
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
            if config["canal_avaliacoes"]:
                avaliacoes_channel = self.bot.get_channel(config["canal_avaliacoes"])
                if avaliacoes_channel:
                    await avaliacoes_channel.send(embed=nextcord.Embed(
                        title="Nova Avaliação",
                        description=(
                            f"**Usuário:** {user.mention}\n"
                            f"**Categoria:** {self.ticket_categories[ticket_data['category']]['name']}\n"
                            f"**Nota:** {rating}/5\n"
                            f"**Atendente:** {self.bot.get_user(ticket_data['assumed_by']).mention if ticket_data['assumed_by'] else 'Nenhum'}"
                        ),
                        color=nextcord.Color.from_rgb(*config["embed_color_rgb"]),
                        timestamp=datetime.now(self.br_tz)
                    ))
            await interaction.response.send_message("Obrigado pela avaliação!", ephemeral=True)

        select.callback = select_callback
        view.add_item(select)
        try:
            await user.send(embed=embed, view=view)
        except nextcord.Forbidden:
            await channel.send(f"{user.mention}, avalie o atendimento aqui (DM bloqueada):", embed=embed, view=view)

    # Comandos Slash
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
        cor_r: int = SlashOption(description="Cor R (0-255)", default=43, min_value=0, max_value=255),
        cor_g: int = SlashOption(description="Cor G (0-255)", default=45, min_value=0, max_value=255),
        cor_b: int = SlashOption(description="Cor B (0-255)", default=49, min_value=0, max_value=255),
        tempo_notificacao: int = SlashOption(description="Horas para notificar inatividade", default=24, min_value=1, max_value=168),
        tempo_fechamento: int = SlashOption(description="Horas para fechar ticket inativo", default=48, min_value=2, max_value=168)
    ):
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)
        config.update({
            "categoria_tickets": categoria.id,
            "canal_menu": canal_menu.id,
            "cargo_suporte": cargo_suporte.id,
            "canal_avaliacoes": canal_avaliacoes.id,
            "canal_logs": canal_logs.id,
            "embed_color_rgb": [cor_r, cor_g, cor_b],
            "tempo_notificacao_horas": tempo_notificacao,
            "tempo_fechamento_horas": tempo_fechamento
        })
        self.save_config(guild_id, config)
        await interaction.response.send_message(
            f"✅ Sistema configurado!\n"
            f"**Categoria:** {categoria.name}\n**Canal do Menu:** {canal_menu.mention}\n"
            f"**Cargo:** {cargo_suporte.mention}\n**Avaliações:** {canal_avaliacoes.mention}\n"
            f"**Logs:** {canal_logs.mention}\n**Cor RGB:** {cor_r},{cor_g},{cor_b}\n"
            f"**Notificação:** {tempo_notificacao}h\n**Fechamento:** {tempo_fechamento}h",
            ephemeral=True
        )

    @nextcord.slash_command(name="create_ticket_menu", description="Cria o menu de tickets no canal configurado.")
    @commands.has_permissions(administrator=True)
    async def create_ticket_menu(self, interaction: Interaction):
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)
        if not config["canal_menu"]:
            await interaction.response.send_message("O sistema não foi configurado. Use /config_tickets primeiro!", ephemeral=True)
            return
        channel = self.bot.get_channel(config["canal_menu"])
        await self.create_menu_embed(guild_id, channel)
        await interaction.response.send_message(f"Menu de tickets criado em {channel.mention}!", ephemeral=True)

def setup(bot):
    bot.add_cog(TicketCog(bot))