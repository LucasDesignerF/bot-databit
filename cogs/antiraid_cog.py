# antiraid_cog.py
# Description: Sistema Anti-Raid para proteção de servidores contra ataques e exploits
# Date of Creation: 20/03/2025
# Created by: Grok (xAI) & CodeProjects
# Modified by: Grok (xAI), CodeProjects, RedeGamer
# Date of Modification: 23/04/2025
# Reason of Modification: Migração de JSON para SQLite, remoção de gerenciamento de arquivos
# Version: 3.0
# Developer Of Version: Grok (xAI), CodeProjects, RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui
import json
import logging
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict
import pytz

# Configuração de logging
logger = logging.getLogger("DataBit.AntiRaidCog")
logger.setLevel(logging.INFO)

class AntiRaidCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Usa a conexão SQLite fornecida pelo main.py
        self.br_tz = pytz.timezone("America/Sao_Paulo")
        self.activity_tracker = defaultdict(list)  # Rastreia ações por usuário
        self.lockdown_active = {}  # Estado de lockdown por servidor
        self.default_config = {
            "enabled": False,
            "log_channel": None,
            "max_messages_per_minute": 10,
            "max_channel_changes_per_hour": 5,
            "max_bans_per_hour": 3,
            "max_role_changes_per_hour": 5,
            "max_invites_per_hour": 10,
            "lockdown_duration_minutes": 30,
            "whitelist_roles": []
        }

    def load_config(self, guild_id: str) -> dict:
        """Carrega a configuração de anti-raid do banco de dados."""
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM antiraid_config WHERE guild_id = ?", (guild_id,))
            result = cursor.fetchone()
            if result:
                config = dict(result)
                # Desserializa whitelist_roles de JSON
                config["whitelist_roles"] = json.loads(config["whitelist_roles"]) if config["whitelist_roles"] else []
                return {**self.default_config, **config}
            return self.default_config
        except Exception as e:
            logger.error(f"Erro ao carregar antiraid_config de {guild_id}: {e}")
            return self.default_config

    def save_config(self, guild_id: str, config: dict):
        """Salva a configuração de anti-raid no banco de dados."""
        try:
            cursor = self.db.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO antiraid_config (
                    guild_id, enabled, log_channel, max_messages_per_minute,
                    max_channel_changes_per_hour, max_bans_per_hour, max_role_changes_per_hour,
                    max_invites_per_hour, lockdown_duration_minutes, whitelist_roles
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    config.get("enabled", self.default_config["enabled"]),
                    config.get("log_channel"),
                    config.get("max_messages_per_minute", self.default_config["max_messages_per_minute"]),
                    config.get("max_channel_changes_per_hour", self.default_config["max_channel_changes_per_hour"]),
                    config.get("max_bans_per_hour", self.default_config["max_bans_per_hour"]),
                    config.get("max_role_changes_per_hour", self.default_config["max_role_changes_per_hour"]),
                    config.get("max_invites_per_hour", self.default_config["max_invites_per_hour"]),
                    config.get("lockdown_duration_minutes", self.default_config["lockdown_duration_minutes"]),
                    json.dumps(config.get("whitelist_roles", self.default_config["whitelist_roles"]))
                )
            )
            self.db.commit()
            logger.info(f"Configuração anti-raid salva para servidor {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar antiraid_config de {guild_id}: {e}")

    async def log_action(self, guild_id: str, embed: nextcord.Embed):
        config = self.load_config(guild_id)
        if config["log_channel"]:
            channel = self.bot.get_channel(config["log_channel"])
            if channel:
                try:
                    await channel.send(embed=embed)
                    logger.info(f"Ação registrada no canal de logs {config['log_channel']} para {guild_id}")
                except Exception as e:
                    logger.error(f"Erro ao enviar log para canal {config['log_channel']} em {guild_id}: {e}")

    async def activate_lockdown(self, guild: nextcord.Guild):
        guild_id = str(guild.id)
        if guild_id in self.lockdown_active:
            return

        config = self.load_config(guild_id)
        self.lockdown_active[guild_id] = True

        everyone_role = guild.default_role
        try:
            await everyone_role.edit(
                permissions=nextcord.Permissions(
                    send_messages=False,
                    create_instant_invite=False,
                    manage_channels=False,
                    manage_roles=False
                ),
                reason="Anti-Raid: Lockdown ativado devido a atividade suspeita"
            )
        except Exception as e:
            logger.error(f"Erro ao ativar lockdown em {guild_id}: {e}")
            self.lockdown_active.pop(guild_id, None)
            return

        embed = nextcord.Embed(
            title="<:lock:1351976522168402081> Modo de Quarentena Ativado",
            description=f"O servidor entrou em lockdown por {config['lockdown_duration_minutes']} minutos devido a atividades suspeitas.",
            color=nextcord.Color.red(),
            timestamp=datetime.now(self.br_tz)
        )
        await self.log_action(guild_id, embed)

        await asyncio.sleep(config["lockdown_duration_minutes"] * 60)
        try:
            await everyone_role.edit(
                permissions=nextcord.Permissions.general(),
                reason="Anti-Raid: Lockdown encerrado"
            )
        except Exception as e:
            logger.error(f"Erro ao desativar lockdown em {guild_id}: {e}")

        self.lockdown_active.pop(guild_id, None)

        embed = nextcord.Embed(
            title="<:unlock:1351976453901910048> Modo de Quarentena Desativado",
            description="O servidor voltou ao normal após o período de lockdown.",
            color=nextcord.Color.green(),
            timestamp=datetime.now(self.br_tz)
        )
        await self.log_action(guild_id, embed)

    # Listeners para monitoramento
    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        config = self.load_config(guild_id)
        if not config["enabled"] or message.author.top_role.id in config["whitelist_roles"]:
            return

        user_id = message.author.id
        now = datetime.now(self.br_tz)
        self.activity_tracker[(guild_id, user_id, "messages")].append(now)

        self.activity_tracker[(guild_id, user_id, "messages")] = [
            t for t in self.activity_tracker[(guild_id, user_id, "messages")]
            if (now - t).total_seconds() <= 60
        ]

        if len(self.activity_tracker[(guild_id, user_id, "messages")]) > config["max_messages_per_minute"]:
            try:
                await message.author.timeout(timedelta(minutes=10), reason="Anti-Raid: Flood detectado")
                embed = nextcord.Embed(
                    title="<:alert:1351976384779517972> Flood Detectado",
                    description=f"{message.author.mention} foi silenciado por 10 minutos por enviar mensagens em excesso.",
                    color=nextcord.Color.red(),
                    timestamp=now
                )
                await self.log_action(guild_id, embed)
            except Exception as e:
                logger.error(f"Erro ao silenciar {message.author.id} em {guild_id}: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: nextcord.abc.GuildChannel):
        guild_id = str(channel.guild.id)
        config = self.load_config(guild_id)
        if not config["enabled"]:
            return

        now = datetime.now(self.br_tz)
        self.activity_tracker[(guild_id, "channel_create")].append(now)
        self.activity_tracker[(guild_id, "channel_create")] = [
            t for t in self.activity_tracker[(guild_id, "channel_create")]
            if (now - t).total_seconds() <= 3600
        ]

        if len(self.activity_tracker[(guild_id, "channel_create")]) > config["max_channel_changes_per_hour"]:
            await self.activate_lockdown(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: nextcord.abc.GuildChannel):
        guild_id = str(channel.guild.id)
        config = self.load_config(guild_id)
        if not config["enabled"]:
            return

        now = datetime.now(self.br_tz)
        self.activity_tracker[(guild_id, "channel_delete")].append(now)
        self.activity_tracker[(guild_id, "channel_delete")] = [
            t for t in self.activity_tracker[(guild_id, "channel_delete")]
            if (now - t).total_seconds() <= 3600
        ]

        if len(self.activity_tracker[(guild_id, "channel_delete")]) > config["max_channel_changes_per_hour"]:
            await self.activate_lockdown(channel.guild)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: nextcord.Guild, user: nextcord.User):
        guild_id = str(guild.id)
        config = self.load_config(guild_id)
        if not config["enabled"]:
            return

        now = datetime.now(self.br_tz)
        self.activity_tracker[(guild_id, "bans")].append(now)
        self.activity_tracker[(guild_id, "bans")] = [
            t for t in self.activity_tracker[(guild_id, "bans")]
            if (now - t).total_seconds() <= 3600
        ]

        if len(self.activity_tracker[(guild_id, "bans")]) > config["max_bans_per_hour"]:
            await self.activate_lockdown(guild)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: nextcord.Role):
        guild_id = str(role.guild.id)
        config = self.load_config(guild_id)
        if not config["enabled"]:
            return

        now = datetime.now(self.br_tz)
        self.activity_tracker[(guild_id, "role_create")].append(now)
        self.activity_tracker[(guild_id, "role_create")] = [
            t for t in self.activity_tracker[(guild_id, "role_create")]
            if (now - t).total_seconds() <= 3600
        ]

        if len(self.activity_tracker[(guild_id, "role_create")]) > config["max_role_changes_per_hour"]:
            await self.activate_lockdown(role.guild)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: nextcord.Role):
        guild_id = str(role.guild.id)
        config = self.load_config(guild_id)
        if not config["enabled"]:
            return

        now = datetime.now(self.br_tz)
        self.activity_tracker[(guild_id, "role_delete")].append(now)
        self.activity_tracker[(guild_id, "role_delete")] = [
            t for t in self.activity_tracker[(guild_id, "role_delete")]
            if (now - t).total_seconds() <= 3600
        ]

        if len(self.activity_tracker[(guild_id, "role_delete")]) > config["max_role_changes_per_hour"]:
            await self.activate_lockdown(role.guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: nextcord.Invite):
        guild_id = str(invite.guild.id)
        config = self.load_config(guild_id)
        if not config["enabled"]:
            return

        now = datetime.now(self.br_tz)
        self.activity_tracker[(guild_id, "invites")].append(now)
        self.activity_tracker[(guild_id, "invites")] = [
            t for t in self.activity_tracker[(guild_id, "invites")]
            if (now - t).total_seconds() <= 3600
        ]

        if len(self.activity_tracker[(guild_id, "invites")]) > config["max_invites_per_hour"]:
            try:
                await invite.delete(reason="Anti-Raid: Limite de convites excedido")
                embed = nextcord.Embed(
                    title="<:alert:1351976384779517972> Spam de Convites Detectado",
                    description="Um convite foi deletado por exceder o limite por hora.",
                    color=nextcord.Color.red(),
                    timestamp=now
                )
                await self.log_action(guild_id, embed)
            except Exception as e:
                logger.error(f"Erro ao deletar convite em {guild_id}: {e}")

    # Classe para o menu de configuração interativa
    class AntiRaidConfigView(ui.View):
        def __init__(self, cog, guild_id: str):
            super().__init__(timeout=None)
            self.cog = cog
            self.guild_id = guild_id
            self.config = self.cog.load_config(self.guild_id)

        async def update_embed(self, interaction: Interaction, embed: nextcord.Embed):
            try:
                await interaction.message.edit(embed=embed, view=self)
            except Exception as e:
                logger.error(f"Erro ao atualizar embed de configuração em {self.guild_id}: {e}")

        @ui.button(label="Ativar/Desativar", style=nextcord.ButtonStyle.grey, emoji="<:raid:1351968258537947316>")
        async def toggle_button(self, button: ui.Button, interaction: Interaction):
            self.config["enabled"] = not self.config["enabled"]
            self.cog.save_config(self.guild_id, self.config)
            embed = self.create_config_embed()
            await self.update_embed(interaction, embed)

        @ui.select(
            placeholder="Definir Canal de Logs",
            options=[nextcord.SelectOption(label="Escolha um canal", value="placeholder", emoji="<:raid:1351968258537947316>")],
            custom_id="log_channel_select"
        )
        async def log_channel_select(self, select: ui.Select, interaction: Interaction):
            channels = [c for c in interaction.guild.text_channels if c.permissions_for(interaction.guild.me).send_messages]
            select.options = [
                nextcord.SelectOption(label=c.name, value=str(c.id), emoji="<:raid:1351968258537947316>")
                for c in channels[:25]  # Limite de 25 opções por select
            ]
            if interaction.data["values"][0] != "placeholder":
                self.config["log_channel"] = int(interaction.data["values"][0])
                self.cog.save_config(self.guild_id, self.config)
                embed = self.create_config_embed()
                await self.update_embed(interaction, embed)
            else:
                await interaction.response.defer()

        @ui.select(
            placeholder="Máx. Mensagens/Min",
            options=[
                nextcord.SelectOption(label=f"{i} mensagens", value=str(i), emoji="<:raid:1351968258537947316>")
                for i in [5, 10, 15, 20, 25, 30, 40, 50]
            ],
            custom_id="max_messages_select"
        )
        async def max_messages_select(self, select: ui.Select, interaction: Interaction):
            self.config["max_messages_per_minute"] = int(interaction.data["values"][0])
            self.cog.save_config(self.guild_id, self.config)
            embed = self.create_config_embed()
            await self.update_embed(interaction, embed)

        @ui.select(
            placeholder="Máx. Mudanças de Canais/Hora",
            options=[
                nextcord.SelectOption(label=f"{i} mudanças", value=str(i), emoji="<:raid:1351968258537947316>")
                for i in [1, 3, 5, 7, 10, 15, 20]
            ],
            custom_id="max_channels_select"
        )
        async def max_channels_select(self, select: ui.Select, interaction: Interaction):
            self.config["max_channel_changes_per_hour"] = int(interaction.data["values"][0])
            self.cog.save_config(self.guild_id, self.config)
            embed = self.create_config_embed()
            await self.update_embed(interaction, embed)

        @ui.select(
            placeholder="Máx. Bans/Hora",
            options=[
                nextcord.SelectOption(label=f"{i} bans", value=str(i), emoji="<:raid:1351968258537947316>")
                for i in [1, 2, 3, 5, 7, 10]
            ],
            custom_id="max_bans_select"
        )
        async def max_bans_select(self, select: ui.Select, interaction: Interaction):
            self.config["max_bans_per_hour"] = int(interaction.data["values"][0])
            self.cog.save_config(self.guild_id, self.config)
            embed = self.create_config_embed()
            await self.update_embed(interaction, embed)

        @ui.button(style=nextcord.ButtonStyle.grey, emoji="<:rejects:1350169812751614064>")
        async def close_button(self, button: ui.Button, interaction: Interaction):
            try:
                await interaction.message.delete()
            except Exception as e:
                logger.error(f"Erro ao deletar mensagem de configuração em {self.guild_id}: {e}")

        def create_config_embed(self):
            embed = nextcord.Embed(
                title="Configuração Anti-Raid",
                description="<:raid:1351968258537947316> Ajuste as configurações de proteção contra raids usando os botões e menus abaixo.",
                color=nextcord.Color.from_rgb(43, 45, 49),
                timestamp=datetime.now(self.cog.br_tz)
            )
            embed.add_field(
                name="Status",
                value=f"**Ativado:** {'Sim' if self.config['enabled'] else 'Não'}",
                inline=True
            )
            embed.add_field(
                name="Canal de Logs",
                value=f"<#{self.config['log_channel']}>" if self.config["log_channel"] else "Não definido",
                inline=True
            )
            embed.add_field(
                name="Limites",
                value=(
                    f"**Mensagens/Min:** {self.config['max_messages_per_minute']}\n"
                    f"**Mudanças de Canais/Hora:** {self.config['max_channel_changes_per_hour']}\n"
                    f"**Bans/Hora:** {self.config['max_bans_per_hour']}"
                ),
                inline=False
            )
            emoji = self.cog.bot.get_emoji(1351968258537947316)
            if emoji:
                embed.set_author(name="Anti-Raid", icon_url=emoji.url)
            embed.set_footer(text="Anti-Raid - by CodeProjects")
            return embed

    # Comando para configurar o sistema Anti-Raid
    @nextcord.slash_command(name="config_antiraid", description="Configura o sistema Anti-Raid de forma interativa.")
    @commands.has_permissions(administrator=True)
    async def config_antiraid(self, interaction: Interaction):
        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)

        view = self.AntiRaidConfigView(self, guild_id)
        embed = view.create_config_embed()

        try:
            await interaction.response.send_message(embed=embed, view=view)
            logger.info(f"Configuração anti-raid iniciada por {interaction.user.id} em {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao enviar configuração anti-raid em {guild_id}: {e}")
            await interaction.response.send_message(
                "Erro ao iniciar a configuração. Tente novamente.", ephemeral=True
            )

def setup(bot):
    bot.add_cog(AntiRaidCog(bot))