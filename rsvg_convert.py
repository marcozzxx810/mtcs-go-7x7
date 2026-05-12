from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


OPTIONS_WITH_VALUES = {
    "-f",
    "--format",
    "-o",
    "--output",
    "-w",
    "--width",
    "-h",
    "--height",
    "--dpi-x",
    "--dpi-y",
    "--zoom",
    "--page-width",
    "--page-height",
    "--top",
    "--left",
}


def svg_length_to_points(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"^\s*([0-9.]+)", value)
    if not match:
        return None
    # SVG/CSS px is defined at 96 dpi; PDF points are 72 dpi.
    return float(match.group(1)) * 72.0 / 96.0


def svg_page_size(input_path: Path, fallback: tuple[int, int]) -> tuple[float, float]:
    try:
        root = ET.parse(input_path).getroot()
    except ET.ParseError:
        return float(fallback[0]), float(fallback[1])

    width = svg_length_to_points(root.attrib.get("width"))
    height = svg_length_to_points(root.attrib.get("height"))
    if width is not None and height is not None:
        return width, height

    view_box = root.attrib.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            try:
                return float(parts[2]) * 72.0 / 96.0, float(parts[3]) * 72.0 / 96.0
            except ValueError:
                pass

    return float(fallback[0]), float(fallback[1])


def parse_args(argv: list[str]) -> argparse.Namespace:
    fmt = "pdf"
    output: str | None = None
    positional: list[str] = []
    index = 0

    while index < len(argv):
        arg = argv[index]
        if arg.startswith("--format="):
            fmt = arg.split("=", 1)[1]
        elif arg.startswith("--output="):
            output = arg.split("=", 1)[1]
        elif arg in {"-f", "--format"} and index + 1 < len(argv):
            fmt = argv[index + 1]
            index += 1
        elif arg in {"-o", "--output"} and index + 1 < len(argv):
            output = argv[index + 1]
            index += 1
        elif arg in OPTIONS_WITH_VALUES and index + 1 < len(argv):
            index += 1
        elif arg.startswith("-"):
            pass
        else:
            positional.append(arg)
        index += 1

    return argparse.Namespace(fmt=fmt, output=output, input=positional[-1] if positional else None)


def render_svg_to_png(input_path: Path, scale: int = 1800) -> bytes:
    with tempfile.TemporaryDirectory() as output_dir:
        subprocess.run(
            ["qlmanage", "-t", "-s", str(scale), "-o", output_dir, str(input_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        generated = Path(output_dir) / f"{input_path.name}.png"
        if not generated.exists():
            generated_files = list(Path(output_dir).glob("*.png"))
            if not generated_files:
                raise SystemExit("qlmanage did not produce a PNG file")
            generated = generated_files[0]
        return crop_png(generated.read_bytes())


def crop_png(png_data: bytes, padding: int = 24) -> bytes:
    image = Image.open(io.BytesIO(png_data)).convert("RGBA")
    bg = image.getpixel((0, 0))
    width, height = image.size
    pixels = image.load()
    threshold = 18
    min_x, min_y = width, height
    max_x, max_y = -1, -1

    for y in range(height):
        for x in range(width):
            pixel = pixels[x, y]
            if pixel[3] < 10:
                continue
            if sum(abs(pixel[i] - bg[i]) for i in range(3)) > threshold:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if max_x < min_x or max_y < min_y:
        return png_data

    box = (
        max(min_x - padding, 0),
        max(min_y - padding, 0),
        min(max_x + padding + 1, width),
        min(max_y + padding + 1, height),
    )
    cropped = image.crop(box)
    output = io.BytesIO()
    cropped.save(output, format="PNG")
    return output.getvalue()


def png_bytes_to_pdf(input_path: Path, png_data: bytes) -> bytes:
    image = Image.open(io.BytesIO(png_data)).convert("RGB")
    page_width = image.width * 72.0 / 160.0
    page_height = image.height * 72.0 / 160.0

    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=(page_width, page_height))
    pdf.drawImage(
        ImageReader(image),
        0,
        0,
        width=page_width,
        height=page_height,
        preserveAspectRatio=True,
        anchor="c",
    )
    pdf.showPage()
    pdf.save()
    return output.getvalue()


def main() -> None:
    args = parse_args(sys.argv[1:])

    output_path = Path(args.output) if args.output else None
    fmt = args.fmt.lower()

    temp_path: Path | None = None
    if args.input:
        input_path = Path(args.input)
    else:
        data = sys.stdin.buffer.read()
        if not data:
            raise SystemExit("rsvg-convert compatibility wrapper requires SVG input")
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            tmp.write(data)
            temp_path = Path(tmp.name)
        input_path = temp_path

    if fmt not in {"pdf", "png"}:
        raise SystemExit(f"unsupported output format: {args.fmt}")

    try:
        png_data = render_svg_to_png(input_path)
        if fmt == "pdf":
            pdf_data = png_bytes_to_pdf(input_path, png_data)
            if output_path is None:
                sys.stdout.buffer.write(pdf_data)
            else:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(pdf_data)
        else:
            if output_path is None:
                sys.stdout.buffer.write(png_data)
            else:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(png_data)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
