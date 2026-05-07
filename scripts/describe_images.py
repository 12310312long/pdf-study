"""GPU-accelerated image description for PDF study pages.

Uses Salesforce/blip-image-captioning-large (~1.5GB) via transformers + PyTorch.
Natively supported — no trust_remote_code needed. On first run, downloads model.
Subsequent runs use cache.

Fallback tiers: CUDA (fp16, fast) -> CPU (fp32, slow) -> empty JSON (degraded)
"""
import sys, os, json, io, time, argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# HF mirrors (hf.co is blocked in some regions)
HF_MIRRORS = {
    "hf": "https://huggingface.co",
    "hf-mirror": "https://hf-mirror.com",
}

MODEL_NAME = "Salesforce/blip-image-captioning-large"


def describe_images(out_dir: str, device: str = "auto", skip_text_heavy: bool = False,
                    mirror: str = "auto"):
    from PIL import Image
    import torch

    data_dir = os.path.join(out_dir, "data")
    images_dir = os.path.join(out_dir, "images")

    if not os.path.isdir(images_dir):
        print(f"Images directory not found: {images_dir}")
        _write_empty(data_dir)
        return {}

    image_files = sorted([f for f in os.listdir(images_dir) if f.endswith(".png")])
    if not image_files:
        print("No PNG images found.")
        _write_empty(data_dir)
        return {}

    # --- Device selection ---
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        dtype = torch.float16
    else:
        print("CUDA unavailable, running on CPU (10-15s per page).")
        dtype = torch.float32

    # --- Mirror selection ---
    if mirror == "auto":
        mirror_order = ["hf-mirror", "hf"]
    else:
        mirror_order = [mirror]

    # --- Load model ---
    print(f"Loading {MODEL_NAME} (first run downloads ~1.5GB)...")
    model = processor = None
    last_error = None

    for m in mirror_order:
        endpoint = HF_MIRRORS.get(m)
        if endpoint:
            os.environ["HF_ENDPOINT"] = endpoint
            print(f"  Trying {endpoint} ...")
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration

            model = BlipForConditionalGeneration.from_pretrained(
                MODEL_NAME, torch_dtype=dtype,
            ).to(device)
            model.eval()
            processor = BlipProcessor.from_pretrained(MODEL_NAME)
            print("Model loaded.")
            break
        except Exception as e:
            last_error = e
            continue

    if model is None:
        print(f"Failed to load {MODEL_NAME} from any mirror: {last_error}")
        print("Image descriptions unavailable. Pipeline will use text-only analysis.")
        _write_empty(data_dir)
        return {}

    # --- Determine skip set ---
    skip_pages = set()
    if skip_text_heavy:
        pt_path = os.path.join(data_dir, "page_text.json")
        if os.path.exists(pt_path):
            with open(pt_path, encoding="utf-8") as f:
                text_map = json.load(f)
            skip_pages = {int(k) for k, v in text_map.items() if len(v.strip()) > 300}
            print(f"Skipping {len(skip_pages)} text-heavy pages.")

    # --- Process images ---
    descriptions = {}
    total = len(image_files)
    start_time = time.time()

    for i, fname in enumerate(image_files):
        page_idx = int(fname.replace("page_", "").replace(".png", ""))

        if page_idx in skip_pages:
            descriptions[str(page_idx)] = ""
            continue

        img_path = os.path.join(images_dir, fname)
        try:
            img = Image.open(img_path).convert("RGB")
            inputs = processor(img, return_tensors="pt")
            if device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            with torch.no_grad():
                generated_ids = model.generate(**inputs, max_new_tokens=200)

            caption = processor.decode(generated_ids[0], skip_special_tokens=True).strip()
            descriptions[str(page_idx)] = caption

        except Exception as e:
            print(f"  Error page {page_idx}: {e}")
            descriptions[str(page_idx)] = ""

        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        eta = (total - i - 1) / rate if rate > 0 else 0
        print(f"  [{i+1}/{total}] page_{page_idx:03d}.png  ({rate:.1f} pg/s, ETA {eta:.0f}s)")

    # --- Save ---
    output_path = os.path.join(data_dir, "image_descriptions.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(descriptions, f, ensure_ascii=False, indent=2)

    total_time = time.time() - start_time
    described = sum(1 for v in descriptions.values() if v)
    print(f"Done: {described}/{total} pages described in {total_time:.0f}s -> {output_path}")
    return descriptions


def _write_empty(data_dir: str):
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "image_descriptions.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({}, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GPU-accelerated PDF page image description")
    parser.add_argument("out_dir", help="The *_study/ output directory")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--mirror", default="auto",
                        choices=["auto", "hf", "hf-mirror"],
                        help="HF endpoint mirror (auto tries hf-mirror.com then hf.co)")
    parser.add_argument("--skip-text-heavy", action="store_true",
                        help="Skip pages with >300 chars of extracted text")
    args = parser.parse_args()
    describe_images(args.out_dir, args.device, args.skip_text_heavy, args.mirror)
