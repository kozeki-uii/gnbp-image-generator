from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
LOGO_PATH = ROOT / "logo.png"
ICON_PATH = ROOT / "app_icon.ico"
CANVAS_SIZE = 1024
ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def create_logo() -> Image.Image:
    """Draw a compact image-generation mark that remains clear at 16 px."""
    image = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Dark neutral tile with a light image canvas.
    draw.rounded_rectangle((48, 48, 976, 976), radius=220, fill="#171B20")
    draw.rounded_rectangle((180, 236, 790, 826), radius=108, fill="#F4F7F5")

    # A bold landscape motif: sun, distant hill, and foreground hill.
    draw.ellipse((280, 340, 414, 474), fill="#F2C14E")
    draw.polygon([(214, 744), (430, 500), (600, 692), (760, 744)], fill="#32B89A")
    draw.polygon([(214, 744), (508, 580), (760, 744)], fill="#E56B5D")

    # Generation sparkle, separated from the picture frame for small-size clarity.
    sparkle = [
        (792, 112),
        (830, 244),
        (962, 282),
        (830, 320),
        (792, 452),
        (754, 320),
        (622, 282),
        (754, 244),
    ]
    draw.polygon(sparkle, fill="#F4F7F5")
    draw.ellipse((760, 250, 824, 314), fill="#F2C14E")

    return image


def create_icon() -> None:
    logo = create_logo()
    logo.save(LOGO_PATH, format="PNG", optimize=True)
    logo.save(ICON_PATH, format="ICO", sizes=ICON_SIZES)
    print(f"Created {LOGO_PATH.name} and {ICON_PATH.name}")


if __name__ == "__main__":
    create_icon()
