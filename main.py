# main.py
# Description: Arquivo principal do bot
# Date of Creation: 12/03/2025
# Created by: CodeProjects
# Modified by: CodeProjects
# Date of Modification: 19/03/2025
# Reason of Modification: Ajuste na cor da embed do comando /root_notify
# Version: 1.6
# Developer Of Version: CodeProjects and RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
import os
import importlib.util
import re
import asyncio
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configuração do bot com todas as intents
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ID do dono (você)
OWNER_ID = 1219787450583486500

# Função para processar emoji personalizado para exibição
def process_emoji(emoji_input: str) -> str:
    emoji_pattern = r"<a?:[a-zA-Z0-9_]+:\d+>"
    if re.match(emoji_pattern, emoji_input):
        return emoji_input
    return emoji_input

# Função para limpar emoji do status (já que CustomActivity não suporta emojis personalizados)
def clean_status(text: str) -> str:
    return re.sub(r"<a?:[a-zA-Z0-9_]+:\d+>", "", text).strip()

# Classe para o Modal de configuração de status
class StatusModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Configurar Status do Bot")
        
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
            placeholder="Ex: <:manutencao:1351925349067522059>",
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
            clean_status_text = f"{clean_status(display_status)}"
        
        status = status_map[status_type_input]
        await bot.change_presence(
            status=status,
            activity=nextcord.CustomActivity(name=clean_status_text)
        )
        
        await interaction.response.send_message(
            f"Status atualizado para '{display_status}' com tipo '{status_type_input.capitalize()}'!\n"
            f"Nota: Emojis personalizados não aparecem no status, apenas em mensagens. Use emojis Unicode se desejar.",
            ephemeral=True
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
        
        # Cria a embed de notificação com título, thumbnail e footer fixos, e cor personalizada
        embed = nextcord.Embed(
            title="<:1786617:1351930958156140644> Notificação de Atualização",
            description=notify_text,
            color=nextcord.Color.from_rgb(43, 45, 49)  # Cor RGB (43, 45, 49)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/5060/5060502.png")
        embed.set_footer(text="📢 Mensagem de Notificação ADM")

        await interaction.response.send_message(
            "Iniciando envio de notificações aos donos dos servidores... Isso pode levar um tempo!",
            ephemeral=True
        )

        # Envia a embed para cada dono de servidor
        for guild in bot.guilds:
            owner = guild.owner
            if owner:
                try:
                    await owner.send(embed=embed)
                    print(f"Notificação enviada para {owner} do servidor {guild.name}")
                    await asyncio.sleep(35)  # Atraso de 35 segundos para evitar rate limit
                except nextcord.Forbidden:
                    print(f"Não foi possível enviar DM para {owner} do servidor {guild.name} (DMs fechadas)")
                except Exception as e:
                    print(f"Erro ao enviar notificação para {owner} do servidor {guild.name}: {e}")

# Evento de inicialização
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}! 🤖")
    
    # Define o status fixo ao iniciar o bot
    status_text = "🛡️ Anti-Raid Ativado"
    await bot.change_presence(
        status=nextcord.Status.online,
        activity=nextcord.CustomActivity(name=status_text)
    )
    
    try:
        await bot.sync_application_commands()
        print("Comandos slash sincronizados com sucesso! ✅")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e} ❌")

# Evento de entrada em um novo servidor
@bot.event
async def on_guild_join(guild):
    guild_id = str(guild.id)
    data_dir = "data"
    guild_dir = os.path.join(data_dir, guild_id)
    if not os.path.exists(guild_dir):
        os.makedirs(guild_dir)
        print(f"Pasta de dados criada para o servidor: {guild.name} ({guild_id}) 📁")
    else:
        print(f"Pasta de dados já existe para o servidor: {guild.name} ({guild_id}) ✅")

# Comando /status restrito ao dono
@bot.slash_command(name="status", description="Atualiza o status personalizado do bot (apenas dono)")
async def status_command(interaction: nextcord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando!",
            ephemeral=True
        )
        return
    await interaction.response.send_modal(StatusModal())

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
    try:
        spec = importlib.util.spec_from_file_location("module", file_path)
        if spec is None:
            return False
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return hasattr(module, "setup") and callable(module.setup)
    except Exception as e:
        print(f"Erro ao verificar se {file_path} é um cog: {str(e)} ❌")
        return False

# Função para carregar cogs dinamicamente
def load_cogs():
    cogs_dir = "cogs"
    if not os.path.exists(cogs_dir):
        print(f"Diretório '{cogs_dir}' não encontrado! Criando... 📁")
        os.makedirs(cogs_dir)
        return
    for root, _, files in os.walk(cogs_dir):
        for filename in files:
            if filename.endswith(".py") and not filename.startswith("__"):
                file_path = os.path.join(root, filename)
                cog_path = file_path.replace(os.sep, ".")[:-3]
                if is_cog(file_path):
                    try:
                        bot.load_extension(cog_path)
                        print(f"Carreguei o cog: {cog_path} ✔️")
                    except Exception as e:
                        print(f"Erro ao carregar o cog {cog_path}: {e} ❌")
                else:
                    print(f"Ignorando {cog_path}: não é um cog válido (sem função 'setup') ⚠️")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Erro: DISCORD_TOKEN não encontrado no .env! ❌")
        exit(1)
    load_cogs()
    bot.run(DISCORD_TOKEN)