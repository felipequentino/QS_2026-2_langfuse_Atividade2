"""Carrega os prompts versionados de prompts/*.txt (seções ### META, ### SYSTEM, ### USER)."""
import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from app.config import PROMPTS_DIR

ARQUIVOS = {"P1": "P1_direto.txt", "P2": "P2_estruturado.txt", "P3": "P3_few_shot.txt"}


@dataclass(frozen=True)
class Prompt:
    id: str
    nome: str
    versao: str
    system: str | None
    user: str

    def render(self, contexto: str, pergunta: str) -> tuple[str | None, str]:
        # replace (e não str.format) porque os prompts contêm JSON com chaves
        return self.system, self.user.replace("{contexto}", contexto).replace("{pergunta}", pergunta)

    @property
    def nome_langfuse(self) -> str:
        return f"av2-{self.id}"


@lru_cache(maxsize=None)
def carregar(prompt_id: str) -> Prompt:
    raw = (PROMPTS_DIR / ARQUIVOS[prompt_id]).read_text(encoding="utf-8")
    secoes = dict(re.findall(r"^### (\w+)\n(.*?)(?=^### |\Z)", raw, re.S | re.M))
    meta = yaml.safe_load(secoes["META"])
    return Prompt(
        id=meta["id"],
        nome=meta["nome"],
        versao=str(meta["versao"]),
        system=secoes.get("SYSTEM", "").strip() or None,
        user=secoes["USER"].strip(),
    )
