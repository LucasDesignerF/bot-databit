# main.py
# Description: Arquivo principal do bot DataBit, responsável por inicialização, cogs e comandos administrativos
# Date of Creation: 12/03/2025
# Created by: CodeProjects
# Modified by: CodeProjects, RedeGamer
# Date of Modification: 19/04/2025
# Reason of Modification: Correção de sincronização de comandos e implementação de status por servidor via canais
# Version: 1.6.4
# Developer Of Version: CodeProjects and RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
import os
import importlib.util
import re
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import sys
import json

# Configuração de logging
logger = logging.getLogger("DataBit")
logger.setLevel(logging.INFO)
os.makedirs("logs", exist_ok=True)  # Cria diretório de logs se não existir
handler = RotatingFileHandler("logs/databit.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Configura StreamHandler com tratamento de codificação para o console
console_handler = logging.StreamHandler(stream=sys.stdout)
console_handler.setFormatter(formatter)
if sys.platform == "win32":
    console_handler.setStream(open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace'))
logger.addHandler(console_handler)

# Carrega variáveis do .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN não encontrado no .env!")
    exit(1)

# Configurações
OWNER_ID = 1219787450583486500
DATA_DIR = "data"
GLOBAL_STATUS_FILE = os.path.join(DATA_DIR, "global_status.json")
NOTIFY_COLOR = nextcord.Color.from_rgb(43, 45, 49)
NOTIFY_THUMBNAIL = "https://cdn-icons-png.flaticon.com/512/5060/5060502.png"
NOTIFY_DELAY = 5  # Atraso em segundos entre notificações

# Configuração do bot com todas as intents
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Função para processar emoji personalizado para exibição
def process_emoji(emoji_input: str) -> str:
    """Valida e retorna emoji personalizado para exibição."""
    emoji_pattern = r"<a?:[a-zA-Z0-9_]+:\d+>"
    if re.match(emoji_pattern, emoji_input):
        return emoji_input
    return emoji_input

# Função para limpar emoji do status (CustomActivity não suporta emojis personalizados)
def clean_status(text: str) -> str:
    """Remove emojis personalizados do texto do status."""
    return re.sub(r"<a?:[a-zA-Z0-9_]+:\d+>", "", text).strip()

# Função para carregar status de um servidor ou global
def load_status(guild_id: str = None) -> dict:
    """Carrega o status de um servidor ou o status global."""
    status_file = GLOBAL_STATUS_FILE if guild_id is None else os.path.join(DATA_DIR, guild_id, "status.json")
    default_status = {"text": "🛡️ Anti-Raid Ativado", "type": "online", "emoji": "", "channel_id": None}
    try:
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return default_status
    except Exception as e:
        logger.error(f"Erro ao carregar status de {status_file}: {e}")
        return default_status

# Função para salvar status de um servidor ou global
def save_status(status_text: str, status_type: str, emoji: str, guild_id: str = None, channel_id: str = None):
    """Salva o status de um servidor ou o status global."""
    status_file = GLOBAL_STATUS_FILE if guild_id is None else os.path.join(DATA_DIR, guild_id, "status.json")
    try:
        os.makedirs(os.path.dirname(status_file), exist_ok=True)
        status_data = {"text": status_text, "type": status_type, "emoji": emoji, "channel_id": channel_id}
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar status em {status_file}: {e}")

# Classe para o Modal de configuração de status
class StatusModal(nextcord.ui.Modal):
    def __init__(self, guild_id: str = None):
        super().__init__(f"Configurar Status {'Global' if guild_id is None else f'do Servidor {guild_id}'}")
        self.guild_id = guild_id
        
        self.status_text = nextcord.ui.TextInput(
            label="Frase do Status",
            placeholder="Digite a frase que deseja exibir",
            required=True,
            max_length=128
        )
        self.add_item(self.status_text)
        
        self.status_type = nextcord.ui.TextInput(
            label="Tipo de Status",
            placeholder="Digite: Online, Ausente, Ocupado ou Offline",
            required=True,
            max_length=10
        )
        self.add_item(self.status_type)
        
        self.status_emoji = nextcord.ui.TextInput(
            label="Emoji Personalizado (Opcional)",
            placeholder="Ex: <:manutencao:1351925349067522059> ou 😊",
            required=False,
            max_length=32
        )
        self.add_item(self.status_emoji)

    async def callback(self, interaction: nextcord.Interaction):
        status_text = self.status_text.value
        status_type_input = self.status_type.value.lower()
        emoji_input = self.status_emoji.value or ""
        
        status_map = {
            "online": nextcord.Status.online,
            "ausente": nextcord.Status.idle,
            "ocupado": nextcord.Status.dnd,
            "offline": nextcord.Status.invisible
        }
        
        if status_type_input not in status_map:
            await interaction.response.send_message(
                "Tipo de status inválido! Use: Online, Ausente, Ocupado ou Offline",
                ephemeral=True
            )
            return
        
        display_status = status_text
        clean_status_text = status_text
        if emoji_input:
            processed_emoji = process_emoji(emoji_input)
            display_status = f"{processed_emoji} {status_text}"
            clean_status_text = clean_status(display_status)
        
        status = status_map[status_type_input]
        scope = "global" if self.guild_id is None else f"servidor {self.guild_id}"
        try:
            if self.guild_id:
                guild = bot.get_guild(int(self.guild_id))
                if not guild:
                    await interaction.response.send_message(
                        f"Servidor com ID {self.guild_id} não encontrado!",
                        ephemeral=True
                    )
                    return
                # Carrega o canal de status do servidor
                status_config = load_status(self.guild_id)
                channel_id = status_config.get("channel_id")
                if channel_id:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        embed = nextcord.Embed(
                            title="Status do Bot",
                            description=f"{display_status} ({status_type_input.capitalize()})",
                            color=NOTIFY_COLOR
                        )
                        await channel.send(embed=embed)
                    else:
                        logger.warning(f"Canal {channel_id} não encontrado no servidor {self.guild_id}")
                save_status(status_text, status_type_input, emoji_input, self.guild_id, channel_id)
                await interaction.response.send_message(
                    f"Status configurado para '{display_status}' ({status_type_input.capitalize()}) no {scope}. "
                    f"{'Exibido no canal configurado.' if channel_id else 'Configure um canal com /set_status_channel.'}",
                    ephemeral=True
                )
            else:
                # Atualiza o status global do bot
                await bot.change_presence(
                    status=status,
                    activity=nextcord.CustomActivity(name=clean_status_text)
                )
                save_status(status_text, status_type_input, emoji_input)
                await interaction.response.send_message(
                    f"Status global atualizado para '{display_status}' ({status_type_input.capitalize()})!",
                    ephemeral=True
                )
            logger.info(f"Status atualizado por {interaction.user}: {display_status} ({status_type_input}) ({scope})")
        except Exception as e:
            logger.error(f"Erro ao atualizar status ({scope}): {e}")
            await interaction.response.send_message(
                f"Erro ao atualizar status ({scope}). Tente novamente.", ephemeral=True
            )

# Classe para o Modal de notificação
class NotifyModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Notificação para Donos de Servidores")
        
        self.notify_text = nextcord.ui.TextInput(
            label="Texto do Aviso",
            placeholder="Digite o texto completo da notificação",
            required=True,
            max_length=2000,
            style=nextcord.TextInputStyle.paragraph
        )
        self.add_item(self.notify_text)

    async def callback(self, interaction: nextcord.Interaction):
        notify_text = self.notify_text.value
        
        embed = nextcord.Embed(
            title="<:1786617:1351930958156140644> Notificação de Atualização",
            description=notify_text,
            color=NOTIFY_COLOR
        )
        embed.set_thumbnail(url=NOTIFY_THUMBNAIL)
        embed.set_footer(text="📢 Mensagem de Notificação ADM")

        await interaction.response.send_message(
            "Iniciando envio de notificações aos donos dos servidores... Isso pode levar um tempo!",
            ephemeral=True
        )

        success_count = 0
        for guild in bot.guilds:
            owner = guild.owner
            if owner:
                try:
                    await owner.send(embed=embed)
                    logger.info(f"Notificação enviada para {owner} do servidor {guild.name}")
                    success_count += 1
                    await asyncio.sleep(NOTIFY_DELAY)  # Atraso configurável para evitar rate limit
                except nextcord.Forbidden:
                    logger.warning(f"Não foi possível enviar DM para {owner} do servidor {guild.name} (DMs fechadas)")
                except nextcord.HTTPException as e:
                    if e.status == 429:  # Rate limit
                        retry_after = e.retry_after or NOTIFY_DELAY
                        logger.warning(f"Rate limit atingido. Aguardando {retry_after}s")
                        await asyncio.sleep(retry_after)
                        try:
                            await owner.send(embed=embed)
                            logger.info(f"Notificação enviada para {owner} do servidor {guild.name} após retry")
                            success_count += 1
                        except Exception as retry_e:
                            logger.error(f"Erro ao retry notificação para {owner} do servidor {guild.name}: {retry_e}")
                    else:
                        logger.error(f"Erro ao enviar notificação para {owner} do servidor {guild.name}: {e}")
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação para {owner} do servidor {guild.name}: {e}")

        await interaction.followup.send(
            f"Notificações enviadas com sucesso para {success_count}/{len(bot.guilds)} servidores!",
            ephemeral=True
        )
        logger.info(f"Notificação enviada por {interaction.user} para {success_count}/{len(bot.guilds)} servidores")

# Evento de inicialização
@bot.event
async def on_ready():
    logger.info(f"Bot conectado como {bot.user}!")
    
    # Aplica status global
    global_status = load_status()
    status_map = {
        "online": nextcord.Status.online,
        "ausente": nextcord.Status.idle,
        "ocupado": nextcord.Status.dnd,
        "offline": nextcord.Status.invisible
    }
    
    try:
        status_text = global_status["text"]
        status_type = global_status.get("type", "online")
        emoji = process_emoji(global_status.get("emoji", ""))
        display_status = f"{emoji} {status_text}" if emoji else status_text
        clean_status_text = clean_status(display_status)
        await bot.change_presence(
            status=status_map.get(status_type, nextcord.Status.online),
            activity=nextcord.CustomActivity(name=clean_status_text)
        )
        logger.info(f"Status global aplicado: {display_status} ({status_type})")
    except Exception as e:
        logger.error(f"Erro ao aplicar status inicial: {e}")
    
    # Sincroniza comandos
    try:
        await bot.sync_application_commands()
        logger.info("Comandos slash sincronizados com sucesso")
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos: {e}")
        try:
            owner = bot.get_user(OWNER_ID)
            if owner:
                await owner.send(f"⚠️ Erro ao sincronizar comandos: {e}")
        except Exception as notify_e:
            logger.warning(f"Não foi possível notificar dono {OWNER_ID}: {notify_e}")

# Evento de entrada em um novo servidor
@bot.event
async def on_guild_join(guild):
    guild_id = str(guild.id)
    guild_dir = os.path.join(DATA_DIR, guild_id)
    try:
        os.makedirs(guild_dir, exist_ok=True)
        logger.info(f"Pasta de dados criada para o servidor: {guild.name} ({guild_id})")
    except Exception as e:
        logger.error(f"Erro ao criar pasta para {guild.name} ({guild_id}): {e}")

# Comando /status restrito ao dono (status por servidor)
@bot.slash_command(name="status", description="Configura o status do bot em um servidor específico (apenas dono)")
async def status_command(interaction: nextcord.Interaction, guild_id: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando!",
            ephemeral=True
        )
        return
    if not guild_id.isdigit() or not bot.get_guild(int(guild_id)):
        await interaction.response.send_message(
            "ID de servidor inválido ou o bot não está nesse servidor!",
            ephemeral=True
        )
        return
    await interaction.response.send_modal(StatusModal(guild_id))

# Comando /status_all restrito ao dono (status global)
@bot.slash_command(name="status_all", description="Atualiza o status do bot em todos os servidores (apenas dono)")
async def status_all_command(interaction: nextcord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando!",
            ephemeral=True
        )
        return
    await interaction.response.send_modal(StatusModal())

# Comando /set_status_channel restrito ao dono
@bot.slash_command(name="set_status_channel", description="Define o canal para exibir o status em um servidor (apenas dono)")
async def set_status_channel_command(interaction: nextcord.Interaction, guild_id: str, channel_id: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando!",
            ephemeral=True
        )
        return
    if not guild_id.isdigit() or not bot.get_guild(int(guild_id)):
        await interaction.response.send_message(
            "ID de servidor inválido ou o bot não está nesse servidor!",
            ephemeral=True
        )
        return
    if not channel_id.isdigit():
        await interaction.response.send_message(
            "ID de canal inválido!",
            ephemeral=True
        )
        return
    guild = bot.get_guild(int(guild_id))
    channel = guild.get_channel(int(channel_id))
    if not channel:
        await interaction.response.send_message(
            f"Canal com ID {channel_id} não encontrado no servidor {guild_id}!",
            ephemeral=True
        )
        return
    try:
        status_config = load_status(guild_id)
        save_status(
            status_config["text"],
            status_config["type"],
            status_config["emoji"],
            guild_id,
            channel_id
        )
        await interaction.response.send_message(
            f"Canal <#{channel_id}> configurado para exibir o status no servidor {guild_id}!",
            ephemeral=True
        )
        logger.info(f"Canal de status configurado por {interaction.user}: {channel_id} no servidor {guild_id}")
    except Exception as e:
        logger.error(f"Erro ao configurar canal de status para servidor {guild_id}: {e}")
        await interaction.response.send_message(
            "Erro ao configurar canal de status. Tente novamente.", ephemeral=True
        )

# Comando /root_notify restrito ao dono
@bot.slash_command(name="root_notify", description="Envia notificação aos donos de servidores (apenas dono)")
async def root_notify_command(interaction: nextcord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando!",
            ephemeral=True
        )
        return
    await interaction.response.send_modal(NotifyModal())

# Função para verificar se o arquivo é um cog
def is_cog(file_path: str) -> bool:
    """Verifica se o arquivo contém uma função setup válida."""
    try:
        spec = importlib.util.spec_from_file_location("module", file_path)
        if spec is None:
            return False
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return hasattr(module, "setup") and callable(module.setup)
    except Exception as e:
        logger.error(f"Erro ao verificar se {file_path} é um cog: {str(e)}")
        return False

# Função para carregar cogs dinamicamente
def load_cogs():
    """Carrega todos os cogs válidos do diretório cogs/."""
    cogs_dir = "cogs"
    try:
        os.makedirs(cogs_dir, exist_ok=True)
        logger.info(f"Diretório '{cogs_dir}' criado ou já existente")
    except Exception as e:
        logger.error(f"Erro ao criar diretório '{cogs_dir}': {e}")
        return
    for root, _, files in os.walk(cogs_dir):
        for filename in files:
            if filename.endswith(".py") and not filename.startswith("__"):
                file_path = os.path.join(root, filename)
                cog_path = file_path.replace(os.sep, ".")[:-3]
                if is_cog(file_path):
                    try:
                        bot.load_extension(cog_path)
                        logger.info(f"Carregado cog: {cog_path}")
                    except Exception as e:
                        logger.error(f"Erro ao carregar cog {cog_path}: {e}")
                else:
                    logger.warning(f"Ignorado {cog_path}: não é um cog válido (sem função 'setup')")

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)  # Cria diretório de dados se não existir
    load_cogs()
    bot.run(DISCORD_TOKEN)