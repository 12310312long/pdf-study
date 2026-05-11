---
name: pdf-study
description: |
  Use when the user provides a PDF of courseware/slides and wants to study it page-by-page with AI explanations.
  Triggers: "analyze this PDF", "help me study this lecture", "explain each page of this PDF",
  "convert this PDF to study notes", "生成学习笔记", "帮我复习这个课件", "讲解这个PDF", "/pdf-study",
  or anytime a user uploads/mentions a PDF and asks for explanations, study aids, or learning materials.
  Works globally — not tied to any specific project directory.
compatibility: "Requires pypdfium2, pdfplumber, Pillow. GPU acceleration requires torch + transformers (auto-fallback to CPU if unavailable). Install: pip install pypdfium2 pdfplumber Pillow"
---

# PDF Study — 课件复习助手

Turn a PDF courseware into an interactive HTML study guide (plus optional Markdown export) with per-page screenshots and teacher-style explanations in Chinese.

## Output Structure

Create a folder next to the original PDF:

```
<original_name>_study/
├── <original_name>_study.html    # Final HTML (images loaded locally, not base64)
├── <original_name>_study.md      # Markdown version (same content, portable)
├── images/
│   ├── page_000.png
│   └── ...
└── data/
    ├── extracted_text.txt
    ├── page_text.json
    ├── image_descriptions.json   # GPU-generated
    ├── analyses.json
    └── pages_text/               # Per-page text files
```

## Workflow (target: under 3 minutes for 50-page PDF)

### Step 1: Setup (render + extract + GPU describe)

```bash
PDF="<pdf_path>"
OUT_DIR="${PDF%.pdf}_study"

# 1a. Render all pages to images
python "<skill-dir>/scripts/pdf_to_images.py" "$PDF" "$OUT_DIR/images" 2.0

# 1b. Extract text for ground truth
python "<skill-dir>/scripts/extract_text.py" "$PDF" "$OUT_DIR/data"
```

### Step 1c: GPU image descriptions (NEW — solves image reading for agents)

```bash
python "<skill-dir>/scripts/describe_images.py" "$OUT_DIR"
```

Uses `Salesforce/blip-image-captioning-large` (local vision model, ~1.5GB download on first use) to generate descriptions of every page image. Agents receive these descriptions as text — they never need to read image files.

- **First run:** downloads model (~1-2 minutes one-time, ~1.5GB)
- **Subsequent runs:** loads from cache (~5 seconds)
- **GPU:** ~1-2 seconds per page on NVIDIA GPU
- **CPU fallback:** works without GPU, ~10-15 sec/page (functional but slower)
- **Failure:** outputs empty JSON, pipeline degrades gracefully to text-only analysis
- **Output:** `data/image_descriptions.json`

Options: `--device cpu` to force CPU, `--skip-text-heavy` to skip pages with >300 chars of extracted text.

### Step 2: Inline analysis (all pages in main conversation)

**Read the data files, then generate analyses page-by-page directly in the current conversation.**
**No sub-agents. No file permissions issues. No cold-start overhead.**

**Procedure:**

1. Read `data/page_text.json` — dict of string page keys to extracted text
2. Read `data/image_descriptions.json` — dict of string page keys to image description
3. Classify each page (type, overview text) based on the extracted text
4. Divide pages into 2-3 batches (15-25 pages each, to keep output length manageable)
5. For each batch, generate the full JSON and write with the Write tool to `data/batch_N.json`

**Page type classification (classify EACH page before writing):**

| Type | Detection | Minimum Sections | Minimum Total Chars |
|------|-----------|-----------------|---------------------|
| simple | Title, divider, outline, thank-you, blank | 2 (内容讲解 + 背景知识) | 400 |
| text | Mainly text, no figures/diagrams | 2 (内容讲解 + 背景知识/补充说明) | 500 |
| figure | Has diagrams, charts, screenshots, photos | 3 (内容讲解 + 图表详解 + one other) | 700 |
| math | Has formulas, equations | 2 (内容讲解 + 公式解读) | 550 |
| mixed | Has both figures AND formulas | 4 (内容讲解 + 图表详解 + 公式解读 + one other) | 800 |

**Section types — use only what fits the page:**

