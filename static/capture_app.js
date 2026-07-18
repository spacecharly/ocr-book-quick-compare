document.addEventListener("DOMContentLoaded", () => {
    const page = document.querySelector(".capture-page");
    const video = document.querySelector("[data-camera-video]");
    const cameraSelect = document.querySelector("[data-camera-select]");
    const statusEl = document.querySelector("[data-capture-status]");
    const modeSelect = document.querySelector("[data-capture-mode]");
    const centerLine = document.querySelector("[data-capture-center-line]");
    const modeHintEl = document.querySelector("[data-capture-mode-hint]");
    const counterEl = document.querySelector("[data-capture-counter]");
    const resolutionEl = document.querySelector("[data-capture-resolution]");
    const prefixInput = document.querySelector("[data-capture-prefix]");
    const beepToggle = document.querySelector("[data-capture-beep]");
    const browserStatusBanner = document.querySelector("[data-browser-status-banner]");
    const enableButton = document.querySelector("[data-capture-enable]");
    const refreshButton = document.querySelector("[data-capture-refresh]");
    const captureButton = document.querySelector("[data-capture-now]");
    const startVoiceButton = document.querySelector("[data-start-voice]");
    const stopVoiceButton = document.querySelector("[data-stop-voice]");
    const rotateLeftButton = document.querySelector("[data-rotate-left]");
    const rotateRightButton = document.querySelector("[data-rotate-right]");
    const scanToggleButton = document.querySelector("[data-scan-toggle]");
    const voiceEngineIndicatorEl = document.querySelector("[data-voice-engine-indicator]");
    const voiceEngineTextEl = document.querySelector("[data-voice-engine-text]");
    const previewShell = document.querySelector(".capture-preview-shell");
    const captureFlashEl = document.querySelector("[data-capture-flash]");

    const i18n = page?.dataset || {};
    const captureSaveUrl = page?.dataset.captureSaveUrl || "/capture-save-images";
    const VOICE_CHUNK_MS = 1400;
    const CAPTURE_SETTINGS_KEY = "capture-companion-settings-v1";
    const state = {
        stream: null,
        keepListening: false,
        captureInFlight: false,
        captureCount: 0,
        audioContext: null,
        voiceStream: null,
        voiceSource: null,
        voiceProcessor: null,
        voiceSamples: [],
        voiceInterval: null,
        voiceRequestInFlight: false,
        previewRotation: 0,
        captureResolutionMode: "pending",
    };

    const detectedBrowser = (() => {
        const ua = navigator.userAgent || "";
        const vendor = navigator.vendor || "";
        if (/Chrome|CriOS|Edg\//.test(ua) && /Google/i.test(vendor || ua)) {
            return "chrome";
        }
        if (/Safari/.test(ua) && !/Chrome|CriOS|Chromium|Edg\//.test(ua)) {
            return "safari";
        }
        if (/Firefox|FxiOS/.test(ua)) {
            return "firefox";
        }
        return "unknown";
    })();

    const flashCaptureIndicator = () => {
        if (!captureFlashEl) {
            return;
        }
        captureFlashEl.classList.remove("is-flashing");
        // Force reflow so the animation restarts even for rapid captures
        void captureFlashEl.offsetWidth;
        captureFlashEl.classList.add("is-flashing");
        captureFlashEl.addEventListener("animationend", () => {
            captureFlashEl.classList.remove("is-flashing");
        }, { once: true });
    };

    const setStatus = (message, isError = false) => {
        if (!statusEl) {
            return;
        }
        statusEl.textContent = message;
        statusEl.style.color = isError ? "#b91c1c" : "#4b5563";
    };

    const setVoiceEngineState = (stateName) => {
        if (!voiceEngineIndicatorEl || !voiceEngineTextEl) {
            return;
        }

        voiceEngineIndicatorEl.classList.remove("is-idle", "is-listening", "is-processing", "is-error");

        if (stateName === "listening") {
            voiceEngineIndicatorEl.classList.add("is-listening");
            voiceEngineTextEl.textContent = i18n.i18nVoiceEngineListening || "Listening";
            return;
        }
        if (stateName === "processing") {
            voiceEngineIndicatorEl.classList.add("is-processing");
            voiceEngineTextEl.textContent = i18n.i18nVoiceEngineProcessing || "Processing audio...";
            return;
        }
        if (stateName === "error") {
            voiceEngineIndicatorEl.classList.add("is-error");
            voiceEngineTextEl.textContent = i18n.i18nVoiceEngineError || "Error";
            return;
        }

        voiceEngineIndicatorEl.classList.add("is-idle");
        voiceEngineTextEl.textContent = i18n.i18nVoiceEngineIdle || "Stopped";
    };

    const updateBrowserStatus = () => {
        if (!browserStatusBanner) {
            return;
        }

        if (detectedBrowser === "chrome") {
            browserStatusBanner.textContent = i18n.i18nBrowserStatusChrome || "Detected browser: Chrome / Chromium.";
            return;
        }
        if (detectedBrowser === "safari") {
            browserStatusBanner.textContent = i18n.i18nBrowserStatusSafari || "Detected browser: Safari.";
            return;
        }
        if (detectedBrowser === "firefox") {
            browserStatusBanner.textContent = i18n.i18nBrowserStatusFirefox || "Detected browser: Firefox.";
            return;
        }

        const fallback = i18n.i18nBrowserStatusGeneric || i18n.i18nBrowserStatusUnknown || "Detected browser: unknown.";
        browserStatusBanner.textContent = fallback.replace("__BROWSER__", navigator.userAgent || "unknown");
    };

    const updateCounter = () => {
        if (counterEl) {
            counterEl.textContent = String(state.captureCount);
        }
    };

    const updateResolutionIndicator = () => {
        if (!resolutionEl) {
            return;
        }
        if (state.captureResolutionMode === "photo") {
            resolutionEl.textContent = i18n.i18nResolutionPhoto || "Full-resolution photo";
            return;
        }
        if (state.captureResolutionMode === "video") {
            resolutionEl.textContent = i18n.i18nResolutionVideo || "Video frame fallback";
            return;
        }
        resolutionEl.textContent = i18n.i18nResolutionPending || "Resolution unknown";
    };

    const readSettings = () => {
        try {
            const raw = window.localStorage.getItem(CAPTURE_SETTINGS_KEY);
            return raw ? JSON.parse(raw) : {};
        } catch (_error) {
            return {};
        }
    };

    const persistSettings = () => {
        try {
            const settings = {
                mode: modeSelect?.value || "one_page",
                prefix: prefixInput?.value || "",
                beepEnabled: Boolean(beepToggle?.checked),
                rotation: normalizeRotation(state.previewRotation),
            };
            window.localStorage.setItem(CAPTURE_SETTINGS_KEY, JSON.stringify(settings));
        } catch (_error) {
            // ignore localStorage unavailability
        }
    };

    const applyPersistedSettings = () => {
        const settings = readSettings();
        if (modeSelect && (settings.mode === "one_page" || settings.mode === "two_pages")) {
            modeSelect.value = settings.mode;
        }
        if (prefixInput && typeof settings.prefix === "string") {
            prefixInput.value = settings.prefix;
        }
        if (beepToggle && typeof settings.beepEnabled === "boolean") {
            beepToggle.checked = settings.beepEnabled;
        }
        if (typeof settings.rotation === "number") {
            state.previewRotation = normalizeRotation(settings.rotation);
        }
    };

    const normalizedPrefix = () => {
        const raw = (prefixInput?.value || "").trim().toLowerCase();
        if (!raw) {
            return "";
        }
        return raw
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9_-]+/g, "-")
            .replace(/^-+|-+$/g, "");
    };

    const buildFilenameBase = () => {
        const prefix = normalizedPrefix();
        const slug = timestampSlug();
        return prefix ? `${prefix}-${slug}` : slug;
    };

    const playBeep = async () => {
        if (!beepToggle?.checked) {
            return;
        }

        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) {
            return;
        }

        if (!state.audioContext) {
            state.audioContext = new AudioContextCtor();
        }

        if (state.audioContext.state === "suspended") {
            await state.audioContext.resume();
        }

        const oscillator = state.audioContext.createOscillator();
        const gainNode = state.audioContext.createGain();
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(880, state.audioContext.currentTime);
        gainNode.gain.setValueAtTime(0.001, state.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.08, state.audioContext.currentTime + 0.01);
        gainNode.gain.exponentialRampToValueAtTime(0.001, state.audioContext.currentTime + 0.18);
        oscillator.connect(gainNode);
        gainNode.connect(state.audioContext.destination);
        oscillator.start();
        oscillator.stop(state.audioContext.currentTime + 0.2);
    };

    const stopTracks = (stream) => {
        if (!stream) {
            return;
        }
        stream.getTracks().forEach((track) => track.stop());
    };

    const releaseStream = () => {
        stopTracks(state.stream);
        state.stream = null;
        if (video) {
            video.srcObject = null;
        }
    };

    const timestampSlug = () => {
        const now = new Date();
        const pad = (value, width = 2) => String(value).padStart(width, "0");
        return [
            now.getFullYear(),
            pad(now.getMonth() + 1),
            pad(now.getDate()),
        ].join("") +
        "-" +
        [pad(now.getHours()), pad(now.getMinutes()), pad(now.getSeconds())].join("") +
        "-" +
        pad(now.getMilliseconds(), 3);
    };

    const updateModeUi = () => {
        const twoPages = modeSelect?.value === "two_pages";
        if (centerLine) {
            centerLine.hidden = !twoPages;
        }
        if (modeHintEl) {
            modeHintEl.style.visibility = twoPages ? "visible" : "hidden";
        }
    };

    const normalizeRotation = (angle) => {
        const normalized = angle % 360;
        return normalized < 0 ? normalized + 360 : normalized;
    };

    const applyPreviewRotation = () => {
        if (!video) {
            return;
        }
        video.style.transform = `rotate(${state.previewRotation}deg)`;
    };

    const rotatePreview = (delta) => {
        state.previewRotation = normalizeRotation(state.previewRotation + delta);
        applyPreviewRotation();
        persistSettings();
    };

    const updateScanButtonLabel = () => {
        if (!scanToggleButton || !previewShell) {
            return;
        }
        const isFullscreen = document.fullscreenElement === previewShell;
        scanToggleButton.textContent = isFullscreen
            ? (i18n.i18nScanExit || "Exit fullscreen")
            : (i18n.i18nScanEnter || "Enter fullscreen");
    };

    const toggleScanMode = async () => {
        if (!previewShell) {
            return;
        }
        try {
            if (document.fullscreenElement === previewShell) {
                await document.exitFullscreen();
            } else {
                await previewShell.requestFullscreen();
            }
        } catch (error) {
            setStatus(`Fullscreen failed: ${error.message}`, true);
        }
    };

    const populateCameraOptions = async () => {
        if (!navigator.mediaDevices?.enumerateDevices || !cameraSelect) {
            setStatus(i18n.i18nBrowserUnsupported || "Browser unsupported", true);
            return;
        }

        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const cameras = devices.filter((device) => device.kind === "videoinput");
            cameraSelect.innerHTML = "";

            if (!cameras.length) {
                cameraSelect.innerHTML = `<option value="">${i18n.i18nNoCamera || "No camera detected"}</option>`;
                setStatus(i18n.i18nNoCamera || "No camera detected", true);
                return;
            }

            cameras.forEach((camera, index) => {
                const option = document.createElement("option");
                option.value = camera.deviceId;
                option.textContent = camera.label || `${i18n.i18nCameraLabel || "Camera"} ${index + 1}`;
                cameraSelect.appendChild(option);
            });
        } catch (_error) {
            setStatus(i18n.i18nCameraRefreshFailed || "Could not refresh camera list", true);
        }
    };

    const openSelectedCamera = async () => {
        if (!cameraSelect?.value || !navigator.mediaDevices?.getUserMedia) {
            setStatus(i18n.i18nBrowserUnsupported || "Browser unsupported", true);
            return;
        }

        try {
            releaseStream();
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    deviceId: { exact: cameraSelect.value },
                    width: { ideal: 4032 },
                    height: { ideal: 3024 },
                },
                audio: false,
            });
            state.stream = stream;
            video.srcObject = stream;
            await video.play();
            const cameraName = cameraSelect.options[cameraSelect.selectedIndex]?.textContent || "camera";
            setStatus(`${i18n.i18nCameraOpened || "Camera ready"}: ${cameraName}`);
        } catch (error) {
            setStatus(`${i18n.i18nCameraFailed || "Camera access failed"}: ${error.message}`, true);
        }
    };

    const requestCameraAccess = async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
            setStatus(i18n.i18nBrowserUnsupported || "Browser unsupported", true);
            return;
        }

        try {
            const tempStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            stopTracks(tempStream);
            await populateCameraOptions();
            if (cameraSelect?.value) {
                await openSelectedCamera();
            }
            setStatus(i18n.i18nCameraEnabled || "Camera access granted");
        } catch (error) {
            setStatus(`${i18n.i18nCameraFailed || "Camera access failed"}: ${error.message}`, true);
        }
    };

    const canvasToBlob = (canvas) => new Promise((resolve, reject) => {
        canvas.toBlob((blob) => {
            if (!blob) {
                reject(new Error("Could not encode image as JPEG"));
                return;
            }
            resolve(blob);
        }, "image/jpeg", 0.95);
    });

    const saveCapturedBlobsToServer = async (captures) => {
        const formData = new FormData();
        captures.forEach((capture) => {
            formData.append("images", capture.blob, capture.filename);
        });

        const response = await fetch(captureSaveUrl, { method: "POST", body: formData });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.message || "Capture upload failed");
        }
        return Array.isArray(payload.filenames) ? payload.filenames : captures.map((item) => item.filename);
    };

    const captureCanvas = (source, sx, sy, sw, sh, dw, dh) => {
        const canvas = document.createElement("canvas");
        canvas.width = dw;
        canvas.height = dh;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(source, sx, sy, sw, sh, 0, 0, dw, dh);
        return canvas;
    };

    const blobToCanvas = async (blob) => {
        if (typeof createImageBitmap === "function") {
            const bitmap = await createImageBitmap(blob);
            const canvas = document.createElement("canvas");
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(bitmap, 0, 0);
            bitmap.close();
            return canvas;
        }

        const imageUrl = URL.createObjectURL(blob);
        try {
            const image = await new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => resolve(img);
                img.onerror = () => reject(new Error("Could not decode captured image"));
                img.src = imageUrl;
            });
            const canvas = document.createElement("canvas");
            canvas.width = image.naturalWidth;
            canvas.height = image.naturalHeight;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(image, 0, 0);
            return canvas;
        } finally {
            URL.revokeObjectURL(imageUrl);
        }
    };

    const buildCaptureSourceCanvas = async () => {
        const track = state.stream?.getVideoTracks?.()[0];
        if (track && typeof window.ImageCapture === "function") {
            try {
                const imageCapture = new window.ImageCapture(track);
                const photoBlob = await imageCapture.takePhoto();
                state.captureResolutionMode = "photo";
                updateResolutionIndicator();
                return await blobToCanvas(photoBlob);
            } catch (_error) {
                // Fallback to current video frame when still capture is unavailable.
            }
        }

        const width = video?.videoWidth || 0;
        const height = video?.videoHeight || 0;
        if (!width || !height) {
            throw new Error(i18n.i18nCaptureMissingStream || "No live camera stream available");
        }

        state.captureResolutionMode = "video";
        updateResolutionIndicator();
        return captureCanvas(video, 0, 0, width, height, width, height);
    };

    const rotateCanvasBy90Steps = (sourceCanvas, rotationDegrees) => {
        const rotation = normalizeRotation(rotationDegrees);
        if (rotation === 0) {
            return sourceCanvas;
        }

        const shouldSwap = rotation === 90 || rotation === 270;
        const outputCanvas = document.createElement("canvas");
        outputCanvas.width = shouldSwap ? sourceCanvas.height : sourceCanvas.width;
        outputCanvas.height = shouldSwap ? sourceCanvas.width : sourceCanvas.height;

        const ctx = outputCanvas.getContext("2d");
        ctx.translate(outputCanvas.width / 2, outputCanvas.height / 2);
        ctx.rotate((rotation * Math.PI) / 180);
        ctx.drawImage(sourceCanvas, -sourceCanvas.width / 2, -sourceCanvas.height / 2);
        return outputCanvas;
    };

    const mergeVoiceSamples = (chunks) => {
        if (!chunks.length) {
            return new Float32Array(0);
        }
        const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const merged = new Float32Array(totalLength);
        let offset = 0;
        chunks.forEach((chunk) => {
            merged.set(chunk, offset);
            offset += chunk.length;
        });
        return merged;
    };

    const encodeWavFromFloat32 = (samples, sampleRate) => {
        const buffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(buffer);
        const writeString = (offset, value) => {
            for (let index = 0; index < value.length; index += 1) {
                view.setUint8(offset + index, value.charCodeAt(index));
            }
        };

        writeString(0, "RIFF");
        view.setUint32(4, 36 + samples.length * 2, true);
        writeString(8, "WAVE");
        writeString(12, "fmt ");
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, "data");
        view.setUint32(40, samples.length * 2, true);

        let offset = 44;
        for (let index = 0; index < samples.length; index += 1) {
            const value = Math.max(-1, Math.min(1, samples[index]));
            view.setInt16(offset, value < 0 ? value * 0x8000 : value * 0x7fff, true);
            offset += 2;
        }

        return new Blob([buffer], { type: "audio/wav" });
    };

    const sendVoiceChunk = async () => {
        if (!state.keepListening || state.voiceRequestInFlight) {
            return;
        }

        const samples = mergeVoiceSamples(state.voiceSamples);
        state.voiceSamples = [];
        if (!samples.length) {
            return;
        }

        const sampleRate = Math.round(state.audioContext?.sampleRate || 16000);
        const wavBlob = encodeWavFromFloat32(samples, sampleRate);
        const formData = new FormData();
        formData.append("audio", wavBlob, "voice.wav");

        state.voiceRequestInFlight = true;
        setVoiceEngineState("processing");
        try {
            const response = await fetch("/capture-voice-detect", { method: "POST", body: formData });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                setStatus(payload.message || (i18n.i18nVoiceNetworkUnavailable || "Voice endpoint unavailable"), true);
                setVoiceEngineState("error");
                return;
            }

            if (payload.detected) {
                setStatus(i18n.i18nTriggerDetected || "Trigger word detected: next");
                captureNow();
            }
            if (state.keepListening) {
                setVoiceEngineState("listening");
            }
        } catch (_error) {
            setStatus(i18n.i18nVoiceNetworkUnavailable || "Speech recognition network error keeps happening", true);
            setVoiceEngineState("error");
        } finally {
            state.voiceRequestInFlight = false;
        }
    };

    const captureNow = async () => {
        if (state.captureInFlight) {
            return;
        }
        if (!state.stream) {
            setStatus(i18n.i18nCaptureMissingStream || "No live camera stream available", true);
            return;
        }

        const baseName = buildFilenameBase();
        state.captureInFlight = true;
        try {
            const sourceCanvas = await buildCaptureSourceCanvas();
            const width = sourceCanvas.width;
            const height = sourceCanvas.height;

            if (modeSelect?.value === "two_pages") {
                const midpoint = Math.floor(width / 2);
                const leftCanvas = rotateCanvasBy90Steps(
                    captureCanvas(sourceCanvas, 0, 0, midpoint, height, midpoint, height),
                    state.previewRotation
                );
                const rightCanvas = rotateCanvasBy90Steps(
                    captureCanvas(sourceCanvas, midpoint, 0, width - midpoint, height, width - midpoint, height),
                    state.previewRotation
                );
                const leftBlob = await canvasToBlob(leftCanvas);
                const rightBlob = await canvasToBlob(rightCanvas);
                const rotation = normalizeRotation(state.previewRotation);
                // At 180 deg, horizontal sides are mirrored in the final visual result.
                const isMirroredLeftRight = rotation === 180;
                const savedNames = await saveCapturedBlobsToServer([
                    {
                        filename: `${baseName}-left.jpg`,
                        blob: isMirroredLeftRight ? rightBlob : leftBlob,
                    },
                    {
                        filename: `${baseName}-right.jpg`,
                        blob: isMirroredLeftRight ? leftBlob : rightBlob,
                    },
                ]);
                state.captureCount += 2;
                updateCounter();
                await playBeep();
                flashCaptureIndicator();
                setStatus(`${i18n.i18nCaptureSavedTwo || "Saved 2 pages"}: ${savedNames.join(", ")}`);
                return;
            }

            const canvas = rotateCanvasBy90Steps(
                sourceCanvas,
                state.previewRotation
            );
            const blob = await canvasToBlob(canvas);
            const savedNames = await saveCapturedBlobsToServer([{ filename: `${baseName}.jpg`, blob }]);
            state.captureCount += 1;
            updateCounter();
            await playBeep();
            flashCaptureIndicator();
            setStatus(`${i18n.i18nCaptureSavedOne || "Saved 1 page"}: ${savedNames[0] || `${baseName}.jpg`}`);
        } catch (error) {
            setStatus(`Capture failed: ${error.message}`, true);
        } finally {
            state.captureInFlight = false;
        }
    };


    const stopVoice = (options = {}) => {
        const { silentStatus = false, keepIndicatorError = false } = options;
        state.keepListening = false;

        if (state.voiceInterval) {
            window.clearInterval(state.voiceInterval);
            state.voiceInterval = null;
        }

        if (state.voiceProcessor) {
            state.voiceProcessor.disconnect();
            state.voiceProcessor.onaudioprocess = null;
            state.voiceProcessor = null;
        }

        if (state.voiceSource) {
            state.voiceSource.disconnect();
            state.voiceSource = null;
        }

        if (state.voiceStream) {
            stopTracks(state.voiceStream);
            state.voiceStream = null;
        }

        state.voiceSamples = [];
        if (!silentStatus) {
            setStatus(i18n.i18nVoiceStopped || "Voice recognition stopped");
        }
        if (!keepIndicatorError) {
            setVoiceEngineState("idle");
        }
    };

    const startVoice = async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
            setStatus(i18n.i18nVoiceUnsupported || "Speech recognition is not supported in this browser", true);
            return;
        }

        stopVoice({ silentStatus: true });

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                },
                video: false,
            });

            const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextCtor) {
                stopTracks(stream);
                setStatus(i18n.i18nVoiceUnsupported || "Speech recognition is not supported in this browser", true);
                return;
            }

            if (!state.audioContext || state.audioContext.state === "closed") {
                state.audioContext = new AudioContextCtor();
            }
            if (state.audioContext.state === "suspended") {
                await state.audioContext.resume();
            }

            const source = state.audioContext.createMediaStreamSource(stream);
            const processor = state.audioContext.createScriptProcessor(4096, 1, 1);
            const silentGain = state.audioContext.createGain();
            silentGain.gain.value = 0;

            processor.onaudioprocess = (event) => {
                if (!state.keepListening) {
                    return;
                }
                const channelData = event.inputBuffer.getChannelData(0);
                state.voiceSamples.push(new Float32Array(channelData));
            };

            source.connect(processor);
            processor.connect(silentGain);
            silentGain.connect(state.audioContext.destination);

            state.voiceStream = stream;
            state.voiceSource = source;
            state.voiceProcessor = processor;
            state.keepListening = true;
            state.voiceInterval = window.setInterval(sendVoiceChunk, VOICE_CHUNK_MS);
            setVoiceEngineState("listening");
            setStatus(i18n.i18nVoiceStarted || "Voice recognition started");
        } catch (_error) {
            setVoiceEngineState("error");
            setStatus(i18n.i18nVoicePermissionBlocked || "Microphone is blocked", true);
            stopVoice({ silentStatus: true, keepIndicatorError: true });
        }
    };

    enableButton?.addEventListener("click", requestCameraAccess);
    refreshButton?.addEventListener("click", populateCameraOptions);
    cameraSelect?.addEventListener("change", openSelectedCamera);
    captureButton?.addEventListener("click", captureNow);
    startVoiceButton?.addEventListener("click", startVoice);
    stopVoiceButton?.addEventListener("click", stopVoice);
    rotateLeftButton?.addEventListener("click", () => rotatePreview(-90));
    rotateRightButton?.addEventListener("click", () => rotatePreview(90));
    scanToggleButton?.addEventListener("click", toggleScanMode);
    modeSelect?.addEventListener("change", updateModeUi);
    modeSelect?.addEventListener("change", persistSettings);
    prefixInput?.addEventListener("input", persistSettings);
    beepToggle?.addEventListener("change", persistSettings);
    document.addEventListener("fullscreenchange", updateScanButtonLabel);

    applyPersistedSettings();
    updateCounter();
    updateResolutionIndicator();
    updateModeUi();
    applyPreviewRotation();
    updateScanButtonLabel();
    updateBrowserStatus();
    setVoiceEngineState("idle");
    populateCameraOptions();

    if (!navigator.mediaDevices?.getUserMedia) {
        setStatus(i18n.i18nBrowserUnsupported || "Browser unsupported", true);
    }

    window.addEventListener("beforeunload", () => {
        stopVoice();
        releaseStream();
    });
});



