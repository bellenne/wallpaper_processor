class UnitConverter:
    CM_PER_INCH = 2.54
    MM_IN_CM = 10.0

    def __init__(self, dpi: int) -> None:
        self.dpi = dpi

    @property
    def px_per_cm(self) -> float:
        return self.dpi / self.CM_PER_INCH

    @property
    def px_per_mm(self) -> float:
        return self.px_per_cm / self.MM_IN_CM

    def px_to_cm(self, px: int | float) -> float:
        return px / self.px_per_cm

    def cm_to_px(self, cm: int | float) -> int:
        return round(cm * self.px_per_cm)

    def mm_to_px(self, mm: int | float) -> int:
        return round(mm * self.px_per_mm)
