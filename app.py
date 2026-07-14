import os
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, send_from_directory, url_for

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

IMAGE_EXTENSIONS = {".jpg", ".jpeg"}
SORT_OPTIONS = {"oldest", "newest", "name_asc", "name_desc", "text_length_desc"}
TEXT_FILTER_OPTIONS = {"all", "empty", "filled"}
THUMBNAILS_PER_PAGE = 20


@dataclass
class PairRecord:
    image_path: Path
    text_path: Path
    text_content: str
    image_mtime: float

    @property
    def image_name(self) -> str:
        return self.image_path.name

    @property
    def text_name(self) -> str:
        return self.text_path.name

    @property
    def text_is_empty(self) -> bool:
        return not self.text_content.strip()

    @property
    def text_length(self) -> int:
        return len(self.text_content.strip())


@dataclass
class ViewState:
    selected_name: str = ""
    query: str = ""
    sort_key: str = "oldest"
    text_filter: str = "all"
    thumbnail_page: int = 1



def is_supported_image(file_path: Path) -> bool:
    return file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS



def is_supported_image_name(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS



def iter_root_images(images_dir: Path) -> Iterable[Path]:
    return (path for path in images_dir.iterdir() if is_supported_image(path))



def image_sort_key(image_path: Path) -> tuple[float, str]:
    return (image_path.stat().st_mtime, image_path.name.casefold())



def text_path_for(image_path: Path) -> Path:
    return image_path.with_suffix(".txt")



def normalize_sort_key(sort_key: str) -> str:
    return sort_key if sort_key in SORT_OPTIONS else "oldest"



def normalize_text_filter(text_filter: str) -> str:
    return text_filter if text_filter in TEXT_FILTER_OPTIONS else "all"



def build_view_state(source) -> ViewState:
    return ViewState(
        selected_name=(source.get("current_image") or source.get("file") or "").strip(),
        query=(source.get("q") or "").strip(),
        sort_key=normalize_sort_key((source.get("sort") or "oldest").strip()),
        text_filter=normalize_text_filter((source.get("text_filter") or "all").strip()),
        thumbnail_page=max(1, int(source.get("thumb_page", 1) or 1)),
    )



def build_index_params(view_state: ViewState, selected_name: Optional[str] = None) -> dict:
    file_name = selected_name if selected_name is not None else view_state.selected_name
    params = {
        "sort": view_state.sort_key,
        "text_filter": view_state.text_filter,
        "thumb_page": view_state.thumbnail_page,
    }

    if file_name:
        params["file"] = file_name
    if view_state.query:
        params["q"] = view_state.query
    return params



def count_supported_images(directory: Path) -> int:
    return len([path for path in directory.iterdir() if is_supported_image(path)])



def get_pending_records(images_dir: Path) -> tuple[list[PairRecord], list[Path]]:
    records: list[PairRecord] = []
    missing_texts: list[Path] = []

    for image_path in iter_root_images(images_dir):
        text_path = text_path_for(image_path)
        if not text_path.exists():
            missing_texts.append(image_path)
            continue

        records.append(
            PairRecord(
                image_path=image_path,
                text_path=text_path,
                text_content=text_path.read_text(encoding="utf-8"),
                image_mtime=image_path.stat().st_mtime,
            )
        )

    records.sort(key=lambda record: (record.image_mtime, record.image_name.casefold()))
    missing_texts.sort(key=image_sort_key)
    return records, missing_texts



def filter_and_sort_records(records: list[PairRecord], view_state: ViewState) -> list[PairRecord]:
    filtered_records: list[PairRecord] = []
    normalized_query = view_state.query.casefold()

    for record in records:
        if normalized_query:
            haystacks = (record.image_name.casefold(), record.text_content.casefold())
            if all(normalized_query not in haystack for haystack in haystacks):
                continue

        if view_state.text_filter == "empty" and not record.text_is_empty:
            continue
        if view_state.text_filter == "filled" and record.text_is_empty:
            continue

        filtered_records.append(record)

    if view_state.sort_key == "newest":
        filtered_records.sort(key=lambda record: (record.image_mtime, record.image_name.casefold()), reverse=True)
    elif view_state.sort_key == "name_asc":
        filtered_records.sort(key=lambda record: record.image_name.casefold())
    elif view_state.sort_key == "name_desc":
        filtered_records.sort(key=lambda record: record.image_name.casefold(), reverse=True)
    elif view_state.sort_key == "text_length_desc":
        filtered_records.sort(key=lambda record: (record.text_length, record.image_name.casefold()), reverse=True)
    else:
        filtered_records.sort(key=lambda record: (record.image_mtime, record.image_name.casefold()))

    return filtered_records



def get_selected_record(records: list[PairRecord], selected_name: str) -> tuple[Optional[PairRecord], int]:
    if not records:
        return None, -1

    if selected_name:
        for index, record in enumerate(records):
            if record.image_name == selected_name:
                return record, index

    return records[0], 0



def create_missing_text_files(images_dir: Path) -> list[Path]:
    created_files: list[Path] = []
    for image_path in sorted(iter_root_images(images_dir), key=image_sort_key):
        text_path = text_path_for(image_path)
        if not text_path.exists():
            text_path.write_text("", encoding="utf-8")
            created_files.append(text_path)
    return created_files



def save_uploaded_images(files: list, images_dir: Path, auto_ocr: bool = False, ocr_lang: str = "eng") -> tuple[int, int, list]:
    created_count = 0
    skipped_count = 0
    created_images: list = []

    for storage in files:
        raw_name = (storage.filename or "").strip()
        if not raw_name:
            continue

        filename = Path(raw_name).name
        if not is_supported_image_name(filename):
            skipped_count += 1
            continue

        destination = images_dir / filename
        if destination.exists():
            skipped_count += 1
            continue

        storage.save(str(destination))
        created_count += 1
        created_images.append((destination, text_path_for(destination)))

    if auto_ocr and created_images:
        for image_path, text_path in created_images:
            try:
                extracted_text = run_ocr_for_image(image_path, ocr_lang)
                text_path.write_text(extracted_text, encoding="utf-8")
            except RuntimeError:
                text_path.write_text("", encoding="utf-8")

    return created_count, skipped_count, created_images



def move_pair_to_done(image_path: Path, text_path: Path, check_done_dir: Path) -> None:
    check_done_dir.mkdir(parents=True, exist_ok=True)

    image_target = check_done_dir / image_path.name
    text_target = check_done_dir / text_path.name

    if image_target.exists() or text_target.exists():
        raise FileExistsError(
            "Le fichier cible existe déjà dans check-done. Supprime-le ou renomme-le avant de valider."
        )

    shutil.move(str(image_path), str(image_target))
    shutil.move(str(text_path), str(text_target))



def undo_last_validation(check_done_dir: Path, images_dir: Path, count: int = 1) -> int:
    undone_count = 0
    images_in_done = sorted(iter_root_images(check_done_dir), key=image_sort_key, reverse=True)

    for image_path in images_in_done[:count]:
        text_path = text_path_for(image_path)
        if text_path.exists():
            image_dest = images_dir / image_path.name
            text_dest = images_dir / text_path.name

            if not image_dest.exists() and not text_dest.exists():
                shutil.move(str(image_path), str(image_dest))
                shutil.move(str(text_path), str(text_dest))
                undone_count += 1

    return undone_count



def export_all_texts(images_dir: Path, check_done_dir: Path) -> bytes:
    zip_buffer = __import__("io").BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for text_path in sorted(images_dir.glob("*.txt")):
            arcname = f"texts/{text_path.name}"
            zipf.write(text_path, arcname=arcname)

        for text_path in sorted(check_done_dir.glob("*.txt")):
            arcname = f"texts_done/{text_path.name}"
            zipf.write(text_path, arcname=arcname)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()



def _paddle_language_code(language: str) -> str:
    normalized = (language or "").strip().lower()
    if normalized.startswith("fra"):
        return "fr"
    if normalized.startswith("eng"):
        return "en"
    return "en"


@lru_cache(maxsize=4)
def get_paddle_ocr(language: str):
    if PaddleOCR is None:
        raise RuntimeError("Paddle OCR is not installed. Install paddleocr to enable this feature.")

    return PaddleOCR(use_textline_orientation=True, lang=_paddle_language_code(language))


def extract_text_from_paddle_result(result) -> str:
    lines: list[str] = []

    if not result:
        return ""

    for page in result:
        if page is None:
            continue

        rec_texts = None
        if hasattr(page, "get"):
            rec_texts = page.get("rec_texts")
        elif hasattr(page, "rec_texts"):
            rec_texts = getattr(page, "rec_texts")

        if rec_texts:
            lines.extend(str(text).strip() for text in rec_texts if str(text).strip())
            continue

        if isinstance(page, dict):
            raw_text = page.get("text")
            if raw_text:
                lines.append(str(raw_text).strip())
            continue

        if isinstance(page, (list, tuple)):
            for item in page:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("rec_text")
                    if text:
                        lines.append(str(text).strip())
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    text = item[1]
                    if text:
                        lines.append(str(text).strip())

    return "\n".join(line for line in lines if line)


def run_ocr_for_image(image_path: Path, language: str) -> str:
    try:
        ocr = get_paddle_ocr(language)
        result = ocr.predict(str(image_path))
        extracted_text = extract_text_from_paddle_result(result)
        if not extracted_text:
            legacy_result = ocr.ocr(str(image_path))
            extracted_text = extract_text_from_paddle_result(legacy_result)
        return extracted_text
    except Exception as exc:
        raise RuntimeError(f"Paddle OCR failed: {exc}") from exc


def create_app(test_config: Optional[dict] = None) -> Flask:
    base_dir = Path(__file__).resolve().parent

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("OCR_COMPARE_SECRET", "dev-secret-change-me"),
        IMAGES_DIR=base_dir / "images",
        CHECK_DONE_DIR=base_dir / "images" / "check-done",
        OCR_LANG=os.environ.get("OCR_LANG", "eng"),
        AUTO_OCR=os.environ.get("AUTO_OCR", "0").lower() in ("1", "true", "yes"),
        MAX_CONTENT_LENGTH=64 * 1024 * 1024,
        AUTOSAVE_INTERVAL_MS=1500,
    )

    if test_config:
        app.config.update(test_config)

    app.config["IMAGES_DIR"] = Path(app.config["IMAGES_DIR"])
    app.config["CHECK_DONE_DIR"] = Path(app.config["CHECK_DONE_DIR"])

    app.config["IMAGES_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["CHECK_DONE_DIR"].mkdir(parents=True, exist_ok=True)

    def redirect_to_index(view_state: ViewState, selected_name: Optional[str] = None):
        return redirect(url_for("index", **build_index_params(view_state, selected_name)))

    def get_filtered_context(view_state: ViewState) -> tuple[list[PairRecord], list[PairRecord], list[Path]]:
        pending_records, missing_texts = get_pending_records(app.config["IMAGES_DIR"])
        filtered_records = filter_and_sort_records(pending_records, view_state)
        return pending_records, filtered_records, missing_texts

    @app.get("/")
    def index():
        images_dir: Path = app.config["IMAGES_DIR"]
        check_done_dir: Path = app.config["CHECK_DONE_DIR"]
        view_state = build_view_state(request.args)

        pending_records, filtered_records, missing_texts = get_filtered_context(view_state)
        current_record, current_index = get_selected_record(filtered_records, view_state.selected_name)

        current_image_name = current_record.image_name if current_record else ""
        prev_name = filtered_records[current_index - 1].image_name if current_record and current_index > 0 else None
        next_name = (
            filtered_records[current_index + 1].image_name
            if current_record and current_index < len(filtered_records) - 1
            else None
        )

        paginated_records = filtered_records[
            (view_state.thumbnail_page - 1) * THUMBNAILS_PER_PAGE : view_state.thumbnail_page * THUMBNAILS_PER_PAGE
        ]
        total_thumbnail_pages = (len(filtered_records) + THUMBNAILS_PER_PAGE - 1) // THUMBNAILS_PER_PAGE

        root_image_count = count_supported_images(images_dir)
        done_count = count_supported_images(check_done_dir)
        total_page_count = root_image_count + done_count
        progress_percent = round((done_count / total_page_count) * 100) if total_page_count else 0

        return render_template(
            "index.html",
            current_record=current_record,
            current_image_name=current_image_name,
            current_position=(current_index + 1) if current_record else 0,
            ready_total_count=len(pending_records),
            pending_count=len(filtered_records),
            missing_text_count=len(missing_texts),
            total_images=root_image_count,
            total_page_count=total_page_count,
            done_count=done_count,
            progress_percent=progress_percent,
            prev_name=prev_name,
            next_name=next_name,
            paginated_records=paginated_records,
            filtered_records=filtered_records,
            has_filtered_results=bool(filtered_records),
            has_ready_pages=bool(pending_records),
            thumbnail_page=view_state.thumbnail_page,
            total_thumbnail_pages=total_thumbnail_pages,
            ocr_available=(PaddleOCR is not None),
            ocr_lang=app.config["OCR_LANG"],
            autosave_interval_ms=app.config["AUTOSAVE_INTERVAL_MS"],
            view_state=view_state,
        )

    @app.post("/create-missing-texts")
    def create_texts():
        view_state = build_view_state(request.form)
        created_files = create_missing_text_files(app.config["IMAGES_DIR"])
        if created_files:
            flash(f"{len(created_files)} fichier(s) texte créé(s).", "success")
        else:
            flash("Aucun nouveau fichier texte à créer.", "info")
        return redirect_to_index(view_state, view_state.selected_name)

    @app.post("/upload-images")
    def upload_images():
        uploaded_files = request.files.getlist("images")
        auto_ocr = request.form.get("auto_ocr") == "1"
        created_count, skipped_count, _ = save_uploaded_images(
            uploaded_files, app.config["IMAGES_DIR"], auto_ocr=auto_ocr, ocr_lang=app.config["OCR_LANG"]
        )

        if created_count:
            msg = f"{created_count} image(s) importée(s)."
            if auto_ocr:
                msg += " OCR auto appliqué."
            flash(msg, "success")
        if skipped_count:
            flash(f"{skipped_count} fichier(s) ignoré(s) (doublon ou format non supporté).", "info")
        if not created_count and not skipped_count:
            flash("Aucun fichier reçu.", "info")

        return redirect(url_for("index"))

    @app.post("/save")
    def save_text():
        view_state = build_view_state(request.form)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, _ = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            flash("Aucune page à mettre à jour.", "info")
            return redirect(url_for("index"))

        updated_text = request.form.get("text", "")
        current_record.text_path.write_text(updated_text, encoding="utf-8")
        flash(f"Texte mis à jour pour {current_record.text_name}.", "success")
        return redirect_to_index(view_state, current_record.image_name)

    @app.post("/autosave")
    def autosave_text():
        payload = request.get_json(silent=True) or {}
        view_state = build_view_state(payload)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, _ = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            return jsonify({"saved": False, "message": "No matching page available for autosave."}), 404

        updated_text = payload.get("text", "")
        current_record.text_path.write_text(updated_text, encoding="utf-8")
        return jsonify(
            {
                "saved": True,
                "filename": current_record.text_name,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
        )

    @app.post("/run-ocr")
    def run_ocr():
        view_state = build_view_state(request.form)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, _ = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            flash("Aucune page disponible pour lancer l'OCR.", "info")
            return redirect(url_for("index"))

        try:
            extracted_text = run_ocr_for_image(current_record.image_path, app.config["OCR_LANG"])
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect_to_index(view_state, current_record.image_name)

        if not extracted_text.strip():
            flash(f"Paddle OCR n'a renvoyé aucun texte pour {current_record.image_name}.", "error")
            return redirect_to_index(view_state, current_record.image_name)

        current_record.text_path.write_text(extracted_text, encoding="utf-8")
        flash(f"Paddle OCR exécuté pour {current_record.image_name}.", "success")
        return redirect_to_index(view_state, current_record.image_name)

    @app.post("/validate")
    def validate_pair():
        view_state = build_view_state(request.form)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, current_index = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            flash("Aucune page à valider.", "info")
            return redirect(url_for("index"))

        remaining_records = filtered_records[:current_index] + filtered_records[current_index + 1 :]
        next_name = remaining_records[min(current_index, len(remaining_records) - 1)].image_name if remaining_records else ""

        try:
            move_pair_to_done(current_record.image_path, current_record.text_path, app.config["CHECK_DONE_DIR"])
        except FileExistsError as exc:
            flash(str(exc), "error")
            return redirect_to_index(view_state, current_record.image_name)

        flash(f"Page validée: {current_record.image_name}.", "success")
        return redirect_to_index(view_state, next_name)

    @app.post("/validate-and-next")
    def validate_and_next():
        view_state = build_view_state(request.form)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, current_index = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            flash("Aucune page à valider.", "info")
            return redirect(url_for("index"))

        updated_text = request.form.get("text", "")
        current_record.text_path.write_text(updated_text, encoding="utf-8")
        remaining_records = filtered_records[:current_index] + filtered_records[current_index + 1 :]
        next_name = remaining_records[min(current_index, len(remaining_records) - 1)].image_name if remaining_records else ""

        try:
            move_pair_to_done(current_record.image_path, current_record.text_path, app.config["CHECK_DONE_DIR"])
        except FileExistsError as exc:
            flash(str(exc), "error")
            return redirect_to_index(view_state, current_record.image_name)

        flash(f"Page sauvegardée et validée: {current_record.image_name}.", "success")
        return redirect_to_index(view_state, next_name)

    @app.post("/undo-validation")
    def undo_validation():
        view_state = build_view_state(request.form)
        undone_count = undo_last_validation(app.config["CHECK_DONE_DIR"], app.config["IMAGES_DIR"], count=1)
        if undone_count > 0:
            flash(f"Dernière validation annulée ({undone_count} fichier(s) restauré(s)).", "success")
        else:
            flash("Aucune validation à annuler.", "info")
        return redirect_to_index(view_state, view_state.selected_name)

    @app.get("/export-texts")
    def export_texts():
        zip_data = export_all_texts(app.config["IMAGES_DIR"], app.config["CHECK_DONE_DIR"])
        return send_file(
            __import__("io").BytesIO(zip_data),
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"ocr-texts-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip",
        )

    @app.get("/page-image/<path:filename>")
    def page_image(filename: str):
        return send_from_directory(str(app.config["IMAGES_DIR"]), filename)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)



