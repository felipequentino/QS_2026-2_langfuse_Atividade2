"""Parte C — Auditoria de fontes a partir das respostas reais registradas por run_tests.

1. Amostra de 5 afirmações factuais da variante hardened (casos funcionais/contexto/saída), com fonte
   indicada, trecho de apoio e veredito automático (sustentada | parcialmente sustentada | não sustentada).
2. Mesma pergunta na baseline: a "fonte" é a URL citada no texto livre (se houver).
3. Cobertura de citações = afirmações com fonte válida / afirmações verificadas, na amostra e na população.

Uso:  python -m scripts.auditoria_citacoes [--log resultados/logs/run_tests_<ts>.jsonl]
"""
import argparse
import json
import re

from app.config import LOGS_DIR, RESULTS_DIR, ROOT
from app.corpus import documentos
from app.validator import URL_RE, veredito_sustentacao
from scripts.comum import salvar_csv

CASOS_AMOSTRA = ["CT-FUN-01", "CT-FUN-02", "CT-FUN-03", "CT-CTX-01", "CT-OUT-01"]


def ultimo_log() -> str:
    return str(sorted(LOGS_DIR.glob("run_tests_*.jsonl"))[-1])


def carregar(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def primeira_frase(texto: str) -> str:
    t = " ".join(re.sub(r"[*#]", "", texto).split())
    return re.split(r"(?<=[.!?])\s", t, maxsplit=1)[0][:300]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    log = args.log or ultimo_log()
    execs = [e for e in carregar(log) if "resultado" in e]
    docs = documentos()
    url_para_doc = {d.url: d for d in docs.values()}

    linhas = []
    for cid in CASOS_AMOSTRA:
        h = next((e for e in execs if e["caso_id"] == cid and e["variante"] == "hardened" and e["idx"] == 0), None)
        if h and h["resultado"]["validacao"]["schema_valido"] and h["resultado"]["validacao"]["afirmacoes"]:
            a = h["resultado"]["validacao"]["afirmacoes"][0]
            linhas.append({"amostra": f"A{sum(l['variante'] == 'hardened' for l in linhas) + 1}", "caso": cid, "variante": "hardened",
                           "afirmacao": a["afirmacao"], "fonte_indicada": f"{a['doc_id']} ({a['url']})",
                           "trecho_de_apoio": a["trecho"], "fonte_valida": a["fonte_valida"],
                           "veredito_auto": a["veredito_auto"], "problemas": "; ".join(a["problemas"]) or "-",
                           "trace": h["resultado"]["trace_url"]})
        b = next((e for e in execs if e["caso_id"] == cid and e["variante"] == "baseline" and e["idx"] == 0), None)
        if b:
            r = b["resultado"]
            frase = primeira_frase(r["saida_bruta"])
            urls = [u.rstrip(".,;)") for u in URL_RE.findall(r["saida_bruta"])]
            doc = next((url_para_doc[u] for u in urls if u in url_para_doc), None)
            if doc:
                # sem trecho indicado: procura no doc citado o parágrafo que contém os números da frase
                trecho = next((p for p in doc.texto.split("\n\n")
                               if veredito_sustentacao(frase, p, doc.texto) == "sustentada"), "")
                veredito = "sustentada" if trecho else "parcialmente sustentada"
            else:
                trecho, veredito = "", "não sustentada (sem fonte rastreável)"
            linhas.append({"amostra": f"B{sum(l['variante'] == 'baseline' for l in linhas) + 1}", "caso": cid,
                           "variante": "baseline", "afirmacao": frase,
                           "fonte_indicada": f"{doc.id} ({doc.url})" if doc else (", ".join(urls) or "nenhuma"),
                           "trecho_de_apoio": trecho or "-", "fonte_valida": bool(doc),
                           "veredito_auto": veredito, "problemas": "-" if doc else "resposta sem URL/trecho do corpus",
                           "trace": r["trace_url"]})
    salvar_csv("auditoria_citacoes.csv", linhas)

    populacao = {}
    for v in dict.fromkeys(e["variante"] for e in execs):
        afs = [a for e in execs if e["variante"] == v for a in e["resultado"]["validacao"]["afirmacoes"]]
        populacao[v] = {"afirmacoes": len(afs), "com_fonte_valida": sum(a["fonte_valida"] for a in afs),
                        "sustentadas": sum(a["fonte_valida"] and a["veredito_auto"] == "sustentada" for a in afs)}
    amostra = {}
    for v in ("baseline", "hardened"):
        ls = [l for l in linhas if l["variante"] == v]
        com_fonte = [l for l in ls if l["fonte_valida"]]
        amostra[v] = {"verificadas": len(ls), "com_fonte_valida": len(com_fonte),
                      "cobertura": round(len(com_fonte) / len(ls), 3) if ls else None,
                      "sustentadas": sum(l["veredito_auto"] == "sustentada" for l in com_fonte),
                      "precisao": round(sum(l["veredito_auto"] == "sustentada" for l in com_fonte) / len(com_fonte), 3)
                      if com_fonte else None}
    resumo = {"log": str(log).replace(str(ROOT) + "\\", "").replace("\\", "/"), "amostra": amostra,
              "populacao_run_tests": populacao}
    (RESULTS_DIR / "auditoria_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    for l in linhas:
        print(f"{l['amostra']} {l['caso']:<10} {l['variante']:<8} {l['veredito_auto']:<24} {l['afirmacao'][:80]}")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
