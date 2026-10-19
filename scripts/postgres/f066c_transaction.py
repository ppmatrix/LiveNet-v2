"""Composicao transacional F0.66C, sem execucao PostgreSQL."""

from pathlib import Path
from hashlib import sha256
import re

from f066c_integrity import APPROVED_HASHES, load_verified_guard


BEGIN = re.compile(r"(?im)^[ \t]*BEGIN[ \t]*;[ \t]*$")
COMMIT = re.compile(r"(?im)^[ \t]*COMMIT[ \t]*;[ \t]*$")
CONTROL = re.compile(
    r"(?im)^[ \t]*(?:BEGIN|COMMIT|ROLLBACK|SAVEPOINT|"
    r"RELEASE|START[ \t]+TRANSACTION)[ \t;]"
)


def compose_transaction(sql_path: Path, guard_path: Path) -> str:
    """Insere a guarda dentro da transacao administrativa existente."""

    expected = APPROVED_HASHES.get(sql_path.name)
    if expected is None:
        raise ValueError('Ficheiro SQL nao autorizado')

    raw = sql_path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError('Integridade SQL divergente')

    source = raw.decode('utf-8')
    guard = load_verified_guard(guard_path)

    lines = source.splitlines(keepends=True)

    if not lines or lines[0].strip() != r"\set ON_ERROR_STOP on":
        raise ValueError("Diretiva psql inicial inesperada")

    body_source = "".join(lines[1:])

    if any(
        line.lstrip().startswith("\\")
        for line in body_source.splitlines()
    ):
        raise ValueError("Diretivas psql adicionais")

    begins = list(BEGIN.finditer(body_source))
    commits = list(COMMIT.finditer(body_source))

    if len(begins) != 1 or len(commits) != 1:
        raise ValueError("Limites transacionais inesperados")

    begin = begins[0]
    commit = commits[0]

    if begin.start() >= commit.start():
        raise ValueError("Ordem transacional inesperada")

    before = body_source[:begin.start()]
    after = body_source[commit.end():]

    def comments_only(text: str) -> bool:
        return all(
            not line.strip() or line.lstrip().startswith("--")
            for line in text.splitlines()
        )

    if not comments_only(before) or not comments_only(after):
        raise ValueError("Conteudo fora da transacao")

    body = body_source[begin.end():commit.start()]

    if CONTROL.search(body):
        raise ValueError("Controlo transacional adicional")

    if guard.count("DO $f066c_guard$") != 1:
        raise ValueError("Guarda de sessao inesperada")

    return (
        "BEGIN;\n"
        + guard.rstrip()
        + "\n"
        + body
        + "\nCOMMIT;\n"
    )
