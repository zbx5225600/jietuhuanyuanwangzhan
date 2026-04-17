#!/usr/bin/env python3
"""
Test harness: generate per-checkpoint routes from checkpoints/ and infer button interactions
from video.mp4 (if available). Outputs to output/ with routes/ HTML files and
interactions.json describing button coordinates.
"""
import os
import sys
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any

try:
    import cv2
    HAS_OPENCV = True
except Exception:
    HAS_OPENCV = False

CHECKPOINTS_DIR_DEFAULT = Path("checkpoints")
VIDEO_PATH_DEFAULT = Path("video.mp4")
OUTPUT_DIR_DEFAULT = Path("output")

def ensure_dirs(out_dir: Path):
    routes_dir = out_dir / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)
    return routes_dir

def list_checkpoints(checkpoints_dir: Path) -> List[Path]:
    exts = {".png", ".jpg", ".jpeg"}
    imgs = [p for p in sorted(checkpoints_dir.glob("*")) if p.suffix.lower() in exts]
    return imgs

def copy_image_to_output(img_path: Path, out_routes_dir: Path, route_name: str) -> Path:
    dest_img = out_routes_dir / f"{route_name}.png"
    shutil.copy2(str(img_path), str(dest_img))
    return dest_img

def generate_html_for_route(route_name: str, image_file: Path, output_routes_dir: Path) -> Path:
    html_path = output_routes_dir / f"{route_name}.html"
    html = f'''<!doctype html>
<html>
  <head><meta charset="utf-8"><title>{route_name}</title></head>
  <body style="font-family: sans-serif;">
    <h2>{route_name}</h2>
    <div style="max-width: 1200px; margin: 0 auto;">
      <img src="{route_name}.png" alt="{route_name}" style="width:100%; height:auto;" />
    </div>
  </body>
</html>'''
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path

def detect_buttons_with_opencv(frame) -> List[Dict[str, float]]:
    import numpy as np
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = frame.shape[:2]
    boxes = []
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        area = bw * bh
        if 200 < area < 10000:
            boxes.append((x, y, bw, bh))
    uniq = []
    for b in boxes:
        if not any(abs(b[0]-u[0])<20 and abs(b[1]-u[1])<20 for u in uniq):
            uniq.append(b)
    results = []
    for x, y, bw, bh in uniq:
        results.append({
            "x": max(0.0, min(1.0, x / w)),
            "y": max(0.0, min(1.0, y / h)),
            "w": max(0.0, min(1.0, bw / w)),
            "h": max(0.0, min(1.0, bh / h)),
        })
    return results

def extract_buttons_from_video(video_path: Path) -> List[Dict[str, Any]]:
    """
    Try to extract button-like regions from video frames.
    Returns a list of dicts with normalized positions (x,y,w,h)
    """
    if not video_path.exists():
        return []
    if not HAS_OPENCV:
        return [
            {"x": 0.15, "y": 0.45, "w": 0.25, "h": 0.08},
            {"x": 0.60, "y": 0.45, "w": 0.25, "h": 0.08},
            {"x": 0.37, "y": 0.68, "w": 0.25, "h": 0.08},
        ]
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, int(fps))
    boxes_all = []
    count = 0
    while True:
        ret = cap.grab()
        if not ret:
            break
        if int(cap.get(cv2.CAP_PROP_POS_FRAMES)) % step == 0:
            ok, frame = cap.read()
            if not ok:
                break
            boxes = detect_buttons_with_opencv(frame)
            boxes_all.extend(boxes)
        count += 1
        if frame_count > 0 and count > frame_count:
            break
    cap.release()
    uniq = []
    for b in boxes_all:
        if not any(abs(b.get("x",0)-u.get("x",0))<0.05 and abs(b.get("y",0)-u.get("y",0))<0.05 for u in uniq):
            uniq.append(b)
    return uniq

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Checkpoints to routes test harness")
    parser.add_argument("--checkpoints", default=str(CHECKPOINTS_DIR_DEFAULT), help="Path to checkpoints dir (images)")
    parser.add_argument("--video", default=str(VIDEO_PATH_DEFAULT), help="Path to video.mp4 for interactions")
    parser.add_argument("--output", default=str(OUTPUT_DIR_DEFAULT), help="Output directory")
    args = parser.parse_args()

    checkpoints_dir = Path(args.checkpoints)
    video_path = Path(args.video)
    output_dir = Path(args.output)

    print(f"Checkpoints: {checkpoints_dir.resolve()}")
    print(f"Video: {video_path.resolve() if video_path.exists() else video_path}")
    print(f"Output: {output_dir.resolve()}")

    routes_dir = ensure_dirs(output_dir)

    images = list_checkpoints(checkpoints_dir)
    if not images:
        print("No checkpoint images found. Generating sample placeholders...")
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image, ImageDraw
            for i in range(1, 3):
                w, h = 800, 480
                img = Image.new("RGB", (w, h), color=(200, 200, 200))
                d = ImageDraw.Draw(img)
                d.text((w//4, h//2), f"Page {i}", fill=(0,0,0))
                path = checkpoints_dir / f"page_{i}.png"
                img.save(path)
                images.append(path)
        except Exception as e:
            print(f"Warning: could not generate placeholders: {e}")
    if not images:
        print("No checkpoints available after placeholder generation. Exiting.")
        sys.exit(0)

    routes_info = []
    for idx, img_path in enumerate(images, start=1):
        route_name = f"route_{idx}"
        copied_img = copy_image_to_output(img_path, routes_dir, route_name)
        html_path = generate_html_for_route(route_name, copied_img, routes_dir)
        routes_info.append({"route": f"/{route_name}", "html": str(html_path.name), "image": copied_img.name})

    buttons = extract_buttons_from_video(video_path)
    route_buttons = []
    per_route = max(1, len(buttons) // max(1, len(images)))
    for i, img_path in enumerate(images, start=1):
        route_name = f"route_{i}"
        if buttons:
            slice_start = (i - 1) * per_route
            slice_end = slice_start + per_route
            btns = buttons[slice_start:slice_end]
        else:
            btns = [
                {"x": 0.15, "y": 0.45, "w": 0.25, "h": 0.08},
                {"x": 0.60, "y": 0.45, "w": 0.25, "h": 0.08},
            ]
        route_buttons.append({"route": f"/{route_name}", "buttons": btns})

    interactions = {"routes": route_buttons}
    with open(output_dir / "interactions.json", "w", encoding="utf-8") as f:
        json.dump(interactions, f, indent=2, ensure_ascii=False)

    print("\nGenerated outputs:")
    for r in routes_info:
        print(f" - Route {r['route']}: HTML -> {r['html']}, image -> {r['image']}")
    print(f"Intersections: interactions.json with {len(route_buttons)} routes")
    print(f"\nDone. Output directory: {output_dir.resolve()}")

if __name__ == "__main__":
    main()
