# main.py
# Description: Arquivo principal do bot
# Date of Creation: 12/03/2025
# Created by: CodeProjects
# Modified by: CodeProjects
# Date of Modification: 19/03/2025
# Reason of Modification: Adição de status personalizado com suporte a emojis
# Version: 1.2
# Developer Of Version: CodeProjects and RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
import os
import importlib.util
import re
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configuração do bot com todas as intents
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ID do dono (você)
OWNER_ID = 1219787450583486500

# Função para converter emoji personalizado em formato utilizável
def process_emoji(emoji_input: str) -> str:
    # Regex para detectar emojis personalizados no formato <:nome:ID> ou <a:nome:ID>
    emoji_pattern = r"<a?:[a-zA-Z0-9_]+:\d+>"
    if re.match(emoji_pattern, emoji_input):
        # Extrai o ID do emoji
        emoji_id = emoji_input.split(":")[-1][:-1]
        # Verifica se o emoji existe no cache do bot
        emoji = nextcord.utils.get(bot.emojis, id=int(emoji_id))
        if emoji:
            return str(emoji)  # Retorna o emoji como string utilizável
        else:
            return emoji_input  # Retorna o texto original se o emoji não for encontrado
    return emoji_input

# Classe para o Modal de configuração de status
class StatusModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Configurar Status do Bot")
        
        # Campo para a frase do status
        self.status_text = nextcord.ui.TextInput(
            label="Frase do Status",
            placeholder="Digite a frase que deseja exibir",
            required=True,
            max_length=128
        )
        self.add_item(self.status_text)
        
        # Campo para o tipo de status
        self.status_type = nextcord.ui.TextInput(
            label="Tipo de Status",
            placeholder="Digite: Online, Ausente, Ocupado ou Offline",
            required=True,
            max_length=10
        )
        self.add_item(self.status_type)
        
        # Campo opcional para emoji personalizado
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
        
        # Mapeamento dos tipos de status
        status_map = {
            "online": nextcord.Status.online,
            "ausente": nextcord.Status.idle,
            "ocupado": nextcord.Status.dnd,
            "offline": nextcord.Status.invisible
        }
        
        # Verifica se o tipo de status é válido
        if status_type_input not in status_map:
            await interaction.response.send_message(
                "Tipo de status inválido! Use: Online, Ausente, Ocupado ou Offline",
                ephemeral=True
            )
            return
        
        # Processa o emoji personalizado, se fornecido
        final_status = status_text
        if emoji_input:
            processed_emoji = process_emoji(emoji_input)
            final_status = f"{processed_emoji} {status_text}"
        
        # Define o novo status
        status = status_map[status_type_input]
        await bot.change_presence(
            status=status,
            activity=nextcord.CustomActivity(name=final_status)
        )
        
        await interaction.response.send_message(
            f"Status atualizado para '{final_status}' com tipo '{status_type_input.capitalize()}'!",
            ephemeral=True
        )

# Evento de inicialização
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}! 🤖")
    try:
        # Sincroniza os slash commands
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

    # Cria a pasta do servidor se ela não existir
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
    
    # Envia o modal
    await interaction.response.send_modal(StatusModal())

# Função para verificar se o arquivo é um cog (tem função setup)
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

# Função para carregar cogs dinamicamente em todas as subpastas de cogs/
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
                cog_path = file_path.replace(os.sep, ".")[:-3]  # Converte pra formato de módulo
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
