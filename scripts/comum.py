"""Utilidades compartilhadas pelos scripts de experimento."""
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.config import LOGS_DIR, RESULTS_DIR


def carimbo() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def salvar_csv(nome: str, linhas: list[dict]) -> str:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = RESULTS_DIR / nome
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: abre certo no Excel
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    return str(caminho.relative_to(RESULTS_DIR.parent))


def salvar_jsonl(nome: str, registros: list[dict]) -> str:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = LOGS_DIR / nome
    with open(caminho, "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    return str(caminho.relative_to(RESULTS_DIR.parent)).replace("\\", "/")


def paralelo(funcao, itens: list, workers: int = 4) -> list:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(funcao, itens))


def resumo_texto(r: dict, limite: int = 400) -> str:
    obj = r["saida_final"] if r["guard"] else r["validacao"]["objeto"]
    texto = obj["resposta"] if obj else r["saida_bruta"]
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[:limite] + "…"
