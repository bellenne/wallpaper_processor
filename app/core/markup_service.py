from PIL import Image, ImageDraw, ImageFont

from app.core.config import AppConfig
from app.core.models import ImageDocument
from app.core.panel_layout_service import PanelInfo, PanelLayoutService
from app.core.qr_service import QrCodeService
from app.core.units import UnitConverter


class WallpaperMarkupService:
    def __init__(
        self,
        config: AppConfig,
        converter: UnitConverter,
        panel_service: PanelLayoutService,
        qr_service: QrCodeService,
    ) -> None:
        self.config = config
        self.converter = converter
        self.panel_service = panel_service
        self.qr_service = qr_service

    def process(self, document: ImageDocument) -> Image.Image:
        return self.process_from_image(document.image, document.sanitized_stem)

    def detect_existing_tech_field_cut_cm(self, image) -> int:
        """
        Определяет, сколько сантиметров нужно срезать снизу
        по последней цифре физической высоты изображения.
        """
        height_cm = round(self.converter.px_to_cm(image.height))
        last_digit = height_cm % 10

        if last_digit in (0, 3, 6, 9):
            return last_digit

        return 0

    def rebuild_existing_tech_field(self, document: ImageDocument) -> Image.Image:
        source_without_footer = self.remove_existing_tech_field(document.image)
        return self.process_from_image(source_without_footer, document.sanitized_stem)

    def remove_existing_tech_field(self, image):
        cut_cm = self.detect_existing_tech_field_cut_cm(image)
        cut_px = self.converter.cm_to_px(cut_cm)

        if cut_px <= 0:
            return image.copy()

        if image.height <= cut_px:
            raise ValueError("Нельзя обрезать тех.поля: высота изображения слишком мала")

        return image.crop((0, 0, image.width, image.height - cut_px))

    def process_from_image(self, image: Image.Image, filename: str) -> Image.Image:
        source = self._normalize_source(image)
        tech_field_height_px = self.converter.cm_to_px(self.config.tech_field_height_cm)

        result = Image.new(
            'RGB',
            (source.width, source.height + tech_field_height_px),
            color=self.config.background_color,
        )
        result.paste(source, (0, 0))

        draw = ImageDraw.Draw(result)
        font = self._load_font()
        panels = self.panel_service.build_panels(source.width)
        total_panels = len(panels)

        width_cm = round(self.converter.px_to_cm(source.width))
        height_cm = round(self.converter.px_to_cm(source.height))

        for panel in panels:
            self._draw_panel_footer(
                canvas=result,
                draw=draw,
                font=font,
                filename=filename,
                panel=panel,
                total_panels=total_panels,
                image_width_cm=width_cm,
                image_height_cm=height_cm,
                original_height_px=source.height,
                tech_field_height_px=tech_field_height_px,
            )

        return result

    def _draw_panel_footer(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
        filename: str,
        panel: PanelInfo,
        total_panels: int,
        image_width_cm: int,
        image_height_cm: int,
        original_height_px: int,
        tech_field_height_px: int,
    ) -> None:
        footer_top = original_height_px
        footer_bottom = original_height_px + tech_field_height_px
        text_x = panel.left_px + self.converter.cm_to_px(self.config.text_left_margin_cm)

        text = (
            f'Размеры: {image_width_cm}x{image_height_cm} см \\ '
            f'Артикул товара: {filename} \\ '
            f'Количество полотен: {total_panels} \\ '
            f'Полотно № {panel.number}'
        )

        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_height = text_bbox[3] - text_bbox[1]
        text_y = footer_top + max(0, (tech_field_height_px - text_height) // 2)

        draw.text((text_x, text_y), text, fill=self.config.text_color, font=font)

        self._place_qr(
            canvas=canvas,
            filename=filename,
            panel=panel,
            footer_top=footer_top,
            footer_bottom=footer_bottom,
        )

    def _place_qr(
        self,
        canvas: Image.Image,
        filename: str,
        panel: PanelInfo,
        footer_top: int,
        footer_bottom: int,
    ) -> None:
        qr_top_margin_px = self.converter.mm_to_px(self.config.qr_top_margin_mm)
        qr_bottom_margin_px = self.converter.mm_to_px(self.config.qr_bottom_margin_mm)
        qr_right_margin_px = self.converter.mm_to_px(self.config.qr_right_margin_mm)

        qr_size_px = max(16, (footer_bottom - footer_top) - qr_top_margin_px - qr_bottom_margin_px)
        qr_payload = f'{filename}|{panel.number}'
        qr_img = self.qr_service.build_qr(qr_payload, qr_size_px)

        qr_x = panel.right_px - qr_right_margin_px - qr_size_px
        qr_y = footer_top + qr_top_margin_px
        if qr_x < panel.left_px:
            qr_x = panel.left_px

        canvas.paste(qr_img, (qr_x, qr_y))

    @staticmethod
    def _normalize_source(image: Image.Image) -> Image.Image:
        if image.mode == 'RGBA':
            white_bg = Image.new('RGB', image.size, 'white')
            white_bg.paste(image, mask=image.getchannel('A'))
            return white_bg
        return image.convert('RGB')

    def _load_font(self) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
        candidates = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/segoeui.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/Supplemental/Arial.ttf',
        ]

        for font_path in candidates:
            try:
                return ImageFont.truetype(font_path, self.config.font_size_px)
            except OSError:
                continue

        return ImageFont.load_default()
