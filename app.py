import os
import shutil
import subprocess
import sys
import zipfile
import io
import json
import wave
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, send_from_directory, url_for

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_IMPORT_ERROR = ""
except Exception as exc:
    PaddleOCR = None
    PADDLEOCR_IMPORT_ERROR = str(exc)

try:
    from vosk import KaldiRecognizer, Model as VoskModel
except Exception:
    KaldiRecognizer = None
    VoskModel = None

IMAGE_EXTENSIONS = {".jpg", ".jpeg"}
SORT_OPTIONS = {"oldest", "newest", "name_asc", "name_desc", "text_length_desc"}
TEXT_FILTER_OPTIONS = {"all", "empty", "filled"}
THUMBNAILS_PER_PAGE = 20
SUPPORTED_LANGS = ("fr", "en", "it", "de")
SUPPORTED_OCR_LANGS = ("", "fr", "en", "it", "de")
LANGUAGE_LABELS = {
    "fr": "Français",
    "en": "English",
    "it": "Italiano",
    "de": "Deutsch",
}

TRANSLATIONS = {
    "fr": {
        "title": "OCR Book Quick Compare",
        "subtitle": "v4 - Correction mise en page",
        "dropzone_title": "Déposer images ici",
        "dropzone_hint": "ou cliquer pour sélectionner",
        "auto_ocr": "OCR auto",
        "create_txt": "Créer les .txt manquants",
        "export": "Exporter les .txt du projet",
        "undo": "Annuler la dernière validation",
        "ocr_language": "Langue OCR",
        "ocr_lang_auto": "Automatique (langue du site)",
        "total_pages": "Pages au total",
        "validated": "Validées",
        "progress": "Progression",
        "to_process": "À traiter",
        "image": "Image",
        "previous": "Précédent",
        "next": "Suivant",
        "thumbnails": "Miniatures",
        "thumbnail_page": "Page {page} / {total}",
        "prev_page": "Page précédente",
        "next_page": "Page suivante",
        "text_ocr": "Texte OCR",
        "save": "Sauvegarder",
        "validate_next": "Valider & Suivant",
        "paddle_ocr": "Paddle OCR",
        "empty_state_title": "Aucune page disponible",
        "empty_state_hint": "Commence par importer des images avec le formulaire ci-dessus.",
        "flash_created_txt": "{count} fichier(s) texte créé(s).",
        "flash_no_new_txt": "Aucun nouveau fichier texte à créer.",
        "flash_uploaded_images": "{count} image(s) importée(s).",
        "flash_auto_ocr_suffix": " OCR auto appliqué.",
        "flash_skipped_files": "{count} fichier(s) ignoré(s) (doublon ou format non supporté).",
        "launch_capture_app": "Ouvrir Capture App",
        "working_folder": "Working Folder",
        "working_folder_hint": "Chemin absolu du dossier de travail partagé",
        "choose_working_folder": "Choisir dossier travail",
        "apply_working_folder": "Appliquer",
        "flash_working_folder_updated": "Working Folder mis à jour: {path}",
        "flash_working_folder_invalid": "Working Folder invalide: {error}",
        "flash_working_folder_picker_unavailable": "Le sélecteur de dossier Finder est indisponible sur ce système.",
        "flash_working_folder_picker_failed": "Impossible d'ouvrir le sélecteur Finder: {error}",
        "capture_title": "Capture App",
        "capture_subtitle": "Prise de vue depuis le navigateur avec sélection caméra, voix et découpe 2 pages.",
        "capture_back": "Retour à OCR Book Quick Compare",
        "capture_enable_camera": "Activer la caméra",
        "capture_refresh_cameras": "Rafraîchir les caméras",
        "capture_camera": "Caméra",
        "capture_mode": "Mode",
        "capture_rotation": "Rotation",
        "capture_resolution": "Resolution",
        "capture_rotate_left": "↺ -90°",
        "capture_rotate_right": "↻ +90°",
        "capture_scan_mode": "Mode scan",
        "capture_scan_enter": "Plein ecran",
        "capture_scan_exit": "Quitter plein ecran",
        "capture_mode_one": "1 page à la fois",
        "capture_mode_two": "2 pages à la fois",
        "capture_output_folder": "Dossier de sauvegarde",
        "capture_save_to_working_folder": "Enregistrement direct dans le Working Folder",
        "capture_choose_folder": "Choisir un dossier",
        "capture_capture_now": "Capturer maintenant",
        "capture_start_voice": "Démarrer la voix",
        "capture_stop_voice": "Arrêter la voix",
        "capture_prefix": "Préfixe de nommage",
        "capture_prefix_hint": "Optionnel. Exemple: livre-a",
        "capture_counter": "Captures réalisées",
        "capture_beep": "Bip audio après capture",
        "capture_browser_status": "Compatibilité navigateur",
        "capture_browser_status_unknown": "Navigateur détecté: inconnu.",
        "capture_browser_status_chrome": "Navigateur détecté: Chrome / Chromium. Support recommandé pour caméra, dossier et voix.",
        "capture_browser_status_safari": "Navigateur détecté: Safari. Caméra généralement OK, mais dossier et voix peuvent être limités.",
        "capture_browser_status_firefox": "Navigateur détecté: Firefox. Caméra généralement OK, mais dossier et voix peuvent être limités.",
        "capture_browser_status_generic": "Navigateur détecté: {name}. Certaines APIs peuvent varier selon la version.",
        "capture_voice_hint": "Mot déclencheur: “next” (anglais).",
        "capture_alignment_hint": "En mode 2 pages, aligne la reliure du livre sur la ligne centrale.",
        "capture_browser_note": "Conseil: Chrome est recommandé pour la sélection de dossier. Safari peut fonctionner pour la caméra mais pas forcément pour le choix du dossier.",
        "capture_status_ready": "Prêt. Active la caméra puis sélectionne la source souhaitée.",
        "capture_status_browser_unsupported": "Ce navigateur ne supporte pas toutes les API nécessaires (caméra ou reconnaissance vocale).",
        "capture_status_open_new_tab": "La Capture App s'ouvre maintenant dans un nouvel onglet.",
        "capture_voice_browser_not_supported": "La commande vocale n'est pas fiable sur ce navigateur. Utilise Chrome pour le mot déclencheur 'next'.",
        "capture_voice_network_retry": "Erreur réseau de reconnaissance vocale. Nouvelle tentative automatique...",
        "capture_voice_network_unavailable": "Erreur réseau de reconnaissance vocale persistante. Vérifie la connexion Internet ou passe sur Chrome.",
        "capture_voice_permission_blocked": "Micro bloqué. Autorise le micro dans le navigateur puis relance la voix.",
        "capture_voice_engine": "Moteur vocal",
        "capture_voice_engine_idle": "Arrêté",
        "capture_voice_engine_listening": "En écoute",
        "capture_voice_engine_processing": "Analyse audio...",
        "capture_voice_engine_error": "Erreur",
        "flash_no_file_received": "Aucun fichier reçu.",
        "flash_no_page_save": "Aucune page à mettre à jour.",
        "flash_text_updated": "Texte mis à jour pour {name}.",
        "flash_no_page_rename": "Aucune page à renommer.",
        "flash_renamed": "Fichier renommé: {name}",
        "flash_no_page_ocr": "Aucune page disponible pour lancer l'OCR.",
        "flash_ocr_empty": "Paddle OCR n'a renvoyé aucun texte pour {name}.",
        "flash_ocr_done": "Paddle OCR exécuté pour {name}.",
        "flash_no_page_validate": "Aucune page à valider.",
        "flash_page_validated": "Page validée: {name}.",
        "flash_page_saved_validated": "Page sauvegardée et validée: {name}.",
        "flash_undo_done": "Dernière validation annulée ({count} fichier(s) restauré(s)).",
        "flash_undo_none": "Aucune validation à annuler.",
        "flash_undo_conflict": "Annulation impossible: {count} validation(s) bloquée(s) car le nom existe déjà dans le dossier actif.",
        "error_target_exists_in_done": "Le fichier cible existe déjà dans check-done. Supprime-le ou renomme-le avant de valider.",
        "error_rename_empty": "Le nom ne peut pas être vide.",
        "error_rename_invalid": "Le nom contient des caractères non autorisés.",
        "error_rename_exists": "Un fichier avec ce nom existe déjà.",
        "js_autosave_saving": "Autosave en cours...",
        "js_autosaved_at": "Autosauvegardé à",
        "js_autosave_failed": "Autosave échoué",
        "js_dirty": "Texte modifié non sauvegardé",
        "js_save_saving": "Sauvegarde...",
        "js_confirm_validate_next_dirty": "Sauvegarder le texte courant, valider cette page et passer à la suivante ?",
        "js_confirm_validate_next": "Valider cette page et passer à la suivante ?",
        "js_confirm_ocr_overwrite": "Le texte affiché a été modifié. Lancer l'OCR va remplacer le contenu actuel. Continuer ?",
        "js_upload_ready": "{count} fichier(s) prêt(s). Déposez-en d'autres ou relâchez pour importer.",
    },
    "en": {
        "title": "OCR Book Quick Compare",
        "subtitle": "v5",
        "dropzone_title": "Drop images here",
        "dropzone_hint": "or click to select",
        "auto_ocr": "Auto OCR",
        "create_txt": "Create missing .txt files",
        "export": "Export project .txt files",
        "undo": "Undo last validation",
        "ocr_language": "OCR language",
        "ocr_lang_auto": "Automatic (site language)",
        "total_pages": "Total pages",
        "validated": "Validated",
        "progress": "Progress",
        "to_process": "To process",
        "image": "Image",
        "previous": "Previous",
        "next": "Next",
        "thumbnails": "Thumbnails",
        "thumbnail_page": "Page {page} / {total}",
        "prev_page": "Previous page",
        "next_page": "Next page",
        "text_ocr": "OCR Text",
        "save": "Save",
        "validate_next": "Validate & Next",
        "paddle_ocr": "Paddle OCR",
        "empty_state_title": "No page available",
        "empty_state_hint": "Start by importing images with the form above.",
        "flash_created_txt": "{count} text file(s) created.",
        "flash_no_new_txt": "No new text file to create.",
        "flash_uploaded_images": "{count} image(s) imported.",
        "flash_auto_ocr_suffix": " Auto OCR applied.",
        "flash_skipped_files": "{count} file(s) skipped (duplicate or unsupported format).",
        "launch_capture_app": "Open Capture App",
        "working_folder": "Working Folder",
        "working_folder_hint": "Absolute path of the shared working folder",
        "choose_working_folder": "Choose working folder",
        "apply_working_folder": "Apply",
        "flash_working_folder_updated": "Working Folder updated: {path}",
        "flash_working_folder_invalid": "Invalid Working Folder: {error}",
        "flash_working_folder_picker_unavailable": "Finder folder picker is unavailable on this OS.",
        "flash_working_folder_picker_failed": "Could not open Finder folder picker: {error}",
        "capture_title": "Capture App",
        "capture_subtitle": "Browser-based capture with camera selection, voice trigger, and 2-page split.",
        "capture_back": "Back to OCR Book Quick Compare",
        "capture_enable_camera": "Enable camera",
        "capture_refresh_cameras": "Refresh cameras",
        "capture_camera": "Camera",
        "capture_mode": "Mode",
        "capture_rotation": "Rotation",
        "capture_resolution": "Resolution",
        "capture_rotate_left": "↺ -90°",
        "capture_rotate_right": "↻ +90°",
        "capture_scan_mode": "Scan mode",
        "capture_scan_enter": "Enter fullscreen",
        "capture_scan_exit": "Exit fullscreen",
        "capture_mode_one": "1 page at a time",
        "capture_mode_two": "2 pages at a time",
        "capture_output_folder": "Save folder",
        "capture_save_to_working_folder": "Direct save into Working Folder",
        "capture_choose_folder": "Choose folder",
        "capture_capture_now": "Capture now",
        "capture_start_voice": "Start voice",
        "capture_stop_voice": "Stop voice",
        "capture_prefix": "File prefix",
        "capture_prefix_hint": "Optional. Example: book-a",
        "capture_counter": "Captures taken",
        "capture_beep": "Audio beep after capture",
        "capture_browser_status": "Browser compatibility",
        "capture_browser_status_unknown": "Detected browser: unknown.",
        "capture_browser_status_chrome": "Detected browser: Chrome / Chromium. Recommended support for camera, folder picker, and voice.",
        "capture_browser_status_safari": "Detected browser: Safari. Camera is usually OK, but folder picker and voice may be limited.",
        "capture_browser_status_firefox": "Detected browser: Firefox. Camera is usually OK, but folder picker and voice may be limited.",
        "capture_browser_status_generic": "Detected browser: {name}. Some APIs may vary depending on the version.",
        "capture_voice_hint": "Trigger word: “next” (English).",
        "capture_alignment_hint": "In 2-page mode, align the book spine with the center line.",
        "capture_browser_note": "Tip: Chrome is recommended for folder selection. Safari may work for camera access but not always for folder picking.",
        "capture_status_ready": "Ready. Enable the camera, then choose the source you want.",
        "capture_status_browser_unsupported": "This browser does not support all required APIs (camera or speech recognition).",
        "capture_status_open_new_tab": "Capture App now opens in a new browser tab.",
        "capture_voice_browser_not_supported": "Voice trigger is not reliable on this browser. Use Chrome for the 'next' keyword.",
        "capture_voice_network_retry": "Speech recognition network error. Retrying automatically...",
        "capture_voice_network_unavailable": "Speech recognition network error keeps happening. Check Internet access or switch to Chrome.",
        "capture_voice_permission_blocked": "Microphone is blocked. Allow microphone access in the browser and retry voice.",
        "capture_voice_engine": "Voice engine",
        "capture_voice_engine_idle": "Stopped",
        "capture_voice_engine_listening": "Listening",
        "capture_voice_engine_processing": "Processing audio...",
        "capture_voice_engine_error": "Error",
        "flash_no_file_received": "No file received.",
        "flash_no_page_save": "No page available to update.",
        "flash_text_updated": "Text updated for {name}.",
        "flash_no_page_rename": "No page available to rename.",
        "flash_renamed": "File renamed: {name}",
        "flash_no_page_ocr": "No page available to run OCR.",
        "flash_ocr_empty": "Paddle OCR returned no text for {name}.",
        "flash_ocr_done": "Paddle OCR executed for {name}.",
        "flash_no_page_validate": "No page available to validate.",
        "flash_page_validated": "Page validated: {name}.",
        "flash_page_saved_validated": "Page saved and validated: {name}.",
        "flash_undo_done": "Last validation cancelled ({count} file(s) restored).",
        "flash_undo_none": "No validation to undo.",
        "flash_undo_conflict": "Undo blocked: {count} validation(s) could not be restored because the name already exists in active files.",
        "error_target_exists_in_done": "Target file already exists in check-done. Delete or rename it before validating.",
        "error_rename_empty": "Name cannot be empty.",
        "error_rename_invalid": "Name contains forbidden characters.",
        "error_rename_exists": "A file with this name already exists.",
        "js_autosave_saving": "Autosave in progress...",
        "js_autosaved_at": "Autosaved at",
        "js_autosave_failed": "Autosave failed",
        "js_dirty": "Unsaved text changes",
        "js_save_saving": "Saving...",
        "js_confirm_validate_next_dirty": "Save current text, validate this page, and move to the next one?",
        "js_confirm_validate_next": "Validate this page and move to the next one?",
        "js_confirm_ocr_overwrite": "Displayed text was edited. Running OCR will replace current content. Continue?",
        "js_upload_ready": "{count} file(s) ready. Drop more files or release to import.",
    },
    "it": {
        "title": "OCR Book Quick Compare",
        "subtitle": "v4 - Correzione layout",
        "dropzone_title": "Trascina qui le immagini",
        "dropzone_hint": "oppure clicca per selezionare",
        "auto_ocr": "OCR automatico",
        "create_txt": "Crea i .txt mancanti",
        "export": "Esporta i .txt del progetto",
        "undo": "Annulla l'ultima validazione",
        "ocr_language": "Lingua OCR",
        "ocr_lang_auto": "Automatico (lingua del sito)",
        "total_pages": "Pagine totali",
        "validated": "Convalidate",
        "progress": "Avanzamento",
        "to_process": "Da elaborare",
        "image": "Immagine",
        "previous": "Precedente",
        "next": "Successiva",
        "thumbnails": "Miniature",
        "thumbnail_page": "Pagina {page} / {total}",
        "prev_page": "Pagina precedente",
        "next_page": "Pagina successiva",
        "text_ocr": "Testo OCR",
        "save": "Salva",
        "validate_next": "Convalida & Successiva",
        "paddle_ocr": "Paddle OCR",
        "empty_state_title": "Nessuna pagina disponibile",
        "empty_state_hint": "Inizia importando immagini dal modulo qui sopra.",
        "flash_created_txt": "{count} file di testo creato/i.",
        "flash_no_new_txt": "Nessun nuovo file di testo da creare.",
        "flash_uploaded_images": "{count} immagine/i importata/e.",
        "flash_auto_ocr_suffix": " OCR automatico applicato.",
        "flash_skipped_files": "{count} file ignorato/i (duplicato o formato non supportato).",
        "launch_capture_app": "Apri Capture App",
        "working_folder": "Working Folder",
        "working_folder_hint": "Percorso assoluto della cartella di lavoro condivisa",
        "choose_working_folder": "Scegli cartella lavoro",
        "apply_working_folder": "Applica",
        "flash_working_folder_updated": "Working Folder aggiornata: {path}",
        "flash_working_folder_invalid": "Working Folder non valida: {error}",
        "flash_working_folder_picker_unavailable": "Il selettore cartelle Finder non è disponibile su questo sistema.",
        "flash_working_folder_picker_failed": "Impossibile aprire il selettore Finder: {error}",
        "capture_title": "Capture App",
        "capture_subtitle": "Acquisizione nel browser con selezione camera, trigger vocale e separazione 2 pagine.",
        "capture_back": "Torna a OCR Book Quick Compare",
        "capture_enable_camera": "Attiva la camera",
        "capture_refresh_cameras": "Aggiorna camere",
        "capture_camera": "Camera",
        "capture_mode": "Modalità",
        "capture_rotation": "Rotazione",
        "capture_resolution": "Risoluzione",
        "capture_rotate_left": "↺ -90°",
        "capture_rotate_right": "↻ +90°",
        "capture_scan_mode": "Modalita scansione",
        "capture_scan_enter": "Schermo intero",
        "capture_scan_exit": "Esci da schermo intero",
        "capture_mode_one": "1 pagina alla volta",
        "capture_mode_two": "2 pagine alla volta",
        "capture_output_folder": "Cartella di salvataggio",
        "capture_save_to_working_folder": "Salvataggio diretto nella Working Folder",
        "capture_choose_folder": "Scegli cartella",
        "capture_capture_now": "Acquisisci ora",
        "capture_start_voice": "Avvia voce",
        "capture_stop_voice": "Ferma voce",
        "capture_prefix": "Prefisso file",
        "capture_prefix_hint": "Opzionale. Esempio: libro-a",
        "capture_counter": "Acquisizioni effettuate",
        "capture_beep": "Bip audio dopo l'acquisizione",
        "capture_browser_status": "Compatibilità browser",
        "capture_browser_status_unknown": "Browser rilevato: sconosciuto.",
        "capture_browser_status_chrome": "Browser rilevato: Chrome / Chromium. Supporto consigliato per camera, cartella e voce.",
        "capture_browser_status_safari": "Browser rilevato: Safari. La camera di solito funziona, ma cartella e voce possono essere limitate.",
        "capture_browser_status_firefox": "Browser rilevato: Firefox. La camera di solito funziona, ma cartella e voce possono essere limitate.",
        "capture_browser_status_generic": "Browser rilevato: {name}. Alcune API possono variare in base alla versione.",
        "capture_voice_hint": "Parola trigger: “next” (inglese).",
        "capture_alignment_hint": "In modalità 2 pagine, allinea il dorso del libro alla linea centrale.",
        "capture_browser_note": "Suggerimento: Chrome è consigliato per la selezione della cartella. Safari può funzionare per la camera ma non sempre per la scelta della cartella.",
        "capture_status_ready": "Pronto. Attiva la camera, poi scegli la sorgente desiderata.",
        "capture_status_browser_unsupported": "Questo browser non supporta tutte le API richieste (camera o riconoscimento vocale).",
        "capture_status_open_new_tab": "Capture App ora si apre in una nuova scheda del browser.",
        "capture_voice_browser_not_supported": "Il trigger vocale non è affidabile su questo browser. Usa Chrome per la parola 'next'.",
        "capture_voice_network_retry": "Errore di rete nel riconoscimento vocale. Nuovo tentativo automatico...",
        "capture_voice_network_unavailable": "Errore di rete persistente nel riconoscimento vocale. Verifica Internet o usa Chrome.",
        "capture_voice_permission_blocked": "Microfono bloccato. Consenti l'accesso al microfono nel browser e riprova.",
        "capture_voice_engine": "Motore vocale",
        "capture_voice_engine_idle": "Fermo",
        "capture_voice_engine_listening": "In ascolto",
        "capture_voice_engine_processing": "Analisi audio...",
        "capture_voice_engine_error": "Errore",
        "flash_no_file_received": "Nessun file ricevuto.",
        "flash_no_page_save": "Nessuna pagina da aggiornare.",
        "flash_text_updated": "Testo aggiornato per {name}.",
        "flash_no_page_rename": "Nessuna pagina da rinominare.",
        "flash_renamed": "File rinominato: {name}",
        "flash_no_page_ocr": "Nessuna pagina disponibile per OCR.",
        "flash_ocr_empty": "Paddle OCR non ha restituito testo per {name}.",
        "flash_ocr_done": "Paddle OCR eseguito per {name}.",
        "flash_no_page_validate": "Nessuna pagina da convalidare.",
        "flash_page_validated": "Pagina convalidata: {name}.",
        "flash_page_saved_validated": "Pagina salvata e convalidata: {name}.",
        "flash_undo_done": "Ultima validazione annullata ({count} file ripristinato/i).",
        "flash_undo_none": "Nessuna validazione da annullare.",
        "flash_undo_conflict": "Annullamento impossibile: {count} validazione/i bloccata/e perché il nome esiste già tra i file attivi.",
        "error_target_exists_in_done": "Il file di destinazione esiste già in check-done. Eliminalo o rinominalo prima di convalidare.",
        "error_rename_empty": "Il nome non può essere vuoto.",
        "error_rename_invalid": "Il nome contiene caratteri non consentiti.",
        "error_rename_exists": "Esiste già un file con questo nome.",
        "js_autosave_saving": "Autosalvataggio in corso...",
        "js_autosaved_at": "Autosalvato alle",
        "js_autosave_failed": "Autosalvataggio fallito",
        "js_dirty": "Modifiche non salvate",
        "js_save_saving": "Salvataggio...",
        "js_confirm_validate_next_dirty": "Salvare il testo corrente, convalidare questa pagina e passare alla successiva?",
        "js_confirm_validate_next": "Convalidare questa pagina e passare alla successiva?",
        "js_confirm_ocr_overwrite": "Il testo visualizzato è stato modificato. L'OCR sostituirà il contenuto corrente. Continuare?",
        "js_upload_ready": "{count} file pronto/i. Trascinane altri o rilascia per importare.",
    },
    "de": {
        "title": "OCR Book Quick Compare",
        "subtitle": "v4 - Layout-Korrektur",
        "dropzone_title": "Bilder hier ablegen",
        "dropzone_hint": "oder klicken zum Auswählen",
        "auto_ocr": "Auto OCR",
        "create_txt": "Fehlende .txt erstellen",
        "export": "Projekt-.txt exportieren",
        "undo": "Letzte Validierung rückgängig",
        "ocr_language": "OCR-Sprache",
        "ocr_lang_auto": "Automatisch (Seitensprache)",
        "total_pages": "Seiten gesamt",
        "validated": "Validiert",
        "progress": "Fortschritt",
        "to_process": "Zu bearbeiten",
        "image": "Bild",
        "previous": "Zurück",
        "next": "Weiter",
        "thumbnails": "Vorschaubilder",
        "thumbnail_page": "Seite {page} / {total}",
        "prev_page": "Vorherige Seite",
        "next_page": "Nächste Seite",
        "text_ocr": "OCR-Text",
        "save": "Speichern",
        "validate_next": "Validieren & Weiter",
        "paddle_ocr": "Paddle OCR",
        "empty_state_title": "Keine Seite verfügbar",
        "empty_state_hint": "Importiere zuerst Bilder über das obige Formular.",
        "flash_created_txt": "{count} Textdatei(en) erstellt.",
        "flash_no_new_txt": "Keine neue Textdatei zu erstellen.",
        "flash_uploaded_images": "{count} Bild(er) importiert.",
        "flash_auto_ocr_suffix": " Auto-OCR angewendet.",
        "flash_skipped_files": "{count} Datei(en) übersprungen (Duplikat oder nicht unterstütztes Format).",
        "launch_capture_app": "Capture App öffnen",
        "working_folder": "Working Folder",
        "working_folder_hint": "Absoluter Pfad des gemeinsamen Arbeitsordners",
        "choose_working_folder": "Arbeitsordner wählen",
        "apply_working_folder": "Anwenden",
        "flash_working_folder_updated": "Working Folder aktualisiert: {path}",
        "flash_working_folder_invalid": "Ungültiger Working Folder: {error}",
        "flash_working_folder_picker_unavailable": "Der Finder-Ordnerdialog ist auf diesem System nicht verfügbar.",
        "flash_working_folder_picker_failed": "Finder-Ordnerdialog konnte nicht geöffnet werden: {error}",
        "capture_title": "Capture App",
        "capture_subtitle": "Browserbasierte Aufnahme mit Kameraauswahl, Sprach-Trigger und 2-Seiten-Trennung.",
        "capture_back": "Zurück zu OCR Book Quick Compare",
        "capture_enable_camera": "Kamera aktivieren",
        "capture_refresh_cameras": "Kameras aktualisieren",
        "capture_camera": "Kamera",
        "capture_mode": "Modus",
        "capture_rotation": "Drehung",
        "capture_resolution": "Auflosung",
        "capture_rotate_left": "↺ -90°",
        "capture_rotate_right": "↻ +90°",
        "capture_scan_mode": "Scanmodus",
        "capture_scan_enter": "Vollbild aktivieren",
        "capture_scan_exit": "Vollbild beenden",
        "capture_mode_one": "1 Seite gleichzeitig",
        "capture_mode_two": "2 Seiten gleichzeitig",
        "capture_output_folder": "Speicherordner",
        "capture_save_to_working_folder": "Direktes Speichern im Working Folder",
        "capture_choose_folder": "Ordner wählen",
        "capture_capture_now": "Jetzt aufnehmen",
        "capture_start_voice": "Sprache starten",
        "capture_stop_voice": "Sprache stoppen",
        "capture_prefix": "Dateipräfix",
        "capture_prefix_hint": "Optional. Beispiel: buch-a",
        "capture_counter": "Erfasste Aufnahmen",
        "capture_beep": "Signalton nach Aufnahme",
        "capture_browser_status": "Browser-Kompatibilität",
        "capture_browser_status_unknown": "Erkannter Browser: unbekannt.",
        "capture_browser_status_chrome": "Erkannter Browser: Chrome / Chromium. Empfohlene Unterstützung für Kamera, Ordnerwahl und Sprache.",
        "capture_browser_status_safari": "Erkannter Browser: Safari. Kamera funktioniert meist, aber Ordnerwahl und Sprache können eingeschränkt sein.",
        "capture_browser_status_firefox": "Erkannter Browser: Firefox. Kamera funktioniert meist, aber Ordnerwahl und Sprache können eingeschränkt sein.",
        "capture_browser_status_generic": "Erkannter Browser: {name}. Manche APIs können je nach Version variieren.",
        "capture_voice_hint": "Auslösewort: “next” (Englisch).",
        "capture_alignment_hint": "Im 2-Seiten-Modus den Buchrücken an der Mittellinie ausrichten.",
        "capture_browser_note": "Tipp: Chrome wird für die Ordnerauswahl empfohlen. Safari kann für die Kamera funktionieren, aber nicht immer für die Ordnerauswahl.",
        "capture_status_ready": "Bereit. Kamera aktivieren und dann die gewünschte Quelle wählen.",
        "capture_status_browser_unsupported": "Dieser Browser unterstützt nicht alle erforderlichen APIs (Kamera oder Spracherkennung).",
        "capture_status_open_new_tab": "Capture App öffnet sich jetzt in einem neuen Browser-Tab.",
        "capture_voice_browser_not_supported": "Sprach-Trigger ist in diesem Browser nicht zuverlässig. Verwende Chrome für das Schlüsselwort 'next'.",
        "capture_voice_network_retry": "Netzwerkfehler bei der Spracherkennung. Automatischer neuer Versuch...",
        "capture_voice_network_unavailable": "Anhaltender Netzwerkfehler bei der Spracherkennung. Internet prüfen oder Chrome verwenden.",
        "capture_voice_permission_blocked": "Mikrofon blockiert. Mikrofonzugriff im Browser erlauben und erneut starten.",
        "capture_voice_engine": "Sprachmodul",
        "capture_voice_engine_idle": "Gestoppt",
        "capture_voice_engine_listening": "Hört zu",
        "capture_voice_engine_processing": "Audio wird analysiert...",
        "capture_voice_engine_error": "Fehler",
        "flash_no_file_received": "Keine Datei empfangen.",
        "flash_no_page_save": "Keine Seite zum Aktualisieren verfügbar.",
        "flash_text_updated": "Text für {name} aktualisiert.",
        "flash_no_page_rename": "Keine Seite zum Umbenennen verfügbar.",
        "flash_renamed": "Datei umbenannt: {name}",
        "flash_no_page_ocr": "Keine Seite für OCR verfügbar.",
        "flash_ocr_empty": "Paddle OCR hat keinen Text für {name} geliefert.",
        "flash_ocr_done": "Paddle OCR für {name} ausgeführt.",
        "flash_no_page_validate": "Keine Seite zum Validieren verfügbar.",
        "flash_page_validated": "Seite validiert: {name}.",
        "flash_page_saved_validated": "Seite gespeichert und validiert: {name}.",
        "flash_undo_done": "Letzte Validierung rückgängig ({count} Datei(en) wiederhergestellt).",
        "flash_undo_none": "Keine Validierung zum Rückgängigmachen.",
        "flash_undo_conflict": "Rückgängig blockiert: {count} Validierung(en) konnten nicht wiederhergestellt werden, da der Name bereits bei aktiven Dateien existiert.",
        "error_target_exists_in_done": "Zieldatei existiert bereits in check-done. Vor dem Validieren löschen oder umbenennen.",
        "error_rename_empty": "Name darf nicht leer sein.",
        "error_rename_invalid": "Name enthält unzulässige Zeichen.",
        "error_rename_exists": "Eine Datei mit diesem Namen existiert bereits.",
        "js_autosave_saving": "Autospeichern läuft...",
        "js_autosaved_at": "Automatisch gespeichert um",
        "js_autosave_failed": "Autospeichern fehlgeschlagen",
        "js_dirty": "Ungespeicherte Textänderungen",
        "js_save_saving": "Speichern...",
        "js_confirm_validate_next_dirty": "Aktuellen Text speichern, Seite validieren und zur nächsten wechseln?",
        "js_confirm_validate_next": "Diese Seite validieren und zur nächsten wechseln?",
        "js_confirm_ocr_overwrite": "Der angezeigte Text wurde geändert. OCR ersetzt den aktuellen Inhalt. Fortfahren?",
        "js_upload_ready": "{count} Datei(en) bereit. Weitere ablegen oder zum Import loslassen.",
    },
}


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

    @property
    def image_size_kb(self) -> int:
        byte_size = self.image_path.stat().st_size
        if byte_size <= 0:
            return 0
        # Keep tiny files readable in the UI instead of showing an empty/zero-like value.
        return max(1, round(byte_size / 1024))


