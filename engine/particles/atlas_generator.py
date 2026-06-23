from PIL import Image
from pathlib import Path
import json

from data.particles import ASSETS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT = PROJECT_ROOT / "assets" / "particles"

OUT_DIR = Path(__file__).resolve().parent
OUT_DIR = OUT_DIR / "atlas" 
OUT_DIR.mkdir(exist_ok=True)

rows = []

class AtlasGenerator():
    def __init__(self) -> None:
        pass
        
    def _generate_atlas(self):
        """
        Generates a png texture atlas and a config file.
        """
        atlas_file = OUT_DIR / "atlas.png"
        config_file = OUT_DIR / "atlas.json"

        #check if source pngs have been modified and if not - return
        if atlas_file.exists() and config_file.exists():
            atlas_time = atlas_file.stat().st_mtime

            newest_source = max(
                f.stat().st_mtime
                for folder in INPUT.iterdir()
                if folder.is_dir()
                for f in folder.glob("*.png")
            )

            if atlas_time >= newest_source:
                print("  Atlas up to date")
                return
            
        print("  Generating...")

        # Load assets
        for asset_name, asset_path in ASSETS.items():
            folder = INPUT / asset_path
            print("getting assets from", folder)

            frames = sorted(folder.glob("*.png"))
            imgs = [Image.open(f).convert("RGBA") for f in frames]

            if not imgs:
                continue

            rows.append((asset_name, frames, imgs))

        # 1. Load all folders
        # for folder in sorted(INPUT.iterdir()):
        #     if not folder.is_dir():
        #         continue

        #     frames = sorted(folder.glob("*.png"))
        #     imgs = [Image.open(f).convert("RGBA") for f in frames]

        #     if not imgs:
        #         continue

        #     rows.append((folder.name, frames, imgs))

        # 2. Compute atlas size
        atlas_w = max(sum(img.width for img in imgs) for _, _, imgs in rows)
        atlas_h = sum(max(img.height for img in imgs) for _, _, imgs in rows)

        atlas = Image.new("RGBA", (atlas_w, atlas_h))

        # whole atlas information
        meta = {
            "atlas_width": atlas_w,
            "atlas_height": atlas_h,
            "assets": {}
        }

        y = 0

        # 3. Build atlas (per particle type information)
        for asset_name, frames, imgs in rows:
            x = 0
            row_h = max(img.height for img in imgs)

            meta["assets"][asset_name] = {
                "y": y,
                "height": row_h,
                "frame_count": len(imgs),
                "aspect_ratio": imgs[0].width / imgs[0].height,
                "frames": []
            }

            for f, img in zip(frames, imgs):
                atlas.paste(img, (x, y))

                meta["assets"][asset_name]["frames"].append({
                    "file": f.name,

                    "w": img.width,
                    "h": img.height,

                    "u0": x / atlas_w,
                    "u1": (x + img.width) / atlas_w,

                    "v0": 1.0 - ((y + img.height) / atlas_h),
                    "v1": 1.0 - (y / atlas_h),
                })

                x += img.width

            y += row_h

        # 4. Save outputs
        atlas.save(OUT_DIR / "atlas.png")

        with open(OUT_DIR / "atlas.json", "w") as f:
            json.dump(meta, f, indent=4)

        print("Atlas generated.")