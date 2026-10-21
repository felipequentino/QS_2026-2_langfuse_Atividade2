"""Validador/adaptador da saída do LLM (Parte C).

Verifica, em camadas:
  1. JSON válido (aceita cerca ```json``` mas registra como aviso)
  2. Conformidade ao esquema RespostaRAG (campos obrigatórios, tipos, sem campos extras)
  3. Para cada afirmação: doc_id existe no corpus, URL corresponde ao doc, doc foi de fato recuperado,
     trecho é literal do documento, e números citados na afirmação aparecem no trecho (sustentação)
  4. URLs presentes no texto da resposta pertencem a documentos conhecidos (allowlist)
"""
import json
import re
import unicodedata

from pydantic import ValidationError

from app.corpus import documentos
from app.schema import RespostaRAG

URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"[\"'“”‘’]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _numeros(t: str) -> set[str]:
    out = set()
    for n in NUM_RE.findall(t):
        n = n.replace(",", ".")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        out.add(n)
    return out


def extrair_json(texto: str) -> tuple[dict | None, list[str], list[str]]:
    """Retorna (objeto, avisos, erros)."""
    bruto = texto.strip()
    avisos = []
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", bruto, re.S)
    if m:
        avisos.append("JSON envolvido em cerca de código markdown")
        bruto = m.group(1)
    try:
        obj = json.loads(bruto)
    except json.JSONDecodeError as e:
        return None, avisos, [f"JSON inválido: {e.msg} (linha {e.lineno}, col {e.colno})"]
    if not isinstance(obj, dict):
        return None, avisos, ["JSON não é um objeto"]
    return obj, avisos, []


def veredito_sustentacao(afirmacao: str, trecho: str, doc_texto: str) -> str:
    """sustentada | parcialmente sustentada | não sustentada (heurística automática)."""
    if normalizar(trecho) not in normalizar(doc_texto):
        return "não sustentada"
    nums_af = _numeros(afirmacao)
    nums_tr = _numeros(trecho)
    if nums_af and not nums_af <= nums_tr:
        return "parcialmente sustentada" if nums_af & nums_tr else "não sustentada"
    return "sustentada"


def validar(texto: str, doc_ids_recuperados: set[str] | None = None) -> dict:
    docs = documentos()
    urls_validas = {d.url for d in docs.values()}
    r = {
        "json_valido": False,
        "schema_valido": False,
        "erros": [],
        "avisos": [],
        "afirmacoes": [],
        "total_afirmacoes": 0,
        "afirmacoes_fonte_valida": 0,
        "afirmacoes_sustentadas": 0,
        "urls_desconhecidas_na_resposta": sorted({u.rstrip(".,;") for u in URL_RE.findall(texto)} - urls_validas),
        "objeto": None,
    }
    if r["urls_desconhecidas_na_resposta"]:
        r["erros"].append(f"URLs fora da allowlist: {r['urls_desconhecidas_na_resposta']}")

    obj, avisos, erros = extrair_json(texto)
    r["avisos"] += avisos
    if obj is None:
        r["erros"] += erros
        return r
    r["json_valido"] = True

    try:
        resp = RespostaRAG.model_validate(obj)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            r["erros"].append(f"esquema: {loc}: {err['msg']}")
        return r
    r["schema_valido"] = True
    r["objeto"] = resp.model_dump()

    for a in resp.afirmacoes:
        problemas = []
        doc = docs.get(a.doc_id)
        if doc is None:
            problemas.append(f"doc_id inexistente: {a.doc_id}")
        if a.url not in urls_validas:
            problemas.append(f"URL inexistente: {a.url}")
        elif doc is not None and a.url != doc.url:
            problemas.append(f"URL não corresponde ao documento {a.doc_id}")
        if doc is not None and doc_ids_recuperados is not None and a.doc_id not in doc_ids_recuperados:
            problemas.append("documento citado não estava no contexto recuperado")
        fonte_valida = not problemas
        if doc is not None and not doc.vigente:
            problemas.append("documento citado está revogado")
        veredito = veredito_sustentacao(a.afirmacao, a.trecho, doc.texto) if doc else "não sustentada"
        r["afirmacoes"].append({**a.model_dump(), "fonte_valida": fonte_valida, "veredito_auto": veredito,
                                "problemas": problemas})
        r["afirmacoes_fonte_valida"] += fonte_valida
        r["afirmacoes_sustentadas"] += fonte_valida and veredito == "sustentada"
    r["total_afirmacoes"] = len(resp.afirmacoes)
    return r
