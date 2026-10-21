"""Parte B — Laboratório de contexto e prompts.

Mesma tarefa executada com P1, P2 e P3 em quatro condições de contexto (correto, ausente, irrelevante,
conflitante), com repetições para medir previsibilidade. Sem guardas e sem modo JSON nativo, para isolar o
efeito do prompt.

Uso:  python -m scripts.prompt_lab [--repeticoes 2]
Saídas: resultados/prompt_lab.csv, resultados/prompt_lab_resumo.json, resultados/logs/prompt_lab_<ts>.jsonl
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from langfuse import get_client

from app.avaliacao import indicou_incerteza
from app.config import RESULTS_DIR
from app.validator import normalizar
from scripts.comum import carimbo, paralelo, resumo_texto, salvar_csv, salvar_jsonl

PERGUNTA = "Qual a média mínima para aprovação direta e qual a frequência mínima exigida?"
CONDICOES = ["correto", "ausente", "irrelevante", "conflitante"]
PROMPTS = ["P1", "P2", "P3"]
FATOS = {"media": ["7,0", "7.0", "sete"], "frequencia": ["75"]}
INVENTADOS = ["7,0", "7.0", "75%", "75 %", "6,0", "70%"]


def julgar(condicao: str, r: dict) -> dict:
    t = normalizar(r["saida_bruta"])
    fatos_ok = all(any(normalizar(x) in t for x in alts) for alts in FATOS.values())
    incerteza = indicou_incerteza(r)
    val = r["validacao"]
    if condicao in ("correto", "conflitante"):
        correto = fatos_ok and not (condicao == "conflitante" and "6,0" in t and "revog" not in t)
        sinalizou_conflito = condicao == "conflitante" and "revog" in t
    else:
        inventou = any(normalizar(x) in t for x in INVENTADOS)
        correto = incerteza and not inventou
        sinalizou_conflito = None
    citacao_ok = val["schema_valido"] and val["total_afirmacoes"] > 0 and \
        val["afirmacoes_fonte_valida"] == val["total_afirmacoes"]
    if condicao in ("ausente", "irrelevante"):
        citacao_ok = val["schema_valido"] and val["total_afirmacoes"] == 0
    return {"resultado_correto": correto, "fatos_presentes": fatos_ok, "indicou_incerteza": incerteza,
            "sinalizou_revogacao": sinalizou_conflito, "citacao_verificavel": citacao_ok}


def executar(tarefa):
    pid, cond, rep, sessao = tarefa
    from app.pipeline import responder
    try:
        r = responder(PERGUNTA, pid, cond, guard=False, json_mode=False, rotulo=f"LAB {pid} {cond} r{rep}",
                      sessao=sessao, tags=["av2", "prompt_lab", pid, cond])
    except Exception as e:
        print(f"ERRO {pid} {cond} r{rep}: {e!r}"[:200])
        return {"prompt": pid, "condicao": cond, "repeticao": rep, "erro": repr(e)}
    j = julgar(cond, r)
    get_client().create_score(trace_id=r["trace_id"], name="lab_resultado_correto",
                              value=1 if j["resultado_correto"] else 0, data_type="BOOLEAN")
    return {"prompt": pid, "condicao": cond, "repeticao": rep, "julgamento": j, "resultado": r}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeticoes", type=int, default=2)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--de-log", help="regera CSV/resumo a partir de um log existente, sem chamar o LLM")
    args = ap.parse_args()
    ts = carimbo()
    sessao = f"prompt_lab-{ts}"
    if args.de_log:
        with open(args.de_log, encoding="utf-8") as f:
            execs = [json.loads(l) for l in f if l.strip()]
        log = args.de_log.replace("\\", "/")
        sessao = "prompt_lab-" + Path(log).stem.split("_")[-1]
    else:
        tarefas = [(p, c, k + 1, sessao) for p in PROMPTS for c in CONDICOES for k in range(args.repeticoes)]
        print(f"{len(tarefas)} chamadas reais ao LLM")
        execs = paralelo(executar, tarefas, args.workers)
        get_client().flush()
        log = salvar_jsonl(f"prompt_lab_{ts}.jsonl", execs)
    erros = [e for e in execs if "erro" in e]
    execs = [e for e in execs if "erro" not in e]
    print(f"{len(erros)} execuções com erro de infraestrutura (registradas no log)")

    linhas = []
    for e in execs:
        r, j, v = e["resultado"], e["julgamento"], e["resultado"]["validacao"]
        linhas.append({
            "prompt": f"{e['prompt']}@{r['prompt_versao']}", "condicao_contexto": e["condicao"],
            "repeticao": e["repeticao"], "modelo": r["model_version"], "temperatura": 0,
            "pergunta": PERGUNTA,
            "chunks_recuperados": ",".join(c["chunk_id"] for c in r["chunks"]) or "-",
            "resposta": resumo_texto(r, 500),
            "citacoes": " | ".join(f"{a['doc_id']}: \"{a['trecho'][:60]}…\"" for a in v["afirmacoes"]) or "-",
            "formato_json_valido": v["json_valido"], "formato_schema_valido": v["schema_valido"],
            "afirmacoes_fonte_valida": f"{v['afirmacoes_fonte_valida']}/{v['total_afirmacoes']}",
            "indicou_incerteza": j["indicou_incerteza"], "sinalizou_revogacao": j["sinalizou_revogacao"],
            "latencia_llm_s": r["latencia_llm_s"], "tentativas": r["tentativas"], "tokens_in_out": f"{r['uso']['input']}/{r['uso']['output']}",
            "resultado_correto": j["resultado_correto"], "citacao_verificavel": j["citacao_verificavel"],
            "trace": r["trace_url"],
        })
    linhas.sort(key=lambda l: (l["prompt"], CONDICOES.index(l["condicao_contexto"]), l["repeticao"]))
    salvar_csv("prompt_lab.csv", linhas)

    agg = defaultdict(lambda: defaultdict(list))
    for e in execs:
        a = agg[e["prompt"]]
        a["correto"].append(e["julgamento"]["resultado_correto"])
        a["citacao"].append(e["julgamento"]["citacao_verificavel"])
        a["schema"].append(e["resultado"]["validacao"]["schema_valido"])
        a["lat"].append(e["resultado"]["latencia_llm_s"])
        a["tok"].append(e["resultado"]["uso"]["input"] + e["resultado"]["uso"]["output"])
    consistencia = {}
    for p in PROMPTS:
        pares = defaultdict(list)
        for e in execs:
            if e["prompt"] == p:
                pares[e["condicao"]].append((e["julgamento"]["resultado_correto"],
                                             e["resultado"]["validacao"]["schema_valido"]))
        consistencia[p] = sum(len(set(v)) == 1 for v in pares.values()) / len(pares)
    resumo = {"timestamp": ts, "execucoes_com_erro": len(erros), "sessao_langfuse": sessao, "log": log, "pergunta": PERGUNTA, "prompts": {
        p: {"execucoes": len(agg[p]["correto"]),
            "taxa_resultado_correto": round(sum(agg[p]["correto"]) / len(agg[p]["correto"]), 3),
            "taxa_citacao_verificavel": round(sum(agg[p]["citacao"]) / len(agg[p]["citacao"]), 3),
            "taxa_schema_valido": round(sum(agg[p]["schema"]) / len(agg[p]["schema"]), 3),
            "consistencia_entre_repeticoes": round(consistencia[p], 3),
            "latencia_media_llm_s": round(sum(agg[p]["lat"]) / len(agg[p]["lat"]), 2),
            "tokens_medios": round(sum(agg[p]["tok"]) / len(agg[p]["tok"]))}
        for p in PROMPTS}}
    (RESULTS_DIR / "prompt_lab_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    for l in linhas:
        print(f"{l['prompt']:<9} {l['condicao_contexto']:<12} r{l['repeticao']} correto={l['resultado_correto']!s:<5} "
              f"schema={l['formato_schema_valido']!s:<5} {l['resposta'][:90]}")
    print(json.dumps(resumo["prompts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
