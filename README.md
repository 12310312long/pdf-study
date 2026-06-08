# PDF Study - 课件复习助手

Turn PDF courseware into local HTML and Markdown study guides with page screenshots, Chinese explanations, and exam-oriented summaries.

## Features

- Render PDF pages to high-resolution PNG images.
- Extract per-page text as ground truth.
- Prepare a visual review queue for GPT/Codex vision.
- Generate page-by-page Chinese explanations.
- Support exam mode: formulas, calculation templates, likely questions, and pitfalls.
- Build local HTML and Markdown outputs.

## Important Vision Policy

This skill does not use BLIP, Hugging Face, torch, transformers, or any local image captioning model.

Visual understanding is done by GPT/Codex directly inspecting rendered page screenshots. The helper script `describe_images.py` only prepares `visual_review_queue.json`; it does not describe images by itself.

## Quick Start

```bash
pip install -r requirements.txt

PDF="path/to/courseware.pdf"
SKILL_DIR="path/to/pdf-study"
OUT_DIR="${PDF%.pdf}_study"

python "$SKILL_DIR/scripts/pdf_to_images.py" "$PDF" "$OUT_DIR/images" 2.0
python "$SKILL_DIR/scripts/extract_text.py" "$PDF" "$OUT_DIR/data"
python "$SKILL_DIR/scripts/describe_images.py" "$OUT_DIR" --all

# Then the assistant reads page_text.json, visual_review_queue.json, and selected/all PNGs with GPT vision,
# writes data/batch_*.json, and builds outputs:
python "$SKILL_DIR/scripts/build_html.py" "$OUT_DIR"
python "$SKILL_DIR/scripts/build_md.py" "$OUT_DIR"
```

## Output Structure

```
<courseware>_study/
|-- <courseware>_study.html
|-- <courseware>_study.md
|-- images/
|   |-- page_000.png
|   `-- ...
`-- data/
    |-- extracted_text.txt
    |-- page_text.json
    |-- visual_review_queue.json
    |-- image_descriptions.json
    |-- analyses.json
    `-- pages_text/
```

## Analysis JSON

Each batch file should contain a list of pages:

```json
[
  {
    "page": 1,
    "type": "mixed",
    "overview": "本页介绍 cache 地址如何拆成 tag、index 和 offset。",
    "sections": [
      ["内容讲解", "..."],
      ["图表详解", "..."],
      ["公式解读", "..."],
      ["考试重点", "..."]
    ],
    "exam": {
      "formulas": ["offset bits = log2(block size)"],
      "calculation_templates": ["先算 offset，再算 index，最后算 tag。"],
      "pitfalls": ["Tag 不是 Data 的一部分。"],
      "likely_questions": ["给地址和 cache 参数，求 tag/index/offset。"]
    }
  }
]
```

## Dependencies

- pypdfium2: PDF rendering
- pdfplumber: text extraction
- Pillow: image handling

## License

MIT
