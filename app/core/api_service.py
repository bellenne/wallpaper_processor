from __future__ import annotations

from io import BytesIO

import requests
from PIL import Image


class ApiService:
    ARTICLE_URL = 'https://customcraft-mes.ru/api/v1/articles'
    STICKER_URL = 'https://system.oboi-3d.ru/api/sticker'

    def __init__(self, timeout: int = 60) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    def update_article(
        self,
        article: str,
        width_cm: int,
        height_cm: int,
        preview_image: Image.Image,
    ) -> None:
        preview_bytes = self._build_preview_jpeg_bytes(
            image=preview_image,
            max_side_px=800,
            quality=55,
        )

        response = self.session.put(
            self.ARTICLE_URL,
            data={
                'article': article,
                'f_width': str(width_cm),
                'f_height': str(height_cm),
            },
            files={
                'image': (f'{article}.jpg', preview_bytes, 'image/jpeg'),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

    def upload_sticker(self, sticker_image: Image.Image, filename: str) -> None:
        sticker_bytes = self._image_to_jpeg_bytes(
            image=sticker_image,
            quality=85,
            dpi=(150, 150),
        )

        response = self.session.put(
            self.STICKER_URL,
            files={
                'image': (f'{filename}_наклейка.jpg', sticker_bytes, 'image/jpeg'),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

    def _build_preview_jpeg_bytes(
        self,
        image: Image.Image,
        max_side_px: int = 800,
        quality: int = 55,
    ) -> bytes:
        preview = self._normalize_image(image)
        preview.thumbnail((max_side_px, max_side_px), Image.Resampling.LANCZOS)
        return self._image_to_jpeg_bytes(
            image=preview,
            quality=quality,
            dpi=(72, 72),
        )

    def _image_to_jpeg_bytes(
        self,
        image: Image.Image,
        quality: int = 80,
        dpi: tuple[int, int] = (72, 72),
    ) -> bytes:
        normalized = self._normalize_image(image)
        buffer = BytesIO()
        normalized.save(
            buffer,
            format='JPEG',
            quality=quality,
            optimize=True,
            dpi=dpi,
        )
        return buffer.getvalue()

    @staticmethod
    def _normalize_image(image: Image.Image) -> Image.Image:
        if image.mode == 'RGBA':
            white_bg = Image.new('RGB', image.size, 'white')
            white_bg.paste(image, mask=image.getchannel('A'))
            return white_bg
        return image.convert('RGB')