@dataclass
class ViewState:
    selected_name: str = ""
    query: str = ""
    sort_key: str = "oldest"
    text_filter: str = "all"
    thumbnail_page: int = 1
    lang: str = "fr"
    ocr_lang: str = ""



def is_supported_image(file_path: Path) -> bool:
    return file_path.is_file() and not is_hidden_sidecar(file_path) and file_path.suffix.lower() in IMAGE_EXTENSIONS



def is_supported_image_name(filename: str) -> bool:
    candidate = Path(filename)
    return candidate.suffix.lower() in IMAGE_EXTENSIONS and not candidate.name.startswith(".")


def is_hidden_sidecar(file_path: Path) -> bool:
    name = file_path.name
    return name.startswith("._") or (name.startswith(".") and name != ".")



def iter_root_images(images_dir: Path) -> Iterable[Path]:
    return (path for path in images_dir.iterdir() if is_supported_image(path))



def image_sort_key(image_path: Path) -> tuple[float, str]:
    return (image_path.stat().st_mtime, image_path.name.casefold())



def text_path_for(image_path: Path) -> Path:
    return image_path.with_suffix(".txt")


def unique_image_destination(images_dir: Path, filename: str) -> Path:
    candidate_name = Path(filename).name
    base = Path(candidate_name).stem
    suffix = Path(candidate_name).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".jpg"

    candidate = images_dir / f"{base}{suffix}"
    index = 1
    while candidate.exists() or text_path_for(candidate).exists():
        candidate = images_dir / f"{base}-{index}{suffix}"
        index += 1
    return candidate


