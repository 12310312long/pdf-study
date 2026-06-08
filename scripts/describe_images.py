"""Prepare a GPT/Codex vision review queue for rendered PDF page images.

This script intentionally does not run a local captioning model. It replaces the
old BLIP/Hugging Face path with a lightweight manifest that the assistant can use
when inspecting page PNGs with GPT vision.
"""
import argparse
import io
import json
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def prepare_visual_queue(out_dir: str, all_pages: bool = False, text_threshold: int = 300) -> list[dict]:
    out_path = Path(out_dir)
    data_dir = out_path / "data"
    images_dir = out_path / "images"
    data_dir.mkdir(parents=True, exist_ok=True)

    if not images_dir.is_dir():
        raise SystemExit(f"Images directory not found: {images_dir}")

    page_text = {}
    page_text_path = data_dir / "page_text.json"
    if page_text_path.exists():
        with page_text_path.open("r", encoding="utf-8") as f:
            page_text = json.load(f)

    queue = []
    for image_path in sorted(images_dir.glob("page_*.png")):
        page_idx = int(image_path.stem.replace("page_", ""))
        text = (page_text.get(str(page_idx)) or page_text.get(page_idx) or "").strip()
        needs_review = all_pages or len(text) < text_threshold
        queue.append({
            "page_index": page_idx,
            "page_number": page_idx + 1,
            "image": str(image_path),
            "text_chars": len(text),
            "review_with_gpt_vision": needs_review,
            "reason": "all pages requested" if all_pages else (
                "little extracted text" if needs_review else "text extraction likely sufficient; inspect if figures/formulas are present"
            ),
        })

    queue_path = data_dir / "visual_review_queue.json"
    with queue_path.open("w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    descriptions_path = data_dir / "image_descriptions.json"
    if not descriptions_path.exists():
        with descriptions_path.open("w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

    review_count = sum(1 for item in queue if item["review_with_gpt_vision"])
    print(f"Prepared GPT vision queue: {len(queue)} pages, {review_count} marked for review")
    print(f"Queue: {queue_path}")
    print("Next: inspect the listed PNGs with GPT/Codex vision and save notes to data/image_descriptions.json")
    return queue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare GPT vision review queue for PDF study pages")
    parser.add_argument("out_dir", help="The *_study output directory")
    parser.add_argument("--all", action="store_true", help="Mark every page for GPT vision review")
    parser.add_argument("--text-threshold", type=int, default=300, help="Review pages with fewer extracted text chars")
    args = parser.parse_args()
    prepare_visual_queue(args.out_dir, args.all, args.text_threshold)
