from pathlib import Path

from app.core.image_loader import ImageLoader


class ImageFileDiscovery:
    def __init__(self, image_loader: ImageLoader) -> None:
        self.image_loader = image_loader

    def from_folder(self, folder_path: str | Path) -> list[Path]:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return []

        files = [p for p in folder.iterdir() if self.image_loader.is_supported_image(p)]
        return sorted(files, key=lambda p: p.name.lower())

    def from_folder_recursive(self, folder_path: str | Path) -> list[Path]:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return []

        files: list[Path] = []
        for path in folder.rglob('*'):
            if not self.image_loader.is_supported_image(path):
                continue

            name = path.stem.lower()
            if name.startswith('миниатюра '):
                continue
            if name.endswith('_наклейка'):
                continue

            files.append(path)

        return sorted(files, key=lambda p: str(p).lower())

    def from_mixed_paths(self, paths: list[str | Path]) -> list[Path]:
        found: list[Path] = []

        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                found.extend(self.from_folder(path))
            elif self.image_loader.is_supported_image(path):
                found.append(path)

        unique = {p.resolve(): p for p in found}
        return sorted(unique.values(), key=lambda p: p.name.lower())
