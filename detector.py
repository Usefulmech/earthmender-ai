"""
EarthMender AI — Phase 1: Plastic Waste Detector
==================================================
YOLOv8-powered detection — optimised for CPU deployment on Render.

Speed optimisations applied:
  - imgsz=320 (half the pixels, ~2x faster, negligible accuracy loss for large objects)
  - Model warmup on load (eliminates cold-start lag)
  - Input image capped at 800px before inference (reduces memory pressure)
  - Per-class confidence thresholds (water_sachet higher = fewer false positives)
  - NMS deduplication (removes overlapping boxes for same object)
  - Confidence band display: Certain / Likely / Possible

Final 5-Class System:
    plastic_bottle | water_sachet | polythene_bag | disposable | waste_container
"""

from ultralytics import YOLO
from PIL import Image
import numpy as np
import cv2
import os

# ─── CLASS CONFIGURATION ──────────────────────────────────────────────────────
PLASTIC_CLASSES = {
    0: "plastic_bottle",
    1: "water_sachet",
    2: "polythene_bag",
    3: "disposable",
    4: "waste_container",
}

CLASS_COLORS = {
    "plastic_bottle":  ( 76, 175,  80),
    "water_sachet":    ( 33, 150, 243),
    "polythene_bag":   (255,  87,  34),
    "disposable":      (156,  39, 176),
    "waste_container": (121,  85,  72),
}

DISPOSAL_TIPS = {
    "plastic_bottle":
        "Rinse and flatten before disposal. PET (#1) bottles like Eva and Pepsi "
        "are highly recyclable. Take to RecyclePoints kiosks — they pay cash or airtime.",
    "water_sachet":
        "Collect 20+ sachets before taking to a recycler — payment is per kg. "
        "Keep them dry and clean. RecyclePoints kiosks are at many Lagos filling stations.",
    "polythene_bag":
        "Do NOT burn — toxic fumes cause serious lung damage. Collect clean, dry "
        "nylons in a separate bag. Wecyclers and RecyclePoints accept them for cash.",
    "disposable":
        "Takeaway packs and cups are hard to recycle when food-contaminated. "
        "Rinse if possible, then take to your PSP collector. Avoid single-use "
        "disposables where possible — carry a reusable cup.",
    "waste_container":
        "Ensure the container is sealed to prevent leaching. Report to LAWMA/PSP "
        "for scheduled collection. Large metal jerry cans have scrap value — "
        "contact a local Ọlọbẹ scrap dealer.",
}

CLASS_SEVERITY_WEIGHT = {
    "plastic_bottle":  1,
    "water_sachet":    1,
    "polythene_bag":   1,
    "disposable":      2,
    "waste_container": 4,
}

# ── Per-class confidence thresholds ───────────────────────────────────────────
# water_sachet is our weakest class (mAP50 0.463) so we require higher
# confidence to reduce false positives for that class specifically
PER_CLASS_CONF = {
    "plastic_bottle":  0.38,
    "water_sachet":    0.50,   # higher — weak class, avoid false positives
    "polythene_bag":   0.38,
    "disposable":      0.40,
    "waste_container": 0.38,
}

# ── Confidence band labels ────────────────────────────────────────────────────
def confidence_band(conf: float) -> tuple:
    """Returns (label, color) for confidence display."""
    if conf >= 0.75:
        return "Certain",  "#1a7a4a"
    elif conf >= 0.55:
        return "Likely",   "#ff9800"
    else:
        return "Possible", "#9e9e9e"

# ── Image quality check ───────────────────────────────────────────────────────
def check_image_quality(img_array: np.ndarray) -> dict:
    """
    Basic image quality assessment — tells user if image is too blurry or dark.
    Returns dict with quality score and message.
    """
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Blurriness — Laplacian variance (higher = sharper)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Brightness — mean pixel value
    brightness = np.mean(gray)

    issues = []
    if blur_score < 50:
        issues.append("image is blurry — move closer or hold camera steady")
    if brightness < 40:
        issues.append("image is too dark — find better lighting")
    if brightness > 230:
        issues.append("image is overexposed — avoid pointing at bright light")

    quality = "good" if not issues else "poor"
    return {
        "quality":    quality,
        "blur":       round(blur_score, 1),
        "brightness": round(brightness, 1),
        "issues":     issues,
        "message":    f"Image quality: {quality.title()}. " + (
            "Detection may be unreliable — " + "; ".join(issues) + "."
            if issues else "Good lighting and focus detected."
        )
    }

# ── Pre-process: cap image at 800px longest side ──────────────────────────────
def _resize_for_inference(image: Image.Image) -> Image.Image:
    """
    Caps image at 800px on the longest side before inference.
    Reduces memory pressure on Render's 512MB RAM.
    """
    MAX_SIDE = 800
    w, h = image.size
    if max(w, h) <= MAX_SIDE:
        return image
    if w >= h:
        new_w = MAX_SIDE
        new_h = int(h * MAX_SIDE / w)
    else:
        new_h = MAX_SIDE
        new_w = int(w * MAX_SIDE / h)
    return image.resize((new_w, new_h), Image.LANCZOS)

