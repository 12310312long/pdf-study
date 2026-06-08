"""Merge batch analyses and build a Markdown study guide."""
import io
import json
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKIP_KW = ["封面", "目录", "过渡", "总结", "结论", "谢谢", "Thanks", "Conclusion", "Outline", "Content", "Brief Review", "Review"]


def _load_pages(data_dir: Path) -> list[dict]:
    analyses_path = data_dir / "analyses.json"
    if analyses_path.exists():
        with analyses_path.open("r", encoding="utf-8") as f:
            pages = json.load(f)
    else:
        pages = []
        for path in sorted(data_dir.glob("batch_*.json")):
            with path.open("r", encoding="utf-8") as f:
                batch = json.load(f)
            pages.extend(batch if isinstance(batch, list) else [batch])

    if not pages:
        raise SystemExit(f"No batch_*.json or analyses.json found in {data_dir}")

    pages.sort(key=lambda x: x.get("page", x.get("page_num", 0)))
    min_page = min(p.get("page", p.get("page_num", 0)) for p in pages)
    if min_page == 0:
        for p in pages:
            p["page"] = p.get("page", p.get("page_num", 0)) + 1
    return pages


def generate_summary(pages: list[dict]) -> str:
    lines = ["## 复习总表 {#summary}\n", f"本资料共 {len(pages)} 页。\n"]
    buckets = [
        ("公式速查", "formulas"),
        ("计算题模板", "calculation_templates"),
        ("易错点", "pitfalls"),
        ("可能考法", "likely_questions"),
    ]
    wrote_any = False
    for title, key in buckets:
        items = []
        for p in pages:
            page_num = p.get("page", p.get("page_num", 0))
            for text in (p.get("exam") or {}).get(key, []):
                items.append((page_num, text))
        if items:
            wrote_any = True
            lines.append(f"### {title}\n")
            for page_num, text in items[:12]:
                lines.append(f"- 第 {page_num} 页：{text}")
            lines.append("")

    if not wrote_any:
        lines.append("### 关键页\n")
        scored = []
        for p in pages:
            overview = str(p.get("overview", ""))
            if any(kw in overview for kw in SKIP_KW):
                continue
            scored.append((len(p.get("sections", [])), p.get("page", 0), overview[:80]))
        for _, page_num, overview in sorted(scored, reverse=True)[:8]:
            lines.append(f"- [第 {page_num} 页](#page-{page_num})：{overview}")
        lines.append("")
    return "\n".join(lines)


def build_md(out_dir: str):
    out_path = Path(out_dir)
    data_dir = out_path / "data"
    pdf_basename = out_path.name.removesuffix("_study")
    pages = _load_pages(data_dir)
    total = len(pages)

    lines = [f"# {pdf_basename} - 学习笔记\n", "> 本笔记由 AI 根据课件文字、页图和考试导向分析生成。\n"]
    lines.append("## 目录\n")
    for p in pages:
        page_num = p.get("page", p.get("page_num", 0))
        overview = str(p.get("overview", ""))[:36].replace("[", "").replace("]", "").replace("|", "")
        lines.append(f"- [第 {page_num} 页 · {overview}](#page-{page_num})")
    lines.append("- [复习总表](#summary)\n")

    for p in pages:
        page_num = p.get("page", p.get("page_num", 0))
        overview = str(p.get("overview", ""))
        lines.append(f'<a id="page-{page_num}"></a>')
        lines.append(f"## 第 {page_num} 页 / 共 {total} 页\n")
        lines.append(f'<img src="images/page_{page_num - 1:03d}.png" width="100%" style="max-width:620px;border:1px solid #ddd;border-radius:6px">\n')
        if overview:
            lines.append(f"**{overview}**\n")
        for item in p.get("sections", []):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            label, content = item[0], item[1]
            lines.append(f"### {label}\n")
            lines.append(f"{content}\n")
        lines.append("---\n")

    lines.append(generate_summary(pages))
    md_path = out_path / f"{pdf_basename}_study.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown built: {md_path} ({md_path.stat().st_size / 1024:.1f} KB)")
    return str(md_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_md.py <output_dir>")
        sys.exit(1)
    build_md(sys.argv[1])
