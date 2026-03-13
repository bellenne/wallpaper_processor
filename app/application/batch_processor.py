from pathlib import Path

from app.application.result_dto import ProcessingResult
from app.core.api_service import ApiService
from app.core.exporter import JpegExporter
from app.core.image_loader import ImageLoader
from app.core.markup_service import WallpaperMarkupService
from app.core.sticker_service import StickerService
from app.core.thumbnail_service import ThumbnailService


class WallpaperBatchProcessor:
    def __init__(
        self,
        image_loader: ImageLoader,
        markup_service: WallpaperMarkupService,
        thumbnail_service: ThumbnailService,
        sticker_service: StickerService,
        exporter: JpegExporter,
        api_service: ApiService,
    ) -> None:
        self.image_loader = image_loader
        self.markup_service = markup_service
        self.thumbnail_service = thumbnail_service
        self.sticker_service = sticker_service
        self.exporter = exporter
        self.api_service = api_service

    def set_output_dir(self, output_dir: str | Path) -> None:
        self.exporter.set_base_output_dir(output_dir)

    def process_files(
        self,
        files: list[Path],
        rewrite_existing_tech_fields: bool = False,
    ) -> list[ProcessingResult]:
        results: list[ProcessingResult] = []

        for file_path in files:
            try:
                document = self.image_loader.load(file_path)
                folder_name = document.sanitized_stem

                if rewrite_existing_tech_fields:
                    source_without_footer = self.markup_service.remove_existing_tech_field(document.image)
                    width_cm, height_cm = self._get_image_size_cm(source_without_footer)

                    rebuilt_markup = self.markup_service.process_from_image(source_without_footer, folder_name)
                    sticker_document = document.__class__(path=document.original_path, image=source_without_footer)
                    sticker = self.sticker_service.process(sticker_document)

                    self.api_service.update_article(
                        article=folder_name,
                        width_cm=width_cm,
                        height_cm=height_cm,
                        preview_image=source_without_footer,
                    )
                    self.api_service.upload_sticker(
                        sticker_image=sticker,
                        filename=folder_name,
                    )

                    overwritten = self.exporter.overwrite(rebuilt_markup, file_path)
                    results.append(
                        ProcessingResult(
                            source_path=file_path,
                            success=True,
                            output_paths=[overwritten],
                        )
                    )
                    continue

                source_image = document.image
                width_cm, height_cm = self._get_image_size_cm(source_image)

                rendered_markup = self.markup_service.process(document)
                thumbnail = self.thumbnail_service.process(document)
                sticker = self.sticker_service.process(document)

                self.api_service.update_article(
                    article=folder_name,
                    width_cm=width_cm,
                    height_cm=height_cm,
                    preview_image=source_image,
                )
                self.api_service.upload_sticker(
                    sticker_image=sticker,
                    filename=folder_name,
                )

                markup_output = self.exporter.export(
                    rendered_markup,
                    folder_name=folder_name,
                    output_filename=f'{folder_name}.jpg',
                )
                thumbnail_output = self.exporter.export(
                    thumbnail,
                    folder_name=folder_name,
                    output_filename=f'миниатюра {folder_name}.jpg',
                )
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

    def _get_image_size_cm(self, image) -> tuple[int, int]:
        width_cm = round(self.markup_service.converter.px_to_cm(image.width))
        height_cm = round(self.markup_service.converter.px_to_cm(image.height))
        return width_cm, height_cm
