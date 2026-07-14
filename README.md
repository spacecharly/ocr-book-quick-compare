# OCR Book Quick Compare v4

Small local web app to compare scanned book page images with their OCR text, edit the text, and validate each page.

## v4 Features (New!)

- **Validation history**: Undo the last validated page to move it back to the queue
- **Inline rename**: Click the current filename to rename `.jpg/.jpeg` and paired `.txt`
- **Image rotation**: Rotate images ±90° for better orientation viewing
- **Pagination of thumbnails**: Browse large thumbnail lists with pagination (20 per page)
- **Auto-import upload flow**: Drag/drop or file selection starts import immediately
- **Auto `.txt` pairing on upload**: Imported images get their `.txt` sibling instantly
- **Auto-OCR on import**: Optional OCR processing while importing images
- **Multilingual UI**: Language switcher (FR / EN / IT / DE)
- **Separate OCR language selection**: OCR language can differ from UI language
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

If you ever prefer a PHP version later, the same workflow can absolutely be ported.

## Requirements

- Python 3.9+ (3.11+ recommended)
- OCR dependencies from `requirements.txt` (`paddleocr` + `paddlepaddle`)

## Project layout

```text
[PROJECT DIR]/
├── app.py
├── requirements.txt
├── README.md
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
8. Click **Validate + next** to save, validate, and move to the next page
9. Use thumbnails/filters to jump to another page
10. Continue until no page is left in `images/`

## Keyboard shortcuts

- `Cmd/Ctrl + S`: save the current text
- `Alt + V`: save, validate, and go to the next page
- `Alt + Shift + V`: validate only
- `Alt + Left`: go to the previous ready page
- `Alt + Right`: go to the next ready page
- `Alt + C`: create missing `.txt` files
- **Rotation** & **Zoom**: Use the UI buttons (keyboard shortcuts planned for future versions)

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
```

## Notes

- only root-level files inside `images/` are treated as active pages
- files already moved to `images/check-done/` are counted as validated
- text files are created only when missing, never overwritten by the generation step
- uploaded image names are preserved as-is

## Privacy & Publishing

- `images/` content is intentionally not versioned (local test/work data)
- `.idea/` is ignored
- before public push, re-check tracked files:

```bash
git ls-files
```








