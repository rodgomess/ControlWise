from PIL import Image, ImageOps
from io import BytesIO

class ImageTransform():
    def __init__(self):
        pass

    def create_thumbnail(
            self,
            image_file,
            max_size: tuple[int, int] = (200, 200)
            ):
        
        with Image.open(image_file) as image:
            image = ImageOps.exif_transpose(image)

            image.thumbnail(
                max_size,
                Image.Resampling.LANCZOS,
            )

            # WebP funciona melhor com RGB/RGBA
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")
            
            return image.copy()
    
    def image_to_webp_bytes(
        self,
        image: Image.Image,
        quality: int = 80,
    ) -> bytes:

        buffer = BytesIO()

        image.save(
            buffer,
            format="WEBP",
            quality=quality,
            method=6,
        )

        return buffer.getvalue()