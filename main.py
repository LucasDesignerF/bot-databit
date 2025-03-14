# main.py
# Description: Arquivo principal do bot
# Date of Creation: 12/03/2025
# Created by: CodeProjects
# Modified by: CodeProjects
# Date of Modification: 12/03/2025
# Reason of Modification: Criação do arquivo
# Version: 1.0
# Developer Of Version: CodeProjects and RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
import os
import importlib.util
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configuração do bot com todas as intents
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

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