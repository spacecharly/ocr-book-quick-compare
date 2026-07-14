import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app, extract_text_from_paddle_result


class OCRCompareAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.images_dir = self.base_path / "images"
        self.check_done_dir = self.images_dir / "check-done"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.check_done_dir.mkdir(parents=True, exist_ok=True)

        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "IMAGES_DIR": self.images_dir,
                "CHECK_DONE_DIR": self.check_done_dir,
                "OCR_LANG": "fra+eng",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_image(self, name: str, timestamp: int) -> Path:
        image_path = self.images_dir / name
        image_path.write_bytes(b"fake-jpg-content")
        os.utime(image_path, (timestamp, timestamp))
        return image_path

    def test_create_missing_text_files_and_select_oldest_page(self) -> None:
        first_image = self.create_image("page-001.jpg", 100)
        second_image = self.create_image("page-002.jpg", 200)

        response = self.client.post("/create-missing-texts", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(first_image.with_suffix(".txt").exists())
        self.assertTrue(second_image.with_suffix(".txt").exists())
        self.assertIn("2 fichier(s) texte créé(s).", response.get_data(as_text=True))
        self.assertIn("page-001.jpg", response.get_data(as_text=True))

    def test_navigation_uses_selected_page(self) -> None:
        first_image = self.create_image("page-001.jpg", 100)
        second_image = self.create_image("page-002.jpg", 200)
        first_image.with_suffix(".txt").write_text("texte 1", encoding="utf-8")
        second_image.with_suffix(".txt").write_text("texte 2", encoding="utf-8")

        response = self.client.get("/?file=page-002.jpg")
        page_html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("page-002.jpg", page_html)
        self.assertIn("Page filtrée 2 / 2", page_html)

    def test_search_and_filter_can_limit_visible_results(self) -> None:
        first_image = self.create_image("alpha-page.jpg", 100)
        second_image = self.create_image("beta-page.jpg", 200)
        first_image.with_suffix(".txt").write_text("bonjour OCR", encoding="utf-8")
        second_image.with_suffix(".txt").write_text("", encoding="utf-8")

        response = self.client.get("/?q=bonjour&text_filter=filled&sort=name_desc")
        page_html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("alpha-page.jpg", page_html)
        self.assertNotIn("beta-page.jpg", page_html)
        self.assertIn("résultats filtrés", page_html)

    def test_save_updates_selected_text_file(self) -> None:
        image_path = self.create_image("page-save.jpg", 100)
        text_path = image_path.with_suffix(".txt")
        text_path.write_text("avant", encoding="utf-8")

        response = self.client.post(
            "/save",
            data={
                "current_image": "page-save.jpg",
                "text": "après correction OCR",
                "sort": "oldest",
                "text_filter": "all",
                "q": "",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(text_path.read_text(encoding="utf-8"), "après correction OCR")
        self.assertIn("Texte mis à jour", response.get_data(as_text=True))

    def test_autosave_updates_selected_text_file_and_returns_json(self) -> None:
        image_path = self.create_image("page-autosave.jpg", 100)
        text_path = image_path.with_suffix(".txt")
        text_path.write_text("avant", encoding="utf-8")

        response = self.client.post(
            "/autosave",
            json={
                "current_image": "page-autosave.jpg",
                "text": "texte autosauvé",
                "sort": "oldest",
                "text_filter": "all",
                "q": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(text_path.read_text(encoding="utf-8"), "texte autosauvé")
        payload = response.get_json()
        self.assertTrue(payload["saved"])
        self.assertEqual(payload["filename"], "page-autosave.txt")

    def test_validate_moves_selected_pair_and_redirects_to_next_one(self) -> None:
        first_image = self.create_image("page-001.jpg", 100)
        second_image = self.create_image("page-002.jpg", 200)
        third_image = self.create_image("page-003.jpg", 300)
        first_image.with_suffix(".txt").write_text("texte 1", encoding="utf-8")
        second_image.with_suffix(".txt").write_text("texte 2", encoding="utf-8")
        third_image.with_suffix(".txt").write_text("texte 3", encoding="utf-8")

        response = self.client.post(
            "/validate",
            data={"current_image": "page-002.jpg", "sort": "oldest", "text_filter": "all", "q": ""},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(second_image.exists())
        self.assertTrue((self.check_done_dir / "page-002.jpg").exists())
        self.assertTrue((self.check_done_dir / "page-002.txt").exists())
        page_html = response.get_data(as_text=True)
        self.assertIn("page-003.jpg", page_html)
        self.assertTrue(first_image.exists())
        self.assertTrue(third_image.exists())

    def test_validate_and_next_saves_then_moves_pair(self) -> None:
        first_image = self.create_image("page-a.jpg", 100)
        second_image = self.create_image("page-b.jpg", 200)
        first_text = first_image.with_suffix(".txt")
        second_text = second_image.with_suffix(".txt")
        first_text.write_text("draft", encoding="utf-8")
        second_text.write_text("next", encoding="utf-8")

        response = self.client.post(
            "/validate-and-next",
            data={
                "current_image": "page-a.jpg",
                "text": "saved before move",
                "sort": "oldest",
                "text_filter": "all",
                "q": "",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        moved_text = (self.check_done_dir / "page-a.txt").read_text(encoding="utf-8")
        self.assertEqual(moved_text, "saved before move")
        self.assertTrue(second_text.exists())
        self.assertIn("page-b.jpg", response.get_data(as_text=True))

    def test_upload_images_skips_duplicates_and_invalid_extensions(self) -> None:
        self.create_image("existing.jpg", 100)

        response = self.client.post(
            "/upload-images",
            data={
                "images": [
                    (io.BytesIO(b"new-jpg"), "new-page.jpg"),
                    (io.BytesIO(b"dup-jpg"), "existing.jpg"),
                    (io.BytesIO(b"not-image"), "notes.txt"),
                ]
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue((self.images_dir / "new-page.jpg").exists())
        self.assertFalse((self.images_dir / "notes.txt").exists())
        page_html = response.get_data(as_text=True)
        self.assertIn("1 image(s) importée(s).", page_html)
        self.assertIn("2 fichier(s) ignoré(s)", page_html)

    def test_run_ocr_updates_text_file(self) -> None:
        image_path = self.create_image("page-ocr.jpg", 100)
        text_path = image_path.with_suffix(".txt")
        text_path.write_text("", encoding="utf-8")

        with patch("app.run_ocr_for_image", return_value="texte détecté"):
            response = self.client.post(
                "/run-ocr",
                data={"current_image": "page-ocr.jpg", "sort": "oldest", "text_filter": "all", "q": ""},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(text_path.read_text(encoding="utf-8"), "texte détecté")
        self.assertIn("Paddle OCR exécuté pour page-ocr.jpg.", response.get_data(as_text=True))

    def test_extract_text_from_paddle_result_supports_various_shapes(self) -> None:
        nested_result = [
            {"rec_texts": ["Bonjour", "le", "monde"]},
            {"text": "!"},
            [[None, "fin"]],
        ]

        self.assertEqual(extract_text_from_paddle_result(nested_result), "Bonjour\nle\nmonde\n!\nfin")

    def test_run_ocr_can_use_paddle_method(self) -> None:
        image_path = self.create_image("page-paddle.jpg", 100)
        image_path.with_suffix(".txt").write_text("", encoding="utf-8")

        with patch("app.get_paddle_ocr") as mock_get_ocr:
            mock_ocr = mock_get_ocr.return_value
            mock_ocr.predict.return_value = [{"rec_texts": ["texte paddle"]}]

            response = self.client.post(
                "/run-ocr",
                data={"current_image": "page-paddle.jpg", "sort": "oldest", "text_filter": "all", "q": ""},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Paddle OCR exécuté pour page-paddle.jpg.", response.get_data(as_text=True))
        self.assertEqual(image_path.with_suffix(".txt").read_text(encoding="utf-8"), "texte paddle")


if __name__ == "__main__":
    unittest.main()


