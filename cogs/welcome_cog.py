# welcome_cog.py
# Description: Cog para gerenciar boas-vindas de novos membros com imagem personalizada
# Date of Creation: 12/03/2025
# Created by: CodeProjects
# Modified by: Grok (xAI), CodeProjects, RedeGamer
# Date of Modification: 19/04/2025
# Reason of Modification: Adição do comando /formater para edição interativa de imagens de boas-vindas
# Version: 2.9
# Developer Of Version: Grok (xAI), CodeProjects, RedeGamer - Serviços Escaláveis para seu Game

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, File, ButtonStyle, TextInputStyle
import os
import json
import logging
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import asyncio
import hashlib
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

# Configuração de logging
logger = logging.getLogger("DataBit.WelcomeCog")
logger.setLevel(logging.INFO)

class Element:
    """Classe base para elementos da imagem de boas-vindas."""
    def __init__(self, element_type: str, x: int, y: int, opacity: float = 1.0):
        self.type = element_type
        self.x = x
        self.y = y
        self.opacity = max(0.0, min(1.0, opacity))

    def to_dict(self) -> dict:
        return {"type": self.type, "x": self.x, "y": self.y, "opacity": self.opacity}

class AvatarElement(Element):
    """Elemento para o avatar do membro."""
    def __init__(self, x: int, y: int, size: int, outline: bool = True, outline_color: List[int] = [255, 255, 255], opacity: float = 1.0):
        super().__init__("avatar", x, y, opacity)
        self.size = size
        self.outline = outline
        self.outline_color = outline_color

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "size": self.size,
            "outline": self.outline,
            "outline_color": self.outline_color
        })
        return base

class TextElement(Element):
    """Elemento para texto personalizado."""
    def __init__(self, x: int, y: int, text: str, font_size: int, color: List[int], font_path: str = "", opacity: float = 1.0):
        super().__init__("text", x, y, opacity)
        self.text = text
        self.font_size = font_size
        self.color = color
        self.font_path = font_path

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "text": self.text,
            "font_size": self.font_size,
            "color": self.color,
            "font_path": self.font_path
        })
        return base

class ShapeElement(Element):
    """Elemento para formas geométricas."""
    def __init__(self, x: int, y: int, shape_type: str, width: int, height: int, color: List[int], opacity: float = 1.0):
        super().__init__("shape", x, y, opacity)
        self.shape_type = shape_type  # "rectangle" ou "circle"
        self.width = width
        self.height = height
        self.color = color

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "shape_type": self.shape_type,
            "width": self.width,
            "height": self.height,
            "color": self.color
        })
        return base

class BackgroundElement(Element):
    """Elemento para o fundo da imagem."""
    def __init__(self, source: str, color: List[int] = [50, 50, 50], opacity: float = 1.0):
        super().__init__("background", 0, 0, opacity)
        self.source = source  # URL, "local://<hash>.png" ou ""
        self.color = color  # Usado se source for ""

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "source": self.source,
            "color": self.color
        })
        return base

