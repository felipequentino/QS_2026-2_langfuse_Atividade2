"""Parte E — executa os casos de tests/casos.yaml nas variantes baseline e hardened com chamadas reais ao Gemini.

Uso:  python -m scripts.run_tests [--variantes baseline hardened] [--casos CT-FUN-01 ...]
Saídas: resultados/casos_teste.csv, resultados/run_tests_resumo.json, resultados/logs/run_tests_<ts>.jsonl
Cada execução vira um trace no Langfuse com scores caso_passou, schema_valido e injecao_resistida.
"""
import argparse
import json
from pathlib import Path

import yaml
from langfuse import get_client

from app.avaliacao import avaliar, injecao_bem_sucedida
from app.config import ROOT, RESULTS_DIR
from app.pipeline import VARIANTES, responder
from scripts.comum import carimbo, paralelo, resumo_texto, salvar_csv, salvar_jsonl


def carregar_casos() -> list[dict]:
    return yaml.safe_load((ROOT / "tests" / "casos.yaml").read_text(encoding="utf-8"))


def expandir(caso: dict) -> list[dict]:
    base = {"pergunta": caso.get("pergunta"), "modo_contexto": caso.get("modo_contexto", "auto")}
    return [{**base, **v} for v in caso.get("variantes", [{}])]


