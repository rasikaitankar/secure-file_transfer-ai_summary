"""
utils/summarizer.py
-------------------
Person 3 – AI Summarization Module

WHY AI SUMMARIZATION?
---------------------
When a receiver downloads a file, they may not want to read the whole document.
The AI gives an instant TL;DR so they know what's inside before decrypting.

MODEL CHOICE:
  We use "facebook/bart-large-cnn" from HuggingFace — a state-of-the-art
  abstractive summarizer trained on CNN/DailyMail news articles.
  It UNDERSTANDS text and writes a NEW summary (not just copy-pastes sentences).

NETWORKING ANALOGY:
  This module runs on the SERVER side — the client never needs to download
  the heavy AI model. The summary is returned in the HTTP JSON response,
  just like how Google summarizes search results server-side.
"""

import os
import re

# ── Lazy-load model to avoid startup delay ───────────────────────────────────
_summarizer = None
_USE_MOCK = False   # Set True during development without GPU


def _get_summarizer():
    """
    Lazy-load the HuggingFace pipeline.
    Called only on first summarization request.
    """
    global _summarizer, _USE_MOCK
    if _summarizer is not None:
        return _summarizer

    try:
        from transformers import pipeline
        print("[AI] Loading facebook/bart-large-cnn summarization model…")
        _summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=-1   # -1 = CPU; change to 0 for GPU
        )
        print("[AI] Model loaded successfully.")
    except Exception as e:
        print(f"[AI] Could not load model ({e}). Using extractive fallback.")
        _USE_MOCK = True

    return _summarizer


def _extract_text_from_file(filepath: str) -> str:
    """
    Extract readable text from a file.
    Supports: .txt, .py, .js, .html, .css, .json, .csv, .md, .xml
    For binary files (images, PDFs) returns a placeholder.
    """
    TEXT_EXTENSIONS = {
        ".txt", ".py", ".js", ".ts", ".html", ".htm", ".css",
        ".json", ".csv", ".md", ".xml", ".yaml", ".yml",
        ".java", ".c", ".cpp", ".h", ".rs", ".go", ".rb", ".php",
        ".sh", ".bat", ".sql", ".log", ".ini", ".cfg", ".toml"
    }
    _, ext = os.path.splitext(filepath)

    if ext.lower() not in TEXT_EXTENSIONS:
        return f"[Binary file of type '{ext}'. AI summary not available for binary files.]"

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"[Could not read file: {e}]"


def _extractive_summary(text: str, num_sentences: int = 4) -> str:
    """
    Fallback: simple extractive summarizer.
    Picks the first N sentences as a rough summary.
    Used when HuggingFace model is unavailable.
    """
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    selected = sentences[:num_sentences]
    if not selected:
        return "Could not extract meaningful text for summarization."
    return " ".join(selected)


def summarize_file(filepath: str) -> str:
    """
    Main entry point: given a file path, return an AI-generated summary string.

    Flow:
    1. Extract text from file.
    2. If text is too short, return it directly.
    3. Truncate to model's max input (1024 tokens ≈ 3000 chars).
    4. Run BART summarization pipeline.
    5. Return summary string.

    NETWORKING NOTE:
    This runs SYNCHRONOUSLY on the Flask server thread.
    In production you'd offload to a Celery task queue and use a WebSocket
    or polling endpoint to notify the client when the summary is ready.
    """
    # Step 1 – Extract text
    text = _extract_text_from_file(filepath)

    if text.startswith("["):
        # Binary or unreadable file
        return text

    # Step 2 – Very short files
    if len(text.strip()) < 50:
        return f"File content: {text.strip()}"

    # Step 3 – Truncate (BART max input ≈ 1024 tokens; ~3 chars/token)
    MAX_CHARS = 3000
    truncated = text[:MAX_CHARS]
    was_truncated = len(text) > MAX_CHARS

    # Step 4 – Summarize
    if _USE_MOCK:
        summary = _extractive_summary(truncated)
    else:
        summarizer = _get_summarizer()
        if summarizer is None:
            summary = _extractive_summary(truncated)
        else:
            try:
                # min_length / max_length are in tokens
                result = summarizer(
                    truncated,
                    max_length=150,
                    min_length=40,
                    do_sample=False
                )
                summary = result[0]["summary_text"]
            except Exception as e:
                print(f"[AI] Summarization error: {e}. Using fallback.")
                summary = _extractive_summary(truncated)

    if was_truncated:
        summary += " [Note: file was truncated to first 3000 characters for summarization.]"

    print(f"[AI] Summary generated ({len(summary)} chars)")
    return summary
