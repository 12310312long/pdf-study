"""Merge batch analyses and build the final study HTML."""
import json, os, sys, io, html as html_mod
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build_html(out_dir: str):
    data_dir = os.path.join(out_dir, "data")
    images_dir = os.path.join(out_dir, "images")
    pdf_basename = os.path.basename(out_dir.rstrip('/\\').removesuffix('_study'))

    # 1. Merge batch files
    all_pages = []
    for fname in sorted(os.listdir(data_dir)):
        if fname.startswith('batch_') and fname.endswith('.json'):
            with open(os.path.join(data_dir, fname), encoding='utf-8') as f:
                batch = json.load(f)
                all_pages.extend(batch if isinstance(batch, list) else [batch])

    all_pages.sort(key=lambda x: x.get('page', x.get('page_num', 0)))
    total = len(all_pages)

    # Normalize page indexing: images files are 0-indexed (page_000.png = page 1).
    # Detect whether batch JSON uses 0-indexed or 1-indexed page numbers.
    min_page = min(p.get('page', p.get('page_num', 0)) for p in all_pages)
    zero_indexed = min_page == 0

    # Save merged analyses (store 1-indexed page numbers going forward)
    for p in all_pages:
        if zero_indexed:
            p['page'] = p.get('page', p.get('page_num', 0)) + 1
    with open(os.path.join(data_dir, 'analyses.json'), 'w', encoding='utf-8') as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)

    print(f"Merged {total} page analyses (detected {'0-indexed' if zero_indexed else '1-indexed'} input)")

    # Validation: warn about suspiciously short pages
    short_pages = []
    for p in all_pages:
        pn = p.get('page', p.get('page_num', 0))
        sections = p.get('sections', [])
        overview = p.get('overview', '')
        total_chars = sum(len(content) for _, content in sections) + len(overview)
        if total_chars < 200 and not any(kw in overview for kw in SKIP_KW):
            short_pages.append((pn, total_chars))

    if short_pages:
        print(f"Warning: {len(short_pages)} page(s) have very short analysis (<200 chars):")
        for pn, chars in short_pages:
            print(f"  Page {pn}: {chars} chars")

    # 2. Build TOC and content
    toc_items = []
    content_items = []

    for i, p in enumerate(all_pages, 1):
        page_num = p.get('page', p.get('page_num', 0))
        overview = p.get('overview', '')
        sections = p.get('sections', [])

        brief = html_mod.escape(overview[:35])
        toc_items.append(f'<a href="#page-{page_num}">第{page_num}页: {brief}...</a>')

        detail_blocks = '\n'.join(
            f'    <div class="detail-block">\n'
            f'      <div class="detail-label">{html_mod.escape(label)}</div>\n'
            f'      <div class="detail-content"><p>{html_mod.escape(content)}</p></div>\n'
            f'    </div>'
            for label, content in sections
        )

        page_id = f"{page_num-1:03d}"
        section = f'''<section class="page-section" id="page-{page_num}">
  <img src="images/page_{page_id}.png" alt="第{page_num}页截图" loading="lazy">
  <div class="explanation">
    <span class="page-number">第 {page_num} 页 / 共 {total} 页</span>
    <div class="page-topic">{html_mod.escape(overview)}</div>
{detail_blocks}
  </div>
</section>'''
        content_items.append(section)

        if i % 12 == 0:
            print(f"  Built {i}/{total} page sections")

    # 3. Generate summary
    summary = generate_summary(all_pages)

    # 4. Load template and build
    template_path = os.path.join(SKILL_DIR, "assets", "template.html")
    with open(template_path, encoding='utf-8') as f:
        template = f.read()

    toc_items.append('<a href="#summary" style="font-weight:700;border-top:1px solid var(--border);margin-top:8px;padding-top:10px;">课程总结</a>')

    title = pdf_basename + " · 学习笔记"
    html = template.replace("{{TITLE}}", title)
    html = html.replace("{{TOC}}", "\n  ".join(toc_items))
    html = html.replace("{{CONTENT}}", "\n".join(content_items))
    html = html.replace("{{SUMMARY}}", summary)

    html_path = os.path.join(out_dir, f"{pdf_basename}_study.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(html_path) / 1024
    print(f"HTML built: {html_path} ({size_kb:.1f} KB)")
    return html_path


SKIP_KW = ['封面', '目录', '过渡', '总结', '结论', '谢谢', 'Thanks',
            'Conclusion', 'Outline', 'Content', 'Brief Review', 'Review']


def generate_summary(pages: list) -> str:
    """Generate a summary HTML block by auto-selecting representative key pages."""

    # Score each page: richer sections = higher weight for key page selection
    scored = []
    for p in pages:
        overview = p.get('overview', '')
        page_num = p.get('page', p.get('page_num', 0))
        if any(kw in overview for kw in SKIP_KW):
            continue
        sections = p.get('sections', [])
        # Score: section count weights content depth
        score = min(len(sections), 5)
        scored.append((page_num, overview[:60], score))

    total = len(scored)

    # Evenly sample across the range: pick 6-8 pages distributed across the document
    target = min(8, max(4, total))
    if total <= target:
        selected = scored
    else:
        selected = []
        step = total / target
        for i in range(target):
            idx = int(i * step)
            # Within a window around idx, pick the highest-scored page
            window = max(1, int(step))
            start = max(0, idx - window // 2)
            end = min(total, idx + window // 2 + 1)
            best = max(scored[start:end], key=lambda x: x[2], default=scored[idx])
            if best not in selected:
                selected.append(best)

    points = []
    for page_num, desc, _ in selected:
        points.append(f'''  <div class="summary-point">
    <div class="point-title">第{page_num}页要点</div>
    <div class="point-desc">{html_mod.escape(desc)}</div>
    <div class="point-links"><a href="#page-{page_num}">\u2192 第{page_num}页</a></div>
  </div>''')

    return f'''<section class="summary-section" id="summary">
  <h2>课程总结</h2>
  <p class="summary-subtitle">本课件共 {len(pages)} 页，以下是关键页面索引：</p>
{"".join(points)}
</section>'''


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_html.py <output_dir>")
        print("  output_dir: the *_study/ folder containing images/ and data/")
        sys.exit(1)
    build_html(sys.argv[1])