def save_capture_uploads(files: list, images_dir: Path) -> list[str]:
    saved_names: list[str] = []
    for storage in files:
        raw_name = (storage.filename or "").strip()
        if not raw_name:
            continue

        destination = unique_image_destination(images_dir, raw_name)
        storage.save(str(destination))
        text_path_for(destination).write_text("", encoding="utf-8")
        saved_names.append(destination.name)

    return saved_names


def cleanup_capture_sidecars(images_dir: Path) -> int:
    removed = 0
    for path in images_dir.iterdir():
        if not path.is_file():
            continue
        if not is_hidden_sidecar(path):
            continue
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed



def normalize_sort_key(sort_key: str) -> str:
    return sort_key if sort_key in SORT_OPTIONS else "oldest"



def normalize_text_filter(text_filter: str) -> str:
    return text_filter if text_filter in TEXT_FILTER_OPTIONS else "all"


def normalize_lang(lang: str) -> str:
    normalized = (lang or "fr").strip().lower()
    return normalized if normalized in SUPPORTED_LANGS else "fr"


def normalize_ocr_lang(ocr_lang: str) -> str:
    normalized = (ocr_lang or "").strip().lower()
    if normalized in ("fra", "fr"):
        return "fr"
    if normalized in ("eng", "en"):
        return "en"
    if normalized in ("ita", "it"):
        return "it"
    if normalized in ("deu", "de"):
        return "de"
    return ""


