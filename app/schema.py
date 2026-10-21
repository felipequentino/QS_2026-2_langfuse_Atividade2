"""Esquema da saída estruturada (RQ-OUT-01). Campos extras são proibidos."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Afirmacao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    afirmacao: str = Field(min_length=5, description="Afirmação factual feita na resposta")
    doc_id: str = Field(description="Id do documento que sustenta a afirmação, ex.: DOC-AVA-2026")
    url: str = Field(description="URL do documento citado, exatamente como no contexto")
    trecho: str = Field(min_length=10, description="Trecho literal copiado do documento que sustenta a afirmação")


class RespostaRAG(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resposta: str = Field(min_length=1, description="Resposta em linguagem natural ao discente (nunca vazia)")
    afirmacoes: list[Afirmacao] = Field(description="Uma entrada por afirmação factual, com fonte e trecho")
    confianca: Literal["alta", "media", "baixa"]
    recusou: bool = Field(description="true se não respondeu por falta de contexto ou por pedido indevido")
    motivo_recusa: str | None = None
