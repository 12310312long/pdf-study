---
name: pdf-study
description: |
  Use when the user provides or mentions a PDF of courseware/slides and wants to study it, explain it page by page, convert it to notes, or generate an exam-oriented review guide.
  Triggers: "analyze this PDF", "help me study this lecture", "explain each page of this PDF", "convert this PDF to study notes", "生成学习笔记", "帮我复习这个课件", "讲解这个PDF", "考前复习", "计算题速查", "/pdf-study".
  Works globally; not tied to any specific project directory.
compatibility: "Requires pypdfium2, pdfplumber, Pillow. No local vision model is used. Visual understanding is done by GPT/Codex multimodal image inspection over rendered page screenshots."
---

# PDF Study - 课件复习助手

Turn a PDF courseware file into a local HTML and Markdown study guide with page screenshots, Chinese explanations, and optional exam-oriented summaries.

## Core Principle

Use GPT/Codex vision for page images. Do not use BLIP, Hugging Face, torch, transformers, or any local captioning model for visual understanding.

The scripts only render pages, extract text, prepare a visual review queue, and build final artifacts. The actual visual interpretation is performed by the assistant using its image-reading capability on the rendered PNG pages.

## Output Structure

Create a folder next to the original PDF:

```
<original_name>_study/
|-- <original_name>_study.html
|-- <original_name>_study.md
|-- images/
|   |-- page_000.png
|   |-- page_001.png
|   `-- ...
`-- data/
    |-- extracted_text.txt
    |-- page_text.json
    |-- visual_review_queue.json
    |-- image_descriptions.json
    |-- batch_1.json
    |-- analyses.json
    `-- pages_text/
```

## Workflow

### Step 1: Render and Extract

```bash
PDF="<pdf_path>"
OUT_DIR="${PDF%.pdf}_study"
SKILL_DIR="<skill-dir>"

python "$SKILL_DIR/scripts/pdf_to_images.py" "$PDF" "$OUT_DIR/images" 2.0
python "$SKILL_DIR/scripts/extract_text.py" "$PDF" "$OUT_DIR/data"
python "$SKILL_DIR/scripts/describe_images.py" "$OUT_DIR" --all
```

`describe_images.py` is intentionally not an image captioning model. It prepares `data/visual_review_queue.json` so the assistant knows which rendered PNGs to inspect with GPT vision.

### Step 2: GPT Vision Review

Read:

- `data/page_text.json`
- `data/visual_review_queue.json`
- rendered images under `images/page_*.png`

For each page that has diagrams, equations, tables, screenshots, cache/pipeline layouts, memory hierarchy figures, or weak extracted text, inspect the PNG using GPT/Codex vision. Save concise visual notes to `data/image_descriptions.json` using 0-indexed page keys:

```json
{
  "0": "Cover slide for cache lecture; title and instructor metadata.",
  "12": "Diagram compares direct mapped, set associative, and fully associative cache placement."
}
```

If the page is text-only and the extracted text is sufficient, the visual note may be empty.

### Step 3: Generate Analyses

Generate `data/batch_N.json` files in this format. Page numbers must be 1-indexed.

```json
[
  {
    "page": 1,
    "type": "simple|text|figure|math|mixed|exercise",
    "overview": "80-150字中文概览。",
    "sections": [
      ["内容讲解", "核心解释，不能只是复述幻灯片。"],
      ["图表详解", "当页面有图、表、流程图、截图时必须写。"],
      ["公式解读", "当页面有公式、计算流程时必须写。"],
      ["考试重点", "只写真正可能考的点。"],
      ["易错点", "指出常见误解和判题陷阱。"],
      ["计算题模板", "给出可套用的步骤或公式。"]
    ],
    "exam": {
      "formulas": ["可选：本页公式"],
      "calculation_templates": ["可选：计算题步骤"],
      "pitfalls": ["可选：易错点"],
      "likely_questions": ["可选：可能考法"]
    }
  }
]
```

### Page Type Requirements

| Type | Use When | Minimum Sections | Minimum Content |
|---|---|---:|---:|
| simple | cover, outline, divider, blank, thanks | 2 | 300 Chinese chars |
| text | mainly text | 2 | 450 Chinese chars |
| figure | diagram/table/screenshot heavy | 3, including 图表详解 | 650 Chinese chars |
| math | formulas/equations/calculation | 3, including 公式解读 | 600 Chinese chars |
| mixed | figures plus formulas | 4, including 图表详解 and 公式解读 | 750 Chinese chars |
| exercise | worked example/homework/textbook question | 4, including 计算题模板 and 易错点 | 750 Chinese chars |

## Exam Mode

Use exam mode when the user says: 考试, 考前, 复习, 速查, 计算题, textbook, homework, quiz, final, midterm.

In exam mode, add these sections whenever relevant:

- `公式速查`: formulas with variables explained.
- `计算题模板`: step-by-step method that can be reused.
- `判题信号`: how to recognize the problem type from wording.
- `易错点`: traps such as units, index vs offset, local vs global miss rate.
- `一眼结论`: one short sentence for last-minute memory.

For Computer Organization, prioritize:

- Cache address breakdown, hit/miss traces, AMAT/CPI.
- Pipeline hazards, forwarding, stalls, structural hazards.
- Virtual memory VA to PA, TLB/page table, page offset.
- Amdahl's law and speedup limits.
- Hamming/ECC parity and syndrome calculations.
- Parallel speedup/efficiency if present.

## Build Artifacts

```bash
python "$SKILL_DIR/scripts/build_html.py" "$OUT_DIR"
python "$SKILL_DIR/scripts/build_md.py" "$OUT_DIR"
```

Report the output folder, page count, generated files, and any validation warnings.

## Quality Rules

- Explain in Chinese, preserve English technical terms.
- Do not invent slide content. Use extracted text plus GPT vision notes.
- Keep page numbers 1-indexed in `batch_N.json`; image filenames remain 0-indexed.
- Prefer structured formulas and reusable calculation steps over long prose in exam mode.
- If visual inspection was skipped for a figure-heavy page, say so in the report.
- Avoid ASCII double quotes inside JSON string values when possible; use Chinese corner brackets if quoting terms.
