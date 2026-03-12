import qrcode
from PIL import Image


class QrCodeService:
    def build_qr(self, data: str, target_size_px: int) -> Image.Image:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color='black', back_color='white').convert('RGB')
        return img.resize((target_size_px, target_size_px), Image.Resampling.NEAREST)
