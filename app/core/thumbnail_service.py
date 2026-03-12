from PIL import Image, ImageDraw, ImageFont

from app.core.config import AppConfig
from app.core.models import ImageDocument
from app.core.qr_service import QrCodeService
from app.core.units import UnitConverter


class ThumbnailService:
    def __init__(
        self,
        config: AppConfig,
        qr_service: QrCodeService,
    ) -> None:
        self.config = config
        self.qr_service = qr_service
        self.converter = UnitConverter(self.config.thumbnail_dpi)

    def process(self, document: ImageDocument) -> Image.Image:
        source = self._normalize_source(document.image)
        resized = self._resize_to_max_side(source)
        canvas = resized.convert('RGBA')

        self._place_qr(canvas, document)
        self._draw_caption(canvas, document)

        return canvas.convert('RGB')

    def _resize_to_max_side(self, image: Image.Image) -> Image.Image:
        max_side_px = self.converter.cm_to_px(self.config.thumbnail_max_side_cm)
        width, height = image.size
        longest = max(width, height)

        if longest == max_side_px:
            return image.copy()

        scale = max_side_px / longest
        new_width = max(1, round(width * scale))
        new_height = max(1, round(height * scale))
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _place_qr(self, canvas: Image.Image, document: ImageDocument) -> None:
        margin_px = self.converter.mm_to_px(self.config.thumbnail_qr_margin_mm)
        qr_size_px = self.converter.cm_to_px(self.config.thumbnail_qr_size_cm)
        qr_payload = document.sanitized_stem
        qr_img = self.qr_service.build_qr(qr_payload, qr_size_px).convert('RGBA')
        canvas.alpha_composite(qr_img, (margin_px, margin_px))

    def _draw_caption(self, canvas: Image.Image, document: ImageDocument) -> None:
        draw = ImageDraw.Draw(canvas)
        font = self._load_font()
        text = document.sanitized_stem

        margin_px = self.converter.mm_to_px(self.config.thumbnail_caption_margin_mm)
        padding_px = self.converter.mm_to_px(self.config.thumbnail_caption_padding_mm)
        overlay_height_px = self.converter.cm_to_px(self.config.thumbnail_caption_height_cm)

        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        overlay_width_px = min(canvas.width, text_width + padding_px * 2)
        overlay_x = max(0, (canvas.width - overlay_width_px) // 2)
        overlay_y = max(0, canvas.height - margin_px - overlay_height_px)

        overlay = Image.new('RGBA', (overlay_width_px, overlay_height_px), (0, 0, 0, self.config.thumbnail_overlay_alpha))
        canvas.alpha_composite(overlay, (overlay_x, overlay_y))

        text_x = overlay_x + max(0, (overlay_width_px - text_width) // 2)
        text_y = overlay_y + max(0, (overlay_height_px - text_height) // 2) - text_bbox[1]
        draw.text((text_x, text_y), text, fill='white', font=font)

    @staticmethod
    def _normalize_source(image: Image.Image) -> Image.Image:
        if image.mode == 'RGBA':
            white_bg = Image.new('RGB', image.size, 'white')
            white_bg.paste(image, mask=image.getchannel('A'))
            return white_bg
        return image.convert('RGB')

    def _load_font(self) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
        candidates = [
            'C:/Windows/Fonts/segoeui.ttf',
            'C:/Windows/Fonts/arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/Supplemental/Arial.ttf',
        ]

        for font_path in candidates:
            try:
                return ImageFont.truetype(font_path, self.config.thumbnail_font_size_px)
            except OSError:
                continue

        return ImageFont.load_default()
