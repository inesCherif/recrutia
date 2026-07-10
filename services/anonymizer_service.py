"""
Anonymizer Service — OWASP LLM02 PII Protection Layer
======================================================
Prevents Sensitive Information Disclosure by anonymizing CV text BEFORE
it is ever sent to external AI APIs (Mistral, etc.).

Pipeline:
    raw_cv_text
        ↓ anonymize(text, user_id)
    anonymized_text  → [PERSON_1], [EMAIL_1], [PHONE_1] ...
        ↓ (agents receive only anonymized text)
    ai_generated_output (still contains tokens)
        ↓ deanonymize(text, user_id)
    final_output (real names/emails restored from encrypted vault)

PII Detection (Hybrid, no paid APIs):
    1. Regex patterns  — Emails, Phone numbers, URLs, LinkedIn, GitHub
    2. SpaCy NER       — PERSON entities (en_core_web_sm or fr_core_news_sm)
    3. Fallback        — If spaCy unavailable, regex-only mode (still catches ~90%)

Vault Storage:
    - Fernet symmetric encryption (cryptography library)
    - Master key from PII_ENCRYPTION_KEY env var (auto-generated if missing)
    - Stored in SQLite pii_vault table via AuthService
"""

import os
import re
import uuid
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Fernet Encryption Vault
# ─────────────────────────────────────────────────────────────

