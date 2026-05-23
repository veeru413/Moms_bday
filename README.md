# 🎂 Mom's 50th Birthday — Smart Invite System
> Face recognition using OpenCV only — no cloud AI, no paid APIs.

---

## Project Structure

```
birthday-invite/
│
├── backend/
│   ├── main.py                ← FastAPI server (face recognition + card generation)
│   ├── requirements.txt       ← Python dependencies
│   ├── add_person.py          ← Helper to add family members
│   │
│   ├── known_faces/           ← ⬅ PUT FAMILY PHOTOS HERE
│   │   ├── Priya/
│   │   │   ├── photo_1.jpg
│   │   │   └── photo_2.jpg
│   │   ├── Rahul/
│   │   │   └── photo_1.jpg
│   │   └── ... (one folder per person)
│   │
│   ├── templates/
│   │   └── invite_template.png   ← ⬅ YOUR INVITE BACKGROUND IMAGE (optional)
│   │
│   └── generated_cards/       ← output cards are saved here automatically
│
└── frontend/
    ├── index.html             ← The invite website
    └── static/
        ├── css/style.css
        └── js/app.js
```

---

## Step-by-Step Setup

### Step 1 — Install Python (if not already installed)

Download Python 3.11+ from https://python.org
Make sure to check "Add Python to PATH" during installation.

Verify:
```bash
python --version
# should print Python 3.11.x or newer
```

---

### Step 2 — Create a virtual environment

Open a terminal/command prompt inside the `birthday-invite/` folder:

```bash
cd birthday-invite/backend

# Create virtual environment
python -m venv venv

# Activate it:
# Windows:
venv\Scripts\activate
# Mac / Linux:
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, OpenCV (with face recognizer), and Uvicorn.
Takes 2-4 minutes on first run.

---

### Step 4 — Add family photos

Inside `backend/known_faces/`, create one folder per person.
The folder name IS the person's name shown on the card.

```
known_faces/
  Priya/
    photo_1.jpg     ← clear face photo, well-lit
    photo_2.jpg     ← optional second photo (more = better accuracy)
  Rahul/
    photo_1.jpg
  Ananya/
    photo_1.jpg
    photo_2.jpg
```

**Photo tips for best accuracy:**
- Use clear, well-lit photos (not blurry or dark)
- Face should be roughly forward-facing
- Photo should be at least 200×200 pixels
- JPEG or PNG both work
- 1 photo works, 2-3 photos is significantly better
- Avoid sunglasses, heavy filters, or extreme angles

**Alternative — use the helper script:**
```bash
python add_person.py "Priya" /path/to/priya1.jpg /path/to/priya2.jpg
```

---

### Step 5 — (Optional) Add your invite template image

Put your invite background image at:
```
backend/templates/invite_template.png
```

This should be a 1200×900 PNG of your designed invite card — WITHOUT any name on it.
The system will overlay the guest's name on top automatically.

If you don't add a template, the system generates a built-in dark techy card.

---

### Step 6 — Start the backend server

```bash
# Make sure you're in backend/ with venv activated
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO: Started retraining…
✅ Trained on 4 face(s) across 3 person(s).
INFO: Uvicorn running on http://0.0.0.0:8000
```

Leave this terminal running.

---

### Step 7 — Open the invite website

Open a browser and go to:
```
http://localhost:8000
```

You will see the techy invite landing page.

---

### Step 8 — Test it

1. Click "INITIATE SCAN"
2. Allow camera access when the browser asks
3. Position your face in the frame
4. Click "CAPTURE & IDENTIFY"
5. Watch the processing animation
6. See your personalised invite card!

---

### Step 9 — Share with family

**Option A — Local network (simplest)**
If family is on the same Wi-Fi, share your computer's local IP:
```bash
# Find your IP:
# Windows: ipconfig
# Mac/Linux: ifconfig or ip addr
```
Then they open: `http://192.168.1.xxx:8000`
Also update API_BASE in `frontend/static/js/app.js` to this IP.

**Option B — Internet (proper sharing)**
Use ngrok for a temporary public URL (free):
```bash
# Install ngrok from https://ngrok.com
ngrok http 8000
# Gives you: https://abc123.ngrok.io
```
Update `API_BASE` in `frontend/static/js/app.js` to your ngrok URL.

---

## Adding people after the server is running

```bash
python add_person.py "Kavya" /path/to/kavya.jpg
```

Or manually copy photos into `known_faces/Kavya/` and call:
```
POST http://localhost:8000/api/retrain
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "No face detected" | Better lighting, face the camera directly |
| Wrong person identified | Add 1-2 more reference photos for that person |
| Camera not working | Check browser permissions (click the lock icon in address bar) |
| Server won't start | Make sure venv is activated and requirements are installed |
| OpenCV install fails on Windows | Try: `pip install opencv-contrib-python --pre` |
| Low confidence / wrong match | Lower THRESHOLD in main.py from 80 to 70 for stricter matching |

---

## API Reference (for debugging)

```
GET  /api/people       → list all registered family members
POST /api/retrain      → retrain after adding new photos
POST /api/recognize    → send { "image": "data:image/jpeg;base64,..." }
GET  /cards/<filename> → fetch a generated invite card image
```

---

## Confidence Score Guide

The LBPH recognizer returns a confidence where **lower = better match**:
- 0–40:  Very high confidence match
- 40–70: Good match
- 70–80: Borderline (might be correct)
- 80+:   Low confidence → shows "Guest" invite

Tune the `THRESHOLD` in `main.py` line ~130 based on your results.
