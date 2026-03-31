from pathlib import Path
import sys

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.batch_processor import WallpaperBatchProcessor
from app.application.file_discovery import ImageFileDiscovery
from app.core.api_service import ApiService
from app.core.config import AppConfig
from app.core.exporter import JpegExporter
from app.core.image_loader import ImageLoader
from app.core.markup_service import WallpaperMarkupService
from app.core.panel_layout_service import PanelLayoutService
from app.core.qr_service import QrCodeService
from app.core.sticker_service import StickerService
from app.core.thumbnail_service import ThumbnailService
from app.core.units import UnitConverter
from app.ui.drag_drop_list import DragDropListWidget
from app.ui.processing_worker import ProcessingWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Wallpaper Processor')
        self.resize(1100, 760)

        self.config = AppConfig()
        self.converter = UnitConverter(self.config.dpi)

        self.image_loader = ImageLoader()
        self.discovery = ImageFileDiscovery(self.image_loader)
        self.panel_layout_service = PanelLayoutService(self.converter, self.config.panel_width_cm)
        self.qr_service = QrCodeService()
        self.api_service = ApiService()

        self.markup_service = WallpaperMarkupService(
            self.config,
            self.converter,
            self.panel_layout_service,
            self.qr_service,
        )
        self.thumbnail_service = ThumbnailService(self.config, self.qr_service)
        self.sticker_service = StickerService(self.config, self.panel_layout_service)
        self.exporter = JpegExporter(self.config)
        self.batch_processor = WallpaperBatchProcessor(
            self.image_loader,
            self.markup_service,
            self.thumbnail_service,
            self.sticker_service,
            self.exporter,
            self.api_service,
        )

        self.selected_files: list[Path] = []
        self.output_dir = Path('output').resolve()
        self.processing_thread: QThread | None = None
        self.processing_worker: ProcessingWorker | None = None
        self.processing_rewrite_mode = False

        self._build_ui()
        self._sync_output_dir_ui()
        self._on_rewrite_mode_changed()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title = QLabel('\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0439')
        title.setObjectName('titleLabel')

        subtitle = QLabel(
            '\u0412\u044b\u0431\u0435\u0440\u0438 \u043f\u0430\u043f\u043a\u0443 \u0438\u043b\u0438 \u043f\u0435\u0440\u0435\u0442\u0430\u0449\u0438 \u0441\u044e\u0434\u0430 \u0444\u0430\u0439\u043b\u044b/\u043f\u0430\u043f\u043a\u0443.\n'
            '\u041e\u0431\u0440\u0430\u0431\u0430\u0442\u044b\u0432\u0430\u044e\u0442\u0441\u044f \u0442\u043e\u043b\u044c\u043a\u043e \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f.\n'
            '\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u0432\u0441\u0435\u0433\u0434\u0430 \u0432 JPG.'
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName('subtitleLabel')

        top_buttons = QHBoxLayout()
        top_buttons.setSpacing(12)

        self.select_folder_button = QPushButton('\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u043f\u0430\u043f\u043a\u0443')
        self.select_folder_button.clicked.connect(self.select_folder)

        self.clear_button = QPushButton('\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a')
        self.clear_button.clicked.connect(self.clear_files)

        self.process_button = QPushButton('\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c')
        self.process_button.clicked.connect(self.process_files)

        top_buttons.addWidget(self.select_folder_button)
        top_buttons.addWidget(self.clear_button)
        top_buttons.addStretch(1)
        top_buttons.addWidget(self.process_button)

        self.rewrite_checkbox = QCheckBox('\u041f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0441\u0442\u0430\u0440\u044b\u0435 \u0442\u0435\u0445.\u043f\u043e\u043b\u044f')
        self.rewrite_checkbox.stateChanged.connect(self._on_rewrite_mode_changed)

        output_layout = QHBoxLayout()
        output_layout.setSpacing(12)

        output_label = QLabel('\u041f\u0430\u043f\u043a\u0430 \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430')
        output_label.setObjectName('sectionLabel')

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        self.output_dir_edit.setObjectName('pathEdit')

        self.output_dir_button = QPushButton('\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u044d\u043a\u0441\u043f\u043e\u0440\u0442')
        self.output_dir_button.clicked.connect(self.select_output_folder)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_dir_edit, 1)
        output_layout.addWidget(self.output_dir_button)

        self.drop_hint = QLabel('\u041f\u0435\u0440\u0435\u0442\u0430\u0449\u0438 \u0441\u044e\u0434\u0430 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f \u0438\u043b\u0438 \u0446\u0435\u043b\u0443\u044e \u043f\u0430\u043f\u043a\u0443')
        self.drop_hint.setObjectName('dropHint')
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.file_list = DragDropListWidget()
        self.file_list.paths_dropped.connect(self.handle_dropped_paths)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText('\u0417\u0434\u0435\u0441\u044c \u043f\u043e\u044f\u0432\u0438\u0442\u0441\u044f \u043b\u043e\u0433 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438...')
        self.log_box.setMaximumBlockCount(1000)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addLayout(top_buttons)
        main_layout.addWidget(self.rewrite_checkbox)
        main_layout.addLayout(output_layout)
        main_layout.addWidget(self.drop_hint)
        main_layout.addWidget(self.file_list, 1)
        main_layout.addWidget(self.log_box, 1)

    def _sync_output_dir_ui(self) -> None:
        self.output_dir_edit.setText(str(self.output_dir))
        self.batch_processor.set_output_dir(self.output_dir)

    def _on_rewrite_mode_changed(self) -> None:
        rewrite_mode = self.rewrite_checkbox.isChecked()
        self.output_dir_edit.setEnabled(not rewrite_mode)
        self.output_dir_button.setEnabled(not rewrite_mode and self.processing_thread is None)

        if rewrite_mode:
            self.drop_hint.setText('\u0412\u044b\u0431\u0435\u0440\u0438 \u043a\u043e\u0440\u043d\u0435\u0432\u0443\u044e \u043f\u0430\u043f\u043a\u0443 \u0441 \u0432\u043b\u043e\u0436\u0435\u043d\u043d\u044b\u043c\u0438 \u043f\u0430\u043f\u043a\u0430\u043c\u0438 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0439 \u0438\u043b\u0438 \u043f\u0435\u0440\u0435\u0442\u0430\u0449\u0438 \u0435\u0451 \u0441\u044e\u0434\u0430')
        else:
            self.drop_hint.setText(
                f'\u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e \u0444\u0430\u0439\u043b\u043e\u0432: {len(self.selected_files)}'
                if self.selected_files
                else '\u041f\u0435\u0440\u0435\u0442\u0430\u0449\u0438 \u0441\u044e\u0434\u0430 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f \u0438\u043b\u0438 \u0446\u0435\u043b\u0443\u044e \u043f\u0430\u043f\u043a\u0443'
            )

    def select_folder(self) -> None:
        if self.rewrite_checkbox.isChecked():
            folder = QFileDialog.getExistingDirectory(self, '\u0412\u044b\u0431\u0435\u0440\u0438 \u043a\u043e\u0440\u043d\u0435\u0432\u0443\u044e \u043f\u0430\u043f\u043a\u0443 \u0441 \u0432\u043b\u043e\u0436\u0435\u043d\u043d\u044b\u043c\u0438 \u043f\u0430\u043f\u043a\u0430\u043c\u0438 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0439')
            if not folder:
                return

            files = self.discovery.from_folder_recursive(folder)
            self.selected_files = files
            self.refresh_file_list()
            self.log(f'\u0412\u044b\u0431\u0440\u0430\u043d\u0430 \u043a\u043e\u0440\u043d\u0435\u0432\u0430\u044f \u043f\u0430\u043f\u043a\u0430: {folder}')
            self.log(f'\u041d\u0430\u0439\u0434\u0435\u043d\u043e \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0439 \u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u0438 \u0442\u0435\u0445.\u043f\u043e\u043b\u044f: {len(files)}')
            return

        folder = QFileDialog.getExistingDirectory(self, '\u0412\u044b\u0431\u0435\u0440\u0438 \u043f\u0430\u043f\u043a\u0443 \u0441 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f\u043c\u0438')
        if not folder:
            return

        files = self.discovery.from_folder(folder)
        self.add_files(files)
        self.log(f'\u0412\u044b\u0431\u0440\u0430\u043d\u0430 \u043f\u0430\u043f\u043a\u0430: {folder}')
        self.log(f'\u041d\u0430\u0439\u0434\u0435\u043d\u043e \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0439: {len(files)}')

    def select_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, '\u0412\u044b\u0431\u0435\u0440\u0438 \u043f\u0430\u043f\u043a\u0443 \u0434\u043b\u044f \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430', str(self.output_dir))
        if not folder:
            return

        self.output_dir = Path(folder).resolve()
        self._sync_output_dir_ui()
        self.log(f'\u041f\u0430\u043f\u043a\u0430 \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430: {self.output_dir}')

    def handle_dropped_paths(self, paths: list[str]) -> None:
        if self.rewrite_checkbox.isChecked():
            files: list[Path] = []
            for raw_path in paths:
                path = Path(raw_path)
                if path.is_dir():
                    files.extend(self.discovery.from_folder_recursive(path))
                elif self.discovery.is_processable_image(path):
                    files.append(path)

            current = {p.resolve(): p for p in self.selected_files}
            for file_path in files:
                current[file_path.resolve()] = file_path

            self.selected_files = sorted(current.values(), key=lambda p: str(p).lower())
            self.refresh_file_list()
            self.log(f'\u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e \u0432 \u0440\u0435\u0436\u0438\u043c \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u0438: {len(files)} \u0444\u0430\u0439\u043b(\u043e\u0432)')
            return

        files = self.discovery.from_mixed_paths(paths)
        self.add_files(files)
        self.log(f'\u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e \u0447\u0435\u0440\u0435\u0437 drag&drop: {len(files)} \u0444\u0430\u0439\u043b(\u043e\u0432)')

    def add_files(self, files: list[Path]) -> None:
        current = {p.resolve(): p for p in self.selected_files}
        for file_path in files:
            current[file_path.resolve()] = file_path

        self.selected_files = sorted(current.values(), key=lambda p: p.name.lower())
        self.refresh_file_list()

    def clear_files(self) -> None:
        if self.processing_thread is not None:
            return

        self.selected_files = []
        self.refresh_file_list()
        self.log_box.clear()

    def refresh_file_list(self) -> None:
        self.file_list.clear()
        for file_path in self.selected_files:
            item = QListWidgetItem(str(file_path))
            item.setToolTip(str(file_path))
            self.file_list.addItem(item)

        if self.rewrite_checkbox.isChecked():
            self.drop_hint.setText(
                f'\u041d\u0430\u0439\u0434\u0435\u043d\u043e \u0444\u0430\u0439\u043b\u043e\u0432 \u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u0438: {len(self.selected_files)}'
                if self.selected_files
                else '\u0412\u044b\u0431\u0435\u0440\u0438 \u043a\u043e\u0440\u043d\u0435\u0432\u0443\u044e \u043f\u0430\u043f\u043a\u0443 \u0441 \u0432\u043b\u043e\u0436\u0435\u043d\u043d\u044b\u043c\u0438 \u043f\u0430\u043f\u043a\u0430\u043c\u0438 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0439 \u0438\u043b\u0438 \u043f\u0435\u0440\u0435\u0442\u0430\u0449\u0438 \u0435\u0451 \u0441\u044e\u0434\u0430'
            )
        else:
            self.drop_hint.setText(
                f'\u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e \u0444\u0430\u0439\u043b\u043e\u0432: {len(self.selected_files)}'
                if self.selected_files
                else '\u041f\u0435\u0440\u0435\u0442\u0430\u0449\u0438 \u0441\u044e\u0434\u0430 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f \u0438\u043b\u0438 \u0446\u0435\u043b\u0443\u044e \u043f\u0430\u043f\u043a\u0443'
            )

    def process_files(self) -> None:
        if not self.selected_files:
            QMessageBox.information(self, '\u041d\u0435\u0442 \u0444\u0430\u0439\u043b\u043e\u0432', '\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0434\u043e\u0431\u0430\u0432\u044c \u0444\u0430\u0439\u043b\u044b \u0438\u043b\u0438 \u0432\u044b\u0431\u0435\u0440\u0438 \u043f\u0430\u043f\u043a\u0443.')
            return

        if self.processing_thread is not None:
            return

        rewrite_mode = self.rewrite_checkbox.isChecked()
        self.processing_rewrite_mode = rewrite_mode
        self._set_processing_state(True)

        self.log('\u0421\u0442\u0430\u0440\u0442 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438...')
        if rewrite_mode:
            self.log('\u0420\u0435\u0436\u0438\u043c: \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u044c \u0441\u0442\u0430\u0440\u044b\u0445 \u0442\u0435\u0445.\u043f\u043e\u043b\u0435\u0439')
        else:
            self.log(f'\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u0432: {self.output_dir}')

        self.processing_thread = QThread(self)
        self.processing_worker = ProcessingWorker(
            self.batch_processor,
            list(self.selected_files),
            rewrite_mode,
        )
        self.processing_worker.moveToThread(self.processing_thread)

        self.processing_thread.started.connect(self.processing_worker.run)
        self.processing_worker.log_message.connect(self.log)
        self.processing_worker.result_ready.connect(self._handle_processing_result)
        self.processing_worker.completed.connect(self._handle_processing_completed)
        self.processing_worker.failed.connect(self._handle_processing_failed)
        self.processing_worker.finished.connect(self._cleanup_processing)
        self.processing_worker.finished.connect(self.processing_thread.quit)
        self.processing_worker.finished.connect(self.processing_worker.deleteLater)
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)

        self.processing_thread.start()

    def _set_processing_state(self, is_processing: bool) -> None:
        self.select_folder_button.setEnabled(not is_processing)
        self.clear_button.setEnabled(not is_processing)
        self.process_button.setEnabled(not is_processing)
        self.rewrite_checkbox.setEnabled(not is_processing)
        self.file_list.setEnabled(not is_processing)
        self.output_dir_button.setEnabled(not is_processing and not self.rewrite_checkbox.isChecked())

        if is_processing:
            self.process_button.setText('\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430...')
        else:
            self.process_button.setText('\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c')
            self._on_rewrite_mode_changed()

    def _handle_processing_result(self, result) -> None:
        if result.success:
            exported = '; '.join(str(path) for path in result.output_paths)
            self.log(f'OK: {result.source_path.name} -> {exported}')
        else:
            self.log(f'ERROR: {result.source_path.name} -> {result.error_message}')

    def _handle_processing_completed(self, success_count: int, error_count: int) -> None:
        self.log(f'\u0413\u043e\u0442\u043e\u0432\u043e.\n\u0423\u0441\u043f\u0435\u0448\u043d\u043e: {success_count}, \u043e\u0448\u0438\u0431\u043e\u043a: {error_count}')

        if self.processing_rewrite_mode:
            QMessageBox.information(
                self,
                '\u041f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u044c \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430',
                f'\u0423\u0441\u043f\u0435\u0448\u043d\u043e: {success_count}\n\u041e\u0448\u0438\u0431\u043e\u043a: {error_count}\n\u0424\u0430\u0439\u043b\u044b \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u0430\u043d\u044b \u043d\u0430 \u043c\u0435\u0441\u0442\u0435.',
            )
        else:
            QMessageBox.information(
                self,
                '\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430',
                f'\u0423\u0441\u043f\u0435\u0448\u043d\u043e: {success_count}\n\u041e\u0448\u0438\u0431\u043e\u043a: {error_count}\n\u041f\u0430\u043f\u043a\u0430 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u043e\u0432: {self.output_dir}',
            )

    def _handle_processing_failed(self, message: str) -> None:
        self.log(f'\u041a\u0440\u0438\u0442\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438: {message}')
        QMessageBox.warning(
            self,
            '\u041e\u0448\u0438\u0431\u043a\u0430 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438',
            f'\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u043f\u0440\u0435\u0440\u0432\u0430\u043d\u0430: {message}',
        )

    def _cleanup_processing(self) -> None:
        self._set_processing_state(False)
        self.processing_worker = None
        self.processing_thread = None

    def log(self, message: str) -> None:
        self.log_box.appendPlainText(message)


