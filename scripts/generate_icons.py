"""Render deterministic SVG branding into desktop icons (offline only).

Linux desktop launchers use 256px PNG; Windows uses a multi-size .ico.
The canonical asset is assets/e5577-control-icon.svg.
"""

from pathlib import Path
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "e5577-control-icon.svg"
TARGET = ROOT / "build" / "icons"


def generate() -> tuple[Path, Path]:
    TARGET.mkdir(parents=True, exist_ok=True)
    renderer = QSvgRenderer(str(SOURCE))
    if not renderer.isValid():
        raise RuntimeError("L'icona SVG canonica non è valida")
    png = TARGET / "e5577-control.png"
    ico = TARGET / "e5577-control.ico"
    picture = QImage(256, 256, QImage.Format.Format_ARGB32)
    picture.fill(0)
    painter = QPainter(picture)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    if not picture.save(str(png), "PNG"):
        raise RuntimeError("Impossibile renderizzare l'icona PNG")
    with Image.open(png) as raw:
        image = raw.convert("RGBA")
        if image.getbbox() is None:
            raise RuntimeError("L'icona generata risulta vuota")
        image.save(
            ico, format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                   (64, 64), (128, 128), (256, 256)],
        )
    if not ico.is_file() or not png.is_file():
        raise RuntimeError("File icona mancanti")
    return png, ico


if __name__ == "__main__":
    png, ico = generate()
    print("ICON PNG:", png)
    print("ICON ICO:", ico)
