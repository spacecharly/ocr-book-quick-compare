# OCR Book Quick Compare v4

Small local web app to compare scanned book page images with their OCR text, edit the text, and validate each page.

## v4 Features (New!)

- **Validation history**: Undo the last validated page to move it back to the queue
- **Image rotation**: Rotate images ±90° for better orientation viewing
- **Pagination of thumbnails**: Browse large thumbnail lists with pagination (20 per page)
- **Auto-OCR on import**: Option to run OCR automatically when importing images
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
# Set OCR language to French only
OCR_LANG="fra" python3 app.py

# Enable auto-OCR on import
AUTO_OCR="1" python3 app.py

# Combine both
AUTO_OCR="1" OCR_LANG="fra" python3 app.py
```

Then open: `http://127.0.0.1:5000`

## Usage flow

1. Add `.jpg` or `.jpeg` files to `images/`, or import them from the web UI
2. Click **Créer les .txt manquants** to generate missing text files
3. Review the oldest ready page first
4. Edit the OCR text on the right
5. Edit the text; autosave will also save after a short pause while typing
6. Click **Mettre à jour le texte** to save manually when needed
7. Click **Validate + next** to save, validate, and move to the next page
8. Or click **Validate only** to validate without resaving the current textarea content
9. Use the thumbnail strip and filters to jump directly to another ready page
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

The app supports OCR language selection via the `OCR_LANG` environment variable.

**Default setting:** `eng` (English only)

#### Common language codes:
- `eng` – English
- `fra` – French

Current mapping in this project uses:
- `OCR_LANG="eng"` -> Paddle language `en`
- `OCR_LANG="fra"` -> Paddle language `fr`

### ⚠️ Important: Troubleshooting French OCR

If you're seeing **poor OCR results with French documents**:

1. **Use single-language mode when possible**:
   - If your book is **100% French**: use `fra`
   - If your book is **100% English**: use `eng`

2. **Test with a sample page first**:
   ```bash
   OCR_LANG="fra" python3 app.py
   ```
   Import one test page and run OCR to see if results improve.

3. **OCR model quality differs by language and image quality**:
   - For French-only content, prefer `OCR_LANG="fra"`
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
AUTO_OCR="1" OCR_LANG="fra" python3 app.py
```

### Export All Texts

Click **"⬇️ Export"** to download a ZIP file containing:
- `texts/` – all OCR texts from active pages
- `texts_done/` – all OCR texts from validated pages

Use this for backup, bulk processing, or downstream workflows.

## Run locally with OCR Language

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








