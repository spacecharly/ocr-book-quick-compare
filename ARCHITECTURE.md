# Architecture — Book Digitizer Suite

## Overview

**Book Digitizer Suite** is a complete end-to-end solution for book digitization and OCR text validation. It consists of three main components that collaborate to create a comprehensive workflow:

1. **OCR Web Application** (`app.py`) – Main interface for editing and validating OCR text
2. **Web Capture Application** (`capture.html` + `capture_app.js`) – Image capture directly from the browser
3. **Desktop Capture (optional)** (`capture-app/main.py`) – Desktop prototype for specialized cases

## General Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Book Digitizer Suite                           │
└─────────────────────────────────────────────────────────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 │               │               │
        ┌────────▼────────┐  ┌───▼────────┐  ┌──▼──────┐
        │  OCR Web App    │  │ Capture    │  │ Desktop │
        │  (Flask)        │  │ App (Web)  │  │ Capture │
        │ app.py          │  │            │  │ (Tk)    │
        └─────────────────┘  └────────────┘  └─────────┘
                 │                │                │
                 └────────────────┼────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   Shared Working Folder    │
                    │   (/images)                │
                    │  - Raw images              │
                    │  - OCR text files (.txt)   │
                    │  - Validated (check-done/) │
                    └────────────────────────────┘
```

## Detailed Components

### 1. OCR Web Application (`app.py`)

**Language:** Python 3.9+  
**Framework:** Flask  
**Default port:** 5000 (or 5001)  

#### Main Responsibilities:
- Management of the web interface for viewing/editing OCR texts
- OCR pipeline orchestration (PaddleOCR)
- Page validation and file relocation
- Multilingual support (FR, EN, IT, DE)

#### Flask Routes

| Route | Method | Function |
|-------|--------|----------|
| `/` | GET | Main page (page list, selection) |
| `/create-missing-texts` | POST | Creates missing `.txt` files |
| `/upload-images` | POST | Image import (with optional OCR) |
| `/run-ocr` | POST | Runs PaddleOCR on current page |
| `/save` | POST | Saves edited text |
| `/validate` | POST | Validates and archives page to `check-done/` |
| `/validate-and-next` | POST | Validates + saves + moves to next page |
| `/autosave` | POST | Auto-save (JSON, every 1.5s) |
| `/undo-validation` | POST | Undoes last validation |
| `/rename-current` | POST | Renames image and paired text file |
| `/delete-current` | POST | Deletes image and paired text file |
| `/export-texts` | GET | Exports all `.txt` files as ZIP |
| `/set-working-folder` | POST | Changes working folder |
| `/pick-working-folder` | GET | Opens macOS Finder dialog |
| `/capture` | GET | Web Capture App interface |
| `/capture-save-images` | POST | Receives captured images |
| `/capture-voice-detect` | POST | Processes audio for voice trigger detection |
| `/page-image/<filename>` | GET | Serves project images |

#### Data Structures

**`ViewState`** – User session state:
```python
@dataclass
class ViewState:
    selected_name: str          # Currently selected image
    query: str                  # Search filter
    sort_key: str              # Sort (oldest, newest, name_asc, name_desc, text_length_desc)
    text_filter: str           # Text filter (all, empty, filled)
    thumbnail_page: int        # Thumbnail pagination
    lang: str                  # UI language (fr, en, it, de)
    ocr_lang: str             # OCR language (can differ from UI)
    spellcheck_enabled: bool   # Post-OCR spell correction
    downsize_enabled: bool     # Post-validation compression
    downsize_kb: int          # Compression target size
```

**`PairRecord`** – Image + text pair:
```python
@dataclass
class PairRecord:
    image_path: Path           # Path to image
    text_path: Path           # Path to .txt file
    text_content: str         # Text content
    image_mtime: float        # Image modification timestamp
