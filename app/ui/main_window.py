from pathlib import Path
import sys

from PySide6.QtCore import Qt
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

        self._build_ui()
        self._sync_output_dir_ui()
        self._on_rewrite_mode_changed()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title = QLabel('Подготовка изображений')
        title.setObjectName('titleLabel')

        subtitle = QLabel(
            'Выбери папку или перетащи сюда файлы/папку.\n'
            'Обрабатываются только изображения.\n'
            'Экспорт всегда в JPG.'
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName('subtitleLabel')

        top_buttons = QHBoxLayout()
        top_buttons.setSpacing(12)

        self.select_folder_button = QPushButton('Выбрать папку')
        self.select_folder_button.clicked.connect(self.select_folder)

        self.clear_button = QPushButton('Очистить список')
        self.clear_button.clicked.connect(self.clear_files)

        self.process_button = QPushButton('Обработать')
        self.process_button.clicked.connect(self.process_files)

        top_buttons.addWidget(self.select_folder_button)
        top_buttons.addWidget(self.clear_button)
        top_buttons.addStretch(1)
        top_buttons.addWidget(self.process_button)

        self.rewrite_checkbox = QCheckBox('Перезаписать старые тех.поля')
        self.rewrite_checkbox.stateChanged.connect(self._on_rewrite_mode_changed)

        output_layout = QHBoxLayout()
        output_layout.setSpacing(12)

        output_label = QLabel('Папка экспорта')
        output_label.setObjectName('sectionLabel')

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        self.output_dir_edit.setObjectName('pathEdit')

        self.output_dir_button = QPushButton('Выбрать экспорт')
        self.output_dir_button.clicked.connect(self.select_output_folder)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_dir_edit, 1)
        output_layout.addWidget(self.output_dir_button)

        self.drop_hint = QLabel('Перетащи сюда изображения или целую папку')
        self.drop_hint.setObjectName('dropHint')
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.file_list = DragDropListWidget()
        self.file_list.paths_dropped.connect(self.handle_dropped_paths)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText('Здесь появится лог обработки...')
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
        self.output_dir_button.setEnabled(not rewrite_mode)

        if rewrite_mode:
            self.drop_hint.setText('Выбери корневую папку с вложенными папками изображений или перетащи её сюда')
        else:
            self.drop_hint.setText(
                f'Добавлено файлов: {len(self.selected_files)}'
                if self.selected_files
                else 'Перетащи сюда изображения или целую папку'
            )

    def select_folder(self) -> None:
        if self.rewrite_checkbox.isChecked():
            folder = QFileDialog.getExistingDirectory(self, 'Выбери корневую папку с вложенными папками изображений')
            if not folder:
                return

            files = self.discovery.from_folder_recursive(folder)
            self.selected_files = files
            self.refresh_file_list()
            self.log(f'Выбрана корневая папка: {folder}')
            self.log(f'Найдено изображений для перезаписи тех.поля: {len(files)}')
            return

        folder = QFileDialog.getExistingDirectory(self, 'Выбери папку с изображениями')
        if not folder:
            return

        files = self.discovery.from_folder(folder)
        self.add_files(files)
        self.log(f'Выбрана папка: {folder}')
        self.log(f'Найдено изображений: {len(files)}')

    def select_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, 'Выбери папку для экспорта', str(self.output_dir))
        if not folder:
            return

        self.output_dir = Path(folder).resolve()
        self._sync_output_dir_ui()
        self.log(f'Папка экспорта: {self.output_dir}')

    def handle_dropped_paths(self, paths: list[str]) -> None:
        if self.rewrite_checkbox.isChecked():
            files: list[Path] = []
            for raw_path in paths:
                path = Path(raw_path)
                if path.is_dir():
                    files.extend(self.discovery.from_folder_recursive(path))
                elif self.image_loader.is_supported_image(path):
                    files.append(path)

            current = {p.resolve(): p for p in self.selected_files}
            for file_path in files:
                current[file_path.resolve()] = file_path

            self.selected_files = sorted(current.values(), key=lambda p: str(p).lower())
            self.refresh_file_list()
            self.log(f'Добавлено в режим перезаписи: {len(files)} файл(ов)')
            return

        files = self.discovery.from_mixed_paths(paths)
        self.add_files(files)
        self.log(f'Добавлено через drag&drop: {len(files)} файл(ов)')

    def add_files(self, files: list[Path]) -> None:
        current = {p.resolve(): p for p in self.selected_files}
        for file_path in files:
            current[file_path.resolve()] = file_path

        self.selected_files = sorted(current.values(), key=lambda p: p.name.lower())
        self.refresh_file_list()

    def clear_files(self) -> None:
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
                f'Найдено файлов для перезаписи: {len(self.selected_files)}'
                if self.selected_files
                else 'Выбери корневую папку с вложенными папками изображений или перетащи её сюда'
            )
        else:
            self.drop_hint.setText(
                f'Добавлено файлов: {len(self.selected_files)}'
                if self.selected_files
                else 'Перетащи сюда изображения или целую папку'
            )

    def process_files(self) -> None:
        if not self.selected_files:
            QMessageBox.information(self, 'Нет файлов', 'Сначала добавь файлы или выбери папку.')
            return

        rewrite_mode = self.rewrite_checkbox.isChecked()
        self.log('Старт обработки...')
        if rewrite_mode:
            self.log('Режим: перезапись старых тех.полей')
        else:
            self.log(f'Экспорт в: {self.output_dir}')

        results = self.batch_processor.process_files(
            self.selected_files,
            rewrite_existing_tech_fields=rewrite_mode,
        )

        success_count = 0
        error_count = 0

        for result in results:
            if result.success:
                success_count += 1
                exported = '; '.join(str(path) for path in result.output_paths)
                self.log(f'OK: {result.source_path.name} -> {exported}')
            else:
                error_count += 1
                self.log(f'ERROR: {result.source_path.name} -> {result.error_message}')

        self.log(f'Готово.\nУспешно: {success_count}, ошибок: {error_count}')

        if rewrite_mode:
            QMessageBox.information(
                self,
                'Перезапись завершена',
                f'Успешно: {success_count}\nОшибок: {error_count}\nФайлы перезаписаны на месте.',
            )
        else:
            QMessageBox.information(
                self,
                'Обработка завершена',
                f'Успешно: {success_count}\nОшибок: {error_count}\nПапка результатов: {self.output_dir}',
            )

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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
