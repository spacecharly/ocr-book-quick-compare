# OCR Training Playbook (Book-specific)

This playbook is a practical starter for training OCR on one specific book.

## Step 1 - Initialize a workspace

```bash
python scripts/setup_ocr_training_workspace.py --workspace ocr-training --sample-pages 80
```

This creates:

- `ocr-training/dataset/ground_truth/pages/`
- `ocr-training/splits/`
- `ocr-training/eval/baseline/{pred,ref}/`
- `ocr-training/models/`

## Step 2 - Build your first baseline

1. Put OCR outputs in `ocr-training/eval/baseline/pred/`
2. Put corrected reference texts in `ocr-training/eval/baseline/ref/`
3. Compute metrics:

```bash
python scripts/evaluate_ocr_metrics.py \
  --pred-dir ocr-training/eval/baseline/pred \
  --ref-dir ocr-training/eval/baseline/ref \
  --output-json ocr-training/eval/baseline/report.json
```

## Step 3 - Optional offline spell correction

For accent-heavy OCR noise, run an offline pass on `.txt` files:

```bash
python scripts/offline_spellcheck_texts.py --input-dir images --language fr --dry-run
python scripts/offline_spellcheck_texts.py --input-dir images --language fr
```

## CER/WER quick definitions

- **CER** (Character Error Rate): edit distance at character level / reference characters
- **WER** (Word Error Rate): edit distance at word level / reference words

Lower is better. A CER drop from 8% to 4% is typically very noticeable.

## Go/No-Go rule

Use `docs/ocr_training_go_no_go_checklist.md` before each long run.

