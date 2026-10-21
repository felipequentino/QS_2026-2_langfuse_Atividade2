"""Carrega os documentos sintéticos (Markdown com front-matter YAML) e divide em chunks por parágrafo."""
from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from app.config import CORPUS_DIR


@dataclass(frozen=True)
class Documento:
    id: str
    titulo: str
    url: str
    versao: str
    vigente: bool
    classificacao: str
    texto: str
    arquivo: str
    oficial: bool = True


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc: Documento = field(compare=False)
    texto: str

    def meta(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc.id,
            "url": self.doc.url,
            "vigente": self.doc.vigente,
            "classificacao": self.doc.classificacao,
            "oficial": self.doc.oficial,
        }


def _parse(path) -> Documento:
    raw = path.read_text(encoding="utf-8")
    _, front, corpo = raw.split("---", 2)
    meta = yaml.safe_load(front)
    return Documento(
        id=meta["id"],
        titulo=meta["titulo"],
        url=meta["url"],
        versao=str(meta["versao"]),
        vigente=bool(meta["vigente"]),
        classificacao=meta["classificacao"],
        texto=corpo.strip(),
        arquivo=path.name,
        oficial=bool(meta.get("oficial", True)),
    )


@lru_cache(maxsize=1)
def documentos() -> dict[str, Documento]:
    docs = [_parse(p) for p in sorted(CORPUS_DIR.glob("*.md"))]
    return {d.id: d for d in docs}


@lru_cache(maxsize=1)
def chunks() -> list[Chunk]:
    out = []
    for doc in documentos().values():
        paragrafos = [p.strip() for p in doc.texto.split("\n\n") if p.strip()]
        for i, p in enumerate(paragrafos, 1):
            out.append(Chunk(f"{doc.id}#{i}", doc, p))
    return out


def chunks_do_doc(doc_id: str) -> list[Chunk]:
    return [c for c in chunks() if c.doc.id == doc_id]
