"""Publica os prompts versionados (prompts/*.txt) no Langfuse Prompt Management como chat prompts.

As gerações passam a ficar vinculadas à versão do prompt no painel do Langfuse.
Uso:  python -m scripts.sync_prompts
"""
from langfuse import get_client

from app import prompts


def main():
    lf = get_client()
    for pid in prompts.ARQUIVOS:
        p = prompts.carregar(pid)
        msgs = ([{"role": "system", "content": p.system}] if p.system else []) + [
            {"role": "user", "content": p.user.replace("{contexto}", "{{contexto}}").replace("{pergunta}", "{{pergunta}}")}]
        try:
            atual = lf.get_prompt(p.nome_langfuse, label="production", type="chat", max_retries=0)
            if atual.config.get("versao_repo") == p.versao and atual.prompt == msgs:
                print(f"{p.nome_langfuse}: já sincronizado (v{atual.version}, repo {p.versao})")
                continue
        except Exception:
            pass
        novo = lf.create_prompt(name=p.nome_langfuse, prompt=msgs, type="chat", labels=["production"],
                                tags=["av2", p.id], config={"versao_repo": p.versao, "nome": p.nome},
                                commit_message=f"{p.id} {p.versao} sincronizado do repositório")
        print(f"{p.nome_langfuse}: publicado v{novo.version} (repo {p.versao})")
    lf.flush()


if __name__ == "__main__":
    main()
