# PDF Study — 课件复习助手

> Turn PDF courseware into interactive HTML study guides with per-page screenshots and teacher-style explanations in Chinese.

## Features

- **Render PDF pages** to high-resolution PNG images
- **Extract text** from PDF for ground truth reference
- **GPU-accelerated image captioning** (BLIP) for visual content description
- **AI-powered page analysis** with page-type-aware explanations (text, figure, math, mixed)
- **Interactive HTML output** with sidebar TOC, per-page explanations, dark mode, and print support

## Quick Start

```bash
# Install dependencies
pip install pypdfium2 pdfplumber Pillow

# (Optional) GPU-accelerated image descriptions
pip install torch transformers

# Run the pipeline
PDF="path/to/your/courseware.pdf"
SKILL_DIR="path/to/pdf-study"

# Step 1a: Render to images
python "$SKILL_DIR/scripts/pdf_to_images.py" "$PDF" "${PDF%.pdf}_study/images" 2.0

# Step 1b: Extract text
python "$SKILL_DIR/scripts/extract_text.py" "$PDF" "${PDF%.pdf}_study/data"

# Step 1c: (Optional) GPU image descriptions
python "$SKILL_DIR/scripts/describe_images.py" "${PDF%.pdf}_study"

# Step 2: Generate page analyses (requires Claude or manual authoring)
# See SKILL.md for the analysis format

# Step 3: Build HTML
python "$SKILL_DIR/scripts/build_html.py" "${PDF%.pdf}_study"
```

## Output Structure

```
<courseware>_study/
├── <courseware>_study.html    # Final study guide (open in browser)
├── images/
│   ├── page_000.png           # Screenshot of each page
│   └── ...
└── data/
    ├── extracted_text.txt
    ├── page_text.json
    ├── image_descriptions.json
    ├── analyses.json
    └── pages_text/
```

## Workflow

The pipeline consists of 4 steps:

| Step | Description | Time (50 pages) |
|------|-------------|------------------|
| 1a | Render PDF to PNGs | ~2s |
| 1b | Extract text from PDF | ~1.5s |
| 1c | (Optional) GPU image descriptions | ~25s (CUDA) |
| 2 | AI page analysis | ~2-5min (inline) |
| 3 | Build final HTML | <0.1s |

## Dependencies

- **pypdfium2** — PDF rendering
- **pdfplumber** — Text extraction
- **Pillow** — Image processing
- **torch + transformers** — (Optional, for GPU image captioning)

## License

MIT
