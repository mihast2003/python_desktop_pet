from PIL import Image
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT = PROJECT_ROOT / "assets" / "particles"

OUT_DIR = Path(__file__).resolve().parent

OUT_ATLAS = OUT_DIR / "atlas.png"
OUT_META = OUT_DIR / "atlas.py"

rows = []

# 1. Load all folders
for folder in sorted(INPUT.iterdir()):
    if not folder.is_dir():
        continue

    frames = sorted(folder.glob("*.png"))
    imgs = [Image.open(f).convert("RGBA") for f in frames]

    if not imgs:
        continue

    rows.append((folder.name, frames, imgs))

# 2. Compute atlas size
atlas_w = max(sum(img.width for img in imgs) for _, _, imgs in rows)
atlas_h = sum(max(img.height for img in imgs) for _, _, imgs in rows)

atlas = Image.new("RGBA", (atlas_w, atlas_h))

meta = {}
y = 0

# 3. Build atlas
for name, frames, imgs in rows:
    x = 0
    row_h = max(img.height for img in imgs)

    meta[name] = {
        "y": y,
        "height": row_h,
        "frames": []
    }

    for f, img in zip(frames, imgs):
        atlas.paste(img, (x, y))

        meta[name]["frames"].append({
            "file": f.name,
            "x": x,
            "w": img.width,
            "h": img.height
        })

        x += img.width

    y += row_h

# 4. Save outputs
atlas.save(OUT_ATLAS)

with open(OUT_META, "w") as f:
    f.write("ATLAS = ")
    f.write(repr(meta))

print("Done:", OUT_ATLAS, OUT_META)