from pathlib import Path

from app.application.result_dto import ProcessingResult
from app.core.exporter import JpegExporter
from app.core.image_loader import ImageLoader
from app.core.markup_service import WallpaperMarkupService
from app.core.thumbnail_service import ThumbnailService
from app.core.sticker_service import StickerService


class WallpaperBatchProcessor:
    def __init__(
        self,
        image_loader: ImageLoader,
        markup_service: WallpaperMarkupService,
        thumbnail_service: ThumbnailService,
        sticker_service: StickerService,
        exporter: JpegExporter,
    ) -> None:
        self.image_loader = image_loader
        self.markup_service = markup_service
        self.thumbnail_service = thumbnail_service
        self.sticker_service = sticker_service
        self.exporter = exporter

    def set_output_dir(self, output_dir: str | Path) -> None:
        self.exporter.set_base_output_dir(output_dir)

    def process_files(self, files: list[Path], rewrite_existing_tech_fields: bool = False) -> list[ProcessingResult]:
        results: list[ProcessingResult] = []

        for file_path in files:
            try:
                document = self.image_loader.load(file_path)
                folder_name = document.sanitized_stem

                if rewrite_existing_tech_fields:
                    rebuilt_markup = self.markup_service.rebuild_existing_tech_field(document)
                    overwritten = self.exporter.overwrite(rebuilt_markup, file_path)
                    results.append(
                        ProcessingResult(
                            source_path=file_path,
                            success=True,
                            output_paths=[overwritten],
                        )
                    )
                    continue

                rendered_markup = self.markup_service.process(document)
                markup_output = self.exporter.export(
                    rendered_markup,
                    folder_name=folder_name,
                    output_filename=f'{folder_name}.jpg',
                )

                thumbnail = self.thumbnail_service.process(document)
                thumbnail_output = self.exporter.export(
                    thumbnail,
                    folder_name=folder_name,
                    output_filename=f'миниатюра {folder_name}.jpg',
                )

                sticker = self.sticker_service.process(document)
                sticker_output = self.exporter.export(
                    sticker,
                    folder_name=folder_name,
                    output_filename=f'{folder_name}_наклейка.jpg',
                )

                results.append(
                    ProcessingResult(
                        source_path=file_path,
                        success=True,
                        output_paths=[markup_output, thumbnail_output, sticker_output],
                    )
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    ProcessingResult(
                        source_path=file_path,
                        success=False,
                        error_message=str(exc),
                    )
                )

        return results
