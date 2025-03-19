<p align="center">
  <img src="https://imgur.com/FI0J8Aw.png" alt="DataBit Logo" width="150"/>
</p>

<h1 align="center">DataBit 🤖</h1>
<p align="center">Um bot Discord poderoso para tickets, registros e boas-vindas</p>

<p align="center">
  <a href="https://github.com/LucasDesignerF/bot-databit/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/LucasDesignerF/bot-databit?style=flat-square&color=brightgreen" alt="Licença MIT"/>
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.12.7-3776AB?style=flat-square&logo=python" alt="Python 3.12.7"/>
  </a>
  <a href="https://nextcord.readthedocs.io/">
    <img src="https://img.shields.io/badge/Nextcord-3.0.1-7289DA?style=flat-square&logo=discord" alt="Nextcord 3.0.1"/>
  </a>
  <a href="https://github.com/LucasDesignerF/bot-databit/releases">
    <img src="https://img.shields.io/badge/Version-v1.0.0--alpha-orange?style=flat-square" alt="Versão do DataBit"/>
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
    <img src="https://img.shields.io/github/languages/top/LucasDesignerF/bot-databit?style=flat-square&color=FFD700" alt="Linguagem Principal"/>
  </a>
  <a href="https://github.com/LucasDesignerF/bot-databit/releases">
    <img src="https://img.shields.io/badge/Downloads-0+-blueviolet?style=flat-square" alt="Downloads"/>
  </a>
</p>

---

### 🌟 O que é o DataBit?

O **DataBit** é um bot Discord avançado projetado para simplificar a gestão de servidores. Com sistemas integrados de **tickets**, **registro de membros** e **boas-vindas personalizadas**, ele é escalável, personalizável e perfeito para comunidades de qualquer tamanho. Desenvolvido com paixão para oferecer uma experiência fluida e funcional!

---

### ✨ Recursos Principais

#### 🎟 Sistema de Tickets
- 🗂 Criação de tickets por categorias (Suporte, Compras, Parcerias, etc.).
- 🖱 Painel interativo com botões para assumir, notificar e encerrar.
- ⏳ Fechamento automático de tickets inativos.
- ⭐ Avaliação do atendimento após o encerramento.

#### 📝 Sistema de Registro
- 📋 Embed interativa com botão de registro.
- 🛡 Atribuição automática de cargos ao registrar.
- 🔗 Integração com o sistema de boas-vindas.

#### 🎉 Sistema de Boas-Vindas
- 🖼 Mensagens personalizadas com imagens dinâmicas.
- 🎭 Atribuição automática de cargos iniciais.
- ✉️ Mensagem privada de boas-vindas para novos membros.

---

### 📋 Pré-requisitos

- 🐍 **Python 3.8+**
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

---

### 🛠 Como Usar

#### 🎟 Comandos de Tickets
- **`/config_tickets`**: Configura o sistema de tickets.
- **`/create_ticket_menu`**: Cria o menu de tickets.

#### 📝 Comandos de Registro
- **`/config_register`**: Configura o sistema de registro.
- **`/create_register_embed`**: Gera a embed de registro.

#### 🎉 Comandos de Boas-Vindas
- **`/config_welcome`**: Configura as boas-vindas.

---

### 📂 Estrutura do Projeto

```
bot-databit/
├── cogs/                    # Módulos do bot
│   ├── register_cog.py      # Sistema de registro
│   ├── ticket_cog.py        # Sistema de tickets
│   └── welcome_cog.py       # Sistema de boas-vindas
├── data/                    # Dados salvos por servidor
├── fonts/                   # Fontes personalizadas
├── .env                     # Configurações do ambiente
├── main.py                  # Arquivo principal
└── README.md                # Documentação
```

---

### 🎨 Personalização

#### 🖼 Imagens e Fontes
- Substitua as URLs de imagens nos cogs por suas próprias.
- Adicione fontes na pasta `fonts/` e atualize os caminhos.

#### 🌈 Cores e Textos
- Edite as cores RGB e textos diretamente nos arquivos dos cogs.

---

### 🤝 Como Contribuir

1. 🍴 Faça um fork do repositório.
2. 🌿 Crie uma branch (`git checkout -b feature/sua-ideia`).
3. 💾 Commit suas mudanças (`git commit -m '✨ Adiciona algo incrível'`).
4. 🚀 Push para a branch (`git push origin feature/sua-ideia`).
5. 📬 Abra um Pull Request.

---

### 📜 Licença

Licenciado sob a **[MIT License](LICENSE)**. Veja mais detalhes no arquivo de licença.

---

### 📞 Contato

- **GitHub**: [LucasDesignerF](https://github.com/LucasDesignerF)
- **Discord**: `lrfortes`
- **Email**: [ofc.rede@gmail.com](mailto:ofc.rede@gmail.com)

---

<p align="center">
  Feito com ❤️ por <strong>CodeProjects</strong> e <strong>RedeGamer - Serviços Escaláveis para seu Game</strong>
</p>