# ── NMS deduplication ─────────────────────────────────────────────────────────
def _deduplicate(detections: list, iou_threshold: float = 0.5) -> list:
    """
    Removes overlapping bounding boxes for the same class.
    Keeps the higher-confidence detection when two boxes overlap > iou_threshold.
    """
    if len(detections) <= 1:
        return detections

    # Sort by confidence descending
    detections = sorted(detections, key=lambda x: -x["confidence"])
    keep = []

    for det in detections:
        dominated = False
        for kept in keep:
            if kept["label"] != det["label"]:
                continue
            iou = _compute_iou(det["bbox"], kept["bbox"])
            if iou > iou_threshold:
                dominated = True
                break
        if not dominated:
            keep.append(det)

    return keep

def _compute_iou(box1: list, box2: list) -> float:
    """Intersection over Union for two [x1,y1,x2,y2] boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0

    area1 = (box1[2]-box1[0]) * (box1[3]-box1[1])
    area2 = (box2[2]-box2[0]) * (box2[3]-box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


MODEL_PATH = "best.pt"


class PlasticDetector:
    def __init__(self, model_path=MODEL_PATH, confidence=0.35):
        self.base_confidence = confidence

        if os.path.exists(model_path):
            print(f"✅ Loading custom model: {model_path}")
            self.model        = YOLO(model_path)
            self.model_loaded = True
        else:
            print("⚠️  Custom model not found — loading YOLOv8n placeholder.")
            self.model        = YOLO("yolov8n.pt")
            self.model_loaded = False

        # ── Warmup: one dummy inference to pre-allocate memory ────────────────
        # This eliminates the 10–15s cold-start lag on Render
        print("🔥 Warming up model...")
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        try:
            self.model(dummy, conf=0.5, verbose=False, imgsz=320)
            print("✅ Model warmup complete")
        except Exception as e:
            print(f"⚠️  Warmup failed (non-critical): {e}")

    def detect_from_image(self, image: Image.Image):
        """
        Run detection on a PIL Image.
        Returns: (annotated_image, detections, quality_report)
        """
        # Step 1 — quality check on original
        img_array    = np.array(image)
        quality      = check_image_quality(img_array)

        # Step 2 — resize for inference speed
        small_image  = _resize_for_inference(image)
        small_array  = np.array(small_image)

        # Step 3 — run YOLO at 320px (2x faster than 640)
        results      = self.model(
            small_array, conf=self.base_confidence,
            verbose=False, imgsz=320
        )[0]

        # Step 4 — parse, apply per-class thresholds, deduplicate
        detections   = self._parse_results(results)
        detections   = [
            d for d in detections
            if d["confidence"] >= PER_CLASS_CONF.get(d["label"], 0.38)
        ]
        detections   = _deduplicate(detections)

        # Step 5 — draw boxes on original-size image
        annotated    = self._draw_boxes(img_array.copy(), detections)

        return Image.fromarray(annotated), detections, quality

    def detect_from_frame(self, frame: np.ndarray):
        """Run detection on raw OpenCV frame."""
        results    = self.model(frame, conf=self.base_confidence,
                                verbose=False, imgsz=320)[0]
        detections = self._parse_results(results)
        detections = [
            d for d in detections
            if d["confidence"] >= PER_CLASS_CONF.get(d["label"], 0.38)
        ]
        detections = _deduplicate(detections)
        annotated  = self._draw_boxes(frame.copy(), detections)
        return annotated, detections

    def _parse_results(self, results):
        detections = []
        if results.boxes is None:
            return detections
        for box in results.boxes:
            cls_id     = int(box.cls[0])
            confidence = float(box.conf[0])
            label      = PLASTIC_CLASSES.get(cls_id, f"class_{cls_id}")
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            band, _    = confidence_band(confidence)
            detections.append({
                "class_id":        cls_id,
                "label":           label,
                "confidence":      round(confidence, 3),
                "confidence_band": band,
                "bbox":            [x1, y1, x2, y2],
                "tip":             DISPOSAL_TIPS.get(label, "Dispose responsibly."),
                "severity_weight": CLASS_SEVERITY_WEIGHT.get(label, 1),
            })
        return detections

    def _draw_boxes(self, img: np.ndarray, detections: list):
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            label  = det["label"]
            conf   = det["confidence"]
            band   = det["confidence_band"]
            color  = CLASS_COLORS.get(label, (255, 255, 0))

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            # Label with confidence band
            text = f"{label.replace('_',' ')} {conf:.0%} ({band})"
            (tw, th), _ = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 2)
            cv2.rectangle(
                img, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
            cv2.putText(
                img, text, (x1 + 3, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2)
        return img

    def summarise(self, detections: list):
        if not detections:
            return {"found": False, "count": 0, "types": [],
                    "message": "No plastic waste detected."}
        types = list({d["label"] for d in detections})
        certain = sum(1 for d in detections if d["confidence_band"] == "Certain")
        return {
            "found":   True,
            "count":   len(detections),
            "types":   types,
            "certain": certain,
            "message": (
                f"Detected {len(detections)} plastic waste item(s): "
                f"{', '.join(t.replace('_',' ').title() for t in types)}. "
                f"{certain} high-confidence detection(s)."
            ),
        }


if __name__ == "__main__":
    detector = PlasticDetector()
    test_img  = Image.new("RGB", (640, 480), color=(180, 200, 180))
    annotated, detections, quality = detector.detect_from_image(test_img)
    print("Quality:", quality)
    print("Detections:", detections)
    print("✅ Detector OK — speed-optimised 5-class system loaded.")