```

#### OCR Engines

**PaddleOCR** (only supported engine):
- Supported languages: `en`, `fr`, `it`, `de`
- Key function: `run_ocr_for_image()`
- Output: extracted text + optional spell correction (pyspellchecker)

#### Working Folder Management

The "Working Folder" is the root of the workflow:
- Default: `<project-root>/images/`
- Persistent: Saved to `.working-folder.txt`
- Structure:
  ```
  <working-folder>/
  ├── image1.jpg              (active – to be processed)
  ├── image1.txt              (paired)
  ├── image2.jpg
  ├── image2.txt
  └── check-done/             (validated)
      ├── image1.jpg
      └── image1.txt
  ```

### 2. Web Capture Application

**Technology:** HTML5 + JavaScript (Media APIs) + Flask backend  
**Access:** `/capture` from OCR web app  

#### User Flow:
1. User opens "Open Capture App"
2. New browser tab opens with capture interface
3. Select camera and mode (1 page / 2-page auto-split)
4. Manual capture or voice trigger ("next")
5. Images sent to Flask server → saved to Working Folder

#### JavaScript Endpoints

| Endpoint | Method | Payload | Response |
|----------|--------|---------|---------|
| `/capture-save-images` | POST | FormData (images) | `{saved: N, filenames: [...]}` |
| `/capture-voice-detect` | POST | FormData (WAV audio) | `{detected: bool, transcript: str}` |

#### Voice Detection

- **Engine:** Flask + Vosk (local, no cloud)
- **Model:** `vosk-model-small-en-us-0.15` (embedded)
- **Trigger word:** `"next"` (English)
- **Flow:**
  1. JavaScript captures audio stream (Web Audio API)
  2. Sends WAV to backend (`/capture-voice-detect`)
  3. Vosk transcribes locally
  4. Detects trigger word → triggers capture

#### Capture Modes

| Mode | Behavior |
|------|----------|
| `one_page` | Single image capture |
| `two_pages` | Capture, split vertically, save as `-left` and `-right` |

### 3. Desktop Capture Application (Optional)

**Technology:** Python + Tkinter + OpenCV + Vosk  
**Location:** `capture-app/main.py`  
**Status:** Prototype; web version recommended

#### Known Limitations:
- Possible crashes on macOS due to Tk/OpenCV conflicts
- Conflicting dependencies with PaddleOCR
- Reduced maintenance

## Complete Workflow

```
1. PREPARATION
   └─ User places images in <working-folder>/images/
      or imports them via web UI

2. PAIR CREATION
   └─ App automatically creates missing empty .txt files

3. CAPTURE (optional)
   ├─ Opens Capture App
   ├─ Capture via camera (1 or 2 pages)
   └─ Images saved to <working-folder>/images/

4. OCR & EDITING
   ├─ Selects current page
   ├─ Runs PaddleOCR
   ├─ Optional post-correction spell check
   ├─ Edits text
   ├─ Auto-save every 1.5s

5. VALIDATION
   ├─ Clicks "Validate & Next"
   ├─ Text is saved
   ├─ Image resized (optional)
   └─ Pair moved to <working-folder>/images/check-done/

6. CONTINUATION
   └─ Loop steps 4-5 until all files are validated

7. EXPORT (optional)
   └─ Downloads all .txt files as ZIP
```

## File Hierarchy

```
bookdigitizer-suite/
├── app.py                          (Main Flask application)
├── bootstrap.sh                    (Setup venv + dependencies)
├── docker-compose.yml              (Containerized deployment)
├── Dockerfile
├── requirements.txt                (Python dependencies)
├── restart.sh                      (Restart app)
│
├── capture-app/
│   ├── main.py                     (Tkinter desktop app)
│   ├── capture_core.py             (Capture logic + 2-page split)
│   ├── voice_trigger.py            (Voice trigger service)
│   ├── download_vosk_model.py      (Downloads Vosk model)
│   ├── requirements.txt
│   ├── models/
│   │   └── vosk-model-small-en-us-0.15/  (Embedded voice model)
│   └── tests/
│       └── test_capture_core.py
│
├── static/
│   ├── app.js                      (OCR web app JavaScript)
│   ├── capture_app.js              (Capture app JavaScript)
│   └── styles.css
│
├── templates/
│   ├── index.html                  (OCR web template)
│   └── capture.html                (Capture web template)
│
├── tests/
│   └── test_app.py                 (Flask unit tests)
│
├── scripts/
│   ├── add_play_icon_overlay.py    (Utility: YouTube overlay)
│   ├── setup_ocr_training_workspace.py  (OCR training setup)
│   ├── evaluate_ocr_metrics.py     (CER/WER metrics)
│   └── offline_spellcheck_texts.py (Batch offline correction)
│
├── images/                         (Default working folder)
│   ├── *.jpg / *.jpeg              (Images to process)
│   ├── *.txt                       (OCR texts)
│   └── check-done/                 (Validated pages)
│
└── docs/
    ├── ocr_training_playbook.md
    └── ocr_training_go_no_go_checklist.md
