"""Recuperação BM25 em Python puro e modos de contexto controlados para os experimentos.

Modos:
  auto         BM25 top-k sobre o índice completo (inclui o documento contaminado DOC-FAQ-COM)
  correto      somente o regulamento vigente (contexto correto e suficiente, Parte B)
  ausente      nenhum chunk
  irrelevante  apenas o cardápio do RU
  conflitante  regulamento vigente (2026) + revogado (2019)
  malicioso    regulamento vigente + FAQ com injeção indireta
  reverso      auto com a ordem dos chunks invertida (metamórfico)
  ruido        auto + um chunk irrelevante no início (metamórfico)
"""
import math
import re
import unicodedata
from collections import Counter

from app.config import TOP_K
from app.corpus import Chunk, chunks, chunks_do_doc

STOPWORDS = set(
    "a o as os de da do das dos e em no na nos nas um uma para por com que qual quais quanto quantos "
    "como se ao aos ou mais sua seu é ser foi minha meu posso pode deve the what is of to how".split()
)

MODOS = ("auto", "correto", "ausente", "irrelevante", "conflitante", "malicioso", "reverso", "ruido")


def tokenize(texto: str) -> list[str]:
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    # radicalização simples por prefixo (6 letras): "emprestado" e "emprestar" -> "empres"
    return [w[:6] for w in re.findall(r"[a-z0-9]+", t) if w not in STOPWORDS and len(w) > 1]


class BM25:
    def __init__(self, docs: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenize(d.texto + " " + d.doc.titulo)) for d in docs]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avg = sum(self.len) / len(self.len)
        df = Counter(w for tf in self.tf for w in tf)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def buscar(self, consulta: str, k: int) -> list[tuple[Chunk, float]]:
        q = tokenize(consulta)
        scores = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for w in q:
                if w in tf:
                    f = tf[w]
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            scores.append((self.docs[i], s))
        scores = [x for x in scores if x[1] > 0]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


_indices: dict[bool, BM25] = {}


def index(somente_oficiais: bool = False) -> BM25:
    """somente_oficiais=True (melhoria M1) indexa apenas fontes oficiais, excluindo a wiki da comunidade."""
    if somente_oficiais not in _indices:
        _indices[somente_oficiais] = BM25([c for c in chunks() if c.doc.oficial or not somente_oficiais])
    return _indices[somente_oficiais]


def recuperar(pergunta: str, modo: str = "auto", k: int = TOP_K, somente_oficiais: bool = False) -> list[dict]:
    """Retorna lista de {chunk, score} conforme o modo de contexto."""
    if modo not in MODOS:
        raise ValueError(f"modo de contexto inválido: {modo}")
    if modo == "ausente":
        return []
    if modo == "correto":
        return [{"chunk": c, "score": None} for c in chunks_do_doc("DOC-AVA-2026")[:3]]
    if modo == "irrelevante":
        return [{"chunk": c, "score": None} for c in chunks_do_doc("DOC-CARDAPIO")[:2]]
    if modo == "conflitante":
        sel = chunks_do_doc("DOC-AVA-2026")[:3] + chunks_do_doc("DOC-AVA-2019")[:3]
        return [{"chunk": c, "score": None} for c in sel]
    if modo == "malicioso":
        sel = chunks_do_doc("DOC-AVA-2026")[3:5] + chunks_do_doc("DOC-FAQ-COM")
        return [{"chunk": c, "score": None} for c in sel]

    res = [{"chunk": c, "score": round(s, 3)} for c, s in index(somente_oficiais).buscar(pergunta, k)]
    if modo == "reverso":
        res.reverse()
    elif modo == "ruido":
        res.insert(0, {"chunk": chunks_do_doc("DOC-CARDAPIO")[3], "score": None})
    return res
