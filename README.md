<div align="center">

# Book Digitizer Suite v6.1.1

<p>
  <a href="https://youtu.be/8RaAw9v7SG8">
    <img src="resources/imgs/youtube-demo-thumbnail-play.png" alt="Watch the OCR Book Quick Compare introduction video on YouTube" width="400" />
  </a>
</p>

<p>
  <a href="https://youtu.be/8RaAw9v7SG8"><strong>▶ Watch the 8-minutes introduction video on YouTube</strong></a>
</p>

<p>
  <a href="https://youtu.be/DMKcqhTXROw">
    <img src="resources/imgs/capture-app-cover.png" alt="Watch the Capture Companion App demo video on YouTube" width="400" />
  </a>
</p>

<p>
  <a href="https://youtu.be/DMKcqhTXROw"><strong>▶ Watch the Capture Companion App demo on YouTube</strong></a>
</p>

<p>
  Quick demo of the browser-based companion capture app: live camera preview, one-page/two-page capture, rotation, fullscreen scan mode, and instant save to your OCR working folder.
</p>

<p>
  <a href="#quick-start-with-docker-recommended-for-one-click-setup">
    <img alt="Docker" src="https://img.shields.io/badge/Install-Docker-2496ED?logo=docker&logoColor=white" />
  </a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" />
  <img alt="Flask" src="https://img.shields.io/badge/Flask-Web%20App-000000?logo=flask&logoColor=white" />
  <img alt="OCR" src="https://img.shields.io/badge/OCR-PaddleOCR-1F6FEB" />
  <img alt="Languages" src="https://img.shields.io/badge/UI-FR%20%7C%20EN%20%7C%20IT%20%7C%20DE-6A5ACD" />
</p>

Small local web app to digitize and validate scanned book pages with OCR, paired with a companion browser-based capture app for live page photography. Complete end-to-end book digitization workflow.

</div>

## v6.1.1 Hotfix (Latest)

- **Autosave regression fix**: Restored the OCR form wiring required by frontend autosave (`id="save-form"` and view state data attributes)
- **Regression protection**: Added a dedicated test to ensure autosave-critical HTML attributes stay present after UI refactors

## v6.1 Features

- **Delete current page pair**: New **Effacer / Delete** action with confirmation to safely remove the current image and its paired `.txt`
- **Cleaner OCR action bar**: `Save` button replaced by a clear **Autosave ON** badge (autosave logic unchanged)
- **Improved operational safety**: Added backend route and tests for pair deletion with automatic redirect to next available page

## v6 Features

- **Offline post-OCR spell correction**: Optional `pyspellchecker` pass after OCR with visible ON/OFF switch
- **GUI workflow improvements**: OCR tools moved under **OCR Text** for faster editing loops (OCR language, spellcheck switch, post-validation downsize controls)
- **Custom OCR training foundations**: Added scripts and docs for dataset setup, CER/WER evaluation, and go/no-go validation before fine-tuning

## v5 Features

- **Browser-based Capture Companion App**: Live camera preview, browser media APIs, auto image split for two-page mode
- **Shared Working Folder**: Unified folder between OCR app and capture app for seamless workflow
- **Capture modes**: Single page (one_page) or auto-split dual pages (two_pages with -left/-right naming)
- **Voice trigger**: Hands-free capture with `next` keyword (local Vosk + Flask, no cloud dependency)
- **Rotation & preview control**: Real-time rotation preview before capture, ±90° buttons, fullscreen scan mode
- **Capture settings persistence**: Browser local storage for mode, prefix, beep, rotation

## v4 Features

- **Validation history**: Undo the last validated page to move it back to the queue
- **Inline rename**: Click the current filename to rename `.jpg/.jpeg` and paired `.txt`
- **Image rotation**: Rotate images ±90° for better orientation viewing
- **Pagination of thumbnails**: Browse large thumbnail lists with pagination (20 per page)
- **Auto-import upload flow**: Drag/drop or file selection starts import immediately
- **Auto `.txt` pairing on upload**: Imported images get their `.txt` sibling instantly
- **Auto-OCR on import**: Optional OCR processing while importing images
- **Multilingual UI**: Language switcher (FR / EN / IT / DE)
- **Separate OCR language selection**: OCR language can differ from UI language
- **Downsize validated images**: Optional post-validation compression with target size slider (default 300 KB)
- **Global text export**: Download all OCR texts as a ZIP file with organized folders
- **Advanced split view sync**: Horizontal scroll synchronization between image and text panels

