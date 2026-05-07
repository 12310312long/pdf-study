"""Render PDF pages to high-resolution PNG images using pypdfium2."""
import sys
import os
from pathlib import Path

def render_pdf(pdf_path: str, output_dir: str, scale: float = 2.0) -> list[str]:
    """Render each page of a PDF as PNG images.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save rendered images.
        scale: Render scale factor (default 2.0 → ~1920px wide for 16:9 slides).

    Returns:
        List of paths to the rendered PNG files.
    """
    import pypdfium2 as pdfium

    os.makedirs(output_dir, exist_ok=True)
    pdf = pdfium.PdfDocument(pdf_path)
    total = len(pdf)
    image_paths = []

    for i in range(total):
        page = pdf[i]
        bitmap = page.render(scale=scale)
        img = bitmap.to_pil()
        out_path = os.path.join(output_dir, f"page_{i:03d}.png")
        img.save(out_path, "PNG")
        image_paths.append(out_path)
        print(f"[{i+1}/{total}] Rendered {out_path}  ({img.size[0]}x{img.size[1]})")

    pdf.close()
    return image_paths


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_images.py <pdf_path> [output_dir] [scale]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./pages"
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

    paths = render_pdf(pdf_path, output_dir, scale)
    print(f"\nDone. {len(paths)} pages rendered to {output_dir}")
