# OCR Training Go/No-Go Checklist

Use this checklist before launching a long fine-tuning run.

## 1) Data readiness

- [ ] At least 300 corrected lines (better: 1,500+ lines)
- [ ] Train/val/test splits created by page (no page leakage)
- [ ] Test set is frozen and never used for training
- [ ] Difficult page types are included (italics, notes, low contrast)

## 2) Baseline and metrics

- [ ] Baseline OCR predictions exported for the test set
- [ ] CER and WER computed with `scripts/evaluate_ocr_metrics.py`
- [ ] Baseline report stored in `ocr-training/eval/`

## 3) Training run quality gate

- [ ] Validation loss decreases for multiple checkpoints
- [ ] No obvious overfitting (val metrics do not collapse)
- [ ] New model beats baseline CER on the frozen test set
- [ ] New model beats baseline WER or keeps it stable

## 4) Deployment gate

- [ ] Model tested on 10 unseen real pages from the target book
- [ ] Accent-heavy words are improved (`idee` -> `idée` where expected)
- [ ] Rollback path documented (keep previous model checkpoint)
- [ ] Runtime speed is acceptable for your workflow

## Go / No-Go decision

- **GO** when CER improves significantly and manual correction time is reduced.
- **NO-GO** when gains are marginal or regressions appear on difficult pages.

Tip: Keep an experiment log with run date, dataset size, hyper-parameters, CER/WER.


