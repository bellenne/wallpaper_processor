import math
from dataclasses import dataclass

from app.core.units import UnitConverter


@dataclass
class PanelInfo:
    index: int
    number: int
    left_px: int
    right_px: int
    width_px: int


class PanelLayoutService:
    def __init__(self, converter: UnitConverter, panel_width_cm: float) -> None:
        self.converter = converter
        self.panel_width_cm = panel_width_cm

    def calculate_panel_count(self, image_width_px: int) -> int:
        displayed_width_cm = round(self.converter.px_to_cm(image_width_px))
        return max(1, math.ceil(displayed_width_cm / self.panel_width_cm))

    def build_panels(self, image_width_px: int) -> list[PanelInfo]:
        panel_width_px = self.converter.cm_to_px(self.panel_width_cm)
        panel_count = self.calculate_panel_count(image_width_px)
        panels: list[PanelInfo] = []

        for index in range(panel_count):
            left = index * panel_width_px
            right = image_width_px if index == panel_count - 1 else min((index + 1) * panel_width_px, image_width_px)
            panels.append(
                PanelInfo(
                    index=index,
                    number=index + 1,
                    left_px=left,
                    right_px=right,
                    width_px=right - left,
                )
            )

        return panels