def resolve_ocr_lang(view_state: ViewState, configured_ocr_lang: str) -> str:
    if view_state.ocr_lang:
        return view_state.ocr_lang

    normalized_config = normalize_ocr_lang(configured_ocr_lang)
    if normalized_config:
        return normalized_config

    return view_state.lang


def tr(lang: str, key: str, **kwargs) -> str:
    pack = TRANSLATIONS.get(lang, TRANSLATIONS["fr"])
    text = pack.get(key, TRANSLATIONS["fr"].get(key, key))
    return text.format(**kwargs)



def build_view_state(source) -> ViewState:
    return ViewState(
        selected_name=(source.get("current_image") or source.get("file") or "").strip(),
        query=(source.get("q") or "").strip(),
        sort_key=normalize_sort_key((source.get("sort") or "oldest").strip()),
        text_filter=normalize_text_filter((source.get("text_filter") or "all").strip()),
        thumbnail_page=max(1, int(source.get("thumb_page", 1) or 1)),
        lang=normalize_lang(source.get("lang") or "fr"),
        ocr_lang=normalize_ocr_lang(source.get("ocr_lang") or ""),
    )



def build_index_params(view_state: ViewState, selected_name: Optional[str] = None) -> dict:
    file_name = selected_name if selected_name is not None else view_state.selected_name
    params = {
        "sort": view_state.sort_key,
        "text_filter": view_state.text_filter,
        "thumb_page": view_state.thumbnail_page,
        "lang": view_state.lang,
        "ocr_lang": view_state.ocr_lang,
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
                text_content=read_text_file_safe(text_path),
                image_mtime=image_path.stat().st_mtime,
            )
        )

    records.sort(key=lambda record: (record.image_mtime, record.image_name.casefold()))
    missing_texts.sort(key=image_sort_key)
    return records, missing_texts


