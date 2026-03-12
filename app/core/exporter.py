from pathlib import Path
from PIL import Image

from app.core.config import AppConfig


class JpegExporter:
    def __init__(self, config: AppConfig, base_output_dir: str | Path = 'output') -> None:
        self.config = config
        self.base_output_dir = Path(base_output_dir)

    def set_base_output_dir(self, path: str | Path) -> None:
        self.base_output_dir = Path(path)

    def export(self, image: Image.Image, folder_name: str, output_filename: str) -> Path:
        target_folder = self.base_output_dir / folder_name
        target_folder.mkdir(parents=True, exist_ok=True)

        target_path = target_folder / output_filename
        image.convert('RGB').save(target_path, format='JPEG', quality=self.config.jpeg_quality)
        return target_path

    def overwrite(self, image: Image.Image, target_path: str | Path) -> Path:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.convert('RGB').save(target, format='JPEG', quality=self.config.jpeg_quality)
        return target
