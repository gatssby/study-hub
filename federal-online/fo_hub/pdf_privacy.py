"""Conservative privacy and extraction-quality helpers for indexed PDFs.

The FO API exposes indexed text, not private source PDFs. This module removes
high-confidence identifiers from extracted text and marks ambiguous pages for
manual/OCR review instead of guessing.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

CPF_RE = re.compile(r"(?<!\d)\d{3}[.\s]*\d{3}[.\s]*\d{3}[-\s]*\d{2}(?!\d)")
PRIVACY_POLICY_VERSION = 4
LABELED_ID_RE = re.compile(
    r"(?i)\bcpf[ \t]*[:#-][ \t]*[0-9][0-9 ./-]{3,40}"
)
NAME_LABEL = r"(?:nome(?:[ \t]+completo)?|aluno|propriet[aá]rio|titular)"
LABELED_NAME_RE = re.compile(
    rf"(?i)\b{NAME_LABEL}[ \t]*[:#-][ \t]*[^\n\r]{{2,120}}"
)
EMPTY_NAME_RE = re.compile(rf"(?im)\b{NAME_LABEL}[ \t]*[:#-][ \t]*$")
UNRESOLVED_CPF_RE = re.compile(r"(?i)\bcpf[ \t]*(?:[:#-][ \t]*)?[0-9]")
WATERMARK_HINT_RE = re.compile(
    r"(?i)\b(?:cpf|nome(?:\s+completo)?|aluno|propriet[aá]rio|titular|documento)\b"
)


@dataclass(frozen=True)
class PagePrivacy:
    text: str
    pii_redacted: bool
    quality: str
    exposure: str


def _valid_cpf(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    total = sum(int(d) * (10 - i) for i, d in enumerate(digits[:9]))
    first = (total * 10 % 11) % 10
    total = sum(int(d) * (11 - i) for i, d in enumerate(digits[:10]))
    second = (total * 10 % 11) % 10
    return digits[-2:] == f"{first}{second}"


def sanitize_text(text: str) -> tuple[str, bool]:
    """Remove only high-confidence identifiers; never log matched values."""
    value = unicodedata.normalize("NFC", text or "")
    changed = False

    def cpf(match: re.Match[str]) -> str:
        nonlocal changed
        if _valid_cpf(match.group(0)):
            changed = True
            return "[IDENTIFICADOR REMOVIDO]"
        return match.group(0)

    value = CPF_RE.sub(cpf, value)

    def labeled(match: re.Match[str]) -> str:
        nonlocal changed
        changed = True
        label = match.group(0).split(":", 1)[0].split("#", 1)[0].split("-", 1)[0]
        return f"{label}: [DADO REMOVIDO]"

    value = LABELED_ID_RE.sub(labeled, value)
    # A name is only safely removed when it shares a page with a CPF marker.
    # Otherwise the page is blocked by classify_page rather than guessing.
    if "[IDENTIFICADOR REMOVIDO]" in value or "[DADO REMOVIDO]" in value:
        value = LABELED_NAME_RE.sub(labeled, value)
        marker = "[IDENTIFICADOR REMOVIDO]"
        # A repeated unlabelled watermark supplies its own delimiter. Learn
        # only short, letter-only name spans BETWEEN identifiers, never from a
        # person's configured identity or production fixture. Single/ambiguous
        # marks remain blocked, not guessed. Existing v2 text is also supported.
        spans = value.split(marker)
        names = {" ".join(span.split()) for span in spans[1:-1]
                 if re.fullmatch(r"\s*[^\W\d_]+(?:\s+[^\W\d_]+){1,7}\s*", span)}
        for name in names:
            pattern = r"(?<!\w)" + r"\s+".join(map(re.escape, name.split())) + r"\s*" + re.escape(marker)
            if len(re.findall(pattern, value)) >= 2:
                value = re.sub(pattern, "[MARCA D'AGUA REMOVIDA]", value)
                changed = True
                # A clipped/reordered watermark might leave the name without
                # its identifier. Do not release it via a successful partial match.
                if re.search(r"\b" + r"\s+".join(map(re.escape, name.split())) + r"\b", value):
                    return "[REVISAO PRIVACIDADE NECESSARIA]", True
        if "[DADO REMOVIDO]" in value:
            value = re.sub(r"(?i)\bCPF\s*[:#-]\s*" + re.escape(marker), "CPF: [DADO REMOVIDO]", value)
    return value, changed


def classify_page(text: str, *, pii_redacted: bool) -> PagePrivacy:
    normalized = (text or "").strip()
    content = normalized.replace("[MARCA D'AGUA REMOVIDA]", "").strip()
    if not content:
        return PagePrivacy("", pii_redacted, "ocr_pending", "blocked")
    if "[IDENTIFICADOR REMOVIDO]" in normalized or "[REVISAO PRIVACIDADE NECESSARIA]" in normalized:
        return PagePrivacy("", pii_redacted, "privacy_review", "blocked")
    if EMPTY_NAME_RE.search(normalized) or UNRESOLVED_CPF_RE.search(normalized):
        return PagePrivacy("", pii_redacted, "privacy_review", "blocked")
    for name in LABELED_NAME_RE.finditer(normalized):
        if not re.search(r"[:#-]\s*\[DADO REMOVIDO\]\s*$", name.group()):
            return PagePrivacy("", pii_redacted, "privacy_review", "blocked")
    if len(normalized) < 24:
        return PagePrivacy(normalized, pii_redacted, "low_text", "text_only")
    return PagePrivacy(normalized, pii_redacted, "text", "text_only")


def sanitize_page(text: str) -> PagePrivacy:
    sanitized, changed = sanitize_text(text)
    return classify_page(sanitized, pii_redacted=changed)