def read_text_file_safe(text_path: Path) -> str:
    """Read OCR text files robustly even when bytes are not valid UTF-8."""
    try:
        return text_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Keep the page visible instead of crashing the whole UI.
        return text_path.read_bytes().decode("utf-8", errors="replace")



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
        text_path = text_path_for(destination)
        # Always create the paired text file when importing via UI.
        text_path.write_text("", encoding="utf-8")
        created_images.append((destination, text_path))

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
        raise FileExistsError("target_exists_in_done")

    shutil.move(str(image_path), str(image_target))
    shutil.move(str(text_path), str(text_target))



def undo_last_validation(check_done_dir: Path, images_dir: Path, count: int = 1) -> tuple[int, int]:
    undone_count = 0
    blocked_count = 0
    # Use ctime to approximate validation order (move/metadata change time),
    # instead of mtime which usually reflects original scan date.
    images_in_done = sorted(
        iter_root_images(check_done_dir),
        key=lambda path: (path.stat().st_ctime, path.name.casefold()),
        reverse=True,
    )

    for image_path in images_in_done[:count]:
        text_path = text_path_for(image_path)
        if text_path.exists():
            image_dest = images_dir / image_path.name
            text_dest = images_dir / text_path.name

            if not image_dest.exists() and not text_dest.exists():
                shutil.move(str(image_path), str(image_dest))
                shutil.move(str(text_path), str(text_dest))
                undone_count += 1
            else:
                blocked_count += 1

    return undone_count, blocked_count


