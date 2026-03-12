from pathlib import Path
from PIL import Image

from app.core.models import ImageDocument


class ImageLoader:
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}

    def is_supported_image(self, path: str | Path) -> bool:
        file_path = Path(path)
        return file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def load(self, path: str | Path) -> ImageDocument:
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f'Файл не найден: {file_path}')

        if not self.is_supported_image(file_path):
            raise ValueError(f'Неподдерживаемый формат файла: {file_path.suffix}')

        image = Image.open(file_path)
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGBA')
        return ImageDocument(original_path=file_path, image=image)
