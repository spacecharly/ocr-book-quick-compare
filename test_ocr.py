#!/usr/bin/env python
"""Test OCR availability"""
import sys

print("Testing OCR imports...")

# Test Paddle
try:
    from paddleocr import PaddleOCR
    print("✓ PaddleOCR: AVAILABLE")
    paddle_ok = True
except ImportError as e:
    print(f"✗ PaddleOCR: FAILED - {e}")
    paddle_ok = False

# Test from app.py
print("\nTesting app.py imports...")
from app import PaddleOCR as app_PaddleOCR

print(f"app.PaddleOCR = {app_PaddleOCR}")

if app_PaddleOCR is None and paddle_ok:
    print("\n⚠️  PaddleOCR est installe mais app.py ne l'a pas trouve")
    print("Solution: relancer Python/Flask")
else:
    print(f"\nSituation: Paddle={'✓' if app_PaddleOCR else '✗'}")


