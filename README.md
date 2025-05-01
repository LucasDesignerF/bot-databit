<p align="center">
  <img src="https://imgur.com/udXUs5c.png" alt="DataBit Logo" width="150"/>
</p>

<h1 align="center">DataBit 🤖</h1>
<p align="center">Um bot Discord poderoso para tickets, registros, boas-vindas e proteção</p>

<p align="center">
  <a href="https://github.com/LucasDesignerF/bot-databit/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/LucasDesignerF/bot-databit?style=flat-square&color=brightgreen&cacheSeconds=0" alt="Licença MIT"/>
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python" alt="Python 3.12+"/>
  </a>
  <a href="https://nextcord.readthedocs.io/">
    <img src="https://img.shields.io/badge/Nextcord-3.0.2-7289DA?style=flat-square&logo=discord" alt="Nextcord 3.0.2"/>
  </a>
  <a href="https://github.com/LucasDesignerF/bot-databit/releases">
    <img src="https://img.shields.io/badge/Version-v3.0.0-orange?style=flat-square" alt="Versão do DataBit"/>
  </a>
  <a href="https://github.com/LucasDesignerF/bot-databit/commits/main">
    <img src="https://img.shields.io/github/last-commit/LucasDesignerF/bot-databit?style=flat-square&color=purple" alt="Último Commit"/>
  </a>
  <a href="https://discord.gg/AhcHfUpNeM">
    <img src="https://img.shields.io/badge/Discord-Join%20Us-5865F2?style=flat-square&logo=discord" alt="Servidor Oficial"/>
  </a>
  <a href="https://github.com/LucasDesignerF/bot-databit">
    <img src="https://img.shields.io/badge/Status-Online-00FF00?style=flat-square" alt="Status do Bot"/>
  </a>
  <a href="https://github.com/LucasDesignerF/bot-databit">
    <img src="https://img.shields.io/github/repo-size/LucasDesignerF/bot-databit?style=flat-square&color=blue" alt="Tamanho do Repositório"/>
  </a>
  <a href="https://github.com/LucasDesignerF/bot-databit/stargazers">
    <img src="https://img.shields.io/github/stars/LucasDesignerF/bot-databit?style=flat-square&color=yellow" alt="Estrelas"/>
  </a>
</p>

---

### 🌟 Por que DataBit?

O **DataBit** é um bot Discord *gratuito* e *open-source* projetado para simplificar a gestão de servidores com sistemas avançados de **tickets**, **registro**, **boas-vindas personalizadas** e **proteção anti-raid**. Desenvolvido pela **CodeProjects** com contribuições da **RedeGamer** e otimizações da **Grok (xAI)**, ele é perfeito para comunidades de jogos e servidores que buscam automação, segurança e escalabilidade.

- ✨ **Gratuito e Open-Source**: Código aberto, sem custos ocultos.
- 🛠️ **Fácil de Configurar**: Comandos intuitivos e setup rápido.
- 🎨 **Personalização Total**: Embeds, imagens e mensagens sob medida.
- 🛡️ **Seguro e Confiável**: Proteção contra raids e integração com SQLite.

Visite nosso site oficial ou junte-se ao servidor de suporte!

---

### ✨ Recursos Principais

O DataBit é composto por quatro módulos principais (cogs), cada um com funcionalidades específicas:

#### 🎟 Sistema de Tickets (`ticket_cog.py`)

- 🗂 Criação de tickets por categorias (ex.: Suporte, Compras, Parcerias).
- 🖱 Painel interativo com botões para assumir, notificar e encerrar tickets.
- ⏳ Monitoramento de inatividade com notificações e fechamento automático.
- 📜 Transcrições em HTML estilizadas com Tailwind CSS, disponíveis online ou para download.
- ⭐ Sistema de avaliação do atendimento com notas de 1 a 5.
- **Comandos**:
  - `/config_tickets`: Configura canais, cargos e tempos de inatividade.
  - `/create_ticket_menu`: Cria um menu interativo para abertura de tickets.
  - `/add_category`, `/edit_category`, `/remove_category`: Gerencia categorias de tickets.
  - `/person_tickets`: Personaliza embeds do sistema.

#### 📝 Sistema de Registro (`register_cog.py`)

- 📋 Embeds personalizáveis com upload de imagens ou URLs validadas.
- 🛡 Atribuição automática de cargos via botão interativo.
- 🔗 Integração com o sistema de boas-vindas para gerenciamento de cargos.
- **Comandos**:
  - `/config_register`: Define o cargo de registro.
  - `/person_register`: Personaliza a embed de registro.
  - `/create_register_embed`: Gera a embed com botão de registro.

#### 🎉 Sistema de Boas-Vindas (`welcome_cog.py`)

- 🖼 Embeds personalizáveis com suporte a variáveis `{member}`, `{guild}`, `{count}`.
- 🎭 Atribuição automática de cargos iniciais.
- ✉️ Mensagens privadas de boas-vindas.
- 🔗 Validação de URLs de imagens para qualquer serviço de hospedagem (ex.: Imgur, Discord CDN).
- **Comando**:
  - `/config_welcome`: Configura canal, cargo, embed e mensagem de DM.

