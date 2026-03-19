"""
EarthMender AI — Phase 1: Plastic Waste Detector
==================================================
YOLOv8-powered real-time object detection module.

Final 5-Class System:
    plastic_bottle  — All rigid plastic drink bottles (Eva, Pepsi, La Casera,
                      Voltic, Ragolis, Coke PET, energy drinks, water bottles)
    water_sachet    — Pure water nylon sachets (individual) AND outer nylon
                      bundles of sachets packed together
    polythene_bag   — ALL nylon bags — Shoprite bags, black polythene bags,
                      branded product sachets (Milo, Biscuit, chin-chin pouches),
                      bread nylons, market bags, any flexible plastic film
    disposable      — Single-use plastic disposables — cups, takeaway food packs,
                      styrofoam containers, plastic spoons, forks, plates
    waste_container — Dustbins, trash cans, large jerry cans, drums, skips

Install: pip install ultralytics opencv-python pillow
Test:    python phase1_detection/detector.py
"""

from ultralytics import YOLO
from PIL import Image
import numpy as np
import cv2
import os

# ─── CLASS CONFIGURATION ──────────────────────────────────────────────────────
# These labels MUST exactly match your Roboflow project class names.
PLASTIC_CLASSES = {
    0: "plastic_bottle",
    1: "water_sachet",
    2: "polythene_bag",
    3: "disposable",
    4: "waste_container",
}

CLASS_COLORS = {
    "plastic_bottle":  ( 76, 175,  80),   # Green
    "water_sachet":    ( 33, 150, 243),   # Blue
    "polythene_bag":   (255,  87,  34),   # Deep orange
    "disposable":      (156,  39, 176),   # Purple
    "waste_container": (121,  85,  72),   # Brown
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

# Severity weight per class — drives report severity scoring
# Higher weight = fewer items needed to trigger HIGH severity
CLASS_SEVERITY_WEIGHT = {
    "plastic_bottle":  1,
    "water_sachet":    1,
    "polythene_bag":   1,
    "disposable":      2,   # Takeaway waste spreads quickly
    "waste_container": 4,   # Full container = highest priority
}

MODEL_PATH = "best.pt"


class PlasticDetector:
    def __init__(self, model_path=MODEL_PATH, confidence=0.35):
        """
        Load YOLOv8 model.
        Args:
            model_path:  path to trained best.pt weights
            confidence:  minimum detection confidence (0.0–1.0)
        """
        self.confidence   = confidence
        if os.path.exists(model_path):
            print(f"✅ Loading custom model: {model_path}")
            self.model        = YOLO(model_path)
            self.model_loaded = True
        else:
            print("⚠️  Custom model not found. Loading YOLOv8n pretrained as placeholder.")
            print("   Train your model first — see phase1_detection/train.py")
            self.model        = YOLO("yolov8n.pt")
            self.model_loaded = False

    def detect_from_image(self, image: Image.Image):
        """
        Run detection on a PIL Image (upload or camera).
        Returns:
            annotated_image (PIL.Image)
            detections      (list of dicts)
        """
        img_array  = np.array(image)
        results    = self.model(img_array, conf=self.confidence, verbose=False, imgsz=320)[0]
        detections = self._parse_results(results)
        annotated  = self._draw_boxes(img_array.copy(), detections)
        return Image.fromarray(annotated), detections

    def detect_from_frame(self, frame: np.ndarray):
        """Run detection on a raw OpenCV frame (webcam)."""
        results    = self.model(frame, conf=self.confidence, verbose=False, imgsz=320)[0]
        detections = self._parse_results(results)
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
            detections.append({
                "class_id":        cls_id,
                "label":           label,
                "confidence":      round(confidence, 3),
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
            color  = CLASS_COLORS.get(label, (255, 255, 0))
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            text = f"{label.replace('_', ' ')} {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(img, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
            cv2.putText(img, text, (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        return img

    def summarise(self, detections: list):
        if not detections:
            return {"found": False, "count": 0, "types": [],
                    "message": "No plastic waste detected."}
        types = list({d["label"] for d in detections})
        return {
            "found":   True,
            "count":   len(detections),
            "types":   types,
            "message": (f"Detected {len(detections)} plastic waste item(s): "
                        f"{', '.join(t.replace('_', ' ').title() for t in types)}"),
        }


# ─── STANDALONE TEST ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    detector = PlasticDetector()
    test_img  = Image.new("RGB", (640, 480), color=(180, 200, 180))
    annotated, detections = detector.detect_from_image(test_img)
    print("Detections:", detections)
    print("Summary:",    detector.summarise(detections))
    print("✅ Detector module OK — final 5-class system loaded.")
    print("   Classes:", list(PLASTIC_CLASSES.values()))
