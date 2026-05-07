"""Extract text from all PDF pages for ground truth reference."""
import sys, os, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_text(pdf_path: str, output_dir: str) -> dict:
    import pdfplumber
    os.makedirs(output_dir, exist_ok=True)
    text_map = {}

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ''
            text_map[i] = text.strip()

    # Save as readable text file
    txt_path = os.path.join(output_dir, "extracted_text.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        for i in sorted(text_map.keys()):
            f.write(f'=== PAGE {i+1} ===\n{text_map[i]}\n\n')

    # Save as JSON for script access
    json_path = os.path.join(output_dir, "page_text.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(text_map, f, ensure_ascii=False, indent=2)

    # Also save per-page text files for easy access
    pages_dir = os.path.join(output_dir, "pages_text")
    os.makedirs(pages_dir, exist_ok=True)
    for idx, text in text_map.items():
        with open(os.path.join(pages_dir, f"page_{idx:03d}.txt"), 'w', encoding='utf-8') as f:
            f.write(text.strip())
    print(f"Saved {len(text_map)} per-page text files to {pages_dir}")

    print(f"Extracted text from {len(text_map)} pages -> {output_dir}")
    return text_map

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_text.py <pdf_path> <output_dir>")
        sys.exit(1)
    extract_text(sys.argv[1], sys.argv[2])
