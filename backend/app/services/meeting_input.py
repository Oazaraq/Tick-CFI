"""Entrée isolée des transcriptions (DFB B.2) : fichier ou texte collé → texte brut « Intervenant : texte ».

Le lot 3bis (Microsoft Graph) y branchera sa source : les transcriptions Teams arrivent au même format .vtt.
"""
import html
import re

_VOICE = re.compile(r"^<v(?:\.[\w.-]+)?\s+([^>]+)>(.*?)(?:</v>)?$", re.S)
_TAG = re.compile(r"<[^>]+>")


def to_text(content: str, filename: str | None = None) -> str:
    text = content.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    if (filename or "").lower().endswith(".vtt") or text.startswith("WEBVTT"):
        return vtt_to_text(text)
    return text.strip()


def vtt_to_text(text: str) -> str:
    """Retire l'en-tête WEBVTT, les identifiants et horodatages ; regroupe les répliques successives d'un intervenant."""
    lines: list[list[str | None]] = []  # [intervenant, texte]
    for block in re.split(r"\n\s*\n", text):
        rows = [row.strip() for row in block.split("\n") if row.strip()]
        if not rows or rows[0].startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        while rows and "-->" not in rows[0] and any("-->" in r for r in rows[1:]):
            rows.pop(0)  # identifiant de réplique
        if rows and "-->" in rows[0]:
            rows.pop(0)  # horodatage
        cue = " ".join(rows)
        match = _VOICE.match(cue)
        speaker, said = (match[1].strip(), match[2]) if match else (None, cue)
        said = html.unescape(_TAG.sub("", said)).strip()
        if not said:
            continue
        if lines and speaker and lines[-1][0] == speaker:
            lines[-1][1] = f"{lines[-1][1]} {said}"
        else:
            lines.append([speaker, said])
    return "\n".join(f"{s} : {t}" if s else str(t) for s, t in lines)
