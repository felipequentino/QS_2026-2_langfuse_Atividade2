"""§9 — Consolida as métricas mínimas a partir dos artefatos gerados pelos demais scripts.

Uso:  python -m scripts.metricas
Saídas: resultados/metricas.json e resultados/metricas.md
"""
import json
import statistics

from app.config import RESULTS_DIR
from scripts.auditoria_citacoes import carregar


def ler(nome: str) -> dict:
    return json.loads((RESULTS_DIR / nome).read_text(encoding="utf-8"))


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"


def main():
    rt, lab, aud = ler("run_tests_resumo.json"), ler("prompt_lab_resumo.json"), ler("auditoria_resumo.json")
    execs = [e for e in carregar(str(RESULTS_DIR.parent / rt["log"])) if "resultado" in e]
    lab_execs = [e for e in carregar(str(RESULTS_DIR.parent / lab["log"])) if "erro" not in e]

    m = {"run_tests": {}, "prompt_lab": lab["prompts"], "auditoria": aud}
    for v, res in rt["variantes"].items():
        ex = [e["resultado"] for e in execs if e["variante"] == v]
        lat = [r["latencia_llm_s"] for r in ex]  # só a chamada final ao LLM (exclui esperas de rate limit)
        m["run_tests"][v] = {
            **res,
            "execucoes": len(ex),
            "chamadas_llm": sum(r.get("chamadas_llm", 1) for r in ex),
            "saidas_json_validas": sum(r["validacao"]["json_valido"] for r in ex),
            "saidas_schema_validas": sum(r["validacao"]["schema_valido"] for r in ex),
            "latencia_media_s": round(statistics.mean(lat), 2),
            "latencia_p95_s": round(sorted(lat)[max(0, int(0.95 * len(lat)) - 1)], 2),
            "tokens_entrada": sum(r["uso"]["input"] for r in ex),
            "tokens_saida": sum(r["uso"]["output"] for r in ex),
            "chunks_em_quarentena": sum(len(r["chunks_quarentena"]) for r in ex),
        }
    (RESULTS_DIR / "metricas.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

    vs = list(m["run_tests"])
    rv = m["run_tests"]
    nomes = {"baseline": "Baseline (P1, sem controles)", "hardened": "Hardened (P2 + controles)",
             "hardened_v2": "Hardened v2 (reteste: + M1 índice oficial + M2 reescrita)"}
    am, pop = aud["amostra"], aud["populacao_run_tests"]

    def linha(rotulo, f):
        return f"| {rotulo} | " + " | ".join(f(rv[v]) for v in vs) + " |"
    linhas = [
        "# Métricas consolidadas (geradas por `python -m scripts.metricas`)", "",
        f"Modelo: `{execs[0]['resultado']['model_version']}` · temperatura 0 · log `{rt['log']}`", "",
        "## Testes obrigatórios (Parte E)", "",
        "| Métrica | " + " | ".join(nomes.get(v, v) for v in vs) + " |", "|---|" + "---|" * len(vs),
        linha("Casos aprovados", lambda x: pct(x["passou"], x["casos"])),
    ]
    for cat in rv[vs[0]]["por_categoria"]:
        linhas.append(linha(f"— {cat}", lambda x, c=cat: x["por_categoria"].get(c, "n/a")))
    linhas += [
        linha("Taxa de sucesso das injeções (menor é melhor)", lambda x: pct(x["ataques_bem_sucedidos"], x["ataques"])),
        linha("Saídas JSON válidas", lambda x: pct(x["saidas_json_validas"], x["execucoes"])),
        linha("Saídas válidas no esquema", lambda x: pct(x["saidas_schema_validas"], x["execucoes"])),
        linha("Chunks postos em quarentena", lambda x: str(x["chunks_em_quarentena"])),
        linha("Execuções / chamadas ao LLM", lambda x: f"{x['execucoes']} / {x['chamadas_llm']}"),
        linha("Latência média / p95 (s)", lambda x: f"{x['latencia_media_s']} / {x['latencia_p95_s']}"),
        linha("Tokens entrada / saída", lambda x: f"{x['tokens_entrada']} / {x['tokens_saida']}"),
        "", "## Citações (Parte C)", "",
        "| Métrica | " + " | ".join(nomes.get(v, v) for v in pop) + " |", "|---|" + "---|" * len(pop),
        "| Cobertura de citações na amostra de 5 afirmações | " + " | ".join(pct(am[v]["com_fonte_valida"], am[v]["verificadas"]) if v in am else "—" for v in pop) + " |",
        "| Precisão de citações na amostra (sustentadas / com fonte) | " + " | ".join(pct(am[v]["sustentadas"], am[v]["com_fonte_valida"]) if v in am else "—" for v in pop) + " |",
        "| Cobertura na população (todas as afirmações estruturadas) | " + " | ".join(pct(pop[v]["com_fonte_valida"], pop[v]["afirmacoes"]) if pop[v]["afirmacoes"] else "n/a (texto livre, sem afirmações estruturadas)" for v in pop) + " |",
        "| Precisão na população | " + " | ".join(pct(pop[v]["sustentadas"], pop[v]["com_fonte_valida"]) for v in pop) + " |",
        "", "## Laboratório de prompts (Parte B)", "",
        f"Pergunta: _{lab['pergunta']}_ · {len(lab_execs)} execuções válidas (3 prompts × 4 contextos × 2 repetições; 1 perdida por rate limit, P2 conflitante r2)", "",
        "| Prompt | Resultado correto | Citação verificável | JSON no esquema | Consistência entre repetições | Latência média do LLM (s) | Tokens médios |",
        "|---|---|---|---|---|---|---|",
    ]
    for p, r in lab["prompts"].items():
        linhas.append(f"| {p} | {r['taxa_resultado_correto']:.0%} | {r['taxa_citacao_verificavel']:.0%} | "
                      f"{r['taxa_schema_valido']:.0%} | {r['consistencia_entre_repeticoes']:.0%} | "
                      f"{r['latencia_media_llm_s']} | {r['tokens_medios']} |")
    (RESULTS_DIR / "metricas.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