WIN11_DARK_STYLESHEET = '''
QWidget {
    background-color: #0f1115;
    color: #f2f4f8;
    font-family: 'Segoe UI';
    font-size: 14px;
}
QMainWindow {
    background-color: #0f1115;
}
QLabel#titleLabel {
    font-size: 28px;
    font-weight: 700;
    color: #ffffff;
}
QLabel#subtitleLabel {
    color: #aab2bf;
    font-size: 14px;
}
QLabel#sectionLabel {
    color: #cfd7e6;
    font-size: 14px;
    font-weight: 600;
}
QLabel#dropHint {
    background-color: #161a22;
    border: 1px dashed #3f4c63;
    border-radius: 14px;
    padding: 20px;
    color: #c4ccda;
    font-size: 15px;
}
QPushButton {
    background-color: #1b2330;
    border: 1px solid #2f3c50;
    border-radius: 12px;
    padding: 10px 16px;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #243042;
}
QPushButton:pressed {
    background-color: #2b3a4f;
}
QCheckBox {
    color: #dbe5f5;
    spacing: 10px;
    padding: 4px 0;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid #46556f;
    background: #151922;
}
QCheckBox::indicator:checked {
    background: #2e5bff;
    border: 1px solid #2e5bff;
}
QListWidget, QPlainTextEdit, QLineEdit {
    background-color: #151922;
    border: 1px solid #2a3342;
    border-radius: 16px;
    padding: 10px;
    selection-background-color: #2e5bff;
    selection-color: white;
}
QLineEdit {
    color: #dbe5f5;
}
QScrollBar:vertical {
    background: #11151d;
    width: 12px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: #394558;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
'''


def run_app() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(WIN11_DARK_STYLESHEET)

    from app.core.updater import AppUpdater

    if AppUpdater().process_startup_update():
        return

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