def rename_pair(image_path: Path, new_base: str) -> tuple[Path, Path]:
    cleaned_base = new_base.strip()
    if not cleaned_base:
        raise ValueError("rename_empty")
    if Path(cleaned_base).name != cleaned_base or "/" in cleaned_base or "\\" in cleaned_base:
        raise ValueError("rename_invalid")

    current_text_path = text_path_for(image_path)
    target_image_path = image_path.with_name(f"{cleaned_base}{image_path.suffix}")
    target_text_path = image_path.with_name(f"{cleaned_base}.txt")

    if target_image_path == image_path:
        return image_path, current_text_path

    if target_image_path.exists() or target_text_path.exists():
        raise FileExistsError("rename_exists")

    image_path.rename(target_image_path)
    if current_text_path.exists():
        current_text_path.rename(target_text_path)

    return target_image_path, target_text_path



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
    if normalized.startswith("fra") or normalized == "fr":
        return "fr"
    if normalized.startswith("eng") or normalized == "en":
        return "en"
    if normalized.startswith("ita") or normalized == "it":
        return "it"
    if normalized.startswith("deu") or normalized == "de":
        return "de"
    return "en"


@lru_cache(maxsize=4)
def get_paddle_ocr(language: str):
    if PaddleOCR is None:
        error_suffix = f" ({PADDLEOCR_IMPORT_ERROR})" if PADDLEOCR_IMPORT_ERROR else ""
        raise RuntimeError(
            "Paddle OCR is not installed or failed to import. "
            f"Install/fix paddleocr dependencies to enable this feature{error_suffix}."
        )

    return PaddleOCR(use_textline_orientation=True, lang=_paddle_language_code(language))


def extract_text_from_paddle_result(result) -> str:
    def _normalize_ocr_text(value) -> str:
        """Extract plain text from OCR payload variants (string or (text, score) tuple)."""
        if value is None:
            return ""
        if isinstance(value, (list, tuple)) and value:
            # Common legacy shape: ("text", confidence)
            return str(value[0]).strip()
        return str(value).strip()

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
            for text in rec_texts:
                normalized = _normalize_ocr_text(text)
                if normalized:
                    lines.append(normalized)
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
                    text = _normalize_ocr_text(item[1])
                    if text:
                        lines.append(text)

    return "\n".join(line for line in lines if line)


def run_ocr_for_image(image_path: Path, language: str) -> str:
    try:
        ocr = get_paddle_ocr(language)
        extracted_text = ""

        if hasattr(ocr, "predict"):
            result = ocr.predict(str(image_path))
            extracted_text = extract_text_from_paddle_result(result)

        if not extracted_text and hasattr(ocr, "ocr"):
            legacy_result = ocr.ocr(str(image_path))
            extracted_text = extract_text_from_paddle_result(legacy_result)

        return extracted_text
    except Exception as exc:
        raise RuntimeError(f"Paddle OCR failed: {exc}") from exc


def contains_trigger_word(text: str, trigger: str = "next") -> bool:
    normalized_text = (text or "").strip().lower()
    normalized_trigger = (trigger or "next").strip().lower()
    if not normalized_text or not normalized_trigger:
        return False
    return normalized_trigger in normalized_text.split() or normalized_trigger in normalized_text


@lru_cache(maxsize=1)
def get_capture_vosk_model(model_path: str):
    if VoskModel is None:
        raise RuntimeError("Vosk is not installed")
    return VoskModel(model_path)