| Section | When Required | Content Guidelines |
|---------|---------------|-------------------|
| 内容讲解 | ALWAYS | Core explanation in Chinese. 200-400 chars. Provide in-depth analysis, not just rephrasing the slide. |
| 图表详解 | REQUIRED for figure/mixed pages | Describe position, visual elements, significance of each figure/diagram. Reference the image description. 150-300 chars. |
| 公式解读 | REQUIRED for math/mixed pages | Explain each formula's meaning, variables, and intuition. 150-300 chars. |
| 背景知识 | Recommended for text/simple pages | Broader context, historical background, real-world connections. 120-250 chars. |
| 重点标注 | Optional — exam-critical points only | Use sparingly (max 2 pages per batch). 80-150 chars. |
| 补充说明 | Optional — nuances, misconceptions | Use when there is a subtle point worth clarifying. 120-250 chars. |

**Output format (page numbers MUST be 1-indexed):**

```json
[
  {
    "page": 1,
    "overview": "页面概览（2-4句中文，80-150字）",
    "sections": [
      ["内容讲解", "核心解释...（200-400字）"],
      ...
    ]
  }
]
```

**OUTPUT VALIDATION before writing each batch:**
1. Every page has overview (80-150 chars)
2. Every page meets its type's minimum section count
3. Every page meets its type's minimum total character count
4. NO ASCII double quotes (`"`) inside string values — use「」instead
5. Valid JSON — every `"` is structural
6. Page numbers are 1-indexed (first page = 1, not 0)

### Step 3: Merge + Build HTML

```bash
python "<skill-dir>/scripts/build_html.py" "$OUT_DIR"
```

### Step 3b (可选): Build Markdown

在 HTML 生成之后（或直接基于 `data/batch_*.json`）输出一份 Markdown 版本：

```bash
python "<skill-dir>/scripts/build_md.py" "$OUT_DIR"
```

Markdown 文件与 HTML 文件同级，位于 `<original_name>_study.md`，包含相同的逐页讲解、图片引用和课程总结，适合在 Obsidian、GitHub 等 Markdown 编辑器中查看。

### Step 3 补充: build_html.py 做了什么

`build_html.py` 的步骤：
1. Merges all `data/batch_*.json` into `data/analyses.json`
2. Validates page quality — warns if any non-skip page has <200 chars of analysis
3. Reads the template from `<skill-dir>/assets/template.html`
4. Generates the summary (extracts key points from analyses)
5. Builds the final HTML with `<img src="images/page_NNN.png">` references

### Step 4: Report

Tell the user: output folder, page count, total analysis sections, any quality warnings, and that both HTML and Markdown study guides are ready (if Markdown was generated).

## Analysis Guidelines

**Language:** Chinese (中文) with English technical terms preserved.

**Depth by page type** (hard minimums — MUST meet these):

| Page Type | Sections | Total Chars |
|-----------|----------|-------------|
| Cover/title/outline/divider | 2 (内容讲解 + 背景知识) | ≥400 |
| Text-only content | 2 (内容讲解 + 背景知识/补充说明) | ≥500 |
| Content with figures | 3 (内容讲解 + 图表详解 + one other) | ≥700 |
| Math/formula pages | 2 (内容讲解 + 公式解读) | ≥550 |
| Mixed (figures + math) | 4 (all four core sections) | ≥800 |

## Tips

- **Dividing pages into batches** — 2-3 batches of 15-25 pages each. Write each as `data/batch_N.json` with the Write tool. Batch JSONs are merged by `build_html.py` automatically.
- **GPU image descriptions** — do not read PNG images. Use `image_descriptions.json` for `图表详解` sections. If BLIP fails (empty JSON), fall back to text-only analysis.
- **First run downloads BLIP** — ~1.5GB one-time download (cached to HF_HOME). Subsequent runs load from cache.
- **GPU acceleration** — BLIP on CUDA does ~1-2 sec/page. Without GPU, CPU fallback is ~10-15 sec/page. Use `--device cpu` to force CPU mode.
- **JSON quoting** — use「」(corner brackets) instead of `"` inside string values to avoid JSON parse errors.
- **Images use local paths** (`images/page_000.png`), not base64. Keeps HTML small (~200KB vs ~28MB). Note: image filenames are 0-indexed (page_000.png = page 1).
- **The bundled scripts** in `scripts/` are the single source of truth. Don't rewrite them.
- **Dependencies:** `pip install pypdfium2 pdfplumber Pillow torch transformers`
