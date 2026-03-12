from dataclasses import dataclass
from pathlib import Path
from PIL import Image


@dataclass
class ImageDocument:
    original_path: Path
    image: Image.Image

    @property
    def width_px(self) -> int:
        return self.image.width

    @property
    def height_px(self) -> int:
        return self.image.height

    @property
    def original_stem(self) -> str:
        return self.original_path.stem

    @property
    def sanitized_stem(self) -> str:
        return self.original_stem.replace('х', 'x').replace('Х', 'X')
