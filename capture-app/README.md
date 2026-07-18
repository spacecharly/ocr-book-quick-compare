# Capture App (macOS, legacy desktop prototype)

> Preferred option: use the browser-based capture page opened by **Open Capture App** from the main web UI.
> This desktop prototype is kept for experimentation only, because some macOS Python/Tk builds can crash when opening native GUI windows.

Desktop companion app to capture book pages from a connected camera (including iPhone camera when exposed by macOS), then save images for OCR Book Quick Compare.

## Features

- camera detection + selection
- live camera preview
- output directory chooser
- voice trigger word: `next` (English)
- capture mode `one_page` or `two_pages`
- fixed center alignment line in `two_pages` mode
- automatic split to `-left.jpg` and `-right.jpg` in `two_pages`

## Install

Quick setup from project root:

```bash
cd "/Volumes/KDRIVE/swisstesting/ocr-book-quick-compare"
./bootstrap.sh
```

Manual setup (capture app only):

```bash
cd "/Volumes/KDRIVE/swisstesting/ocr-book-quick-compare/capture-app"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Voice model setup (required for "next")

```bash
cd "/Volumes/KDRIVE/swisstesting/ocr-book-quick-compare"
source capture-app/.venv/bin/activate
python3 capture-app/download_vosk_model.py
```

This downloads `vosk-model-small-en-us-0.15` into `capture-app/models/`.

## Run

```bash
cd "/Volumes/KDRIVE/swisstesting/ocr-book-quick-compare"
source capture-app/.venv/bin/activate
python3 capture-app/main.py
```

## Run companion tests

```bash
cd "/Volumes/KDRIVE/swisstesting/ocr-book-quick-compare"
source capture-app/.venv/bin/activate
python3 -m unittest discover -s capture-app/tests
```


