"""
EarthMender AI — Phase 1: Model Training Script
=================================================
Run this in Google Colab (free GPU — T4 recommended).

Final 5-Class System:
    plastic_bottle | water_sachet | polythene_bag | disposable | waste_container

─── HOW TO USE ───────────────────────────────────────────────
1. Open https://colab.research.google.com
2. Runtime → Change runtime type → GPU (T4)
3. Run SETUP cell
4. Paste Roboflow snippet into DATASET cell
5. Run VERIFY cell — confirm class names match exactly
6. Run TRAINING cell — 20–40 mins
7. Download best.pt → place in project root (same folder as app.py)
──────────────────────────────────────────────────────────────
"""

# ══════════════════════════════════════════════════════════════
# CELL 1 — SETUP
# ══════════════════════════════════════════════════════════════
"""
!pip install ultralytics roboflow --quiet

import torch
print(f"GPU available: {torch.cuda.is_available()}")
print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
"""

# ══════════════════════════════════════════════════════════════
# CELL 2 — DOWNLOAD DATASET FROM ROBOFLOW
# ══════════════════════════════════════════════════════════════
"""
from roboflow import Roboflow

rf      = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")
project = rf.workspace("YOUR_WORKSPACE").project("earthmender-ai")
version = project.version(1)
dataset = version.download("yolov8")

print(f"Dataset saved at: {dataset.location}")
"""

# ══════════════════════════════════════════════════════════════
# CELL 3 — VERIFY CLASS NAMES (CRITICAL — RUN BEFORE TRAINING)
# ══════════════════════════════════════════════════════════════
"""
# Confirms your Roboflow class names exactly match detector.py.
#
# Expected output:
# ['plastic_bottle', 'water_sachet', 'polythene_bag', 'disposable', 'waste_container']
#
# ── Fix these in Roboflow BEFORE exporting: ──────────────────
#   'diposable'     → rename to 'disposable'  (spelling error)
#   'Packed waste'  → delete if 0 annotations
#   'Plastic debris'→ delete if 0 annotations
#   Capital letters → rename to lowercase_with_underscore
# ─────────────────────────────────────────────────────────────

import yaml
with open(f"{dataset.location}/data.yaml") as f:
    data = yaml.safe_load(f)

print("Classes in your dataset:", data["names"])
print("Number of classes:",       data["nc"])

EXPECTED = ["plastic_bottle", "water_sachet", "polythene_bag",
            "disposable", "waste_container"]

if data["names"] == EXPECTED:
    print("✅ Class names match detector.py — safe to train.")
else:
    print("⚠️  Mismatch detected! Fix in Roboflow before training.")
    print("   Your classes:    ", data["names"])
    print("   Expected classes:", EXPECTED)
"""

# ══════════════════════════════════════════════════════════════
# CELL 4 — TRAINING (full hyperparameters)
# ══════════════════════════════════════════════════════════════
from ultralytics import YOLO

model = YOLO("yolov8n.pt")   # nano — fastest, lowest memory, best for MVP

results = model.train(
    data     = "data.yaml",
    epochs   = 60,
    imgsz    = 640,
    batch    = 16,            # reduce to 8 if Colab runs out of memory

    name     = "earthmender",
    patience = 15,            # early stop if no improvement after 15 epochs
    device   = 0,             # 0 = GPU
    project  = "runs/train",
    exist_ok = True,

    # ── Learning rate ──────────────────────────────────────────────────────
    # lr0  : initial learning rate — how fast weights update each step
    #        too high = unstable training, too low = very slow convergence
    # lrf  : final LR multiplier — LR decays to (lr0 × lrf) by end of training
    #        0.01 means it ends at 1% of starting rate — gradual, stable finish
    lr0      = 0.01,
    lrf      = 0.01,

    # ── Optimiser settings ─────────────────────────────────────────────────
    # momentum    : keeps updates moving in a consistent direction
    #               prevents the optimiser from zigzagging — 0.937 is standard
    # weight_decay: penalises very large weight values
    #               reduces overfitting — important on small datasets like ours
    # warmup_epochs: LR starts very low and ramps up over these first N epochs
    #               gives the model a stable start before full-speed learning
    momentum        = 0.937,
    weight_decay    = 0.0005,
    warmup_epochs   = 3.0,
    warmup_momentum = 0.8,

    # ── Augmentation ───────────────────────────────────────────────────────
    # These multiply the effective dataset size by generating variations.
    # Critical for real-world robustness across Nigerian environments.
    hsv_h    = 0.015,   # hue shift — lighting colour temperature variation
    hsv_s    = 0.7,     # saturation — shade, overcast sky, indoor light
    hsv_v    = 0.4,     # brightness — time of day, sun angle
    flipud   = 0.2,     # occasional vertical flip (bags can land any way)
    fliplr   = 0.5,     # horizontal flip — standard
    mosaic   = 1.0,     # combines 4 images — great for mixed waste scenes
    mixup    = 0.1,     # blends two images — adds variety
    scale    = 0.5,     # random scaling — different distances from waste
    translate= 0.1,     # random position shift
)

# ══════════════════════════════════════════════════════════════
# CELL 5 — VALIDATE + PER-CLASS BREAKDOWN
# ══════════════════════════════════════════════════════════════
"""
metrics = model.val()

print(f"\n✅ Training complete!")
print(f"   mAP50:    {metrics.box.map50:.3f}   (target: > 0.65)")
print(f"   mAP50-95: {metrics.box.map:.3f}")
print(f"\n── Per-class performance ──────────────────────────────")

CLASS_NAMES = ["plastic_bottle", "water_sachet", "polythene_bag",
               "disposable", "waste_container"]

for i, cls_name in enumerate(CLASS_NAMES):
    ap = metrics.box.maps[i] if i < len(metrics.box.maps) else 0.0
    status = "✅" if ap >= 0.50 else "⚠️  needs more images"
    print(f"   {status}  {cls_name}: {ap:.3f}")

print(f"\n📦 Best weights: runs/train/earthmender/weights/best.pt")
"""

# ══════════════════════════════════════════════════════════════
# CELL 6 — DOWNLOAD best.pt
# ══════════════════════════════════════════════════════════════
"""
from google.colab import files
files.download("runs/train/earthmender/weights/best.pt")

# Place best.pt in your project ROOT folder (same level as app.py)
"""

# ══════════════════════════════════════════════════════════════
# CELL 7 — QUICK TEST (optional, after download)
# ══════════════════════════════════════════════════════════════
"""
from ultralytics import YOLO
model   = YOLO("runs/train/earthmender/weights/best.pt")
results = model("path/to/test_image.jpg", conf=0.35)
results[0].show()
"""
