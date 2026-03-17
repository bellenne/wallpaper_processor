from pathlib import Path

import requests

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
            operation_logs: list[str] = []
            try:
                document = self.image_loader.load(file_path)
                folder_name = document.sanitized_stem

                if rewrite_existing_tech_fields:
                    source_without_footer = self.markup_service.remove_existing_tech_field(document.image)
                    width_cm, height_cm = self._get_image_size_cm(source_without_footer)

                    rebuilt_markup = self.markup_service.process_from_image(source_without_footer, folder_name)
                    sticker_document = document.__class__(path=document.original_path, image=source_without_footer)
                    sticker = self.sticker_service.process(sticker_document)

                    operation_logs.append(f'API article: start ({folder_name})')
                    article_response = self.api_service.update_article(
                        article=folder_name,
                        width_cm=width_cm,
                        height_cm=height_cm,
                        preview_image=source_without_footer,
                    )
                    operation_logs.append(
                        f'API article: OK {article_response.status_code} {self.api_service.ARTICLE_URL}'
                    )
                    operation_logs.append(
                        f'API article: body {self._format_response_body(article_response)}'
                    )
                    operation_logs.append(f'API sticker: start ({folder_name})')
                    sticker_response = self.api_service.upload_sticker(
                        sticker_image=sticker,
                        filename=folder_name,
                    )
                    operation_logs.append(
                        f'API sticker: OK {sticker_response.status_code} {self.api_service.STICKER_URL}'
                    )
                    operation_logs.append(
                        f'API sticker: body {self._format_response_body(sticker_response)}'
                    )

                    overwritten = self.exporter.overwrite(rebuilt_markup, file_path)
                    results.append(
                        ProcessingResult(
                            source_path=file_path,
                            success=True,
                            output_paths=[overwritten],
                            operation_logs=operation_logs,
                        )
                    )
                    continue

                source_image = document.image
                width_cm, height_cm = self._get_image_size_cm(source_image)

                rendered_markup = self.markup_service.process(document)
                thumbnail = self.thumbnail_service.process(document)
                sticker = self.sticker_service.process(document)

                operation_logs.append(f'API article: start ({folder_name})')
                article_response = self.api_service.update_article(
                    article=folder_name,
                    width_cm=width_cm,
                    height_cm=height_cm,
                    preview_image=source_image,
                )
                operation_logs.append(
                    f'API article: OK {article_response.status_code} {self.api_service.ARTICLE_URL}'
                )
                operation_logs.append(
                    f'API article: body {self._format_response_body(article_response)}'
                )
                operation_logs.append(f'API sticker: start ({folder_name})')
                sticker_response = self.api_service.upload_sticker(
                    sticker_image=sticker,
                    filename=folder_name,
                )
                operation_logs.append(
                    f'API sticker: OK {sticker_response.status_code} {self.api_service.STICKER_URL}'
                )
                operation_logs.append(
                    f'API sticker: body {self._format_response_body(sticker_response)}'
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
                        operation_logs=operation_logs,
                    )
                )
            except requests.HTTPError as exc:
                response = exc.response
                if response is not None:
                    operation_logs.append(
                        f'HTTP ERROR: {response.status_code} {response.request.method} {response.url}'
                    )
                    operation_logs.append(
                        f'HTTP ERROR body: {self._format_response_body(response)}'
                    )
                else:
                    operation_logs.append(f'HTTP ERROR: {exc}')
                results.append(
                    ProcessingResult(
                        source_path=file_path,
                        success=False,
                        operation_logs=operation_logs,
                        error_message=str(exc),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                operation_logs.append(f'ERROR: {exc}')
                results.append(
                    ProcessingResult(
                        source_path=file_path,
                        success=False,
                        operation_logs=operation_logs,
                        error_message=str(exc),
                    )
                )

        return results

    def _get_image_size_cm(self, image) -> tuple[int, int]:
        width_cm = round(self.markup_service.converter.px_to_cm(image.width))
        height_cm = round(self.markup_service.converter.px_to_cm(image.height))
        return width_cm, height_cm

    @staticmethod
    def _format_response_body(response: requests.Response) -> str:
        body = response.text.strip()
        return body if body else '<empty>'
