from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.application.batch_processor import WallpaperBatchProcessor
from app.application.result_dto import ProcessingResult


class ProcessingWorker(QObject):
    log_message = Signal(str)
    result_ready = Signal(object)
    completed = Signal(int, int)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        batch_processor: WallpaperBatchProcessor,
        files: list[Path],
        rewrite_existing_tech_fields: bool,
    ) -> None:
        super().__init__()
        self.batch_processor = batch_processor
        self.files = files
        self.rewrite_existing_tech_fields = rewrite_existing_tech_fields

    @Slot()
    def run(self) -> None:
        success_count = 0
        error_count = 0

        try:
            def handle_log(file_path: Path, message: str) -> None:
                self.log_message.emit(f'[{file_path.name}] {message}')

            def handle_result(result: ProcessingResult) -> None:
                nonlocal success_count, error_count
                if result.success:
                    success_count += 1
                else:
                    error_count += 1
                self.result_ready.emit(result)

            self.batch_processor.process_files(
                self.files,
                rewrite_existing_tech_fields=self.rewrite_existing_tech_fields,
                log_callback=handle_log,
                result_callback=handle_result,
            )
            self.completed.emit(success_count, error_count)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()
