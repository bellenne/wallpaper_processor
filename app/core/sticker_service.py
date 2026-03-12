from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.core.config import AppConfig
from app.core.models import ImageDocument
from app.core.panel_layout_service import PanelLayoutService
from app.core.units import UnitConverter


class StickerService:
    def __init__(
        self,
        config: AppConfig,
        panel_service: PanelLayoutService,
    ) -> None:
        self.config = config
        self.panel_service = panel_service
        self.sticker_converter = UnitConverter(self.config.sticker_dpi)
        self.source_converter = UnitConverter(self.config.dpi)

    def process(self, document: ImageDocument) -> Image.Image:
        size_px = self.sticker_converter.cm_to_px(self.config.sticker_size_cm)
        canvas = Image.new('RGB', (size_px, size_px), self.config.sticker_background_color)
        draw = ImageDraw.Draw(canvas)

        left_col_width = round(size_px * 0.275)
        top_section_height = round(size_px * 0.62)
        bottom_section_top = top_section_height

        draw.rectangle((0, 0, size_px - 1, size_px - 1), outline=self.config.sticker_border_color, width=1)
        draw.line((left_col_width, bottom_section_top, size_px - 1, bottom_section_top), fill='black', width=1)
        draw.line((left_col_width, 0, left_col_width, size_px - 1), fill='black', width=1)
        draw.rectangle(
            (left_col_width + 1, bottom_section_top + 1, size_px - 2, size_px - 2),
            fill=self.config.sticker_bottom_fill,
            outline=None,
        )

        self._draw_top_preview_block(
            canvas=canvas,
            draw=draw,
            document=document,
            left_col_width=left_col_width,
            top_section_height=top_section_height,
        )
        self._draw_left_info_block(
            canvas=canvas,
            draw=draw,
            document=document,
            left_col_width=left_col_width,
            top_section_height=top_section_height,
        )
        self._draw_logo_block(
            canvas=canvas,
            draw=draw,
            left_col_width=left_col_width,
            top_section_height=top_section_height,
            canvas_size=size_px,
        )
        self._draw_bottom_filename(
            canvas=canvas,
            draw=draw,
            document=document,
            left_col_width=left_col_width,
            top_section_height=top_section_height,
            canvas_size=size_px,
        )

        return canvas

    def _draw_top_preview_block(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        document: ImageDocument,
        left_col_width: int,
        top_section_height: int,
    ) -> None:
        title_font = self._load_font(self.config.sticker_title_font_size_px, bold=True)
        label_font = self._load_font(self.config.sticker_small_font_size_px)
        preview_x = left_col_width + 38
        preview_y = 42
        preview_w = canvas.width - left_col_width - 74
        preview_h = top_section_height - 74

        title = 'РАЗМЕРЫ'
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_x = left_col_width + 38
        title_y = 6
        draw.text((title_x, title_y), title, fill='black', font=title_font)

        preview_image, preview_rect = self._build_preview(document.image, preview_x, preview_y, preview_w, preview_h)
        canvas.paste(preview_image, (preview_rect[0], preview_rect[1]))

        width_cm = round(self.source_converter.px_to_cm(document.width_px))
        height_cm = round(self.source_converter.px_to_cm(document.height_px))
        panels = self.panel_service.build_panels(document.width_px)

        self._draw_preview_panel_lines(draw, preview_rect, panels, document.width_px)
        self._draw_dimension_arrows(draw, preview_rect, width_cm, height_cm, panels, label_font)

    def _draw_preview_panel_lines(
        self,
        draw: ImageDraw.ImageDraw,
        preview_rect: tuple[int, int, int, int],
        panels,
        image_width_px: int,
    ) -> None:
        x1, y1, x2, y2 = preview_rect
        for panel in panels[:-1]:
            rel_x = panel.right_px / image_width_px
            line_x = round(x1 + (x2 - x1) * rel_x)
            self._draw_dashed_line(draw, (line_x, y1, line_x, y2), dash=4, gap=3, fill='#666666')

    def _draw_dimension_arrows(
        self,
        draw: ImageDraw.ImageDraw,
        preview_rect: tuple[int, int, int, int],
        width_cm: int,
        height_cm: int,
        panels,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    ) -> None:
        x1, y1, x2, y2 = preview_rect
        preview_width = x2 - x1

        if panels:
            first_panel_width_px = panels[0].width_px
            total_image_width_px = sum(panel.width_px for panel in panels)
            first_panel_width = round(preview_width * (first_panel_width_px / total_image_width_px))
            top_end = x2 - 4
            top_start = max(x1 + 4, top_end - first_panel_width + 8)
            top_y = max(10, y1 - 12)
            self._draw_arrow_line(draw, (top_start, top_y), (top_end, top_y), fill='black')
            self._draw_centered_text(draw, ((top_start + top_end) // 2, top_y - 9), '100см', font)

        bottom_y = y2 + 10
        self._draw_arrow_line(draw, (x1, bottom_y), (x2, bottom_y), fill='black')
        self._draw_centered_text(draw, ((x1 + x2) // 2, bottom_y - 2), f'{width_cm}см', font, above=False)

        right_x = x2 + 6
        self._draw_arrow_line(draw, (right_x, y1), (right_x, y2), fill='black', vertical=True)
        self._draw_rotated_text(canvas_draw=draw, position=(right_x + 4, (y1 + y2) // 2), text=f'{height_cm}см', font=font)

    def _draw_left_info_block(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        document: ImageDocument,
        left_col_width: int,
        top_section_height: int,
    ) -> None:
        manufacturer_font = self._load_font(self.config.sticker_small_font_size_px)
        filename_font = self._load_font(self.config.sticker_main_font_size_px)

        manufacturer_area = (0, 0, left_col_width, top_section_height)
        manufacturer_text = self.config.sticker_manufacturer_text
        self._draw_rotated_paragraph(
            canvas=canvas,
            area=manufacturer_area,
            text=manufacturer_text,
            font=manufacturer_font,
            fill='black',
            x_offset=16,
            y_offset=12,
        )
        self._draw_rotated_paragraph(
            canvas=canvas,
            area=manufacturer_area,
            text=document.sanitized_stem,
            font=filename_font,
            fill='black',
            x_offset=54,
            y_offset=28,
        )

    def _draw_logo_block(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        left_col_width: int,
        top_section_height: int,
        canvas_size: int,
    ) -> None:
        logo_area = (4, top_section_height + 2, left_col_width - 4, canvas_size - 4)

        logo_path = Path(self.config.sticker_logo_asset_path)
        if logo_path.exists():
            logo = Image.open(logo_path).convert('RGBA')
            inner_w = max(1, logo_area[2] - logo_area[0] - 12)
            inner_h = max(1, logo_area[3] - logo_area[1] - 12)
            fitted = ImageOps.contain(logo, (inner_w, inner_h), Image.Resampling.LANCZOS)
            paste_x = logo_area[0] + (logo_area[2] - logo_area[0] - fitted.width) // 2
            paste_y = logo_area[1] + (logo_area[3] - logo_area[1] - fitted.height) // 2
            canvas.paste(fitted, (paste_x, paste_y), fitted)
            return

        placeholder_font = self._load_font(14, bold=True)
        text = 'LOGO'
        bbox = draw.textbbox((0, 0), text, font=placeholder_font)
        text_x = logo_area[0] + ((logo_area[2] - logo_area[0]) - (bbox[2] - bbox[0])) // 2
        text_y = logo_area[1] + ((logo_area[3] - logo_area[1]) - (bbox[3] - bbox[1])) // 2
        draw.text((text_x, text_y), text, fill='#555555', font=placeholder_font)

    def _draw_bottom_filename(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        document: ImageDocument,
        left_col_width: int,
        top_section_height: int,
        canvas_size: int,
    ) -> None:
        filename = document.sanitized_stem
        box = (left_col_width, top_section_height, canvas_size, canvas_size)
        available_width = max(1, box[2] - box[0] - 28)
        available_height = max(1, box[3] - box[1] - 14)

        font_size = self.config.sticker_main_font_size_px
        while font_size >= 10:
            font = self._load_font(font_size)
            bbox = draw.textbbox((0, 0), filename, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            if text_width <= available_width and text_height <= available_height:
                break
            font_size -= 1
        else:
            font = self._load_font(10)
            bbox = draw.textbbox((0, 0), filename, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

        text_x = box[0] + 14
        text_y = box[1] + ((box[3] - box[1]) - text_height) // 2 - bbox[1]
        draw.text((text_x, text_y), filename, fill='black', font=font)

    @staticmethod
    def _build_preview(
        image: Image.Image,
        box_x: int,
        box_y: int,
        box_width: int,
        box_height: int,
    ) -> tuple[Image.Image, tuple[int, int, int, int]]:
        base = image.convert('RGB')
        fitted = ImageOps.contain(base, (box_width, box_height), Image.Resampling.LANCZOS)
        paste_x = box_x + (box_width - fitted.width) // 2
        paste_y = box_y + (box_height - fitted.height) // 2
        preview_rect = (paste_x, paste_y, paste_x + fitted.width, paste_y + fitted.height)
        return fitted, preview_rect

    @staticmethod
    def _draw_dashed_line(
        draw: ImageDraw.ImageDraw,
        line: tuple[int, int, int, int],
        dash: int,
        gap: int,
        fill: str,
    ) -> None:
        x1, y1, x2, y2 = line
        if x1 == x2:
            y = y1
            while y < y2:
                draw.line((x1, y, x2, min(y + dash, y2)), fill=fill, width=1)
                y += dash + gap
        elif y1 == y2:
            x = x1
            while x < x2:
                draw.line((x, y1, min(x + dash, x2), y2), fill=fill, width=1)
                x += dash + gap

    @staticmethod
    def _draw_arrow_line(
        draw: ImageDraw.ImageDraw,
        start: tuple[int, int],
        end: tuple[int, int],
        fill: str,
        vertical: bool = False,
    ) -> None:
        draw.line((*start, *end), fill=fill, width=1)
        if vertical:
            x, y1 = start
            _, y2 = end
            draw.polygon([(x, y1), (x - 3, y1 + 6), (x + 3, y1 + 6)], fill=fill)
            draw.polygon([(x, y2), (x - 3, y2 - 6), (x + 3, y2 - 6)], fill=fill)
        else:
            x1, y = start
            x2, _ = end
            draw.polygon([(x1, y), (x1 + 6, y - 3), (x1 + 6, y + 3)], fill=fill)
            draw.polygon([(x2, y), (x2 - 6, y - 3), (x2 - 6, y + 3)], fill=fill)

    @staticmethod
    def _draw_centered_text(
        draw: ImageDraw.ImageDraw,
        center: tuple[int, int],
        text: str,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
        above: bool = True,
    ) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = center[0] - w // 2
        y = center[1] - h if above else center[1]
        draw.text((x, y), text, fill='black', font=font)

    @staticmethod
    def _draw_rotated_text(
        canvas_draw: ImageDraw.ImageDraw,
        position: tuple[int, int],
        text: str,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    ) -> None:
        bbox = canvas_draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        temp = Image.new('RGBA', (w + 8, h + 8), (255, 255, 255, 0))
        temp_draw = ImageDraw.Draw(temp)
        temp_draw.text((2, 2), text, fill='black', font=font)
        rotated = temp.rotate(90, expand=True)
        canvas = canvas_draw._image
        canvas.paste(rotated, (position[0] - rotated.width // 2, position[1] - rotated.height // 2), rotated)

    def _draw_rotated_paragraph(
        self,
        canvas: Image.Image,
        area: tuple[int, int, int, int],
        text: str,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
        fill: str,
        x_offset: int,
        y_offset: int,
    ) -> None:
        lines = text.splitlines() if '\n' in text else [text]
        line_spacing = 4
        temp_width = 0
        temp_height = 0
        line_sizes = []
        for line in lines:
            bbox = font.getbbox(line)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            line_sizes.append((line, width, height, bbox))
            temp_width = max(temp_width, width)
            temp_height += height + line_spacing
        temp_height = max(1, temp_height - line_spacing + 6)
        temp_width = max(1, temp_width + 6)

        temp = Image.new('RGBA', (temp_width, temp_height), (255, 255, 255, 0))
        temp_draw = ImageDraw.Draw(temp)
        current_y = 3
        for line, _, _, bbox in line_sizes:
            temp_draw.text((3, current_y - bbox[1]), line, font=font, fill=fill)
            current_y += (bbox[3] - bbox[1]) + line_spacing

        rotated = temp.rotate(90, expand=True)
        paste_x = area[0] + x_offset
        paste_y = area[1] + y_offset
        canvas.paste(rotated, (paste_x, paste_y), rotated)

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
        candidates = [
            'C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',
            'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
        ]

        for font_path in candidates:
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue

        return ImageFont.load_default()
