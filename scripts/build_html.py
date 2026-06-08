"""Merge batch analyses and build the final study HTML."""
import html as html_mod
import io
import json
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).resolve().parent.parent
SKIP_KW = ["封面", "目录", "过渡", "总结", "结论", "谢谢", "Thanks", "Conclusion", "Outline", "Content", "Brief Review", "Review"]


def _load_pages(data_dir: Path) -> list[dict]:
    all_pages = []
    for path in sorted(data_dir.glob("batch_*.json")):
        with path.open("r", encoding="utf-8") as f:
            batch = json.load(f)
        all_pages.extend(batch if isinstance(batch, list) else [batch])

    if not all_pages:
        analyses_path = data_dir / "analyses.json"
        if analyses_path.exists():
            with analyses_path.open("r", encoding="utf-8") as f:
                all_pages = json.load(f)

    if not all_pages:
        raise SystemExit(f"No batch_*.json or analyses.json found in {data_dir}")

    all_pages.sort(key=lambda x: x.get("page", x.get("page_num", 0)))
    min_page = min(p.get("page", p.get("page_num", 0)) for p in all_pages)
    if min_page == 0:
        for p in all_pages:
            p["page"] = p.get("page", p.get("page_num", 0)) + 1
    return all_pages


def _section_html(sections: list) -> str:
    blocks = []
    for item in sections:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        label, content = item[0], item[1]
        paragraphs = "".join(f"<p>{html_mod.escape(part.strip())}</p>" for part in str(content).split("\n") if part.strip())
        blocks.append(
            "<div class=\"detail-block\">"
            f"<div class=\"detail-label\">{html_mod.escape(str(label))}</div>"
            f"<div class=\"detail-content\">{paragraphs}</div>"
            "</div>"
        )
    return "\n".join(blocks)


def _validate_pages(pages: list[dict]) -> list[str]:
    warnings = []
    for p in pages:
        page_num = p.get("page", p.get("page_num", 0))
        overview = str(p.get("overview", ""))
        sections = p.get("sections", [])
        total_chars = len(overview) + sum(len(str(item[1])) for item in sections if isinstance(item, (list, tuple)) and len(item) >= 2)
        if total_chars < 200 and not any(kw in overview for kw in SKIP_KW):
            warnings.append(f"Page {page_num}: short analysis ({total_chars} chars)")
        labels = [str(item[0]) for item in sections if isinstance(item, (list, tuple)) and len(item) >= 2]
        page_type = str(p.get("type", ""))
        if page_type in {"figure", "mixed"} and "图表详解" not in labels:
            warnings.append(f"Page {page_num}: figure/mixed page missing 图表详解")
        if page_type in {"math", "mixed", "exercise"} and "公式解读" not in labels and "计算题模板" not in labels:
            warnings.append(f"Page {page_num}: math/exercise page missing formula or calculation section")
    return warnings


def generate_summary(pages: list[dict]) -> str:
    formulas, templates, pitfalls, likely = [], [], [], []
    for p in pages:
        page_num = p.get("page", p.get("page_num", 0))
        exam = p.get("exam") or {}
        for text in exam.get("formulas", [])[:3]:
            formulas.append((page_num, text))
        for text in exam.get("calculation_templates", [])[:3]:
            templates.append((page_num, text))
        for text in exam.get("pitfalls", [])[:3]:
            pitfalls.append((page_num, text))
        for text in exam.get("likely_questions", [])[:2]:
            likely.append((page_num, text))

    def list_block(title: str, items: list[tuple[int, str]]) -> str:
        if not items:
            return ""
        lis = "".join(
            f"<li><a href=\"#page-{pn}\">第 {pn} 页</a>：{html_mod.escape(str(text))}</li>"
            for pn, text in items[:12]
        )
        return f"<div class=\"summary-point\"><div class=\"point-title\">{title}</div><ul>{lis}</ul></div>"

    key_pages = []
    for p in pages:
        overview = str(p.get("overview", ""))
        if any(kw in overview for kw in SKIP_KW):
            continue
        score = len(p.get("sections", [])) + (2 if p.get("exam") else 0)
        key_pages.append((score, p.get("page", 0), overview[:80]))
    key_pages = sorted(key_pages, reverse=True)[:8]
    key_html = "".join(
        f"<div class=\"summary-point\"><div class=\"point-title\">第 {pn} 页要点</div>"
        f"<div class=\"point-desc\">{html_mod.escape(desc)}</div>"
        f"<div class=\"point-links\"><a href=\"#page-{pn}\">跳转</a></div></div>"
        for _, pn, desc in sorted(key_pages, key=lambda x: x[1])
    )

    exam_html = "".join([
        list_block("公式速查", formulas),
        list_block("计算题模板", templates),
        list_block("易错点", pitfalls),
        list_block("可能考法", likely),
    ])

    return f"""<section class=\"summary-section\" id=\"summary\">
  <h2>复习总表</h2>
  <p class=\"summary-subtitle\">本资料共 {len(pages)} 页。先看公式、模板和易错点，再回到具体页面。</p>
  {exam_html or key_html}
  {key_html if exam_html else ""}
</section>"""


def build_html(out_dir: str):
    out_path = Path(out_dir)
    data_dir = out_path / "data"
    pdf_basename = out_path.name.removesuffix("_study")

    pages = _load_pages(data_dir)
    total = len(pages)

    with (data_dir / "analyses.json").open("w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

    warnings = _validate_pages(pages)
    for warning in warnings:
        print(f"Warning: {warning}")

    toc_items = []
    content_items = []
    for p in pages:
        page_num = p.get("page", p.get("page_num", 0))
        overview = str(p.get("overview", ""))
        brief = html_mod.escape(overview[:36] or "无概览")
        toc_items.append(f'<a href="#page-{page_num}">第 {page_num} 页 · {brief}</a>')

        image_id = f"{page_num - 1:03d}"
        content_items.append(f"""<section class=\"page-section\" id=\"page-{page_num}\">
  <img src=\"images/page_{image_id}.png\" alt=\"第 {page_num} 页截图\" loading=\"lazy\">
  <div class=\"explanation\">
    <span class=\"page-number\">第 {page_num} 页 / 共 {total} 页</span>
    <div class=\"page-topic\">{html_mod.escape(overview)}</div>
    {_section_html(p.get("sections", []))}
  </div>
</section>""")

    toc_items.append('<a href="#summary" class="summary-link">复习总表</a>')
    summary = generate_summary(pages)

    template_path = SKILL_DIR / "assets" / "template.html"
    template = template_path.read_text(encoding="utf-8")
    html = (template
            .replace("{{TITLE}}", f"{pdf_basename} - 学习笔记")
            .replace("{{TOC}}", "\n".join(toc_items))
            .replace("{{CONTENT}}", "\n".join(content_items))
            .replace("{{SUMMARY}}", summary))

    html_path = out_path / f"{pdf_basename}_study.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"Merged {total} page analyses")
    print(f"HTML built: {html_path} ({html_path.stat().st_size / 1024:.1f} KB)")
    return str(html_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_html.py <output_dir>")
        sys.exit(1)
    build_html(sys.argv[1])
