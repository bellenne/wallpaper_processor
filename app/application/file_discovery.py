from pathlib import Path

from app.core.image_loader import ImageLoader


class ImageFileDiscovery:
    AUXILIARY_PREFIXES = (
        'миниатюра ',
        'qr ',
    )
    AUXILIARY_SUFFIXES = (
        '_наклейка',
    )
    AUXILIARY_SUBSTRINGS = (
        'qr article',
        'миниатюра article',
        'article_наклейка',
    )

    def __init__(self, image_loader: ImageLoader) -> None:
        self.image_loader = image_loader

    def from_folder(self, folder_path: str | Path) -> list[Path]:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return []

        files = [p for p in folder.iterdir() if self.is_processable_image(p)]
        return sorted(files, key=lambda p: p.name.lower())

    def from_folder_recursive(self, folder_path: str | Path) -> list[Path]:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return []

        files = [path for path in folder.rglob('*') if self.is_processable_image(path)]
        return sorted(files, key=lambda p: str(p).lower())

    def from_mixed_paths(self, paths: list[str | Path]) -> list[Path]:
        found: list[Path] = []

        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                found.extend(self.from_folder(path))
            elif self.is_processable_image(path):
                found.append(path)

        unique = {p.resolve(): p for p in found}
        return sorted(unique.values(), key=lambda p: p.name.lower())

    def is_processable_image(self, path: str | Path) -> bool:
        candidate = Path(path)
        if not self.image_loader.is_supported_image(candidate):
            return False

        for stem in self._stem_variants(candidate):
            if stem.startswith(self.AUXILIARY_PREFIXES):
                return False
            if stem.endswith(self.AUXILIARY_SUFFIXES):
                return False
            if any(marker in stem for marker in self.AUXILIARY_SUBSTRINGS):
                return False

        return True

    @staticmethod
    def _stem_variants(path: Path) -> set[str]:
        variants = {path.stem.casefold()}
        try:
            variants.add(path.stem.encode('utf-8').decode('cp1251').casefold())
        except UnicodeError:
            pass
        return variants
