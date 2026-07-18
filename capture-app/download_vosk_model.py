from __future__ import annotations

import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_DIR_NAME = "vosk-model-small-en-us-0.15"


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    models_dir = base_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    target_dir = models_dir / MODEL_DIR_NAME

    if target_dir.exists():
        print(f"Model already present: {target_dir}")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / f"{MODEL_DIR_NAME}.zip"

        print(f"Downloading: {MODEL_URL}")
        urllib.request.urlretrieve(MODEL_URL, zip_path)

        extract_dir = temp_path / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)

        extracted_model = extract_dir / MODEL_DIR_NAME
        if not extracted_model.exists():
            raise RuntimeError(f"Expected folder not found after extraction: {extracted_model}")

        shutil.move(str(extracted_model), str(target_dir))

    print(f"Model ready: {target_dir}")


if __name__ == "__main__":
    main()

