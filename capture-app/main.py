from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

import cv2
from PIL import Image, ImageTk

from capture_core import build_capture_paths, draw_alignment_overlay, split_two_pages
from voice_trigger import VoiceTriggerService

CAMERA_SCAN_RANGE = 10


class CaptureApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OCR Capture App")
        self.geometry("1200x820")

        self.base_dir = Path(__file__).resolve().parent
        self.default_output_dir = (self.base_dir.parent / "images").resolve()
        self.model_path = self.base_dir / "models" / "vosk-model-small-en-us-0.15"

        self.output_dir_var = tk.StringVar(value=str(self.default_output_dir))
        self.capture_mode_var = tk.StringVar(value="one_page")
        self.camera_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.voice_status_var = tk.StringVar(value="Voice: idle")

        self.camera_options: list[tuple[str, int]] = []
        self.capture = None
        self.last_raw_frame = None
        self.preview_image = None
        self.after_id = None

        self.voice_service = VoiceTriggerService(
            model_path=self.model_path,
            trigger_word="next",
            on_trigger=lambda: self.after(0, self.capture_now),
            on_status=lambda msg: self.after(0, self.voice_status_var.set, msg),
        )

        self._build_ui()
        self.refresh_cameras()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        controls = ttk.Frame(self, padding=12)
        controls.pack(fill=tk.X)

        ttk.Label(controls, text="Camera").grid(row=0, column=0, sticky=tk.W)
        self.camera_combo = ttk.Combobox(controls, textvariable=self.camera_var, width=34, state="readonly")
        self.camera_combo.grid(row=0, column=1, sticky=tk.W, padx=(8, 8))
        self.camera_combo.bind("<<ComboboxSelected>>", lambda _event: self.open_selected_camera())

        ttk.Button(controls, text="Refresh cameras", command=self.refresh_cameras).grid(row=0, column=2, sticky=tk.W)

        ttk.Label(controls, text="Mode").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        mode_combo = ttk.Combobox(
            controls,
            textvariable=self.capture_mode_var,
            values=["one_page", "two_pages"],
            width=16,
            state="readonly",
        )
        mode_combo.grid(row=1, column=1, sticky=tk.W, padx=(8, 8), pady=(10, 0))

        ttk.Label(controls, text="Output folder").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(controls, textvariable=self.output_dir_var, width=60).grid(row=2, column=1, sticky=tk.W, padx=(8, 8), pady=(10, 0))
        ttk.Button(controls, text="Choose...", command=self.choose_output_dir).grid(row=2, column=2, sticky=tk.W, pady=(10, 0))

        ttk.Button(controls, text="Capture now", command=self.capture_now).grid(row=3, column=0, sticky=tk.W, pady=(12, 0))
        ttk.Button(controls, text="Start voice", command=self.start_voice).grid(row=3, column=1, sticky=tk.W, pady=(12, 0))
        ttk.Button(controls, text="Stop voice", command=self.stop_voice).grid(row=3, column=2, sticky=tk.W, pady=(12, 0))

        ttk.Label(controls, textvariable=self.status_var).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        ttk.Label(controls, textvariable=self.voice_status_var).grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(2, 0))

        self.preview_label = ttk.Label(self)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(self.default_output_dir))
        if selected:
            self.output_dir_var.set(selected)

    def refresh_cameras(self) -> None:
        self.camera_options = self.detect_cameras()
        labels = [label for label, _idx in self.camera_options]
        self.camera_combo["values"] = labels

        if not labels:
            self.camera_var.set("")
            self.status_var.set("No camera detected")
            self.release_camera()
            return

        if self.camera_var.get() not in labels:
            self.camera_var.set(labels[0])
        self.open_selected_camera()

    def detect_cameras(self) -> list[tuple[str, int]]:
        options: list[tuple[str, int]] = []
        backend = cv2.CAP_AVFOUNDATION if hasattr(cv2, "CAP_AVFOUNDATION") else 0

        for idx in range(CAMERA_SCAN_RANGE + 1):
            cap = cv2.VideoCapture(idx, backend)
            if not cap.isOpened():
                cap.release()
                continue

            ok, _frame = cap.read()
            if ok:
                options.append((f"Camera {idx}", idx))
            cap.release()

        return options

    def open_selected_camera(self) -> None:
        label = self.camera_var.get()
        selected = [idx for lbl, idx in self.camera_options if lbl == label]
        if not selected:
            return

        self.release_camera()
        index = selected[0]
        backend = cv2.CAP_AVFOUNDATION if hasattr(cv2, "CAP_AVFOUNDATION") else 0
        self.capture = cv2.VideoCapture(index, backend)

        if not self.capture.isOpened():
            self.status_var.set(f"Cannot open camera index {index}")
            self.release_camera()
            return

        self.status_var.set(f"Camera ready: {label}")
        self.start_preview_loop()

    def start_preview_loop(self) -> None:
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.update_preview()

    def update_preview(self) -> None:
        if self.capture is None:
            return

        ok, frame = self.capture.read()
        if ok:
            self.last_raw_frame = frame
            show_overlay = self.capture_mode_var.get() == "two_pages"
            preview_frame = draw_alignment_overlay(frame, show_overlay)
            rgb = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)

            max_width = max(self.preview_label.winfo_width(), 100)
            max_height = max(self.preview_label.winfo_height(), 100)
            image.thumbnail((max_width, max_height))

            self.preview_image = ImageTk.PhotoImage(image=image)
            self.preview_label.configure(image=self.preview_image)

        self.after_id = self.after(30, self.update_preview)

    def capture_now(self) -> None:
        if self.last_raw_frame is None:
            self.status_var.set("No frame available yet")
            return

        output_dir = Path(self.output_dir_var.get()).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        mode = self.capture_mode_var.get()
        paths = build_capture_paths(output_dir, mode)

        if mode == "two_pages":
            left, right = split_two_pages(self.last_raw_frame)
            cv2.imwrite(str(paths[0]), left)
            cv2.imwrite(str(paths[1]), right)
            self.status_var.set(f"Saved 2 pages: {paths[0].name}, {paths[1].name}")
            return

        cv2.imwrite(str(paths[0]), self.last_raw_frame)
        self.status_var.set(f"Saved 1 page: {paths[0].name}")

    def start_voice(self) -> None:
        self.voice_service.start()

    def stop_voice(self) -> None:
        self.voice_service.stop()

    def release_camera(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def on_close(self) -> None:
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.stop_voice()
        self.release_camera()
        self.destroy()


def main() -> None:
    app = CaptureApp()
    app.mainloop()


if __name__ == "__main__":
    main()

