"""Controles da variante endurecida (hardened): separação contexto/instrução, quarentena de chunks
com padrões de injeção e saneamento da saída."""
import html
import re

from app.corpus import Chunk, documentos
from app.validator import URL_RE, normalizar

PADROES_INJECAO = [
    r"ignore (todas )?(as )?(suas )?(instruc|regras|orientac)",
    r"ignore (all |any )?(previous|prior|the above)",
    r"desconsidere (as |todas )",
    r"instruc\w* para o assistente",
    r"(prompt|instruc\w*) (de|do) sistema",
    r"system prompt",
    r"a partir de agora voce",
    r"modo (desenvolvedor|dan)\b",
    r"\bdan\b",
    r"(revele|mostre|repita|imprima) (o |seu |suas |as )?(prompt|instruc)",
    r"(login|senha|password)",
]
_REGEX = [re.compile(p) for p in PADROES_INJECAO]


def detectar_injecao(texto: str) -> list[str]:
    t = normalizar(texto)
    return [p.pattern for p in _REGEX if p.search(t)]


def quarentena(chunks: list[Chunk]) -> tuple[list[Chunk], list[dict]]:
    seguros, isolados = [], []
    for c in chunks:
        achados = detectar_injecao(c.texto)
        if achados:
            isolados.append({**c.meta(), "padroes": achados, "texto": c.texto})
        else:
            seguros.append(c)
    return seguros, isolados


def formatar_contexto(chunks: list[Chunk], estilo: str, escapar: bool = False) -> str:
    """estilo 'simples' (P1) ou 'tags' (P2/P3). escapar=True neutraliza marcações dentro dos dados."""
    if not chunks:
        return "(nenhum documento recuperado)"
    partes = []
    for c in chunks:
        texto = html.escape(c.texto, quote=False) if escapar else c.texto
        vig = "sim" if c.doc.vigente else "não (revogado)"
        if estilo == "simples":
            partes.append(f"Fonte: {c.doc.titulo} ({c.doc.url})\n{texto}")
        else:
            partes.append(
                f'<documento id="{c.doc.id}" url="{c.doc.url}" titulo="{c.doc.titulo}" vigente="{vig}">\n{texto}\n</documento>'
            )
    return "\n\n".join(partes)


def sanear_saida(objeto: dict) -> tuple[dict, list[str]]:
    """Remove URLs fora da allowlist do texto da resposta e descarta afirmações sem fonte válida."""
    acoes = []
    urls_validas = {d.url for d in documentos().values()}
    resposta = objeto.get("resposta", "")
    for u in set(URL_RE.findall(resposta)):
        if u.rstrip(".,;") not in urls_validas:
            resposta = resposta.replace(u, "[link removido]")
            acoes.append(f"URL removida: {u}")
    objeto = {**objeto, "resposta": resposta}
    return objeto, acoes
