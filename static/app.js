document.addEventListener("DOMContentLoaded", () => {
    const zoomImage = document.querySelector("[data-zoom-image]");
    const zoomRange = document.querySelector("[data-zoom-range]");
    const zoomButtons = document.querySelectorAll("[data-zoom-action]");

    const rotateImage = document.querySelector("[data-rotate-image]");
    const rotateButtons = document.querySelectorAll("[data-rotate-action]");
    const rotateAngleDisplay = document.querySelector("[data-rotate-angle]");

    const editor = document.querySelector("[data-editor]");
    const imageWrapper = document.querySelector(".image-wrapper");

    let currentRotation = 0;

    const saveForm = document.getElementById("save-form");
    const validateForm = document.getElementById("validate-form");
    const createTextsForm = document.getElementById("create-texts-form");
    const prevLink = document.getElementById("prev-link");
    const nextLink = document.getElementById("next-link");

    const uploadForm = document.querySelector("[data-upload-form]");
    const uploadInput = document.querySelector("[data-upload-input]");
    const uploadDropzone = document.querySelector("[data-upload-dropzone]");
    const uploadLabel = document.querySelector("[data-upload-label]");

    const currentImageInput = document.querySelector("[data-current-image]");
    const saveState = document.querySelector("[data-save-state]");
    const saveStateText = document.querySelector("[data-save-state-text]");
    const validateNextButton = document.querySelector('[data-submit-kind="validate-next"]');
    const viewQueryInput = document.querySelector("[data-view-query]");
    const viewSortInput = document.querySelector("[data-view-sort]");
    const viewTextFilterInput = document.querySelector("[data-view-text-filter]");
    const filenameDisplay = document.querySelector("[data-filename-display]");
    const filenameInput = document.querySelector("[data-filename-input]");
    const renameForm = document.querySelector("[data-rename-form]");
    const renameBaseInput = document.querySelector("[data-rename-base]");

    let autosaveTimer = null;
    let isDirty = false;

    const setSaveState = (mode, message) => {
        if (!saveState || !saveStateText) {
            return;
        }

        saveState.classList.remove("is-saved", "is-dirty", "is-saving", "is-error");
        saveState.classList.add(mode);
        saveStateText.textContent = message;
    };

    const clampZoom = (value) => Math.min(3, Math.max(0.5, value));

    const applyZoom = (value) => {
        if (!zoomImage || !zoomRange) {
            return;
        }

        const normalizedValue = clampZoom(Number(value));
        zoomImage.style.transform = `scale(${normalizedValue})`;
        zoomRange.value = String(normalizedValue);
    };

    if (zoomImage && zoomRange) {
        applyZoom(zoomRange.value);

        zoomRange.addEventListener("input", (event) => {
            applyZoom(event.target.value);
        });

        zoomButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const action = button.dataset.zoomAction;
                const currentValue = Number(zoomRange.value);

                if (action === "in") {
                    applyZoom(currentValue + 0.1);
                } else if (action === "out") {
                    applyZoom(currentValue - 0.1);
                } else if (action === "reset") {
                    applyZoom(1);
                }
            });
        });
    }

    const applyRotation = (angle) => {
        if (!rotateImage) return;
        currentRotation = (angle % 360 + 360) % 360;
        rotateImage.style.transform = `rotate(${currentRotation}deg)`;
        if (rotateAngleDisplay) rotateAngleDisplay.textContent = `${currentRotation}°`;
    };

    if (rotateImage && rotateButtons.length > 0) {
        rotateButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const action = button.dataset.rotateAction;
                if (action === "cw") {
                    applyRotation(currentRotation + 90);
                } else if (action === "ccw") {
                    applyRotation(currentRotation - 90);
                }
            });
        });
    }

    if (editor && imageWrapper) {
        imageWrapper.addEventListener("scroll", () => {
            if (editor) {
                editor.scrollLeft = imageWrapper.scrollLeft;
            }
        });
        editor.addEventListener("scroll", () => {
            if (imageWrapper) {
                imageWrapper.scrollLeft = editor.scrollLeft;
            }
        });
    }

    const autosave = async () => {
        if (!saveForm || !editor || !currentImageInput || !currentImageInput.value) {
            return;
        }

        setSaveState("is-saving", "Autosave en cours…");

        try {
            const response = await fetch(saveForm.dataset.autosaveUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    current_image: currentImageInput.value,
                    text: editor.value,
                    q: viewQueryInput?.value || "",
                    sort: viewSortInput?.value || "oldest",
                    text_filter: viewTextFilterInput?.value || "all",
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const payload = await response.json();
            isDirty = false;
            setSaveState("is-saved", `Autosaved at ${payload.timestamp}`);
        } catch (error) {
            setSaveState("is-error", "Autosave failed");
        }
    };

    const scheduleAutosave = () => {
        if (autosaveTimer) {
            window.clearTimeout(autosaveTimer);
        }

        autosaveTimer = window.setTimeout(() => {
            autosave();
        }, Number(saveForm?.dataset.autosaveInterval || 1500));
    };

    if (editor) {
        editor.addEventListener("input", () => {
            isDirty = true;
            setSaveState("is-dirty", "Texte modifié non sauvegardé");
            scheduleAutosave();
        });
    }

    window.addEventListener("beforeunload", (event) => {
        if (!isDirty) {
            return;
        }

        event.preventDefault();
        event.returnValue = "";
    });

    if (validateForm) {
        validateForm.addEventListener("submit", (event) => {
            const confirmMessage = validateForm.dataset.confirmMessage || "Confirmer la validation ?";
            if (!window.confirm(confirmMessage)) {
                event.preventDefault();
            }
        });
    }

    if (saveForm) {
        saveForm.addEventListener("submit", (event) => {
            const submitter = event.submitter;
            const submitKind = submitter?.dataset.submitKind;

            if (submitKind === "validate-next") {
                const message = isDirty
                    ? "Sauvegarder le texte courant, valider cette page et passer à la suivante ?"
                    : "Valider cette page et passer à la suivante ?";
                if (!window.confirm(message)) {
                    event.preventDefault();
                    return;
                }
            }

            if (submitKind === "ocr" && isDirty) {
                const confirmed = window.confirm(
                    "Le texte affiché a été modifié. Lancer l'OCR va remplacer le contenu actuel. Continuer ?"
                );
                if (!confirmed) {
                    event.preventDefault();
                    return;
                }
            }

            if (submitKind === "save") {
                setSaveState("is-saving", "Sauvegarde…");
            }

            isDirty = false;
        });
    }

    document.addEventListener("keydown", (event) => {
        const key = event.key.toLowerCase();
        const withCommand = event.metaKey || event.ctrlKey;

        if (withCommand && key === "s" && saveForm) {
            event.preventDefault();
            saveForm.requestSubmit(document.getElementById("save-button"));
            return;
        }

        if (!event.altKey) {
            return;
        }

        if (key === "v" && event.shiftKey && validateForm) {
            event.preventDefault();
            validateForm.requestSubmit();
        } else if (key === "v" && validateNextButton) {
            event.preventDefault();
            validateNextButton.click();
        } else if (key === "c" && createTextsForm) {
            event.preventDefault();
            createTextsForm.requestSubmit();
        } else if (event.key === "ArrowLeft" && prevLink) {
            event.preventDefault();
            window.location.href = prevLink.href;
        } else if (event.key === "ArrowRight" && nextLink) {
            event.preventDefault();
            window.location.href = nextLink.href;
        }
    });

    if (uploadForm && uploadInput && uploadDropzone) {
        const updateUploadLabel = (count) => {
            if (!uploadLabel) {
                return;
            }

            if (count > 0) {
                uploadLabel.textContent = `${count} file(s) ready. Drop more or submit to import.`;
            } else {
                uploadLabel.innerHTML = 'Glisser-déposer des <code>.jpg</code>/<code>.jpeg</code> ici ou cliquer pour sélectionner.';
            }
        };

        uploadInput.addEventListener("change", () => {
            updateUploadLabel(uploadInput.files.length);
            if (uploadInput.files.length > 0) {
                uploadForm.requestSubmit();
            }
        });

        ["dragenter", "dragover"].forEach((eventName) => {
            uploadDropzone.addEventListener(eventName, (event) => {
                event.preventDefault();
                uploadDropzone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach((eventName) => {
            uploadDropzone.addEventListener(eventName, (event) => {
                event.preventDefault();
                uploadDropzone.classList.remove("dragover");
            });
        });

        uploadDropzone.addEventListener("drop", (event) => {
            const files = event.dataTransfer?.files;
            if (!files || files.length === 0) {
                return;
            }

            const dataTransfer = new DataTransfer();
            Array.from(files).forEach((file) => dataTransfer.items.add(file));
            uploadInput.files = dataTransfer.files;
            updateUploadLabel(uploadInput.files.length);
            uploadForm.requestSubmit();
        });

        uploadDropzone.addEventListener("click", (event) => {
            if (event.target !== uploadInput) {
                uploadInput.click();
            }
        });
    }

    if (filenameDisplay && filenameInput && renameForm && renameBaseInput) {
        const closeEditor = () => {
            filenameInput.style.display = "none";
            filenameDisplay.style.display = "inline";
        };

        filenameDisplay.addEventListener("click", () => {
            filenameDisplay.style.display = "none";
            filenameInput.style.display = "inline";
            filenameInput.focus();
            filenameInput.select();
        });

        filenameInput.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                filenameInput.value = filenameDisplay.textContent || "";
                closeEditor();
                return;
            }

            if (event.key === "Enter") {
                event.preventDefault();
                const nextBase = filenameInput.value.trim();
                if (!nextBase || nextBase === (filenameDisplay.textContent || "").trim()) {
                    closeEditor();
                    return;
                }

                renameBaseInput.value = nextBase;
                renameForm.requestSubmit();
            }
        });

        filenameInput.addEventListener("blur", () => {
            filenameInput.value = filenameDisplay.textContent || "";
            closeEditor();
        });
    }
});