## Core Features (v3 & earlier)

- create missing `.txt` files for each `.jpg` / `.jpeg` image without overwriting existing text files
- process pages in chronological image order (oldest file timestamp first)
- display the current page image next to its editable text
- save text corrections
- autosave text edits while typing
- show a clear unsaved / autosaved status indicator
- validate the current page and move the image/text pair to `images/check-done/`
- automatically continue with the next available page
- `Validate + next` action to save and validate in one step
- confirmation before validate-only actions
- manual previous / next navigation between ready page pairs
- thumbnail gallery for the remaining ready pages (paginated)
- advanced filtering and sorting of ready pages
- global progress counters and progress bar
- image zoom controls
- image rotation controls
- keyboard shortcuts for the main actions
- drag-and-drop or click-to-upload image import
- local OCR action using PaddleOCR


## Technology choice

This implementation uses **Python + Flask**.

Why it fits this project well:

- quick to build and easy to run locally
- straightforward filesystem handling
- very small stack for a workflow-oriented internal tool
- easy to test and extend
- lighter than a full frontend framework for this use case

## Requirements

- Python 3.9+ (3.11+ recommended)
- OCR dependencies from `requirements.txt` (`paddleocr` + `paddlepaddle`)
- Optional offline post-correction: `pyspellchecker` (installed via `requirements.txt`)

## Offline post-OCR spell correction (optional)

If your OCR output has many accent mistakes (for example `idee` instead of `idée`),
you can enable an offline dictionary-based correction pass after OCR.

From the UI:

- Enable **Post-correction orthographique** in the OCR tools area (under **OCR Text**).
- Click **Paddle OCR** to run OCR with post-correction.

Environment flag (global default):

```bash
export OCR_POST_SPELLCHECK=1
```

Notes:

- Correction runs after PaddleOCR text extraction.
- Spellcheck language automatically follows the effective OCR language selected in the app.
- It is best-effort: if spellchecker is unavailable, OCR still works.
- Start with French (`fr`) for accent-heavy books.

## Project layout

```text
[PROJECT DIR]/
├── app.py
├── requirements.txt
├── README.md
├── capture-app/
│   ├── main.py
│   ├── capture_core.py
│   ├── voice_trigger.py
│   ├── download_vosk_model.py
│   ├── requirements.txt
│   └── tests/
│       └── test_capture_core.py
├── static/
│   ├── app.js
│   └── styles.css
├── templates/
│   └── index.html
├── tests/
│   └── test_app.py
└── images/
    └── check-done/
```

## Setup

```bash
cd "[PROJECT DIR]"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start with Docker (Recommended for One-Click Setup)

If you have Docker installed, the fastest way to get started is:

```bash
cd "[PROJECT DIR]"
docker-compose up --build
```

Then open your browser to:

```text
http://127.0.0.1:5001
```

**That's it!** All dependencies (Python, OCR models, image libraries) are pre-configured.

**Stop the app:**

```bash
docker-compose down
```

**Restart later:**

```bash
docker-compose up
```

### Docker Options

- **Change OCR language**: Edit `docker-compose.yml` and uncomment the `OCR_LANG` variable:

```yaml
environment:
  - OCR_LANG=fr  # or: en, it, de
