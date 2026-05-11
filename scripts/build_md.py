"""Merge batch analyses and build a Markdown study guide."""
import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SKIP_KW = ['封面', '目录', '过渡', '总结', '结论', '谢谢', 'Thanks',
           'Conclusion', 'Outline', 'Content', 'Brief Review', 'Review']

def build_md(out_dir: str):
    data_dir = os.path.join(out_dir, "data")
    pdf_basename = os.path.basename(out_dir.rstrip('/\\').removesuffix('_study'))

    # 1. Load merged analyses (merge batches if analyses.json doesn't exist yet)
    analyses_path = os.path.join(data_dir, "analyses.json")
    if os.path.exists(analyses_path):
        with open(analyses_path, encoding='utf-8') as f:
            all_pages = json.load(f)
    else:
        all_pages = []
        for fname in sorted(os.listdir(data_dir)):
            if fname.startswith('batch_') and fname.endswith('.json'):
                with open(os.path.join(data_dir, fname), encoding='utf-8') as f:
                    batch = json.load(f)
                    all_pages.extend(batch if isinstance(batch, list) else [batch])

        if not all_pages:
            print("Error: no batch_*.json or analyses.json found in data/")
            sys.exit(1)

        all_pages.sort(key=lambda x: x.get('page', x.get('page_num', 0)))
        min_page = min(p.get('page', p.get('page_num', 0)) for p in all_pages)
        zero_indexed = min_page == 0
        for p in all_pages:
            if zero_indexed:
                p['page'] = p.get('page', p.get('page_num', 0)) + 1

        # Save merged analyses so build_html.py can reuse if needed
        with open(analyses_path, 'w', encoding='utf-8') as f:
            json.dump(all_pages, f, ensure_ascii=False, indent=2)

    total = len(all_pages)
    print(f"Loaded {total} page analyses")

    # 2. Build Markdown content
    lines = []
    lines.append(f"# {pdf_basename} · 学习笔记\n")
    lines.append("> 本笔记由 AI 自动生成，逐页讲解课件内容。\n")

    # TOC
    lines.append("## 目录\n")
    for p in all_pages:
        page_num = p.get('page', p.get('page_num', 0))
        overview = p.get('overview', '')
        brief = overview[:35] if overview else f"第{page_num}页"
        # Escape pipe and other Markdown special chars in anchor text
        brief_clean = brief.replace('[', '').replace(']', '').replace('|', '')
        lines.append(f"- [第{page_num}页: {brief_clean}...](#page-{page_num})")
    lines.append("- [课程总结](#summary)\n")

    # Per-page content
    for i, p in enumerate(all_pages):
        page_num = p.get('page', p.get('page_num', 0))
        overview = p.get('overview', '')
        sections = p.get('sections', [])

        img_filename = f"page_{page_num-1:03d}.png"
        lines.append(f"## 第 {page_num} 页 / 共 {total} 页 {{#page-{page_num}}}\n")
        img_src = 'images/' + img_filename
        lines.append(f'<img src="{img_src}" width="100%" style="max-width:520px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.1)">\n')

        if overview:
            lines.append(f'<p style="margin-top:8px"><strong>{overview}</strong></p>\n')

        for label, content in sections:
            # Escape any Markdown special chars in content
            lines.append(f"### {label}\n")
            lines.append(f"{content}\n")

        lines.append("---\n")

    # Summary
    summary = generate_summary(all_pages)
    lines.append(summary)

    md_content = "\n".join(lines)

    md_path = os.path.join(out_dir, f"{pdf_basename}_study.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    size_kb = os.path.getsize(md_path) / 1024
    print(f"Markdown built: {md_path} ({size_kb:.1f} KB)")
    return md_path


def generate_summary(pages: list) -> str:
    """Generate a Markdown summary section by auto-selecting representative key pages."""
    scored = []
    for p in pages:
        overview = p.get('overview', '')
        page_num = p.get('page', p.get('page_num', 0))
        if any(kw in overview for kw in SKIP_KW):
            continue
        sections = p.get('sections', [])
        score = min(len(sections), 5)
        scored.append((page_num, overview[:60], score))

    total = len(scored)
    target = min(8, max(4, total))
    if total <= target:
        selected = scored
    else:
        selected = []
        step = total / target
        for i in range(target):
            idx = int(i * step)
            window = max(1, int(step))
            start = max(0, idx - window // 2)
            end = min(total, idx + window // 2 + 1)
            best = max(scored[start:end], key=lambda x: x[2], default=scored[idx])
            if best not in selected:
                selected.append(best)

    lines = ["## 课程总结 {#summary}\n"]
    lines.append(f"本课件共 {len(pages)} 页，以下是关键页面索引：\n")
    for page_num, desc, _ in selected:
        lines.append(f"- **第{page_num}页**: {desc} → [跳转](#page-{page_num})")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_md.py <output_dir>")
        print("  output_dir: the *_study/ folder containing images/ and data/")
        sys.exit(1)
    build_md(sys.argv[1])