#### 🛡️ Proteção Anti-Raid (`antiraid_cog.py`)

- 🚨 Monitoramento de atividades suspeitas (mensagens, canais, bans, cargos, convites).
- 🔒 Lockdowns automáticos configuráveis para restringir permissões do `@everyone`.
- 🖱 Interface interativa com botões e menus para configuração.
- 📋 Suporte a whitelist de cargos para administradores.
- **Comando**:
  - `/config_antiraid`: Configura limites e canais de log.

---

### 📋 Pré-requisitos

- 🐍 **Python 3.9+**
- 📦 **Dependências**:
  - `nextcord`
  - `aiohttp`
  - `python-dotenv`
  - `Pillow` (para manipulação de imagens no `/formater`)
- 🔑 **Token do Discord**: Crie um bot em Discord Developer Portal
- 💾 **SQLite**: Banco de dados para armazenamento de configurações

---

### ⚙️ Instalação

1. **Clone o repositório**

   ```bash
   git clone https://github.com/LucasDesignerF/bot-databit.git
   cd bot-databit
   ```

2. **Instale as dependências**

   ```bash
   pip install nextcord aiohttp python-dotenv Pillow
   ```

3. **Configure o** `.env`\
   Crie um arquivo `.env` na raiz e adicione:

   ```env
   DISCORD_TOKEN=seu_token_aqui
   ```

4. **Estruture o projeto**

   ```
   bot-databit/
   ├── cogs/
   │   ├── antiraid_cog.py      # Proteção anti-raid (v3.0)
   │   ├── register_cog.py      # Sistema de registro (v3.0.1)
   │   ├── ticket_cog.py        # Sistema de tickets (v5.3)
   │   ├── welcome_cog.py       # Sistema de boas-vindas (v4.1)
   ├── fonts/                   # Fontes personalizadas
   ├── transcripts/             # Transcrições de tickets
   ├── .env                     # Configurações do ambiente
   ├── main.py                  # Arquivo principal
   ├── ticket_system.db         # Banco de dados SQLite
   └── README.md                # Documentação
   ```

5. **Crie o** `main.py`

   ```python
   import nextcord
   from nextcord.ext import commands
   import sqlite3
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   bot = commands.Bot(command_prefix='/', intents=nextcord.Intents.all())
   bot.db = sqlite3.connect('ticket_system.db')
   
   for filename in os.listdir('./cogs'):
       if filename.endswith('.py'):
           bot.load_extension(f'cogs.{filename[:-3]}')
   
   bot.run(os.getenv('DISCORD_TOKEN'))
   ```

6. **Inicie o bot**

   ```bash
   python main.py
   ```

*Hospede na Discloud para uptime 24/7. Veja a documentação.*

---

### 🛠 Como Usar

1. **Adicione o bot ao servidor** com permissões de administrador.
2. **Configure os sistemas** usando os comandos:
   - `/config_tickets` para tickets.
   - `/config_register` e `/create_register_embed` para registro.
   - `/config_welcome` para boas-vindas.
   - `/config_antiraid` para proteção anti-raid.
3. **Personalize**:
   - Use `/person_tickets` e `/person_register` para editar embeds.
   - Adicione categorias de tickets com `/add_category`.
   - Use `/formater` para criar imagens dinâmicas de boas-vindas.
4. **Consulte a documentação** em docs.codeprojects.discloud.app para mais detalhes.

---

### 🎨 Personalização

- **Imagens e Fontes**: Use URLs ou uploads locais para embeds (`/person_register`, `/person_tickets`). Adicione fontes na pasta `fonts/` para o `/formater`.
- **Cores e Textos**: Configure cores RGB e mensagens nos comandos de personalização ou diretamente nos cogs.
- **Emojis**: Suporte a emojis personalizados nos sistemas de tickets e boas-vindas.

---

### 🤝 Como Contribuir

1. 🍴 Faça um fork do repositório.
2. 🌿 Crie uma branch: `git checkout -b feature/sua-ideia`.
3. 💾 Commit suas mudanças: `git commit -m '✨ Adiciona algo incrível'`.
4. 🚀 Push para a branch: `git push origin feature/sua-ideia`.
5. 📬 Abra um Pull Request.

Junte-se ao servidor de suporte para discutir ideias!

---

### 📜 Licença

Licenciado sob a **MIT License**. Veja mais detalhes no arquivo de licença.

---

### 📞 Contato

- 🌐 **Website**: codeprojects.discloud.app
- 💬 **Discord**: Servidor Oficial | `lrfortes`
- 🐙 **GitHub**: LucasDesignerF
- 📧 **Email**: ofc.rede@gmail.com

---

<p align="center">
  Feito com ❤️ por <strong><a href="https://codeprojects.discloud.app/">CodeProjects</a></strong> e <strong><a href="https://discord.gg/x74fnzcz2S">RedeGamer - Serviços Escaláveis para seu Game</a></strong>
</p>