```

## Data Flow

```
┌──────────────────┐
│   Images Import  │
│   (Drag/Drop)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│ Create Missing .txt  │  (empty pair)
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│   PaddleOCR Run      │  (text extraction)
│  + Spellcheck (opt)  │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│   Text Edit UI       │  (user edits)
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│   Save (or Autosave) │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│    Validation UI     │  (user confirmation)
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Downsize (optional)  │  (image compression)
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Move to check-done/  │  (archiving)
└──────────────────────┘
```

## State Management and Transitions

### Page States

```
Active (images/)
├─ No text         → Create .txt
├─ Empty text      → Edit/OCR
├─ With text       → Edit/Validate
└─ Validated       → Move to check-done/

Archived (check-done/)
└─ Undo possible   → Return to Active
```

## Architectural Considerations

### 1. Stateless Design
- Each Flask request carries complete `ViewState` (query params)
- No persistent server-side session
- Allows app restart without losing user context

### 2. File Management
- Immutable pairs: image + .txt always identically named
- Atomic validation: bidirectional move (before/after)
- Undo by creation timestamp: `st_ctime` > `st_mtime`

### 3. Multilingual Support
- UI language (FR/EN/IT/DE) ≠ OCR language
- Translation dictionaries in Python (`TRANSLATIONS`)
- Fallback: FR if key missing

### 4. Security
- Path traversal prevention: `pathlib.Path.resolve()`
- File upload: extension verification + uniqueness
- Audio upload: max 4 MB size limit

### 5. Performance
- LRU cache for PaddleOCR instances (`@lru_cache`)
- Lazy thumbnail pagination (20 per page)
- Auto-save batch: 1.5s debounce

## Extensibility

### Adding a New OCR Engine
1. Implement `run_ocr_for_image(image_path, language)` for engine
2. Add case to `extract_text_from_paddle_result()`
3. Test with `test_app.py`

### Adding UI Language
1. Add keys + translations to `TRANSLATIONS` dict
2. Add language code to `SUPPORTED_LANGS`
3. Update `LANGUAGE_LABELS`

### Adding Capture Mode
1. Create new mode in `capture_app.js`
2. Implement split logic in `capture_core.py`
3. Add tests in `test_capture_core.py`

## Deployment

### Local (Recommended)
```bash
./bootstrap.sh
./restart.sh
```

### Docker
```bash
docker-compose up --build
```

### Environment Variables
- `OCR_LANG=fr` – OCR language (defaults to UI language)
- `AUTO_OCR=1` – Enable auto-OCR on import
- `OCR_POST_SPELLCHECK=1` – Global spell correction
- `OCR_COMPARE_SECRET` – Flask secret (dev-secret by default)

## Limitations and Notes

1. **Single active page** – Displays 1 image at a time (intentional design)
2. **Offline OCR** – Models downloaded locally (~500MB)
3. **Voice capture** – Vosk English only (not multilingual)
4. **Desktop app** – Unstable on macOS, web version recommended
5. **OCR performance** – Depends on CPU; can be slow on small machines

---

**Last updated:** 2026-07-19  
**Version:** 6.1.1

