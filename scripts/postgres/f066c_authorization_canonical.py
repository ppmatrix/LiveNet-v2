"""Canonicalizacao JSON para registos de autorizacao F0.66C.

Sem persistencia, acesso externo ou execucao administrativa.
"""

from hashlib import sha256
import json


def canonical_json_bytes(value: dict) -> bytes:
    """Produz uma representacao JSON deterministica em UTF-8."""

    if not isinstance(value, dict):
        raise TypeError("O registo deve ser um objeto JSON")

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Registo nao serializavel em JSON") from exc

    return encoded.encode("utf-8")


def canonical_sha256(value: dict) -> str:
    """Calcula SHA-256 dos bytes JSON canonicos."""

    return sha256(canonical_json_bytes(value)).hexdigest()
