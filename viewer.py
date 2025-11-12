"""
viewer.py
---------
Alternative mammogram viewer without PyQt6 dependency.
This version uses Matplotlib and Pillow for display and preview.

Usage:
  python viewer.py <image_path>               # Opens the image in an interactive Matplotlib window
  python viewer.py <image_path> --preview     # Generates a PNG preview next to the original
  python viewer.py --self-test                # Runs built-in tests (creates synthetic image)
"""

import sys
import os
import argparse
from pathlib import Path
import platform

try:
    from PIL import Image
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

try:
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False


def _safe_readable(path: Path) -> bool:
    return path.exists() and os.access(path, os.R_OK)


def show_image_matplotlib(image_path: Path) -> bool:
    """Display the mammogram using matplotlib."""
    if not HAVE_MPL or not HAVE_PIL:
        print("❌ Matplotlib or Pillow not available.")
        return False

    try:
        img = Image.open(image_path)
        plt.figure(figsize=(10, 10))
        plt.imshow(img, cmap="gray")
        plt.axis("off")
        plt.title(f"Mammogram: {image_path.name}")
        plt.show()
        return True
    except Exception as e:
        print(f"❌ Error displaying image: {e}")
        return False


def export_preview(image_path: Path, out_path: Path | None = None, max_px: int = 1200) -> Path:
    """Create a downscaled preview PNG for environments without GUI."""
    if not HAVE_PIL:
        raise RuntimeError("Pillow not available to export preview.")

    image_path = Path(image_path)
    if out_path is None:
        out_path = image_path.with_name(f"preview_{image_path.stem}.png")

    with Image.open(image_path) as img:
        w, h = img.size
        scale = min(1.0, float(max_px) / max(w, h))
        if scale < 1.0:
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size)
        img.save(out_path, format="PNG")
        print(f"✅ Preview saved to {out_path}")
        return out_path


def show_image(image_path: Path, preview_only: bool = False) -> bool:
    """Display an image or export a preview if requested."""
    image_path = Path(image_path)
    if not _safe_readable(image_path):
        print(f"❌ Image not found or unreadable: {image_path}")
        return False

    if preview_only:
        export_preview(image_path)
        return True

    return show_image_matplotlib(image_path)


def _run_self_test() -> int:
    """Creates a synthetic test image and tests preview/export."""
    print("🧪 Running self-test...")
    if not HAVE_PIL:
        print("⚠️ Pillow not available; skipping test.")
        return 0

    from PIL import Image, ImageDraw

    tmp = Path.cwd() / "_viewer_test_tmp"
    tmp.mkdir(exist_ok=True)
    src = tmp / "synthetic_test.png"

    img = Image.new("L", (1024, 1024), 80)
    draw = ImageDraw.Draw(img)
    draw.rectangle([200, 200, 800, 800], outline=255, width=10)
    draw.text((220, 220), "Test Mammogram", fill=255)
    img.save(src)

    print(f"✅ Created synthetic test image: {src}")
    export_preview(src)

    if HAVE_MPL:
        show_image_matplotlib(src)

    print("✅ Self-test completed successfully.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Mammogram image viewer using Matplotlib and Pillow.")
    parser.add_argument("image", nargs="?", help="Path to the image to display.")
    parser.add_argument("--preview", action="store_true", help="Generate a preview instead of showing.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    args = parser.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    if not args.image:
        print("Usage: python viewer.py <image_path> [--preview]")
        return 1

    path = Path(args.image)
    ok = show_image(path, preview_only=args.preview)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
 