def executar(tarefa: tuple) -> dict:
    caso, variante, entrada, idx, sessao = tarefa
    cfg = VARIANTES[variante]
    rotulo = f"{caso['id']}{'.' + str(idx + 1) if 'variantes' in caso else ''} [{variante}]"
    try:
        r = responder(entrada["pergunta"], cfg["prompt"], entrada["modo_contexto"], cfg["guard"], cfg["json_mode"],
                      rotulo=rotulo, sessao=sessao, tags=["av2", "run_tests", variante, caso["categoria"], caso["id"]],
                      somente_oficiais=cfg.get("somente_oficiais", False),
                      reescrever_consulta=cfg.get("reescrever_consulta", False))
    except Exception as e:  # registra falha de infraestrutura como evidência, sem abortar a bateria
        return {"caso_id": caso["id"], "variante": variante, "idx": idx, "erro": repr(e), "entrada": entrada}
    passou, falhas = avaliar(caso, r)
    lf = get_client()
    lf.create_score(trace_id=r["trace_id"], name="caso_passou", value=1 if passou else 0, data_type="BOOLEAN",
                    comment="; ".join(falhas) or "ok")
    lf.create_score(trace_id=r["trace_id"], name="schema_valido", value=1 if r["validacao"]["schema_valido"] else 0,
                    data_type="BOOLEAN")
    if caso.get("ataque"):
        lf.create_score(trace_id=r["trace_id"], name="injecao_resistida",
                        value=0 if injecao_bem_sucedida(caso, r) else 1, data_type="BOOLEAN")
    return {"caso_id": caso["id"], "variante": variante, "idx": idx, "passou": passou, "falhas": falhas,
            "injecao_ok": injecao_bem_sucedida(caso, r) if caso.get("ataque") else None, "resultado": r}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variantes", nargs="+", default=list(VARIANTES))
    ap.add_argument("--casos", nargs="*")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--anexar", help="log jsonl anterior: reexecuta só as tarefas pedidas e mescla o resto")
    ap.add_argument("--so-erros", action="store_true", help="com --anexar: reexecuta apenas execuções com erro")
    args = ap.parse_args()

    ts = carimbo()
    sessao = f"run_tests-{ts}"
    todos = carregar_casos()
    casos = [c for c in todos if not args.casos or c["id"] in args.casos]
    anteriores = []
    if args.anexar:
        with open(ROOT / args.anexar, encoding="utf-8") as f:
            anteriores = [json.loads(l) for l in f if l.strip()]
    chave = lambda e: (e["caso_id"], e["variante"], e["idx"])
    tarefas = [(c, v, e, i, sessao) for v in args.variantes for c in casos for i, e in enumerate(expandir(c))]
    if args.so_erros:
        com_erro = {chave(e) for e in anteriores if "erro" in e}
        tarefas = [t for t in tarefas if (t[0]["id"], t[1], t[3]) in com_erro]
    print(f"{len(tarefas)} execuções reais ao LLM nesta rodada")
    novas = paralelo(executar, tarefas, args.workers)
    get_client().flush()
    refeitas = {chave(e) for e in novas}
    execucoes = [e for e in anteriores if chave(e) not in refeitas] + novas

    log = salvar_jsonl(f"run_tests_{ts}.jsonl", execucoes)
    linhas, resumo = [], {"timestamp": ts, "sessao_langfuse": sessao, "log": log, "mesclado_de": args.anexar,
                          "variantes": {}}
    variantes = [v for v in VARIANTES if any(e["variante"] == v for e in execucoes)]
    for v in variantes:
        for c in todos:
            if not any(e["caso_id"] == c["id"] and e["variante"] == v for e in execucoes):
                continue
            ex = [e for e in execucoes if e["caso_id"] == c["id"] and e["variante"] == v]
            erros = [e for e in ex if "erro" in e]
            ok = [e for e in ex if "erro" not in e]
            passou = not erros and all(e["passou"] for e in ok)
            rs = [e["resultado"] for e in ok]
            cfg = VARIANTES[v]
            falhas = [f"[{e['idx'] + 1}] {f}" if len(ex) > 1 else f for e in ok for f in e["falhas"]]
            falhas += [f"erro de execução: {e['erro'][:150]}" for e in erros]
            linhas.append({
                "id": c["id"], "categoria": c["categoria"], "requisito": c["requisito"], "variante": v,
                "prompt": f"{cfg['prompt']}@{rs[0]['prompt_versao']}" if rs else cfg["prompt"],
                "controles": ("quarentena+delimitação+JSON nativo+validação+saneamento" if cfg["guard"] else "nenhum")
                             + ("+índice só oficial+reescrita de consulta" if cfg.get("somente_oficiais") else ""),
                "descricao": c["descricao"],
                "entrada": " || ".join(f"{x['pergunta']} [ctx={x['modo_contexto']}]" for x in expandir(c)),
                "contexto_recuperado": " || ".join(",".join(ch["chunk_id"] for ch in r["chunks"]) or "-" for r in rs),
                "chunks_em_quarentena": " || ".join(",".join(q["chunk_id"] for q in r["chunks_quarentena"]) or "-" for r in rs),
                "resultado_esperado": c["esperado"],
                "resultado_observado": " || ".join(resumo_texto(r, 300) for r in rs),
                "json_valido": " || ".join(str(r["validacao"]["json_valido"]) for r in rs),
                "schema_valido": " || ".join(str(r["validacao"]["schema_valido"]) for r in rs),
                "afirmacoes_fonte_valida": " || ".join(
                    f"{r['validacao']['afirmacoes_fonte_valida']}/{r['validacao']['total_afirmacoes']}" for r in rs),
                "injecao_bem_sucedida": "" if not c.get("ataque") else str(any(e["injecao_ok"] for e in ok)),
                "modelo": rs[0]["model_version"] if rs else "",
                "latencia_s": " || ".join(str(r["latencia_total_s"]) for r in rs),
                "tokens_in_out": " || ".join(f"{r['uso']['input']}/{r['uso']['output']}" for r in rs),
                "evidencia_trace": " || ".join(r["trace_url"] for r in rs),
                "evidencia_log": log,
                "status": "PASSOU" if passou else "FALHOU",
                "motivo_falha": "; ".join(falhas),
            })
        lv = [l for l in linhas if l["variante"] == v]
        ataques = [l for l in lv if l["injecao_bem_sucedida"] != ""]
        resumo["variantes"][v] = {
            "casos": len(lv), "passou": sum(l["status"] == "PASSOU" for l in lv),
            "ataques": len(ataques), "ataques_bem_sucedidos": sum(l["injecao_bem_sucedida"] == "True" for l in ataques),
            "por_categoria": {cat: f"{sum(l['status'] == 'PASSOU' for l in lv if l['categoria'] == cat)}/"
                                   f"{sum(l['categoria'] == cat for l in lv)}"
                              for cat in dict.fromkeys(l["categoria"] for l in lv)},
        }
    csv_path = salvar_csv("casos_teste.csv", linhas)
    salvar_csv(f"logs/casos_teste_{ts}.csv", linhas)
    (RESULTS_DIR / "run_tests_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    for l in linhas:
        print(f"{l['id']:<10} {l['variante']:<9} {l['status']:<7} {l['motivo_falha'][:110]}")
    print(json.dumps(resumo["variantes"], ensure_ascii=False, indent=2))
    print("CSV:", csv_path, "| log:", log)


if __name__ == "__main__":
    main()
