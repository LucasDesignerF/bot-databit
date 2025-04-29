# cogs/opcionais/TimeClockCog.py
# Description: Sistema de bate-ponto por voz consolidado, adaptado de ConfigCog, PontoCog e RankingCog para SQLite
# Date of Creation: 23/04/2025
# Created by: Grok (xAI), inspired by CodeProjects, RedeGamer
# Version: 1.2
# Developer: Grok (xAI)
# Changelog: 
# - v1.1: Tentativa de corrigir erro de dropdowns vazios na ConfigView
# - v1.2: Removida ConfigView; implementado comando /config_time_clock com parâmetros diretos para cargos, categorias e canal de logs

import nextcord
from nextcord.ext import commands, tasks
import logging
from datetime import datetime, timedelta
import pytz
import sqlite3
import json
from typing import Optional, List
import asyncio

# Configuração de logging
logger = logging.getLogger("nextcord.TimeClock")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs/time_clock.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class TimeClockCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Usa a conexão SQLite do main.py
        self.active_sessions = {}  # {user_id: session_id}
        self.default_config = {
            "enabled": False,
            "guild_id": None,
            "allowed_role_ids": [],
            "voice_category_ids": [],
            "log_channel_id": None
        }
        self.init_db()
        self.cleanup_old_records.start()

    def cog_unload(self):
        self.cleanup_old_records.cancel()

    def init_db(self):
        """Inicializa o banco de dados SQLite."""
        try:
            with self.db:
                cursor = self.db.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS time_clock_config (
                        guild_id TEXT PRIMARY KEY,
                        enabled BOOLEAN DEFAULT FALSE,
                        allowed_role_ids TEXT,
                        voice_category_ids TEXT,
                        log_channel_id TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS time_clock (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        clock_in TIMESTAMP NOT NULL,
                        clock_out TIMESTAMP,
                        duration INTEGER,
                        session_id TEXT UNIQUE
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS time_clock_config_backup (
                        backup_id TEXT PRIMARY KEY,
                        guild_id TEXT NOT NULL,
                        config TEXT NOT NULL,
                        backup_timestamp TEXT NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_clock_session ON time_clock (session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_clock_config_backup ON time_clock_config_backup (guild_id)")
                logger.info("Banco de dados inicializado")
        except Exception as e:
            logger.error(f"Erro na inicialização do banco: {e}")
            raise

    @tasks.loop(hours=24)
    async def cleanup_old_records(self):
        """Remove registros de bate-ponto com mais de 30 dias."""
        try:
            thirty_days_ago = datetime.now(pytz.UTC) - timedelta(days=30)
            with self.db:
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    DELETE FROM time_clock
                    WHERE clock_out IS NOT NULL AND clock_out < ?
                    """,
                    (thirty_days_ago.isoformat(),)
                )
                deleted_count = cursor.rowcount
                logger.info(f"Removidos {deleted_count} registros antigos de bate-ponto")
        except Exception as e:
            logger.error(f"Erro ao limpar registros antigos: {e}")

    @cleanup_old_records.before_loop
    async def before_cleanup(self):
        """Garante que o bot está pronto antes de iniciar a tarefa de limpeza."""
        await self.bot.wait_until_ready()

    def load_config(self, guild_id: str) -> dict:
        """Carrega a configuração do servidor."""
        try:
            with self.db:
                cursor = self.db.cursor()
                cursor.execute("SELECT * FROM time_clock_config WHERE guild_id = ?", (guild_id,))
                result = cursor.fetchone()
                if result:
                    config = dict(result)
                    return {
                        "enabled": bool(config["enabled"]),
                        "guild_id": guild_id,
                        "allowed_role_ids": json.loads(config["allowed_role_ids"]) if config["allowed_role_ids"] else [],
                        "voice_category_ids": json.loads(config["voice_category_ids"]) if config["voice_category_ids"] else [],
                        "log_channel_id": config["log_channel_id"]
                    }
                return {**self.default_config, "guild_id": guild_id}
        except Exception as e:
            logger.error(f"Erro ao carregar config para {guild_id}: {e}")
            return {**self.default_config, "guild_id": guild_id}

    def save_config(self, guild_id: str, config: dict):
        """Salva a configuração do servidor com backup automático."""
        try:
            with self.db:
                cursor = self.db.cursor()
                # Criar backup
                cursor.execute("SELECT * FROM time_clock_config WHERE guild_id = ?", (guild_id,))
                current_config = cursor.fetchone()
                if current_config:
                    backup_id = f"backup_{guild_id}_{datetime.now(pytz.UTC).strftime('%Y%m%d_%H%M%S')}"
                    backup_config = dict(current_config)
                    cursor.execute(
                        """
                        INSERT INTO time_clock_config_backup (backup_id, guild_id, config, backup_timestamp)
                        VALUES (?, ?, ?, ?)
                        """,
                        (backup_id, guild_id, json.dumps(backup_config), datetime.now(pytz.UTC).isoformat())
                    )
                    # Limitar backups (manter últimos 10)
                    cursor.execute(
                        """
                        SELECT backup_id FROM time_clock_config_backup
                        WHERE guild_id = ? ORDER BY backup_timestamp DESC LIMIT -1 OFFSET 10
                        """,
                        (guild_id,)
                    )
                    old_backups = cursor.fetchall()
                    for backup in old_backups:
                        cursor.execute("DELETE FROM time_clock_config_backup WHERE backup_id = ?", (backup["backup_id"],))

                # Salvar configuração
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO time_clock_config (
                        guild_id, enabled, allowed_role_ids, voice_category_ids, log_channel_id
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        config.get("enabled", False),
                        json.dumps(config.get("allowed_role_ids", [])),
                        json.dumps(config.get("voice_category_ids", [])),
                        config.get("log_channel_id")
                    )
                )
                logger.info(f"Configuração salva para {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar config para {guild_id}: {e}")

    async def send_log(self, guild_id: str, embed: nextcord.Embed) -> Optional[nextcord.Message]:
        """Envia embed para o canal de logs."""
        config = self.load_config(guild_id)
        if not config.get("log_channel_id"):
            return None
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return None
        channel = guild.get_channel(int(config["log_channel_id"]))
        if not channel or not isinstance(channel, nextcord.TextChannel):
            return None
        try:
            return await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Erro ao enviar log em {guild_id}: {e}")
            return None

    def format_duration(self, seconds: int) -> str:
        """Formata a duração em horas, minutos e segundos."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    class ControlPanelView(nextcord.ui.View):
        """Painel de controle para registro de ponto."""
        def __init__(self, cog, guild_id: str):
            super().__init__(timeout=None)
            self.cog = cog
            self.guild_id = guild_id

        async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
            config = self.cog.load_config(self.guild_id)
            return any(role.id == int(rid) for rid in config["allowed_role_ids"] for role in interaction.user.roles)

        @nextcord.ui.button(label="Abrir Ponto", emoji="🕒", style=nextcord.ButtonStyle.green, custom_id="time_clock_clock_in")
        async def clock_in(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
            if interaction.user.id in self.cog.active_sessions:
                await interaction.response.send_message("❌ Você já possui uma sessão ativa!", ephemeral=True)
                return
            tz = pytz.timezone("America/Sao_Paulo")
            now = datetime.now(tz)
            await self.cog.process_clock_in(interaction.user, self.guild_id, now)
            await interaction.response.send_message("✅ Entrada registrada!", ephemeral=True)

        @nextcord.ui.button(label="Ver Minhas Horas", emoji="⏱", style=nextcord.ButtonStyle.blurple, custom_id="time_clock_view_hours")
        async def view_hours(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
            await self.cog.mostrar_ranking(interaction, interaction.user)

    async def process_clock_in(self, member: nextcord.Member, guild_id: str, timestamp: datetime):
        """Processa entrada de ponto."""
        try:
            session_id = f"{guild_id}-{member.id}-{timestamp.timestamp()}"
            with self.db:
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    INSERT INTO time_clock (guild_id, user_id, clock_in, session_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (guild_id, str(member.id), timestamp.isoformat(), session_id)
                )
            self.active_sessions[member.id] = session_id
            embed = nextcord.Embed(
                title="🕒 Entrada Registrada",
                description=f"{member.mention} iniciou uma sessão em {timestamp.strftime('%d/%m/%Y %H:%M:%S')}.",
                color=nextcord.Color.from_rgb(43, 45, 49),
                timestamp=timestamp
            )
            embed.set_footer(text="Bate Ponto")
            await self.send_log(guild_id, embed)
            logger.info(f"Entrada registrada: {member.id} em {guild_id}")
        except Exception as e:
            logger.error(f"Erro no process_clock_in: {member.id} - {e}")

    async def process_clock_out(self, member: nextcord.Member, guild_id: str, timestamp: datetime):
        """Processa saída de ponto."""
        try:
            session_id = self.active_sessions.pop(member.id, None)
            if not session_id:
                with self.db:
                    cursor = self.db.cursor()
                    cursor.execute(
                        """
                        SELECT clock_in, session_id FROM time_clock 
                        WHERE guild_id = ? AND user_id = ? AND clock_out IS NULL
                        ORDER BY clock_in DESC LIMIT 1
                        """,
                        (guild_id, str(member.id))
                    )
                    result = cursor.fetchone()
                    if not result:
                        return
                    clock_in = datetime.fromisoformat(result['clock_in'])
                    session_id = result['session_id']
            else:
                with self.db:
                    cursor = self.db.cursor()
                    cursor.execute(
                        """
                        SELECT clock_in FROM time_clock 
                        WHERE session_id = ?
                        """,
                        (session_id,)
                    )
                    result = cursor.fetchone()
                    if not result:
                        return
                    clock_in = datetime.fromisoformat(result['clock_in'])
            duration = int((timestamp - clock_in).total_seconds())
            with self.db:
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    UPDATE time_clock 
                    SET clock_out = ?, duration = ?
                    WHERE session_id = ?
                    """,
                    (timestamp.isoformat(), duration, session_id)
                )
            embed = nextcord.Embed(
                title="🕔 Saída Registrada",
                description=(
                    f"{member.mention} finalizou a sessão em {timestamp.strftime('%d/%m/%Y %H:%M:%S')}.\n"
                    f"**Duração:** {self.format_duration(duration)}"
                ),
                color=nextcord.Color.from_rgb(43, 45, 49),
                timestamp=timestamp
            )
            embed.set_footer(text="Bate Ponto")
            await self.send_log(guild_id, embed)
            logger.info(f"Saída registrada: {member.id} em {guild_id}, duração: {duration}s")
        except Exception as e:
            logger.error(f"Erro no process_clock_out: {member.id} - {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        """Monitora mudanças de estado de voz."""
        guild_id = str(member.guild.id)
        config = self.load_config(guild_id)
        if not config["enabled"] or not config["voice_category_ids"]:
            return
        if not any(role.id == int(rid) for rid in config["allowed_role_ids"] for role in member.roles):
            return
        tz = pytz.timezone("America/Sao_Paulo")
        now = datetime.now(tz)

        def is_allowed_channel(channel):
            return channel and str(channel.category_id) in config["voice_category_ids"]

        if before.channel != after.channel:
            if not after.channel:  # Desconexão
                if member.id in self.active_sessions:
                    await self.process_clock_out(member, guild_id, now)
            elif is_allowed_channel(before.channel) and not is_allowed_channel(after.channel):
                if member.id in self.active_sessions:
                    await self.process_clock_out(member, guild_id, now)
            elif not is_allowed_channel(before.channel) and is_allowed_channel(after.channel):
                if member.id not in self.active_sessions:
                    await self.process_clock_in(member, guild_id, now)
            elif not before.channel and is_allowed_channel(after.channel):
                if member.id not in self.active_sessions:
                    await self.process_clock_in(member, guild_id, now)

    @nextcord.slash_command(name="config_time_clock", description="Configura o sistema de bate-ponto")
    @commands.has_permissions(administrator=True)
    async def config_time_clock(
        self,
        interaction: nextcord.Interaction,
        allowed_roles: str = nextcord.SlashOption(
            description="Cargos permitidos (IDs separados por vírgula, ex: 123,456)",
            required=True
        ),
        voice_categories: str = nextcord.SlashOption(
            description="Categorias de voz (IDs separados por vírgula, ex: 789,012)",
            required=True
        ),
        log_channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Canal de logs",
            required=True
        ),
        enabled: bool = nextcord.SlashOption(
            description="Ativar o sistema? (Padrão: Sim)",
            required=False,
            default=True
        )
    ):
        """Configura o sistema de bate-ponto com cargos, categorias de voz e canal de logs."""
        guild_id = str(interaction.guild.id)
        guild = interaction.guild

        # Validar cargos
        try:
            role_ids = [rid.strip() for rid in allowed_roles.split(",") if rid.strip()]
            allowed_role_ids = []
            for rid in role_ids:
                role = guild.get_role(int(rid))
                if not role:
                    await interaction.response.send_message(f"❌ Cargo com ID {rid} não encontrado!", ephemeral=True)
                    return
                if role.is_default():
                    await interaction.response.send_message(f"❌ O cargo @everyone não pode ser usado!", ephemeral=True)
                    return
                allowed_role_ids.append(rid)
            if not allowed_role_ids:
                await interaction.response.send_message("❌ Pelo menos um cargo válido deve ser especificado!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ IDs de cargos inválidos! Use números separados por vírgula.", ephemeral=True)
            return

        # Validar categorias de voz
        try:
            category_ids = [cid.strip() for cid in voice_categories.split(",") if cid.strip()]
            voice_category_ids = []
            for cid in category_ids:
                category = guild.get_channel_or_thread(int(cid))
                if not isinstance(category, nextcord.CategoryChannel):
                    await interaction.response.send_message(f"❌ ID {cid} não é uma categoria válida!", ephemeral=True)
                    return
                if not any(isinstance(c, nextcord.VoiceChannel) for c in category.channels):
                    await interaction.response.send_message(f"❌ A categoria {category.name} não possui canais de voz!", ephemeral=True)
                    return
                voice_category_ids.append(cid)
            if not voice_category_ids:
                await interaction.response.send_message("❌ Pelo menos uma categoria válida deve ser especificada!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ IDs de categorias inválidos! Use números separados por vírgula.", ephemeral=True)
            return

        # Validar canal de logs
        if not isinstance(log_channel, nextcord.TextChannel):
            await interaction.response.send_message("❌ O canal de logs deve ser um canal de texto!", ephemeral=True)
            return

        # Salvar configuração
        config = {
            "enabled": enabled,
            "guild_id": guild_id,
            "allowed_role_ids": allowed_role_ids,
            "voice_category_ids": voice_category_ids,
            "log_channel_id": str(log_channel.id)
        }
        self.save_config(guild_id, config)

        # Enviar confirmação
        embed = nextcord.Embed(
            title="⚙️ Configuração do Bate Ponto",
            description="Sistema configurado com sucesso!",
            color=nextcord.Color.from_rgb(43, 45, 49),
            timestamp=datetime.now(pytz.UTC)
        )
        embed.add_field(
            name="Status",
            value="✅ Ativado" if enabled else "❌ Desativado",
            inline=True
        )
        embed.add_field(
            name="Cargos Permitidos",
            value=", ".join(f"<@&{rid}>" for rid in allowed_role_ids),
            inline=True
        )
        embed.add_field(
            name="Categorias de Voz",
            value=", ".join(f"<#{cid}>" for cid in voice_category_ids),
            inline=False
        )
        embed.add_field(
            name="Canal de Logs",
            value=f"<#{log_channel.id}>",
            inline=True
        )
        embed.set_footer(text="Bate Ponto")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Configuração salva por {interaction.user.id} em {guild_id}")

    @nextcord.slash_command(name="mostrar_ranking", description="Exibe o ranking dos membros que mais bateram ponto")
    async def mostrar_ranking(self, interaction: nextcord.Interaction, user: nextcord.Member = None):
        """Exibe o ranking dos membros com mais horas acumuladas ou as horas de um usuário específico."""
        guild_id = str(interaction.guild.id)

        if user:
            # Exibir horas de um usuário específico
            with self.db:
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    SELECT SUM(duration) as total
                    FROM time_clock
                    WHERE guild_id = ? AND user_id = ? AND duration IS NOT NULL
                    """,
                    (guild_id, str(user.id))
                )
                total_seconds = cursor.fetchone()["total"] or 0
                duration = self.format_duration(total_seconds)
                embed = nextcord.Embed(
                    title="⏱️ Horas Acumuladas",
                    description=f"**Usuário:** {user.mention}\n**Horas acumuladas:** {duration}",
                    color=nextcord.Color.from_rgb(43, 45, 49),
                    timestamp=datetime.now(pytz.UTC)
                )
                embed.set_footer(text="Bate Ponto")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        # Exibir ranking completo
        with self.db:
            cursor = self.db.cursor()
            cursor.execute(
                """
                SELECT user_id, SUM(duration) as total
                FROM time_clock
                WHERE guild_id = ? AND duration IS NOT NULL
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 10
                """,
                (guild_id,)
            )
            ranking = cursor.fetchall()

        if not ranking:
            await interaction.response.send_message("❌ Nenhum membro no ranking ainda.", ephemeral=True)
            return

        ranking_text = "\n".join(
            f"{i + 1}. <@{record['user_id']}> - {self.format_duration(record['total'])}"
            for i, record in enumerate(ranking)
        )
        embed = nextcord.Embed(
            title="🏆 Ranking Bate Ponto",
            description=f"**Top membros que mais bateram ponto:**\n{ranking_text}",
            color=nextcord.Color.from_rgb(43, 45, 49),
            timestamp=datetime.now(pytz.UTC)
        )
        embed.set_footer(text="Bate Ponto")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Ranking exibido para guild_id: {guild_id}")

    @nextcord.slash_command(name="zerar_ranking", description="Zera as horas acumuladas de todos os membros")
    @commands.has_permissions(administrator=True)
    async def zerar_ranking(self, interaction: nextcord.Interaction):
        """Zera as horas acumuladas de todos os membros no servidor."""
        guild_id = str(interaction.guild.id)
        try:
            with self.db:
                cursor = self.db.cursor()
                cursor.execute("DELETE FROM time_clock WHERE guild_id = ?", (guild_id,))
                logger.info(f"Ranking zerado para guild_id: {guild_id}")

            config = self.load_config(guild_id)
            embed = nextcord.Embed(
                title="🗑️ Ranking Zerado",
                description=(
                    f"**Usuário:** {interaction.user.mention}\n"
                    f"**Ação:** Ranking de horas acumuladas zerado\n"
                    f"**Data:** {datetime.now(pytz.UTC).strftime('%d/%m/%Y %H:%M:%S')}"
                ),
                color=nextcord.Color.red(),
                timestamp=datetime.now(pytz.UTC)
            )
            embed.set_footer(text="Bate Ponto")
            await self.send_log(guild_id, embed)

            await interaction.response.send_message("✅ Ranking zerado com sucesso!", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao zerar ranking para guild_id: {guild_id}: {e}")
            await interaction.response.send_message("❌ Erro ao zerar ranking.", ephemeral=True)

def setup(bot):
    bot.add_cog(TimeClockCog(bot))