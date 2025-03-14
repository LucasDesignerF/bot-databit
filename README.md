# DataBit - Sistema de Tickets, Registro e Boas-Vindas 🤖

![GitHub](https://img.shields.io/github/license/LucasDesignerF/bot-databit?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Nextcord](https://img.shields.io/badge/Nextcord-2.0%2B-blueviolet?style=for-the-badge&logo=discord)

O **DataBit** é um bot Discord avançado desenvolvido para gerenciar tickets, registrar novos membros e enviar mensagens de boas-vindas personalizadas. Ele foi criado para ser altamente escalável e personalizável, atendendo às necessidades de servidores de todos os tamanhos.

---

## Recursos Principais 🚀

### 🎟 Sistema de Tickets
- Criação de tickets por categoria (Suporte Técnico, Compras, Parcerias, etc.).
- Painel interativo com botões para assumir, notificar e fechar tickets.
- Fechamento automático de tickets inativos.
- Avaliação do atendimento após o fechamento do ticket.

### 📝 Sistema de Registro
- Embed interativa com botão de registro.
- Atribuição automática de cargos após o registro.
- Integração com o sistema de boas-vindas.

### 🎉 Sistema de Boas-Vindas
- Mensagens de boas-vindas personalizadas com imagem gerada dinamicamente.
- Atribuição automática de cargos iniciais.
- Mensagem privada enviada ao novo membro.

---

## Pré-requisitos 📋

- Python 3.8 ou superior.
- Bibliotecas Python: `nextcord`, `Pillow`, `python-dotenv`, `aiohttp`.
- Token de um bot Discord válido.

---

## Instalação e Configuração ⚙️

### 1. Clone o repositório
```bash
git clone https://github.com/LucasDesignerF/bot-databit.git
cd bot-databit
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure o arquivo `.env`
Crie um arquivo `.env` na raiz do projeto e adicione o token do seu bot:
```env
DISCORD_TOKEN=seu_token_aqui
```

### 4. Execute o bot
```bash
python main.py
```

---

## Como Usar 🛠️

### Comandos Disponíveis

#### Sistema de Tickets 🎟
- **`/config_tickets`**: Configura o sistema de tickets.
- **`/create_ticket_menu`**: Cria o menu de tickets no canal especificado.

#### Sistema de Registro 📝
- **`/config_register`**: Configura o sistema de registro.
- **`/create_register_embed`**: Cria uma embed com o botão de registro.

#### Sistema de Boas-Vindas 🎉
- **`/config_welcome`**: Configura o sistema de boas-vindas.

---

## Estrutura do Projeto 📂

```
SeuRepositorio/
├── cogs/
│   ├── register_cog.py       # Cog para o sistema de registro
│   ├── ticket_cog.py         # Cog para o sistema de tickets
│   └── welcome_cog.py        # Cog para o sistema de boas-vindas
├── data/                     # Pasta para armazenar dados por servidor
├── fonts/                    # Pasta para armazenar fontes personalizadas
├── .env                      # Arquivo de configuração do ambiente
├── main.py                   # Arquivo principal do bot
└── README.md                 # Este arquivo
```

---

## Personalização 🎨

### Imagens e Fontes
- Substitua as imagens de fundo e thumbnails nas URLs dentro dos cogs.
- Adicione fontes personalizadas na pasta `fonts/` e atualize os caminhos nos cogs.

### Cores e Textos
- Ajuste as cores das embeds e textos diretamente nos arquivos dos cogs.

---

## Contribuição 🤝

Contribuições são bem-vindas! Siga os passos abaixo:

1. Faça um fork do repositório.
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`).
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`).
4. Faça push para a branch (`git push origin feature/nova-feature`).
5. Abra um Pull Request.

---

## Licença 📜

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## Contato 📞

- **GitHub**: [LucasDesignerF](https://github.com/LucasDesignerF)
- **Discord**: lrfortes
- **Email**: ofc.rede@gmail.com

---

Feito com ❤️ por **CodeProjects** e **RedeGamer - Serviços Escaláveis para seu Game**.