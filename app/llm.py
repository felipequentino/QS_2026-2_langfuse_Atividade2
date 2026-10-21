"""Cliente LLM real (Groq ou Gemini), instrumentado como 'generation' no Langfuse (modelo, parâmetros, tokens, latência).

Provedor escolhido por LLM_PROVIDER no .env. Padrão: Groq (openai/gpt-oss-120b), cuja cota gratuita comporta
a bateria completa. O Gemini free tier limita a 20 requisições/dia por modelo.
"""
import copy
import threading
import time

from langfuse import get_client

from app.config import GEMINI_API_KEY, GROQ_API_KEY, MODEL, PROVIDER, TEMPERATURE
from app.schema import RespostaRAG

_client = None
_lock = threading.Lock()
ERROS_TRANSITORIOS = (429, 500, 502, 503, 504, "rede")


def client():
    """Cliente único compartilhado entre threads (criar dois faria o descartado fechar o httpx em uso)."""
    global _client
    with _lock:
        if _client is None:
            if PROVIDER == "groq":
                from groq import Groq
                if not GROQ_API_KEY:
                    raise RuntimeError("GROQ_API_KEY ausente no .env")
                _client = Groq(api_key=GROQ_API_KEY, max_retries=0)
            else:
                from google import genai
                if not GEMINI_API_KEY:
                    raise RuntimeError("GEMINI_API_KEY ausente no .env")
                _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def schema_estrito() -> dict:
    """JSON Schema do RespostaRAG no formato exigido pelo modo strict (todos os campos em required)."""
    s = copy.deepcopy(RespostaRAG.model_json_schema())

    def ajustar(no):
        if isinstance(no, dict):
            if no.get("type") == "object" and "properties" in no:
                no["required"] = list(no["properties"])
                no["additionalProperties"] = False
            for k in ("default", "title"):
                if k in no and not isinstance(no[k], dict):
                    no.pop(k)
            for v in no.values():
                ajustar(v)
        elif isinstance(no, list):
            for v in no:
                ajustar(v)
    ajustar(s)
    return s


def _chamar_groq(system, user, json_mode):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    kw = {}
    if json_mode:
        kw["response_format"] = {"type": "json_schema",
                                 "json_schema": {"name": "RespostaRAG", "schema": schema_estrito(), "strict": True}}
    r = client().chat.completions.create(model=MODEL, messages=msgs, temperature=TEMPERATURE, **kw)
    uso = {"input": r.usage.prompt_tokens, "output": r.usage.completion_tokens}
    det = getattr(r.usage, "completion_tokens_details", None)
    if det is not None and getattr(det, "reasoning_tokens", None):
        uso["reasoning"] = det.reasoning_tokens
    return r.choices[0].message.content or "", r.model, uso


def _chamar_gemini(system, user, json_mode):
    from google.genai import types
    cfg = types.GenerateContentConfig(temperature=TEMPERATURE, system_instruction=system)
    if json_mode:
        cfg.response_mime_type = "application/json"
        cfg.response_json_schema = RespostaRAG.model_json_schema()
    r = client().models.generate_content(model=MODEL, contents=user, config=cfg)
    um = r.usage_metadata
    uso = {"input": um.prompt_token_count or 0, "output": um.candidates_token_count or 0}
    if getattr(um, "thoughts_token_count", None):
        uso["reasoning"] = um.thoughts_token_count
    return r.text or "", r.model_version, uso


def _codigo_erro(e: Exception):
    for attr in ("status_code", "code"):
        v = getattr(e, attr, None)
        if isinstance(v, int):
            return v
    nome = type(e).__name__
    return "rede" if ("Connection" in nome or "Timeout" in nome or "Transport" in nome) else None


def _espera_sugerida(e: Exception, padrao: float) -> float:
    resp = getattr(e, "response", None)
    try:
        return min(float(resp.headers.get("retry-after")), 90)
    except (AttributeError, TypeError, ValueError):
        return padrao


def gerar(system: str | None, user: str, json_mode: bool = False, prompt_client=None,
          nome: str = "llm-generate", tentativas: int = 8) -> dict:
    lf = get_client()
    params = {"temperature": TEMPERATURE, "json_mode": json_mode, "provider": PROVIDER}
    chamar = _chamar_groq if PROVIDER == "groq" else _chamar_gemini
    entrada = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    with lf.start_as_current_observation(name=nome, as_type="generation", model=MODEL, input=entrada,
                                         model_parameters=params, prompt=prompt_client) as gen:
        espera = 5
        for i in range(1, tentativas + 1):
            inicio = time.perf_counter()
            try:
                texto, versao, uso = chamar(system, user, json_mode)
                break
            except Exception as e:
                codigo = _codigo_erro(e)
                if i == tentativas or codigo not in ERROS_TRANSITORIOS:
                    gen.update(level="ERROR", status_message=str(e)[:500])
                    raise
                time.sleep(_espera_sugerida(e, espera))
                espera = min(espera * 2, 60)
        latencia = time.perf_counter() - inicio
        gen.update(output=texto, usage_details=uso, metadata={"model_version": versao, "provider": PROVIDER,
                                                               "tentativas": i, "latencia_s": round(latencia, 3)})
    return {"texto": texto, "model_version": versao, "uso": uso, "latencia_s": round(latencia, 3), "tentativas": i}