class EditorView(nextcord.ui.View):
    """View interativa para o comando /formater."""
    def __init__(self, cog, interaction: Interaction, elements: List[Element]):
        super().__init__(timeout=300)
        self.cog = cog
        self.interaction = interaction
        self.elements = elements
        self.message = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.interaction.user.id

    @nextcord.ui.button(label="Adicionar Elemento", style=ButtonStyle.green)
    async def add_element(self, button: nextcord.ui.Button, interaction: Interaction):
        modal = AddElementModal(self.cog, self.elements)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label="Editar Elemento", style=ButtonStyle.blurple)
    async def edit_element(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.elements:
            await interaction.response.send_message("Nenhum elemento para editar!", ephemeral=True)
            return
        modal = EditElementModal(self.cog, self.elements)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label="Remover Elemento", style=ButtonStyle.red)
    async def remove_element(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.elements:
            await interaction.response.send_message("Nenhum elemento para remover!", ephemeral=True)
            return
        modal = RemoveElementModal(self.elements)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label="Visualizar", style=ButtonStyle.gray)
    async def preview(self, button: nextcord.ui.Button, interaction: Interaction):
        try:
            preview_image = await self.cog.generate_preview(interaction.guild, self.elements)
            file = nextcord.File(preview_image, filename="preview.png")
            await interaction.response.send_message("Prévia da imagem de boas-vindas:", file=file, ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao gerar prévia: {e}")
            await interaction.response.send_message("Erro ao gerar prévia. Verifique as configurações.", ephemeral=True)

    @nextcord.ui.button(label="Salvar", style=ButtonStyle.primary)
    async def save(self, button: nextcord.ui.Button, interaction: Interaction):
        try:
            self.cog.save_template(str(interaction.guild.id), self.elements)
            await interaction.response.send_message("Template salvo com sucesso!", ephemeral=True)
            self.stop()
        except Exception as e:
            logger.error(f"Erro ao salvar template: {e}")
            await interaction.response.send_message("Erro ao salvar template.", ephemeral=True)

class AddElementModal(nextcord.ui.Modal):
    """Modal para adicionar um novo elemento."""
    def __init__(self, cog, elements: List[Element]):
        super().__init__("Adicionar Elemento", timeout=300)
        self.cog = cog
        self.elements = elements

        self.element_type = nextcord.ui.TextInput(
            label="Tipo de Elemento",
            placeholder="avatar, text, shape, background",
            required=True
        )
        self.add_item(self.element_type)

        self.params = nextcord.ui.TextInput(
            label="Parâmetros (JSON)",
            style=TextInputStyle.paragraph,
            placeholder='Ex.: {"x": 100, "y": 100, "size": 120} para avatar',
            required=True
        )
        self.add_item(self.params)

    async def callback(self, interaction: Interaction):
        try:
            element_type = self.element_type.value.lower()
            params = json.loads(self.params.value)
            element = None

            if element_type == "avatar":
                element = AvatarElement(
                    x=params.get("x", 0),
                    y=params.get("y", 0),
                    size=params.get("size", 120),
                    outline=params.get("outline", True),
                    outline_color=params.get("outline_color", [255, 255, 255]),
                    opacity=params.get("opacity", 1.0)
                )
            elif element_type == "text":
                element = TextElement(
                    x=params.get("x", 0),
                    y=params.get("y", 0),
                    text=params.get("text", "Texto"),
                    font_size=params.get("font_size", 50),
                    color=params.get("color", [255, 255, 255]),
                    font_path=params.get("font_path", ""),
                    opacity=params.get("opacity", 1.0)
                )
            elif element_type == "shape":
                element = ShapeElement(
                    x=params.get("x", 0),
                    y=params.get("y", 0),
                    shape_type=params.get("shape_type", "rectangle"),
                    width=params.get("width", 100),
                    height=params.get("height", 100),
                    color=params.get("color", [255, 255, 255]),
                    opacity=params.get("opacity", 1.0)
                )
            elif element_type == "background":
                element = BackgroundElement(
                    source=params.get("source", ""),
                    color=params.get("color", [50, 50, 50]),
                    opacity=params.get("opacity", 1.0)
                )
            else:
                await interaction.response.send_message("Tipo de elemento inválido!", ephemeral=True)
                return

            self.elements.append(element)
            await interaction.response.send_message(f"Elemento {element_type} adicionado!", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao adicionar elemento: {e}")
            await interaction.response.send_message("Erro ao adicionar elemento. Verifique o JSON.", ephemeral=True)

class EditElementModal(nextcord.ui.Modal):
    """Modal para editar um elemento existente."""
    def __init__(self, cog, elements: List[Element]):
        super().__init__("Editar Elemento", timeout=300)
        self.cog = cog
        self.elements = elements

        self.index = nextcord.ui.TextInput(
            label="Índice do Elemento",
            placeholder="0, 1, 2, ...",
            required=True
        )
        self.add_item(self.index)

        self.params = nextcord.ui.TextInput(
            label="Novos Parâmetros (JSON)",
            style=TextInputStyle.paragraph,
            placeholder='Ex.: {"x": 150, "y": 150, "size": 100} para avatar',
            required=True
        )
        self.add_item(self.params)

    async def callback(self, interaction: Interaction):
        try:
            index = int(self.index.value)
            if index < 0 or index >= len(self.elements):
                await interaction.response.send_message("Índice inválido!", ephemeral=True)
                return
            params = json.loads(self.params.value)
            element = self.elements[index]

            if element.type == "avatar":
                element.x = params.get("x", element.x)
                element.y = params.get("y", element.y)
                element.size = params.get("size", element.size)
                element.outline = params.get("outline", element.outline)
                element.outline_color = params.get("outline_color", element.outline_color)
                element.opacity = params.get("opacity", element.opacity)
            elif element.type == "text":
                element.x = params.get("x", element.x)
                element.y = params.get("y", element.y)
                element.text = params.get("text", element.text)
                element.font_size = params.get("font_size", element.font_size)
                element.color = params.get("color", element.color)
                element.font_path = params.get("font_path", element.font_path)
                element.opacity = params.get("opacity", element.opacity)
            elif element.type == "shape":
                element.x = params.get("x", element.x)
                element.y = params.get("y", element.y)
                element.shape_type = params.get("shape_type", element.shape_type)
                element.width = params.get("width", element.width)
                element.height = params.get("height", element.height)
                element.color = params.get("color", element.color)
                element.opacity = params.get("opacity", element.opacity)
            elif element.type == "background":
                element.source = params.get("source", element.source)
                element.color = params.get("color", element.color)
                element.opacity = params.get("opacity", element.opacity)

            await interaction.response.send_message(f"Elemento {index} editado!", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao editar elemento: {e}")
            await interaction.response.send_message("Erro ao editar elemento. Verifique o JSON ou índice.", ephemeral=True)

class RemoveElementModal(nextcord.ui.Modal):
    """Modal para remover um elemento."""
    def __init__(self, elements: List[Element]):
        super().__init__("Remover Elemento", timeout=300)
        self.elements = elements

        self.index = nextcord.ui.TextInput(
            label="Índice do Elemento",
            placeholder="0, 1, 2, ...",
            required=True
        )
        self.add_item(self.index)

    async def callback(self, interaction: Interaction):
        try:
            index = int(self.index.value)
            if index < 0 or index >= len(self.elements):
                await interaction.response.send_message("Índice inválido!", ephemeral=True)
                return
            removed = self.elements.pop(index)
            await interaction.response.send_message(f"Elemento {removed.type} removido!", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao remover elemento: {e}")
            await interaction.response.send_message("Erro ao remover elemento. Verifique o índice.", ephemeral=True)

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data"
        self.font_dir = "fonts"
        self.assets_dir = "assets"
        self.background_cache = {}  # Cache em memória
        self.session = None
        self.ensure_directories()

    def ensure_directories(self):
        """Cria diretórios necessários."""
        os.makedirs(self.font_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)
        font_path = os.path.join(self.font_dir, "Montserrat-ExtraBold.otf")
        if not os.path.exists(font_path):
            logger.warning("Fonte Montserrat-ExtraBold.otf não encontrada. Usando padrão.")

    def ensure_guild_directory(self, guild_id: str):
        """Garante que a pasta do servidor exista."""
        guild_dir = os.path.join(self.data_dir, guild_id)
        backgrounds_dir = os.path.join(guild_dir, "backgrounds")
        os.makedirs(backgrounds_dir, exist_ok=True)
        return backgrounds_dir

    def load_config(self, guild_id: str) -> dict:
        """Carrega a configuração de boas-vindas do servidor."""
        self.ensure_guild_directory(guild_id)
        config_file = os.path.join(self.data_dir, guild_id, "welcome_config.json")
        default_config = {
            "role_id": None,
            "channel_id": None,
            "background_url": "",  # Vazio indica fundo padrão
            "welcome_text": "Bem-vindo {member} #{count}!",
            "text_color": [255, 255, 255],
            "font_size": 50
        }
        try:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return {**default_config, **config}
            return default_config
        except Exception as e:
            logger.error(f"Erro ao carregar config de {guild_id}: {e}")
            return default_config

    def save_config(self, guild_id: str, config: dict):
        """Salva a configuração de boas-vindas do servidor."""
        self.ensure_guild_directory(guild_id)
        config_file = os.path.join(self.data_dir, guild_id, "welcome_config.json")
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Configuração salva para servidor {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar config de {guild_id}: {e}")

    def load_template(self, guild_id: str) -> List[Element]:
        """Carrega o template de boas-vindas do servidor."""
        template_file = os.path.join(self.data_dir, guild_id, "welcome_template.json")
        try:
            if os.path.exists(template_file):
                with open(template_file, "r", encoding="utf-8") as f:
                    elements_data = json.load(f)
                elements = []
                for data in elements_data:
                    if data["type"] == "avatar":
                        elements.append(AvatarElement(
                            x=data["x"], y=data["y"], size=data["size"],
                            outline=data["outline"], outline_color=data["outline_color"],
                            opacity=data["opacity"]
                        ))
                    elif data["type"] == "text":
                        elements.append(TextElement(
                            x=data["x"], y=data["y"], text=data["text"],
                            font_size=data["font_size"], color=data["color"],
                            font_path=data["font_path"], opacity=data["opacity"]
                        ))
                    elif data["type"] == "shape":
                        elements.append(ShapeElement(
                            x=data["x"], y=data["y"], shape_type=data["shape_type"],
                            width=data["width"], height=data["height"],
                            color=data["color"], opacity=data["opacity"]
                        ))
                    elif data["type"] == "background":
                        elements.append(BackgroundElement(
                            source=data["source"], color=data["color"],
                            opacity=data["opacity"]
                        ))
                return elements
            return [BackgroundElement(source=""), AvatarElement(240, 20, 120), TextElement(30, 150, "Bem-vindo {member} #{count}!", 50, [255, 255, 255])]
        except Exception as e:
            logger.error(f"Erro ao carregar template de {guild_id}: {e}")
            return [BackgroundElement(source=""), AvatarElement(240, 20, 120), TextElement(30, 150, "Bem-vindo {member} #{count}!", 50, [255, 255, 255])]

    def save_template(self, guild_id: str, elements: List[Element]):
        """Salva o template de boas-vindas do servidor."""
        self.ensure_guild_directory(guild_id)
        template_file = os.path.join(self.data_dir, guild_id, "welcome_template.json")
        try:
            elements_data = [element.to_dict() for element in elements]
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(elements_data, f, indent=4)
            logger.info(f"Template salvo para servidor {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar template de {guild_id}: {e}")
            raise

    async def resolve_imgur_url(self, url: str) -> str:
        """Resolve URLs do Imgur para a imagem direta."""
        if not url.startswith("https://imgur.com"):
            return url
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(headers={"User-Agent": "DataBitBot/2.9"})
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"Erro ao acessar {url}: {resp.status}")
                    return url
                html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            img_tag = soup.find("meta", property="og:image")
            if img_tag and img_tag.get("content"):
                direct_url = img_tag["content"]
                logger.debug(f"URL do Imgur resolvida: {url} -> {direct_url}")
                return direct_url
            logger.warning(f"Não foi possível resolver URL do Imgur: {url}")
            return url
        except Exception as e:
            logger.error(f"Erro ao resolver URL do Imgur {url}: {e}")
            return url

    async def download_image(self, url: str, max_retries: int = 3) -> bytes:
        """Baixa uma imagem com retries para erro 429."""
        if not self.session:
            self.session = aiohttp.ClientSession(headers={"User-Agent": "DataBitBot/2.9"})
        for attempt in range(max_retries):
            try:
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "")
                        if not content_type.startswith("image/"):
                            raise ValueError(f"URL {url} não é uma imagem")
                        data = await resp.read()
                        logger.debug(f"Imagem baixada: {url}")
                        return data
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 5))
                        logger.warning(f"Erro 429 ao baixar {url}. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_after}s")
                        await asyncio.sleep(retry_after)
                    else:
                        raise Exception(f"Erro ao baixar: {resp.status}")
            except Exception as e:
                logger.error(f"Erro na tentativa {attempt+1}/{max_retries} para {url}: {e}")
                if attempt == max_retries - 1:
                    raise
        raise Exception("Número máximo de tentativas excedido")

    def wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> list:
        """Quebra o texto em linhas com base na largura máxima."""
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        max_lines = 3

        for word in words:
            word_bbox = font.getbbox(word)
            word_width = word_bbox[2] - word_bbox[0]
            space_width = font.getbbox(" ")[2] - font.getbbox(" ")[0]

            if current_width + word_width + (space_width if current_line else 0) <= max_width:
                current_line.append(word)
                current_width += word_width + (space_width if current_line else 0)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_width = word_width
                else:
                    lines.append(word)
                    current_width = 0
                    current_line = []

            if len(lines) >= max_lines:
                break

        if current_line and len(lines) < max_lines:
            lines.append(" ".join(current_line))

        return lines[:max_lines]

    async def get_background(self, guild_id: str, background_url: str, color: List[int]) -> Image.Image:
        """Obtém a imagem de fundo do cache, disco ou URL."""
        img_width, img_height = 600, 225
        backgrounds_dir = self.ensure_guild_directory(guild_id)

        # Fallback para fundo padrão
        if not background_url:
            default_path = os.path.join(self.assets_dir, "default_background.png")
            if not os.path.exists(default_path):
                img = Image.new("RGBA", (img_width, img_height), tuple(color + [255]))
                img.save(default_path, "PNG")
            return Image.open(default_path).convert("RGBA").resize((img_width, img_height), Image.Resampling.LANCZOS)

        # Verifica fundo local
        if background_url.startswith("local://"):
            file_name = background_url.replace("local://", "")
            local_path = os.path.join(backgrounds_dir, file_name)
            if os.path.exists(local_path):
                try:
                    img = Image.open(local_path).convert("RGBA")
                    img = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
                    self.background_cache[background_url] = img
                    logger.debug(f"Imagem de fundo local carregada: {local_path}")
                    return img.copy()
                except Exception as e:
                    logger.error(f"Erro ao carregar fundo local {local_path}: {e}")
            logger.warning(f"Fundo local {local_path} não encontrado. Usando padrão.")
            return await self.get_background(guild_id, "", color)

        # Resolve URL do Imgur
        resolved_url = await self.resolve_imgur_url(background_url)
        
        # Gera hash da URL para nome do arquivo
        url_hash = hashlib.md5(resolved_url.encode()).hexdigest()
        local_path = os.path.join(backgrounds_dir, f"{url_hash}.png")

        # Carrega do cache em memória
        if resolved_url in self.background_cache:
            return self.background_cache[resolved_url].copy()

        # Carrega do disco
        if os.path.exists(local_path):
            try:
                img = Image.open(local_path).convert("RGBA")
                img = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
                self.background_cache[resolved_url] = img
                logger.debug(f"Imagem de fundo carregada do disco: {local_path}")
                return img.copy()
            except Exception as e:
                logger.error(f"Erro ao carregar fundo do disco {local_path}: {e}")

        # Baixa da URL
        try:
            data = await self.download_image(resolved_url)
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
            img.save(local_path, "PNG")
            self.background_cache[resolved_url] = img
            logger.info(f"Imagem de fundo baixada e salva: {resolved_url} -> {local_path}")
            return img.copy()
        except Exception as e:
            logger.error(f"Erro ao baixar fundo {resolved_url}: {e}")
            return await self.get_background(guild_id, "", color)

    async def generate_preview(self, guild, elements: List[Element]) -> io.BytesIO:
        """Gera uma imagem de prévia com base nos elementos."""
        img_width, img_height = 600, 225
        background_element = next((e for e in elements if e.type == "background"), None)
        if not background_element:
            background_element = BackgroundElement(source="", color=[50, 50, 50])

        background = await self.get_background(
            str(guild.id), background_element.source, background_element.color
        )
        draw = ImageDraw.Draw(background)

        # Mock member para prévia
        class MockMember:
            def __init__(self):
                self.name = "TestUser"
                self.id = 123456789
                self.guild = guild
                self.avatar = None
                self.default_avatar = type("obj", (), {"url": "https://cdn.discordapp.com/embed/avatars/0.png"})()

        mock_member = MockMember()
        guild.member_count = guild.member_count or 100

        # Baixa avatar de teste
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(headers={"User-Agent": "DataBitBot/2.9"})
            avatar_url = mock_member.default_avatar.url
            async with self.session.get(avatar_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Erro ao baixar avatar: {resp.status}")
                avatar_data = await resp.read()
            avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
        except Exception as e:
            logger.error(f"Erro ao processar avatar de prévia: {e}")
            avatar = Image.new("RGBA", (120, 120), (255, 255, 255, 255))

        for element in elements:
            if element.type == "avatar":
                avatar = avatar.resize((element.size, element.size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (element.size, element.size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, element.size, element.size), fill=255)
                avatar.putalpha(mask)
                if element.outline:
                    draw.ellipse(
                        [element.x - 4, element.y - 4, element.x + element.size + 4, element.y + element.size + 4],
                        outline=tuple(element.outline_color + [255]),
                        width=4
                    )
                background.paste(avatar, (element.x, element.y), avatar)
            elif element.type == "text":
                try:
                    font_path = element.font_path or os.path.join(self.font_dir, "Montserrat-ExtraBold.otf")
                    font = ImageFont.truetype(font_path, element.font_size) if os.path.exists(font_path) else ImageFont.load_default()
                except Exception as e:
                    logger.warning(f"Fonte {element.font_path} não encontrada: {e}. Usando padrão.")
                    font = ImageFont.load_default()
                text = element.text.format(member=mock_member.name, guild=guild.name, count=guild.member_count)
                lines = self.wrap_text(text, font, 540)
                line_height = font.getbbox("A")[3] - font.getbbox("A")[1]
                line_spacing = max(5, int(element.font_size * 0.2))
                for i, line in enumerate(lines):
                    text_bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    draw.text(
                        (element.x, element.y + i * (line_height + line_spacing)),
                        line,
                        font=font,
                        fill=tuple(element.color + [int(255 * element.opacity)])
                    )
            elif element.type == "shape":
                color = element.color + [int(255 * element.opacity)]
                if element.shape_type == "rectangle":
                    draw.rectangle(
                        [element.x, element.y, element.x + element.width, element.y + element.height],
                        fill=tuple(color)
                    )
                elif element.shape_type == "circle":
                    draw.ellipse(
                        [element.x, element.y, element.x + element.width, element.y + element.height],
                        fill=tuple(color)
                    )

        buffer = io.BytesIO()
        try:
            background.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
        finally:
            background.close()
            avatar.close()

    async def create_welcome_image(self, member):
        """Cria a imagem de boas-vindas para o membro."""
        guild_id = str(member.guild.id)
        config = self.load_config(guild_id)
        elements = self.load_template(guild_id)
        img_width, img_height = 600, 225

        # Obtém fundo
        background_element = next((e for e in elements if e.type == "background"), None)
        if not background_element:
            background_element = BackgroundElement(source=config.get("background_url", ""))
        background = await self.get_background(
            guild_id, background_element.source, background_element.color
        )
        draw = ImageDraw.Draw(background)

        # Baixa o avatar do membro
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(headers={"User-Agent": "DataBitBot/2.9"})
            avatar_url = str(member.avatar.url if member.avatar else member.default_avatar.url)
            async with self.session.get(avatar_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Erro ao baixar avatar: {resp.status}")
                avatar_data = await resp.read()
            avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
        except Exception as e:
            logger.error(f"Erro ao processar avatar para {member.id}: {e}")
            raise

        # Renderiza elementos
        for element in elements:
            if element.type == "avatar":
                avatar = avatar.resize((element.size, element.size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (element.size, element.size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, element.size, element.size), fill=255)
                avatar.putalpha(mask)
                if element.outline:
                    draw.ellipse(
                        [element.x - 4, element.y - 4, element.x + element.size + 4, element.y + element.size + 4],
                        outline=tuple(element.outline_color + [255]),
                        width=4
                    )
                background.paste(avatar, (element.x, element.y), avatar)
            elif element.type == "text":
                try:
                    font_path = element.font_path or os.path.join(self.font_dir, "Montserrat-ExtraBold.otf")
                    font = ImageFont.truetype(font_path, element.font_size) if os.path.exists(font_path) else ImageFont.load_default()
                except Exception as e:
                    logger.warning(f"Fonte {element.font_path} não encontrada: {e}. Usando padrão.")
                    font = ImageFont.load_default()
                text = element.text.format(member=member.name, guild=member.guild.name, count=member.guild.member_count)
                lines = self.wrap_text(text, font, 540)
                line_height = font.getbbox("A")[3] - font.getbbox("A")[1]
                line_spacing = max(5, int(element.font_size * 0.2))
                for i, line in enumerate(lines):
                    text_bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    draw.text(
                        (element.x, element.y + i * (line_height + line_spacing)),
                        line,
                        font=font,
                        fill=tuple(element.color + [int(255 * element.opacity)])
                    )
            elif element.type == "shape":
                color = element.color + [int(255 * element.opacity)]
                if element.shape_type == "rectangle":
                    draw.rectangle(
                        [element.x, element.y, element.x + element.width, element.y + element.height],
                        fill=tuple(color)
                    )
                elif element.shape_type == "circle":
                    draw.ellipse(
                        [element.x, element.y, element.x + element.width, element.y + element.height],
                        fill=tuple(color)
                    )

        buffer = io.BytesIO()
        try:
            background.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
        finally:
            background.close()
            avatar.close()
            logger.debug(f"Recursos de imagem liberados para {member.id}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Evento disparado quando um membro entra no servidor."""
        if member.bot:
            return
        guild_id = str(member.guild.id)
        config = self.load_config(guild_id)

        # Atribui o cargo
        role_id = config.get("role_id")
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Cargo de boas-vindas")
                    logger.info(f"Cargo {role_id} atribuído a {member.id} em {guild_id}")
                except Exception as e:
                    logger.error(f"Erro ao atribuir cargo a {member.id} em {guild_id}: {e}")

        # Envia imagem de boas-vindas
        channel_id = config.get("channel_id")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                try:
                    welcome_image = await self.create_welcome_image(member)
                    file = nextcord.File(welcome_image, filename="welcome.png")
                    welcome_message = f"Bem-vindo(a) ao servidor, {member.mention}! 🎉"
                    await channel.send(welcome_message, file=file)
                    logger.info(f"Imagem de boas-vindas enviada para {member.id} em {guild_id}")
                except Exception as e:
                    logger.error(f"Erro ao criar/enviar imagem de boas-vindas para {member.id} em {guild_id}: {e}")
                    try:
                        await channel.send(
                            f"Bem-vindo(a) ao servidor, {member.mention}! 🎉\n"
                            f"(Erro ao gerar imagem de boas-vindas. Verifique a URL ou arquivo do fundo.)"
                        )
                        # Notifica administrador
                        owner = self.bot.get_user(1219787450583486500)
                        if owner:
                            await owner.send(
                                f"Erro ao gerar imagem de boas-vindas no servidor {guild_id}: {e}\n"
                                f"Verifique a URL ou arquivo do fundo em /config_welcome."
                            )
                    except Exception as send_e:
                        logger.error(f"Erro ao enviar mensagem de fallback em {guild_id}: {send_e}")

        # Envia DM
        try:
            dm_message = (
                f"Olá {member.name}, bem-vindo(a) ao **{member.guild.name}**! 🎉\n"
                f"Esperamos que você se divirta e participe ativamente!"
            )
            await member.send(dm_message)
            await asyncio.sleep(1)
            logger.info(f"DM enviada para {member.id} em {guild_id}")
        except nextcord.Forbidden:
            logger.warning(f"DM bloqueada para {member.id} em {guild_id}")
        except nextcord.HTTPException as e:
            if e.status == 429:
                retry_after = e.retry_after or 5
                logger.warning(f"Rate limit em DM para {member.id}. Aguardando {retry_after}s")
                await asyncio.sleep(retry_after)
                await member.send(dm_message)
            else:
                logger.error(f"Erro ao enviar DM para {member.id} em {guild_id}: {e}")

    @nextcord.slash_command(
        name="config_welcome",
        description="Configure o sistema de boas-vindas (apenas administradores)"
    )
    async def config_welcome(
        self,
        interaction: Interaction,
        role: nextcord.Role = SlashOption(description="Cargo para novos membros", required=False),
        channel: nextcord.TextChannel = SlashOption(description="Canal de boas-vindas", required=False),
        background_url: str = SlashOption(description="URL da imagem de fundo (PNG/JPG)", required=False),
        welcome_text: str = SlashOption(description="Texto de boas-vindas ({member}, {guild}, {count})", required=False),
        text_color: str = SlashOption(description="Cor do texto (ex.: 255,255,255)", required=False),
        font_size: int = SlashOption(description="Tamanho da fonte (30-60)", required=False, min_value=30, max_value=60),
        background_file: nextcord.Attachment = SlashOption(description="Upload de imagem de fundo", required=False)
    ):
        """Configura o sistema de boas-vindas com opções personalizáveis."""
        if not interaction.user.guild_permissions.administrator and interaction.user.id != 1219787450583486500:
            await interaction.response.send_message(
                "Você precisa ser administrador ou dono do bot para usar este comando!",
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        config = self.load_config(guild_id)
        backgrounds_dir = self.ensure_guild_directory(guild_id)

        # Processa upload de imagem
        if background_file:
            try:
                if not background_file.content_type.startswith("image/"):
                    await interaction.response.send_message(
                        "O arquivo deve ser uma imagem (PNG/JPG)!",
                        ephemeral=True
                    )
                    return
                file_data = await background_file.read()
                file_hash = hashlib.md5(file_data).hexdigest()
                local_path = os.path.join(backgrounds_dir, f"{file_hash}.png")
                with open(local_path, "wb") as f:
                    f.write(file_data)
                config["background_url"] = f"local://{file_hash}.png"
                logger.info(f"Imagem de fundo carregada para {guild_id}: {local_path}")
            except Exception as e:
                logger.error(f"Erro ao processar upload de fundo para {guild_id}: {e}")
                await interaction.response.send_message(
                    "Erro ao processar a imagem carregada. Tente novamente.",
                    ephemeral=True
                )
                return

        # Atualiza configurações fornecidas
        if role:
            config["role_id"] = role.id
        if channel:
            config["channel_id"] = channel.id
        if background_url:
            resolved_url = await self.resolve_imgur_url(background_url)
            if not resolved_url.lower().endswith(('.png', '.jpg', '.jpeg')):
                await interaction.response.send_message(
                    "A URL do fundo deve ser um arquivo PNG ou JPG!",
                    ephemeral=True
                )
                return
            config["background_url"] = resolved_url
            if resolved_url in self.background_cache:
                self.background_cache[resolved_url].close()
                del self.background_cache[resolved_url]
        if welcome_text:
            config["welcome_text"] = welcome_text
        if text_color:
            try:
                rgb = [int(x) for x in text_color.split(",")]
                if len(rgb) != 3 or not all(0 <= x <= 255 for x in rgb):
                    raise ValueError
                config["text_color"] = rgb
            except ValueError:
                await interaction.response.send_message(
                    "Cor inválida! Use o formato R,G,B (ex.: 255,255,255)",
                    ephemeral=True
                )
                return
        if font_size:
            config["font_size"] = font_size

        self.save_config(guild_id, config)
        response = "Sistema de boas-vindas configurado!\n"
        if role:
            response += f"Cargo: {role.mention}\n"
        if channel:
            response += f"Canal: {channel.mention}\n"
        if background_url:
            response += f"Fundo: {resolved_url}\n"
        if background_file:
            response += f"Fundo: Carregado via upload\n"
        if welcome_text:
            response += f"Texto: {welcome_text}\n"
        if text_color:
            response += f"Cor do texto: {text_color}\n"
        if font_size:
            response += f"Tamanho da fonte: {font_size}px\n"

        await interaction.response.send_message(response, ephemeral=True)
        logger.info(f"Configuração de boas-vindas atualizada por {interaction.user.id} em {guild_id}")

    @nextcord.slash_command(
        name="formater",
        description="Edite a imagem de boas-vindas interativamente (apenas administradores)"
    )
    async def formater(self, interaction: Interaction):
        """Comando para editar a imagem de boas-vindas com interface interativa."""
        if not interaction.user.guild_permissions.administrator and interaction.user.id != 1219787450583486500:
            await interaction.response.send_message(
                "Você precisa ser administrador ou dono do bot para usar este comando!",
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        elements = self.load_template(guild_id)
        view = EditorView(self, interaction, elements)
        embed = nextcord.Embed(
            title="Editor de Imagem de Boas-Vindas",
            description="Use os botões abaixo para editar a imagem de boas-vindas. Visualize e salve quando terminar!",
            color=nextcord.Color.blurple()
        )
        embed.add_field(
            name="Elementos Atuais",
            value="\n".join([f"{i}: {e.type}" for i, e in enumerate(elements)]) or "Nenhum elemento",
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_message()
        logger.info(f"Editor /formater iniciado por {interaction.user.id} em {guild_id}")

def setup(bot):
    bot.add_cog(WelcomeCog(bot))