def transcribe_capture_wav(audio_bytes: bytes, model_dir: Path) -> str:
    if KaldiRecognizer is None or VoskModel is None:
        raise RuntimeError("Vosk dependency is not available")
    if not model_dir.exists():
        raise RuntimeError(f"Vosk model not found at {model_dir}")

    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        frame_data = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise RuntimeError("Unsupported WAV sample width (expected 16-bit PCM)")
    if channels != 1:
        raise RuntimeError("Unsupported WAV channel count (expected mono)")

    recognizer = KaldiRecognizer(get_capture_vosk_model(str(model_dir)), float(sample_rate))
    recognizer.AcceptWaveform(frame_data)
    result = json.loads(recognizer.FinalResult() or "{}")
    return str(result.get("text", "")).strip().lower()


def create_app(test_config: Optional[dict] = None) -> Flask:
    base_dir = Path(__file__).resolve().parent

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("OCR_COMPARE_SECRET", "dev-secret-change-me"),
        IMAGES_DIR=base_dir / "images",
        CHECK_DONE_DIR=base_dir / "images" / "check-done",
        WORKING_FOLDER_STATE_FILE=base_dir / ".working-folder.txt",
        OCR_LANG=os.environ.get("OCR_LANG", ""),
        AUTO_OCR=os.environ.get("AUTO_OCR", "0").lower() in ("1", "true", "yes"),
        MAX_CONTENT_LENGTH=64 * 1024 * 1024,
        AUTOSAVE_INTERVAL_MS=1500,
        CAPTURE_VOSK_MODEL_DIR=base_dir / "capture-app" / "models" / "vosk-model-small-en-us-0.15",
        CAPTURE_MAX_AUDIO_BYTES=4 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    def apply_working_folder(folder_path: Path) -> None:
        resolved = Path(folder_path).expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        check_done = resolved / "check-done"
        check_done.mkdir(parents=True, exist_ok=True)
        app.config["IMAGES_DIR"] = resolved
        app.config["CHECK_DONE_DIR"] = check_done

    configured_images_dir = Path(app.config["IMAGES_DIR"])
    state_file = Path(app.config["WORKING_FOLDER_STATE_FILE"])

    # In normal runs, restore last folder used by the user.
    if not test_config and state_file.exists():
        try:
            persisted = state_file.read_text(encoding="utf-8").strip()
            if persisted:
                configured_images_dir = Path(persisted)
        except OSError:
            configured_images_dir = Path(app.config["IMAGES_DIR"])

    apply_working_folder(configured_images_dir)

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
        effective_ocr_lang = resolve_ocr_lang(view_state, app.config["OCR_LANG"])

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
            current_lang=view_state.lang,
            language_labels=LANGUAGE_LABELS,
            supported_ocr_langs=SUPPORTED_LANGS,
            effective_ocr_lang=effective_ocr_lang,
            current_working_folder=str(images_dir),
            t=lambda key, **kwargs: tr(view_state.lang, key, **kwargs),
        )

    @app.post("/create-missing-texts")
    def create_texts():
        view_state = build_view_state(request.form)
        created_files = create_missing_text_files(app.config["IMAGES_DIR"])
        if created_files:
            flash(tr(view_state.lang, "flash_created_txt", count=len(created_files)), "success")
        else:
            flash(tr(view_state.lang, "flash_no_new_txt"), "info")
        return redirect_to_index(view_state, view_state.selected_name)

    @app.post("/upload-images")
    def upload_images():
        view_state = build_view_state(request.form)
        uploaded_files = request.files.getlist("images")
        auto_ocr = request.form.get("auto_ocr") == "1"
        effective_ocr_lang = resolve_ocr_lang(view_state, app.config["OCR_LANG"])
        created_count, skipped_count, _ = save_uploaded_images(
            uploaded_files, app.config["IMAGES_DIR"], auto_ocr=auto_ocr, ocr_lang=effective_ocr_lang
        )

        if created_count:
            msg = tr(view_state.lang, "flash_uploaded_images", count=created_count)
            if auto_ocr:
                msg += tr(view_state.lang, "flash_auto_ocr_suffix")
            flash(msg, "success")
        if skipped_count:
            flash(tr(view_state.lang, "flash_skipped_files", count=skipped_count), "info")
        if not created_count and not skipped_count:
            flash(tr(view_state.lang, "flash_no_file_received"), "info")

        return redirect_to_index(view_state, view_state.selected_name)

    @app.post("/set-working-folder")
    def set_working_folder():
        view_state = build_view_state(request.form)
        requested_folder = (request.form.get("working_folder") or "").strip()
        if not requested_folder:
            flash(tr(view_state.lang, "flash_working_folder_invalid", error="empty path"), "error")
            return redirect_to_index(view_state, view_state.selected_name)

        try:
            new_folder = Path(requested_folder).expanduser().resolve()
            new_folder.mkdir(parents=True, exist_ok=True)
            check_done = new_folder / "check-done"
            check_done.mkdir(parents=True, exist_ok=True)
            app.config["IMAGES_DIR"] = new_folder
            app.config["CHECK_DONE_DIR"] = check_done
            if not app.testing:
                Path(app.config["WORKING_FOLDER_STATE_FILE"]).write_text(str(new_folder), encoding="utf-8")
        except OSError as exc:
            flash(tr(view_state.lang, "flash_working_folder_invalid", error=str(exc)), "error")
            return redirect_to_index(view_state, view_state.selected_name)

        flash(tr(view_state.lang, "flash_working_folder_updated", path=str(new_folder)), "success")
        return redirect_to_index(view_state, "")

    @app.get("/pick-working-folder")
    def pick_working_folder():
        view_state = build_view_state(request.args)

        if sys.platform != "darwin":
            return (
                jsonify(
                    {
                        "selected": False,
                        "message": tr(view_state.lang, "flash_working_folder_picker_unavailable"),
                    }
                ),
                501,
            )

        script = (
            "try\n"
            'POSIX path of (choose folder with prompt "Select Working Folder")\n'
            "on error number -128\n"
            'return ""\n'
            "end try"
        )

        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
        except OSError as exc:
            return (
                jsonify(
                    {
                        "selected": False,
                        "message": tr(view_state.lang, "flash_working_folder_picker_failed", error=str(exc)),
                    }
                ),
                500,
            )

        if result.returncode != 0:
            raw_error = (result.stderr or result.stdout or "").strip() or f"exit {result.returncode}"
            if "User canceled" in raw_error:
                return jsonify({"selected": False, "cancelled": True})
            return (
                jsonify(
                    {
                        "selected": False,
                        "message": tr(view_state.lang, "flash_working_folder_picker_failed", error=raw_error),
                    }
                ),
                500,
            )

        selected_path = (result.stdout or "").strip()
        if not selected_path:
            return jsonify({"selected": False, "cancelled": True})

        return jsonify({"selected": True, "path": selected_path})

    @app.post("/save")
    def save_text():
        view_state = build_view_state(request.form)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, _ = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            flash(tr(view_state.lang, "flash_no_page_save"), "info")
            return redirect_to_index(view_state, view_state.selected_name)

        updated_text = request.form.get("text", "")
        current_record.text_path.write_text(updated_text, encoding="utf-8")
        flash(tr(view_state.lang, "flash_text_updated", name=current_record.text_name), "success")
        return redirect_to_index(view_state, current_record.image_name)

    @app.post("/rename-current")
    def rename_current():
        view_state = build_view_state(request.form)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, _ = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            flash(tr(view_state.lang, "flash_no_page_rename"), "info")
            return redirect_to_index(view_state, view_state.selected_name)

        new_base = request.form.get("new_base", "")
        try:
            target_image, _ = rename_pair(current_record.image_path, new_base)
        except ValueError as exc:
            key = "error_rename_empty" if str(exc) == "rename_empty" else "error_rename_invalid"
            flash(tr(view_state.lang, key), "error")
            return redirect_to_index(view_state, current_record.image_name)
        except FileExistsError:
            flash(tr(view_state.lang, "error_rename_exists"), "error")
            return redirect_to_index(view_state, current_record.image_name)

        flash(tr(view_state.lang, "flash_renamed", name=target_image.name), "success")
        return redirect_to_index(view_state, target_image.name)

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
            flash(tr(view_state.lang, "flash_no_page_ocr"), "info")
            return redirect_to_index(view_state, view_state.selected_name)

        effective_ocr_lang = resolve_ocr_lang(view_state, app.config["OCR_LANG"])
        try:
            extracted_text = run_ocr_for_image(current_record.image_path, effective_ocr_lang)
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect_to_index(view_state, current_record.image_name)

        if not extracted_text.strip():
            flash(tr(view_state.lang, "flash_ocr_empty", name=current_record.image_name), "error")
            return redirect_to_index(view_state, current_record.image_name)

        current_record.text_path.write_text(extracted_text, encoding="utf-8")
        flash(tr(view_state.lang, "flash_ocr_done", name=current_record.image_name), "success")
        return redirect_to_index(view_state, current_record.image_name)

    @app.post("/validate")
    def validate_pair():
        view_state = build_view_state(request.form)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, current_index = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            flash(tr(view_state.lang, "flash_no_page_validate"), "info")
            return redirect_to_index(view_state, view_state.selected_name)

        remaining_records = filtered_records[:current_index] + filtered_records[current_index + 1 :]
        next_name = remaining_records[min(current_index, len(remaining_records) - 1)].image_name if remaining_records else ""

        try:
            move_pair_to_done(current_record.image_path, current_record.text_path, app.config["CHECK_DONE_DIR"])
        except FileExistsError as exc:
            key = "error_target_exists_in_done" if str(exc) == "target_exists_in_done" else str(exc)
            flash(tr(view_state.lang, key) if key in TRANSLATIONS[view_state.lang] else key, "error")
            return redirect_to_index(view_state, current_record.image_name)

        flash(tr(view_state.lang, "flash_page_validated", name=current_record.image_name), "success")
        return redirect_to_index(view_state, next_name)

    @app.post("/validate-and-next")
    def validate_and_next():
        view_state = build_view_state(request.form)
        _, filtered_records, _ = get_filtered_context(view_state)
        current_record, current_index = get_selected_record(filtered_records, view_state.selected_name)
        if not current_record:
            flash(tr(view_state.lang, "flash_no_page_validate"), "info")
            return redirect_to_index(view_state, view_state.selected_name)

        updated_text = request.form.get("text", "")
        current_record.text_path.write_text(updated_text, encoding="utf-8")
        remaining_records = filtered_records[:current_index] + filtered_records[current_index + 1 :]
        next_name = remaining_records[min(current_index, len(remaining_records) - 1)].image_name if remaining_records else ""

        try:
            move_pair_to_done(current_record.image_path, current_record.text_path, app.config["CHECK_DONE_DIR"])
        except FileExistsError as exc:
            key = "error_target_exists_in_done" if str(exc) == "target_exists_in_done" else str(exc)
            flash(tr(view_state.lang, key) if key in TRANSLATIONS[view_state.lang] else key, "error")
            return redirect_to_index(view_state, current_record.image_name)

        flash(tr(view_state.lang, "flash_page_saved_validated", name=current_record.image_name), "success")
        return redirect_to_index(view_state, next_name)

    @app.post("/undo-validation")
    def undo_validation():
        view_state = build_view_state(request.form)
        undone_count, blocked_count = undo_last_validation(app.config["CHECK_DONE_DIR"], app.config["IMAGES_DIR"], count=1)
        if undone_count > 0:
            flash(tr(view_state.lang, "flash_undo_done", count=undone_count), "success")
        elif blocked_count > 0:
            flash(tr(view_state.lang, "flash_undo_conflict", count=blocked_count), "error")
        else:
            flash(tr(view_state.lang, "flash_undo_none"), "info")
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

    @app.get("/capture")
    def capture_companion():
        view_state = build_view_state(request.args)
        return render_template(
            "capture.html",
            current_lang=view_state.lang,
            view_state=view_state,
            current_working_folder=str(app.config["IMAGES_DIR"]),
            t=lambda key, **kwargs: tr(view_state.lang, key, **kwargs),
        )

    @app.post("/capture-save-images")
    def capture_save_images():
        uploaded_files = request.files.getlist("images")
        if not uploaded_files:
            return jsonify({"saved": 0, "filenames": [], "message": "No images received"}), 400

        saved_names = save_capture_uploads(uploaded_files, app.config["IMAGES_DIR"])
        if not saved_names:
            return jsonify({"saved": 0, "filenames": [], "message": "No valid images received"}), 400

        removed_sidecars = cleanup_capture_sidecars(app.config["IMAGES_DIR"])

        return jsonify({"saved": len(saved_names), "filenames": saved_names, "removed_sidecars": removed_sidecars})

    @app.post("/launch-capture-app")
    def launch_capture_app():
        view_state = build_view_state(request.form)
        flash(tr(view_state.lang, "capture_status_open_new_tab"), "info")
        return redirect(url_for("capture_companion", lang=view_state.lang))

    @app.post("/capture-voice-detect")
    def capture_voice_detect():
        audio_file = request.files.get("audio")
        if audio_file is None:
            return jsonify({"detected": False, "message": "No audio payload received"}), 400

        payload = audio_file.read()
        if not payload:
            return jsonify({"detected": False, "message": "Empty audio payload"}), 400
        if len(payload) > int(app.config["CAPTURE_MAX_AUDIO_BYTES"]):
            return jsonify({"detected": False, "message": "Audio payload too large"}), 413

        try:
            transcript = transcribe_capture_wav(payload, Path(app.config["CAPTURE_VOSK_MODEL_DIR"]))
        except RuntimeError as exc:
            return jsonify({"detected": False, "message": str(exc)}), 503
        except wave.Error:
            return jsonify({"detected": False, "message": "Invalid WAV payload"}), 400

        detected = contains_trigger_word(transcript, trigger="next")
        return jsonify({"detected": detected, "transcript": transcript})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)