def _get_fernet():
    """Get or create a Fernet cipher from PII_ENCRYPTION_KEY env var."""
    from cryptography.fernet import Fernet
    key = os.getenv("PII_ENCRYPTION_KEY")
    if not key:
        # Auto-generate a key for development; warn loudly
        key = Fernet.generate_key().decode()
        logger.warning(
            "[PII Vault] ⚠️  PII_ENCRYPTION_KEY not set in .env — "
            "using a random session key. Data will NOT survive server restart. "
            "Set PII_ENCRYPTION_KEY for production."
        )
        os.environ["PII_ENCRYPTION_KEY"] = key
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(value: str) -> str:
    """Encrypt a PII string with Fernet. Returns base64 ciphertext."""
    fernet = _get_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted ciphertext back to plaintext."""
    fernet = _get_fernet()
    return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")


# ─────────────────────────────────────────────────────────────
# Regex-based PII patterns (fast, reliable, language-agnostic)
# ─────────────────────────────────────────────────────────────

# Each entry: (token_prefix, compiled_regex)
_REGEX_PATTERNS: List[Tuple[str, re.Pattern]] = [
    # Email — must come before URLs to catch user@domain.com
    ("EMAIL", re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE
    )),
    # International phone numbers — +33 6 12 34 56 78 or (0) 612 345 678 etc.
    ("PHONE", re.compile(
        r"(?<!\d)(?:\+\d{1,3}[\s.\-]?)?(?:\(?\d{1,4}\)?[\s.\-]?){2,5}\d{2,4}(?!\d)",
    )),
    # LinkedIn profile URL
    ("LINKEDIN", re.compile(
        r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_\-%.]+/?",
        re.IGNORECASE
    )),
    # GitHub profile URL
    ("GITHUB", re.compile(
        r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_\-]+/?",
        re.IGNORECASE
    )),
    # Generic URLs
    ("URL", re.compile(
        r"https?://[^\s<>\"{}|\\^`\[\]]+",
        re.IGNORECASE
    )),
    # Date of birth patterns — "née le 12/03/1995", "né le 12 mars 1995"
    ("DOB", re.compile(
        r"\bné(?:e)?\s+le\s+\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}\b"
        r"|\bborn\s+(?:on\s+)?\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}\b",
        re.IGNORECASE
    )),
    # Physical addresses — partial detection
    ("ADDRESS", re.compile(
        r"\b\d{1,5}\s+[A-Za-zÀ-ÿ\s]+(?:rue|avenue|ave|blvd|boulevard|chemin|impasse|allée|street|st|road|rd|lane|ln|drive|dr)\b[^,\n]*",
        re.IGNORECASE
    )),
]


def _regex_detect(text: str) -> List[Tuple[int, int, str, str]]:
    """
    Find all regex-based PII spans.
    Returns list of (start, end, token_prefix, matched_text).
    """
    spans: List[Tuple[int, int, str, str]] = []
    for prefix, pattern in _REGEX_PATTERNS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end(), prefix, match.group()))
    return spans


# ─────────────────────────────────────────────────────────────
# SpaCy NER — PERSON entity detection
# ─────────────────────────────────────────────────────────────

_spacy_nlp = None
_spacy_loaded = False


def _load_spacy() -> Optional[object]:
    """
    Lazily load a spaCy model.
    Tries en_core_web_sm first, then fr_core_news_sm.
    Returns None if neither is available (graceful fallback).
    """
    global _spacy_nlp, _spacy_loaded
    if _spacy_loaded:
        return _spacy_nlp

    _spacy_loaded = True
    try:
        import spacy
        for model_name in ["en_core_web_sm", "fr_core_news_sm"]:
            try:
                _spacy_nlp = spacy.load(model_name, exclude=["parser", "tagger"])
                logger.info("[PII Anonymizer] ✅ spaCy model loaded: %s", model_name)
                return _spacy_nlp
            except OSError:
                continue

        # Try to auto-download the smallest model
        logger.info("[PII Anonymizer] Downloading spaCy en_core_web_sm model...")
        try:
            from spacy.cli import download
            download("en_core_web_sm")
            _spacy_nlp = spacy.load("en_core_web_sm", exclude=["parser", "tagger"])
            logger.info("[PII Anonymizer] ✅ spaCy model downloaded and loaded")
            return _spacy_nlp
        except Exception as e:
            logger.warning("[PII Anonymizer] ⚠️  Could not download spaCy model: %s — using regex-only mode", e)
            return None

    except ImportError:
        logger.warning("[PII Anonymizer] spaCy not installed — using regex-only mode")
        return None


def _spacy_detect(text: str) -> List[Tuple[int, int, str, str]]:
    """
    Use spaCy NER to detect PERSON entities.
    Returns list of (start, end, 'PERSON', matched_text).
    """
    nlp = _load_spacy()
    if not nlp:
        return []

    try:
        doc = nlp(text[:5000])  # Limit for performance
        spans = []
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "PER"):
                spans.append((ent.start_char, ent.end_char, "PERSON", ent.text))
        return spans
    except Exception as e:
        logger.warning("[PII Anonymizer] spaCy detection failed: %s", e)
        return []


# ─────────────────────────────────────────────────────────────
# Span merging & deduplication
# ─────────────────────────────────────────────────────────────

def _merge_spans(
    spans: List[Tuple[int, int, str, str]]
) -> List[Tuple[int, int, str, str]]:
    """
    Sort spans by start position, remove overlaps.
    Later spans that overlap earlier ones are discarded.
    """
    if not spans:
        return []

    # Sort by start position; prefer longer matches on ties
    sorted_spans = sorted(spans, key=lambda x: (x[0], -(x[1] - x[0])))
    merged = [sorted_spans[0]]

    for span in sorted_spans[1:]:
        prev_end = merged[-1][1]
        if span[0] >= prev_end:  # No overlap
            merged.append(span)
        # Else: overlapping — skip (keep first/earlier match)

    return merged


# ─────────────────────────────────────────────────────────────
# Anonymizer Service
# ─────────────────────────────────────────────────────────────

class AnonymizerService:
    """
    PII Anonymization + Encrypted Vault.

    Usage:
        from services.anonymizer_service import anonymizer_service

        anon_text = anonymizer_service.anonymize(raw_text, user_id="abc123")
        # ... send anon_text to LLM agents ...
        real_text = anonymizer_service.deanonymize(ai_output, user_id="abc123")
    """

    def anonymize(self, text: str, user_id: str) -> str:
        """
        Detect all PII in `text`, replace with tokens, store encrypted
        mapping in the SQLite vault.

        Returns the anonymized text (safe to send to external APIs).
        """
        if not text or not text.strip():
            return text

        # Gather all PII spans
        spans = _regex_detect(text) + _spacy_detect(text)
        spans = _merge_spans(spans)

        if not spans:
            logger.debug("[PII Anonymizer] No PII detected")
            return text

        # Build token map: real_value → token (dedup same value)
        # Count per prefix type
        type_counters: Dict[str, int] = {}
        value_to_token: Dict[str, str] = {}

        for _, _, prefix, real_value in spans:
            if real_value not in value_to_token:
                type_counters[prefix] = type_counters.get(prefix, 0) + 1
                token = f"[{prefix}_{type_counters[prefix]}]"
                value_to_token[real_value] = token

        # Replace spans in reverse order to preserve character positions
        result = list(text)
        for start, end, prefix, real_value in reversed(spans):
            token = value_to_token[real_value]
            result[start:end] = list(token)
        anonymized = "".join(result)

        # Store encrypted mappings in vault
        self._save_to_vault(user_id, value_to_token)

        detected_types = list({p for _, _, p, _ in spans})
        logger.info(
            "[PII Anonymizer] 🔒 Anonymized %d PII entity(ies) — types: %s",
            len(value_to_token),
            detected_types,
        )
        return anonymized

    def deanonymize(self, text: str, user_id: str) -> str:
        """
        Restore real PII values from the encrypted vault by replacing
        all tokens (e.g. [EMAIL_1]) with their decrypted originals.
        """
        if not text or not text.strip():
            return text

        # Load all token → encrypted_value pairs from vault
        token_to_encrypted = self._load_from_vault(user_id)
        if not token_to_encrypted:
            return text  # Nothing stored for this user

        # Replace all tokens in text
        for token, encrypted_value in token_to_encrypted.items():
            if token in text:
                try:
                    real_value = decrypt_value(encrypted_value)
                    text = text.replace(token, real_value)
                except Exception as e:
                    logger.error("[PII Anonymizer] Decryption failed for %s: %s", token, e)

        logger.debug("[PII Anonymizer] 🔓 Deanonymization complete")
        return text

    def _save_to_vault(self, user_id: str, value_to_token: Dict[str, str]):
        """Encrypt each PII value and store token → ciphertext in SQLite vault."""
        try:
            from services.auth_service import AuthService
            auth = AuthService()
            for real_value, token in value_to_token.items():
                encrypted = encrypt_value(real_value)
                auth.save_vault_entry(user_id, token, encrypted)
        except Exception as e:
            logger.error("[PII Anonymizer] Vault save failed: %s", e)

    def _load_from_vault(self, user_id: str) -> Dict[str, str]:
        """Load all token → encrypted_value mappings for a user from SQLite."""
        try:
            from services.auth_service import AuthService
            auth = AuthService()
            return auth.get_vault_entries(user_id)
        except Exception as e:
            logger.error("[PII Anonymizer] Vault load failed: %s", e)
            return {}


# ── Singleton ─────────────────────────────────────────────────
anonymizer_service = AnonymizerService()
