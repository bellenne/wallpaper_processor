from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    dpi: int = 72
    panel_width_cm: float = 100.0
    tech_field_height_cm: float = 3.0
    text_left_margin_cm: float = 2.0
    qr_top_margin_mm: float = 3.0
    qr_bottom_margin_mm: float = 6.0
    qr_right_margin_mm: float = 6.0
    background_color: str = 'white'
    text_color: str = 'black'
    font_size_px: int = 26
    jpeg_quality: int = 95

    thumbnail_dpi: int = 150
    thumbnail_max_side_cm: float = 21.0
    thumbnail_qr_size_cm: float = 3.5
    thumbnail_qr_margin_mm: float = 2.0
    thumbnail_caption_margin_mm: float = 2.0
    thumbnail_caption_height_cm: float = 1.0
    thumbnail_caption_padding_mm: float = 1.0
    thumbnail_font_size_px: int = 28
    thumbnail_overlay_alpha: int = 170

    sticker_dpi: int = 150
    sticker_size_cm: float = 7.0
    sticker_background_color: str = 'white'
    sticker_border_color: str = 'black'
    sticker_bottom_fill: str = 'white'
    sticker_manufacturer_text: str = 'Производитель: Россия,\nООО "КАСТОМ КРАФТ"\n121205, ОГРН-1257700423287'
    sticker_logo_asset_path: str = 'assets/logo.png'
    sticker_title_font_size_px: int = 16
    sticker_label_font_size_px: int = 12
    sticker_main_font_size_px: int = 18
    sticker_small_font_size_px: int = 10