```

Then restart:

```bash
docker-compose up --build
```

- **Rebuild the image** (if requirements.txt changed):

```bash
docker-compose up --build
```

- **View logs**:

```bash
docker-compose logs -f
```

- **One-command start from anywhere**:

```bash
cd /path/to/bookdigitizer-suite
docker-compose up
```

## One-command bootstrap (recommended)

Use the bootstrap script to configure both virtualenvs, install dependencies, download the Vosk model, and run basic checks.

```bash
cd "[PROJECT DIR]"
./bootstrap.sh
```

Useful options:

```bash
cd "[PROJECT DIR]"
./bootstrap.sh --help
./bootstrap.sh --skip-model
./bootstrap.sh --dry-run
```

### Companion app setup (separate venv recommended)

`paddleocr` and camera/audio packages have conflicting OpenCV constraints on some macOS setups.
Use a dedicated virtualenv for `capture-app`:

```bash
cd "[PROJECT DIR]/capture-app"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you already ran `./bootstrap.sh`, this step is already done.

## OCR engine

This project now uses **PaddleOCR only**.

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Run locally with OCR Language

```bash
cd "[PROJECT DIR]"
source .venv/bin/activate
python3 app.py
```

## Daily Start-up Flow

Once `./bootstrap.sh` has been run successfully once, the recommended daily workflow is as follows.

### 1) Restart the OCR web app

Use `restart.sh` to cleanly restart the main Flask application:

```bash
cd "[PROJECT DIR]"
./restart.sh
```

Notes:
- the script automatically uses the root virtualenv `./.venv`
- it stops any old server from this project already listening on the same port
- by default, the port used is `5001`

Then open in your browser:

```text
http://127.0.0.1:5001
```

### 2) Open the companion capture app

From the `OCR Book Quick Compare` interface, click **Open Capture App** in the top toolbar.

The companion app opens in a **new browser tab**.

It uses the browser's web APIs for:
- detecting available cameras
- displaying live feed
- capturing 1 page or 2 pages
- automatically separating left/right in 2-page mode
- listening for the `next` trigger word if the browser supports speech recognition

### 3) Alternative: launch the capture app manually

The recommended version is now the one in the browser.

The desktop prototype in `capture-app/` can remain useful for technical testing, but on some macOS machines it may crash due to the Python/Tk native GUI stack.

If you still want to test the desktop prototype manually:

```bash
cd "[PROJECT DIR]"
source capture-app/.venv/bin/activate
python3 capture-app/main.py
```

### 4) When to re-run `bootstrap.sh`?

You normally don't need to re-run `bootstrap.sh` every day.
Re-run it only if, for example:

- you recreate the virtualenvs
- you modify Python dependencies
- you want to re-download/reconfigure the Vosk speech model

```bash
cd "[PROJECT DIR]"
./bootstrap.sh
```

## Restart the app

If the app is already running, stop the current Flask process first, then start it again.

```bash
# In the terminal where the app is running:
Ctrl+C
```

Then restart with either of these commands:

```bash
# Preferred when the venv is already activated
flask --app app run --debug

# Or, if you want to be explicit
.venv/bin/flask --app app run --debug
```

If port `5000` is already in use on macOS, start on another port:

```bash
.venv/bin/flask --app app run --debug --port 5001
```

Or with environment options:

```bash
# Set OCR language (optional): fr, en, it, de
OCR_LANG="fr" python3 app.py

# Enable auto-OCR on import
AUTO_OCR="1" python3 app.py

# Combine both
AUTO_OCR="1" OCR_LANG="fr" python3 app.py
```

Then open: `http://127.0.0.1:5000` (or `:5001` if you started on port 5001)

## Usage flow

1. Add `.jpg` or `.jpeg` files to `images/`, or import them from the web UI
2. Upload via UI (drag/drop or click) to auto-import files and auto-create paired `.txt`
3. Click **Créer les .txt manquants** when images were copied directly via Finder
4. Pick UI language in the top switcher and OCR language in the top OCR selector if needed
5. Review the oldest ready page first
6. (Optional) Click the current filename under **Image** to rename both image and text pair
7. Run OCR, edit the text on the right, then save
8. (Optional) Enable **Downsize validated images** and set a target size (default 300 KB)
9. Click **Validate + next** to save, validate, and move to the next page
10. If downsize is ON, the image is compressed before it is moved to `images/check-done/`
11. Use thumbnails/filters to jump to another page
12. Continue until no page is left in `images/`

## Keyboard shortcuts

