<p align="center">
  <img src="https://imgur.com/MMvOfe1.png" alt="DataBit Logo" width="150"/>
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
    <img src="https://img.shields.io/badge/Version-v2.3.2-orange?style=flat-square" alt="Versão do DataBit"/>
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

O **DataBit** é um bot Discord *gratuito* e *open-source* projetado para simplificar a gestão de servidores. Com sistemas avançados de **tickets**, **registro**, **boas-vindas personalizadas** e **proteção anti-raid**, ele é perfeito para comunidades de qualquer tamanho. Desenvolvido com paixão pela **CodeProjects** e **RedeGamer**, o DataBit oferece uma experiência fluida, escalável e altamente personalizável!

- ✨ **Gratuito e Open-Source**: Código aberto, sem custos ocultos.
- 🛠️ **Fácil de Configurar**: Comandos intuitivos e setup rápido.
- 🎨 **Personalização Total**: Embeds, imagens e mensagens sob medida.
- 🛡️ **Seguro e Confiável**: Proteção contra raids e hospedagem na Discloud.

Visite nosso [site oficial](https://codeprojects.discloud.app/) ou junte-se ao [servidor de suporte](https://discord.gg/AhcHfUpNeM)!

---

### ✨ Recursos Principais

#### 🎟 Sistema de Tickets
- 🗂 Criação de tickets por categorias (Suporte, Compras, Parcerias, etc.).
- 🖱 Painel interativo com botões para assumir, notificar e encerrar.
- ⏳ Fechamento automático de tickets inativos.
- ⭐ Avaliação do atendimento após o encerramento.

#### 📝 Sistema de Registro
- 📋 Embeds personalizáveis com upload de imagens locais ou URLs validadas.
- 🛡 Atribuição automática de cargos via botão interativo.
- 🔗 Integração com o sistema de boas-vindas.

#### 🎉 Sistema de Boas-Vindas
- 🖼 Imagens dinâmicas criadas com o editor interativo `/formater`.
- 🎭 Atribuição automática de cargos iniciais.
- ✉️ Mensagem privada de boas-vindas para novos membros.

#### 🛡️ Proteção Anti-Raid
- 🚨 Monitoramento de atividades suspeitas.
- 🔒 Lockdowns automáticos configuráveis para proteger o servidor.

---

### 📋 Pré-requisitos

- 🐍 **Python 3.12+**
- 📦 **Dependências**: `nextcord`, `Pillow`, `python-dotenv`, `aiohttp`
- 🔑 **Token do Discord**: Crie um bot em [Discord Developer Portal](https://discord.com/developers/applications)

---

### ⚙️ Instalação

1. **Clone o repositório**  
   ```bash
   git clone https://github.com/LucasDesignerF/bot-databit.git
   cd bot-databit
   ```

2. **Instale as dependências**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure o `.env`**  
   Crie um arquivo `.env` na raiz e adicione:  
   ```env
   DISCORD_TOKEN=seu_token_aqui
   ```

4. **Inicie o bot**  
   ```bash
   python main.py
   ```

*Hospede na [Discloud](https://discloud.app/) para uptime 24/7. Veja a [documentação](https://docs.codeprojects.discloud.app/).*

---

### 🛠 Como Usar

#### Comandos Principais
| **Comando**                | **Descrição**                                              |
|----------------------------|------------------------------------------------------------|
| `/config_tickets`          | Configura o sistema de tickets com categorias e canais.     |
| `/create_ticket_menu`      | Cria um menu interativo para abertura de tickets.           |
| `/config_register`         | Define o cargo e canal para o sistema de registro.          |
| `/create_register_embed`   | Gera uma embed de registro com botão interativo.           |
| `/config_welcome`          | Personaliza mensagens e imagens de boas-vindas.             |
| `/formater`                | Editor interativo para criar imagens de boas-vindas únicas. |

*Consulte a [documentação](https://docs.codeprojects.discloud.app/) para mais comandos.*

---

### 📂 Estrutura do Projeto

```
bot-databit/
├── cogs/                    # Módulos do bot
│   ├── antiraid_cog.py      # Proteção anti-raid
│   ├── register_cog.py      # Sistema de registro (v2.3.2)
│   ├── ticket_cog.py        # Sistema de tickets
│   └── welcome_cog.py       # Sistema de boas-vindas
├── data/                    # Dados salvos por servidor
├── fonts/                   # Fontes personalizadas
├── .env                     # Configurações do ambiente
├── main.py                  # Arquivo principal
├── requirements.txt         # Dependências
└── README.md                # Documentação
```

---

### 🎨 Personalização

#### 🖼 Imagens e Fontes
- Use imagens locais ou URLs no sistema de registro e boas-vindas (`/formater`).
- Adicione fontes na pasta `fonts/` e atualize os caminhos nos cogs.

#### 🌈 Cores e Textos
- Edite cores RGB e textos diretamente nos arquivos dos cogs (`cogs/*.py`).

---

### 🤝 Como Contribuir

1. 🍴 Faça um fork do repositório.
2. 🌿 Crie uma branch: `git checkout -b feature/sua-ideia`.
3. 💾 Commit suas mudanças: `git commit -m '✨ Adiciona algo incrível'`.
4. 🚀 Push para a branch: `git push origin feature/sua-ideia`.
5. 📬 Abra um Pull Request.

Junte-se ao [servidor de suporte](https://discord.gg/AhcHfUpNeM) para discutir ideias!

---

### 📜 Licença

Licenciado sob a **[MIT License](LICENSE)**. Veja mais detalhes no arquivo de licença.

---

### 📞 Contato

- 🌐 **Website**: [codeprojects.discloud.app](https://codeprojects.discloud.app/)
- 💬 **Discord**: [Servidor Oficial](https://discord.gg/AhcHfUpNeM) | `lrfortes`
- 🐙 **GitHub**: [LucasDesignerF](https://github.com/LucasDesignerF)
- 📧 **Email**: [ofc.rede@gmail.com](mailto:ofc.rede@gmail.com)

---

<p align="center">
  Feito com ❤️ por <strong><a href="https://codeprojects.discloud.app/">CodeProjects</a></strong> e <strong><a href="https://discord.gg/x74fnzcz2S">RedeGamer - Serviços Escaláveis para seu Game</a></strong>
</p>
