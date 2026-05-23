"""
Mom's 50th Birthday Invite — Backend Server v2
Beautiful invite card generation using OpenCV only.
Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os, math, base64, json
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="Birthday Invite API v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Paths ───────────────────────────────────────────────────────────────────

BASE_DIR      = Path(__file__).parent
KNOWN_DIR     = BASE_DIR / "known_faces"
CARDS_DIR     = BASE_DIR / "generated_cards"
TEMPLATE_PATH = BASE_DIR / "templates" / "invite_template.png"

KNOWN_DIR.mkdir(exist_ok=True)
CARDS_DIR.mkdir(exist_ok=True)

# ─── Face recognizer ─────────────────────────────────────────────────────────

recognizer   = None
label_map    = {}
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def preprocess_face(gray_img, x, y, w, h):
    """
    Extract + normalise a face ROI consistently for both training and prediction.
    Histogram equalisation compensates for lighting differences between
    a static reference photo and a live webcam selfie.
    """
    # Add a small margin so we don't crop right at the face edge
    margin = int(min(w, h) * 0.10)
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(gray_img.shape[1], x + w + margin)
    y2 = min(gray_img.shape[0], y + h + margin)

    roi = gray_img[y1:y2, x1:x2]
    roi = cv2.resize(roi, (200, 200))
    roi = cv2.equalizeHist(roi)          # normalise brightness/contrast
    return roi


def detect_largest_face(gray_img):
    """
    Run Haar cascade and return (x,y,w,h) of the largest face, or None.
    Identical parameters used in BOTH training and prediction so the
    model sees consistently preprocessed faces.
    """
    detected = face_cascade.detectMultiScale(
        gray_img,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(80, 80),
    )
    if len(detected) == 0:
        return None
    return max(detected, key=lambda r: r[2] * r[3])


def train_recognizer():
    global recognizer, label_map
    label_map = {}
    faces, labels = [], []
    label_id = 0

    for person_dir in sorted(KNOWN_DIR.iterdir()):
        if not person_dir.is_dir():
            continue
        name = person_dir.name
        label_map[label_id] = name
        face_count = 0
        print(f"  ↳ Loading '{name}' → label {label_id}")

        for img_path in sorted(person_dir.glob("*")):
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                print(f"    ⚠ Could not read {img_path.name}, skipping")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            face = detect_largest_face(gray)

            if face is None:
                print(f"    ⚠ No face detected in {img_path.name}, skipping")
                continue

            x, y, w, h = face
            roi = preprocess_face(gray, x, y, w, h)
            faces.append(roi)
            labels.append(label_id)
            face_count += 1

            # Data augmentation: add a horizontally-flipped copy
            # This doubles training data and makes the model more robust
            faces.append(cv2.flip(roi, 1))
            labels.append(label_id)

        print(f"    → {face_count} photo(s) loaded ({face_count*2} samples with flip)")
        label_id += 1

    if not faces:
        print("⚠ No training data found. Add photos to known_faces/ folders.")
        return False

    # LBPH with tighter parameters — more discriminative for small datasets
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1,        # smaller radius = finer texture detail
        neighbors=8,
        grid_x=8,
        grid_y=8,
        threshold=10000  # disable internal threshold — we apply our own below
    )
    recognizer.train(faces, np.array(labels))
    print(f"✅ Trained on {len(faces)} samples across {label_id} person(s).")
    return True


@app.on_event("startup")
def startup():
    print("🎂 Birthday Invite Server starting…")
    train_recognizer()


# ─── Beautiful Invite Card Generator ─────────────────────────────────────────

def hex_to_bgr(h):
    h = h.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return (b, g, r)

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))

def draw_text_centered(img, text, cx, cy, font, scale, color, thickness=2, line_type=cv2.LINE_AA):
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x = cx - tw // 2
    y = cy + th // 2
    cv2.putText(img, text, (x, y), font, scale, color, thickness, line_type)
    return th + baseline

def draw_text_shadow(img, text, cx, cy, font, scale, color, shadow_color, thickness=2):
    # Shadow
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x = cx - tw // 2
    y = cy + th // 2
    cv2.putText(img, text, (x+3, y+3), font, scale, shadow_color, thickness+1, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)

def draw_gradient_rect(img, x1, y1, x2, y2, c1, c2, vertical=True):
    for i in range(y1 if vertical else x1, y2 if vertical else x2):
        t = (i - (y1 if vertical else x1)) / max(1, (y2-y1 if vertical else x2-x1))
        c = lerp_color(c1, c2, t)
        if vertical:
            cv2.line(img, (x1, i), (x2, i), c, 1)
        else:
            cv2.line(img, (i, y1), (i, y2), c, 1)

def draw_circle_pattern(img, cx, cy, n_rings, base_color, alpha=0.25):
    overlay = img.copy()
    for i in range(n_rings, 0, -1):
        radius = i * 60
        color  = tuple(min(255, int(c*1.2)) for c in base_color)
        cv2.circle(overlay, (cx, cy), radius, color, 1)
    cv2.addWeighted(overlay, alpha, img, 1-alpha, 0, img)

def draw_star(img, cx, cy, r_outer, r_inner, n, color, thickness=-1):
    pts = []
    for i in range(n*2):
        angle = math.pi/2 + i * math.pi/n
        r     = r_outer if i%2==0 else r_inner
        pts.append([int(cx + r*math.cos(angle)), int(cy + r*math.sin(angle))])
    cv2.fillPoly(img, [np.array(pts)], color)

def draw_ornate_border(img, W, H, color_gold, color_rose):
    """Multi-layered ornate border with corner flourishes."""
    # Outer border
    cv2.rectangle(img, (12,12), (W-12,H-12), color_gold, 2)
    cv2.rectangle(img, (20,20), (W-20,H-20), color_rose, 1)
    cv2.rectangle(img, (28,28), (W-28,H-28), color_gold, 1)

    # Corner diamond clusters
    corners = [(40,40),(W-40,40),(40,H-40),(W-40,H-40)]
    for cx,cy in corners:
        # Large diamond
        pts = np.array([[cx,cy-18],[cx+14,cy],[cx,cy+18],[cx-14,cy]])
        cv2.fillPoly(img, [pts], color_gold)
        # Small diamond
        pts2 = np.array([[cx,cy-9],[cx+7,cy],[cx,cy+9],[cx-7,cy]])
        cv2.fillPoly(img, [pts2], hex_to_bgr("#1a0814"))
        # Dot center
        cv2.circle(img, (cx,cy), 3, color_gold, -1)

        # Extended corner lines
        dir_x = 1 if cx < W//2 else -1
        dir_y = 1 if cy < H//2 else -1
        cv2.line(img,(cx,cy),(cx+dir_x*60,cy),color_gold,1)
        cv2.line(img,(cx,cy),(cx,cy+dir_y*60),color_gold,1)

    # Mid-edge accents
    for mx,my in [(W//2,15),(W//2,H-15),(15,H//2),(W-15,H//2)]:
        draw_star(img, mx, my, 8, 4, 4, color_gold)

def generate_invite_card(name: str) -> str:
    W, H = 1400, 980

    # ── Base background (deep rose-to-dark gradient) ──────────────────────
    card = np.zeros((H, W, 3), dtype=np.uint8)
    c1   = hex_to_bgr("#160610")   # very dark
    c2   = hex_to_bgr("#3d0e28")   # deep rose
    c3   = hex_to_bgr("#1a0814")   # mid dark
    draw_gradient_rect(card, 0, 0, W, H//2, c1, c2)
    draw_gradient_rect(card, 0, H//2, W, H, c2, c3)

    # ── Radial glow overlays ─────────────────────────────────────────────
    overlay = card.copy()
    # Centre gold glow
    cv2.circle(overlay, (W//2, H//2), 420, hex_to_bgr("#3d1a05"), -1)
    cv2.addWeighted(overlay, 0.35, card, 0.65, 0, card)
    overlay = card.copy()
    # Top-left rose glow
    cv2.circle(overlay, (0, 0), 500, hex_to_bgr("#5c0a2a"), -1)
    cv2.addWeighted(overlay, 0.25, card, 0.75, 0, card)
    # Bottom-right magenta glow
    overlay = card.copy()
    cv2.circle(overlay, (W, H), 480, hex_to_bgr("#400a38"), -1)
    cv2.addWeighted(overlay, 0.22, card, 0.78, 0, card)

    GOLD  = hex_to_bgr("#e8c46a")
    GOLD2 = hex_to_bgr("#f8e4a0")
    GOLD3 = hex_to_bgr("#c9973a")
    ROSE  = hex_to_bgr("#c0395a")
    ROSE2 = hex_to_bgr("#e8607a")
    WHITE = hex_to_bgr("#fff8ee")
    CREAM = hex_to_bgr("#f5ead8")
    SHAD  = hex_to_bgr("#0a0005")

    # ── Concentric circle pattern (centre) ───────────────────────────────
    for r_mult in range(1, 9):
        alpha = 0.07 if r_mult % 2 == 0 else 0.04
        ov = card.copy()
        cv2.circle(ov, (W//2, H//2), r_mult*70, GOLD3, 1)
        cv2.addWeighted(ov, alpha, card, 1-alpha, 0, card)

    # ── Decorative diagonal lines ─────────────────────────────────────────
    for i in range(0, W+H, 120):
        ov = card.copy()
        cv2.line(ov, (i, 0), (i-H, H), GOLD3, 1)
        cv2.addWeighted(ov, 0.04, card, 0.96, 0, card)

    # ── Stars / sparkles scattered ────────────────────────────────────────
    rng = np.random.default_rng(42)
    for _ in range(22):
        sx = int(rng.integers(60, W-60))
        sy = int(rng.integers(60, H-60))
        sr = int(rng.integers(4, 12))
        draw_star(card, sx, sy, sr, sr//2, 4,
                  GOLD if rng.random()>0.4 else ROSE2)
    for _ in range(14):
        sx = int(rng.integers(80, W-80))
        sy = int(rng.integers(80, H-80))
        cv2.circle(card, (sx, sy), int(rng.integers(1,4)), GOLD2, -1)

    # ── Ornate border ────────────────────────────────────────────────────
    draw_ornate_border(card, W, H, GOLD, ROSE)

    # ── Top decorative rosette band ──────────────────────────────────────
    for x in range(50, W-50, 55):
        draw_star(card, x, 72, 10, 5, 8, GOLD3)
    cv2.line(card, (50,90),(W-50,90), GOLD3, 1)

    # ── Bottom decorative band ────────────────────────────────────────────
    cv2.line(card, (50,H-90),(W-50,H-90), GOLD3, 1)
    for x in range(50, W-50, 55):
        draw_star(card, x, H-72, 10, 5, 8, GOLD3)

    # ── HEADER: "You Are Invited To Celebrate" ────────────────────────────
    f    = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX   # elegant script-like font
    fup  = cv2.FONT_HERSHEY_DUPLEX
    fsi  = cv2.FONT_HERSHEY_SIMPLEX

    draw_text_shadow(card, "~ You Are Invited To Celebrate ~",
                     W//2, 148, fup, 0.95, CREAM, SHAD, thickness=1)

    # ── "Savitri's" in italic script style ───────────────────────────────
    draw_text_shadow(card, "Savitri's",
                     W//2, 230, f, 2.2, CREAM, SHAD, thickness=2)

    # ── BIG "FABULOUS" ────────────────────────────────────────────────────
    big_text = "FABULOUS"
    (tw, th), _ = cv2.getTextSize(big_text, fup, 4.5, 6)
    bx = W//2 - tw//2
    # Gradient effect: draw in 3 offset colours
    cv2.putText(card, big_text, (bx+4, 354), fup, 4.5, GOLD3, 8, cv2.LINE_AA)
    cv2.putText(card, big_text, (bx+2, 352), fup, 4.5, GOLD,  7, cv2.LINE_AA)
    cv2.putText(card, big_text, (bx,   350), fup, 4.5, GOLD2, 6, cv2.LINE_AA)

    # ── Giant "50" ────────────────────────────────────────────────────────
    fifty_text = "50"
    (tw50, _), _ = cv2.getTextSize(fifty_text, fup, 7.0, 10)
    bx50 = W//2 - tw50//2
    cv2.putText(card, fifty_text, (bx50+5, 490), fup, 7.0, ROSE,  12, cv2.LINE_AA)
    cv2.putText(card, fifty_text, (bx50+2, 487), fup, 7.0, ROSE2, 11, cv2.LINE_AA)
    cv2.putText(card, fifty_text, (bx50,   485), fup, 7.0, WHITE, 10, cv2.LINE_AA)

    # Superscript "th"
    cv2.putText(card, "th", (W//2 + tw50//2 + 8, 430), fup, 1.6, CREAM, 2, cv2.LINE_AA)

    # ── "Birthday" ────────────────────────────────────────────────────────
    birth_text = "B  I  R  T  H  D  A  Y"
    draw_text_shadow(card, birth_text, W//2, 565, fup, 1.7, GOLD, SHAD, thickness=2)

    # ── Ornate horizontal divider ─────────────────────────────────────────
    dy = 610
    cv2.line(card, (100,dy),(W-100,dy), GOLD3, 1)
    draw_star(card, W//2, dy, 14, 7, 8, GOLD)
    draw_star(card, W//2-120, dy, 8, 4, 8, GOLD3)
    draw_star(card, W//2+120, dy, 8, 4, 8, GOLD3)
    cv2.circle(card, (W//2-240,dy), 4, GOLD3, -1)
    cv2.circle(card, (W//2+240,dy), 4, GOLD3, -1)

    # ── "Dear {Name}," ───────────────────────────────────────────────────
    dear_text  = f"Dear {name},"
    draw_text_shadow(card, dear_text, W//2, 680, f, 2.2, GOLD2, SHAD, thickness=2)

    # ── Sub-message ───────────────────────────────────────────────────────
    msg1 = "Your presence would make this celebration truly complete."
    msg2 = "30th May | 6 PM | Club House, Serenity - With love, The Patil Family"
    draw_text_shadow(card, msg1, W//2, 750, fup, 0.80, CREAM, SHAD, thickness=1)
    draw_text_shadow(card, msg2, W//2, 800, fup, 0.72, CREAM, SHAD, thickness=1)

    # ── Bottom confetti emoji decoration ──────────────────────────────────
    confetti_chars = ["*", "+", "x", "o", "*", "+", "o", "x", "+", "*"]
    colors_conf    = [GOLD, ROSE2, GOLD2, ROSE, GOLD3, GOLD, ROSE2, GOLD2, ROSE, GOLD3]
    for i, (ch, col) in enumerate(zip(confetti_chars, colors_conf)):
        x = 80 + i * 130
        y = H - 118
        cv2.putText(card, ch, (x, y), fsi, 1.2, col, 2, cv2.LINE_AA)

    # ── Subtle vignette ──────────────────────────────────────────────────
    vig = np.zeros((H, W), dtype=np.float32)
    for y_v in range(H):
        for x_v in range(0, W, 4):
            dx_v = (x_v - W/2)/(W/2)
            dy_v = (y_v - H/2)/(H/2)
            vig[y_v, x_v:x_v+4] = 1 - 0.45*(dx_v**2 + dy_v**2)
    vig = np.clip(vig, 0.55, 1.0)
    vig_3ch = cv2.merge([vig, vig, vig])
    card = (card.astype(np.float32) * vig_3ch).astype(np.uint8)

    # ── Save ──────────────────────────────────────────────────────────────
    safe  = "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ","_")
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    path  = CARDS_DIR / f"invite_{safe}_{ts}.png"
    cv2.imwrite(str(path), card, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    print(f"  🎨 Card generated → {path.name}")
    return str(path)


# ─── API Routes ──────────────────────────────────────────────────────────────

class SelfiePayload(BaseModel):
    image: str   # data:image/jpeg;base64,...

@app.post("/api/recognize")
def recognize(payload: SelfiePayload):
    # ── Decode image ─────────────────────────────────────────────────────────
    try:
        header, encoded = (payload.image.split(",", 1) if "," in payload.image
                           else ("", payload.image))
        raw = base64.b64decode(encoded)
        arr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception as e:
        raise HTTPException(400, f"Invalid image: {e}")

    if img is None:
        raise HTTPException(400, "Could not decode image.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Detect face ───────────────────────────────────────────────────────────
    face = detect_largest_face(gray)

    if face is None:
        print("  ℹ No face detected in selfie.")
        path = generate_invite_card("Guest")
        return {"name": "Guest", "confidence": 0, "matched": False,
                "message": "No face detected — move closer and ensure good lighting.",
                "card_url": f"/cards/{Path(path).name}"}

    # ── Preprocess — SAME pipeline as training ────────────────────────────────
    x, y, w, h = face
    face_roi = preprocess_face(gray, x, y, w, h)

    # ── Recognise ─────────────────────────────────────────────────────────────
    if recognizer is None or not label_map:
        path = generate_invite_card("Guest")
        return {"name": "Guest", "confidence": 0, "matched": False,
                "message": "Recognizer not trained yet.",
                "card_url": f"/cards/{Path(path).name}"}

    label, confidence = recognizer.predict(face_roi)

    # ── LBPH confidence: 0 = perfect match, higher = worse ───────────────────
    # With 1-2 photos per person and histogram equalisation:
    #   < 45  → very confident match
    #   45-65 → likely match  (use this range as threshold)
    #   > 65  → too uncertain → show as Guest
    #
    # Print the raw score so YOU can tune this for your family's photos.
    # Check your terminal while testing to see what scores come out.
    THRESHOLD = 65

    matched = confidence < THRESHOLD
    name    = label_map.get(label, "Guest") if matched else "Guest"

    print(f"  🔍 Predict → label={label} ({label_map.get(label,'?')})  "
          f"confidence={confidence:.1f}  threshold={THRESHOLD}  matched={matched}")

    path = generate_invite_card(name)
    return {
        "name":       name,
        "confidence": round(float(confidence), 2),
        "matched":    matched,
        "message":    f"Your personalised invitation is ready, {name}! 🎉" if matched
                      else "Welcome! A guest invite has been prepared for you.",
        "card_url":   f"/cards/{Path(path).name}",
    }


@app.get("/api/debug-scores")
def debug_scores(image_path: str = ""):
    """
    Handy endpoint: POST any base64 image to /api/recognize and watch
    the terminal — it prints the raw confidence score for every prediction.
    Use those scores to tune THRESHOLD above.
    """
    return {
        "tip": "Watch your terminal when someone takes a selfie. "
               "It prints: label, name, confidence score, threshold, matched. "
               "If known family members score > 65, lower THRESHOLD. "
               "If strangers score < 65, raise THRESHOLD.",
        "current_people": list(label_map.values()),
        "threshold_in_use": 65,
    }


@app.post("/api/retrain")
def retrain():
    ok = train_recognizer()
    return {"success": ok, "people": list(label_map.values())}


@app.get("/api/people")
def list_people():
    return {"people": [d.name for d in KNOWN_DIR.iterdir() if d.is_dir()]}


app.mount("/cards", StaticFiles(directory=str(CARDS_DIR)), name="cards")
app.mount("/", StaticFiles(directory=str(BASE_DIR.parent/"frontend"), html=True), name="frontend")