- `Cmd/Ctrl + S`: save the current text
- `Alt + V`: save, validate, and go to the next page
- `Alt + Shift + V`: validate only
- `Alt + Left`: go to the previous ready page
- `Alt + Right`: go to the next ready page
- `Alt + C`: create missing `.txt` files
- **Rotation** & **Zoom**: Use the UI buttons (keyboard shortcuts planned for future versions)

## Text Editing & Spell Checking

### Install LanguageTool for French Spell & Grammar Checking

The text editor uses **LanguageTool** extension for advanced French (and multilingual) spell checking and grammar correction.

**Why LanguageTool?**
- ✓ Excellent French spelling & grammar detection
- ✓ Context-aware suggestions
- ✓ Works offline (after first setup)
- ✓ Personal dictionary (no macOS cache issues)
- ✓ Supports 30+ languages
- ✓ Open source and free

**Installation:**

1. Open Chrome and go to [LanguageTool on Chrome Web Store](https://chrome.google.com/webstore)
2. Search for **"LanguageTool"** (by LanguageTool GmbH)
3. Click **"Add to Chrome"** and confirm permissions
4. The extension will appear in your Chrome toolbar

**Usage:**
- In any text field (including this app), red underlines appear for spelling errors
- Blue underlines appear for grammar suggestions
- Hover or click to see corrections and suggestions
- Right-click and select "Ignore" to skip a word, or "Add to dictionary" to learn it permanently

**Configure language:**
- Click the LanguageTool icon in the toolbar → Settings → Language
- Select **"Français"** (or your preferred language)
- Optionally enable grammar checking (may slow down slightly)

**Remove learned words:**
- LanguageTool stores its personal dictionary locally in your browser profile
- If you accidentally added a word: right-click it → "Remove from dictionary"
- To clear all custom words: LanguageTool Settings → Dictionary → "Clear"

## OCR Setup & Language Configuration

The **Paddle OCR** button uses `paddleocr` and `paddlepaddle` from the Python environment.

### Configuring OCR Language

You can choose OCR language in two ways:

1. **UI selector** (top-right): this value is stored in URL/query state.
2. **Environment variable** `OCR_LANG`: fallback when UI OCR language is not selected.

If neither is set, OCR language falls back to the current UI language.

Supported OCR language values in this project:
- `fr`
- `en`
- `it`
- `de`

#### Common language codes:
- `en` – English
- `fr` – French
- `it` – Italian
- `de` – German

Current mapping in this project uses:
- `OCR_LANG="en"` -> Paddle language `en`
- `OCR_LANG="fr"` -> Paddle language `fr`
- `OCR_LANG="it"` -> Paddle language `it`
- `OCR_LANG="de"` -> Paddle language `de`

### ⚠️ Important: Troubleshooting French OCR

If you're seeing **poor OCR results with French documents**:

1. **Use single-language mode when possible**:
   - If your book is **100% French**: use `fra`
   - If your book is **100% English**: use `eng`

2. **Test with a sample page first**:
   ```bash
   OCR_LANG="fr" python3 app.py
   ```
   Import one test page and run OCR to see if results improve.

3. **OCR model quality differs by language and image quality**:
   - For French-only content, prefer `OCR_LANG="fr"`
   - For mixed content, test with a small batch first
   - If accuracy is critical, consider pre-processing (binarization, skew correction)

4. **Image quality matters**:
   - Binarize images (convert to pure black & white) before OCR
   - Ensure pages are scanned at 300+ DPI
   - Correct skewed pages (rotated text)

### Using Auto-OCR on Import

In the web UI, check **"OCR auto"** when importing images to automatically run OCR with your configured language setting.

Set it globally via:

```bash
cd "[PROJECT DIR]"
source .venv/bin/activate
AUTO_OCR="1" OCR_LANG="fr" python3 app.py
```

### Downsize Validated Images

You can keep high-resolution images for OCR work, then downsize them only after validation for lighter archive storage.

- Toggle **Downsize validated images** to `ON` in the top toolbar.
- Set target size with the slider (default: `300 KB`).
- Quick presets: `150`, `300`, `500`, `800`, `1200` KB.

Recommended ranges:
- `300 KB` for a balanced archive footprint/readability
- `500-800 KB` for more visual comfort
- `150 KB` only for very aggressive storage reduction

Implementation detail: compression runs during validation (before moving files to `images/check-done/`) and uses best-effort JPEG optimization.

### Export All Texts

Click **"⬇️ Export"** to download a ZIP file containing:
- `texts/` – all OCR texts from active pages
- `texts_done/` – all OCR texts from validated pages

Use this for backup, bulk processing, or downstream workflows.

## Run tests

```bash
cd "[PROJECT DIR]"
source .venv/bin/activate
python3 -m unittest discover -s tests

# Companion capture app unit tests
python3 -m unittest discover -s capture-app/tests
```

## Companion Capture App (macOS)

Use this when you want hands-free image capture while holding book pages.

- Trigger word: `next` (English)
- Camera source selection from detected devices
- Shared **Working Folder** configured in the main OCR app
- Captured images are saved directly into that Working Folder (with paired `.txt` files)
- Attempts full-resolution still capture first (`ImageCapture.takePhoto()`), then falls back to the live video frame if unavailable
- Mode `one_page` (single file) or `two_pages` (auto split into `-left` and `-right`)
- Fixed center alignment line shown in `two_pages` mode
- Opens in a new browser tab from the main app
- Visual capture counter
- Configurable filename prefix
- Optional audio beep after each capture
- Capture settings persistence (mode, prefix, beep) via browser local storage
- Large fullscreen scan mode button
- More explicit browser compatibility status (Chrome / Safari / Firefox)
- Voice trigger now auto-retries on transient network errors and shows clearer microphone/network guidance
- Voice trigger now uses local detection through Flask + Vosk (no browser cloud speech dependency)

Start from web UI:
- Click **Open Capture App** in the top toolbar

Configure the shared Working Folder from the main OCR app toolbar, then capture in the companion tab.

Tip: in the main app toolbar you can click **Choose working folder** to select it directly with Finder on macOS.

Recommended browser:
- Chrome for best support of camera + speech + capture responsiveness
- Safari may work for camera access, but speech/capture behavior may be more limited

Legacy desktop prototype (optional):

```bash
cd "[PROJECT DIR]"
source capture-app/.venv/bin/activate
python3 capture-app/download_vosk_model.py
python3 capture-app/main.py
```


## Notes

- only root-level files inside `images/` are treated as active pages
- files already moved to `images/check-done/` are counted as validated
- text files are created only when missing, never overwritten by the generation step
- uploaded image names are preserved as-is

## Utility scripts

- Add a YouTube-like centered play icon on a cover image:

```bash
cd "[PROJECT DIR]"
capture-app/.venv/bin/python scripts/add_play_icon_overlay.py \
  --input resources/imgs/capture-app-cover.png \
  --output resources/imgs/capture-app-cover.png
```

- Initialize a book-specific OCR training workspace (folders + split manifests):

```bash
cd "[PROJECT DIR]"
python scripts/setup_ocr_training_workspace.py --workspace ocr-training --sample-pages 80
```

- Compute CER/WER from OCR predictions vs corrected references:

```bash
cd "[PROJECT DIR]"
python scripts/evaluate_ocr_metrics.py \
  --pred-dir ocr-training/eval/baseline/pred \
  --ref-dir ocr-training/eval/baseline/ref \
  --output-json ocr-training/eval/baseline/report.json
```

- Run offline spell correction on `.txt` files (preview first):

```bash
cd "[PROJECT DIR]"
python scripts/offline_spellcheck_texts.py --input-dir images --language fr --dry-run
python scripts/offline_spellcheck_texts.py --input-dir images --language fr
```

- Training process docs and release checklist:
  - `docs/ocr_training_playbook.md`
  - `docs/ocr_training_go_no_go_checklist.md`

## Privacy & Publishing

- `images/` content is intentionally not versioned (local test/work data)
- `.idea/` is ignored
- before public push, re-check tracked files:

```bash
git ls-files
```
