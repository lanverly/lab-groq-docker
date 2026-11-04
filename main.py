"""Laboratório didático: API HTTP em Docker consumindo IA via GroqCloud."""
import os
from time import perf_counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from groq import Groq, AuthenticationError, RateLimitError, APIConnectionError, APITimeoutError, APIStatusError

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("GROQ_API_KEY ausente. Configure a variável no arquivo .env")

client = Groq(api_key=API_KEY, timeout=30.0, max_retries=0)
app = FastAPI(
    title="Laboratório Docker + GroqCloud",
    description="Uma API REST dentro do Docker consumindo inferência externa da GroqCloud.",
    version="1.0.0",
)


class Pergunta(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pergunta: str = Field(min_length=1, max_length=500, examples=["Explique containers em duas frases."])


@app.get("/")
def inicio():
    return {"servico": "API de IA em Docker", "documentacao": "/docs"}


@app.get("/health")
def health():
    # Mede apenas a saúde local da aplicação; não consulta a GroqCloud.
    return {"status": "ok", "modelo_configurado": MODEL}


@app.post("/perguntar")
def perguntar(dados: Pergunta):
    inicio = perf_counter()
    try:
        resposta = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Você é um professor de computação em nuvem. Responda de forma breve e didática, em português do Brasil."},
                {"role": "user", "content": dados.pergunta},
            ],
            max_completion_tokens=700,
        )
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Limite de requisições ou tokens da Groq atingido.")
    except AuthenticationError:
        raise HTTPException(status_code=502, detail="Falha de autenticação no provedor GroqCloud. Verifique a chave.")
    except (APITimeoutError, APIConnectionError):
        raise HTTPException(status_code=503, detail="GroqCloud indisponível ou tempo de espera excedido.")
    except APIStatusError as erro:
        raise HTTPException(status_code=502, detail=f"O provedor GroqCloud retornou HTTP {erro.status_code}.")

    uso = resposta.usage
    return {
        "modelo": resposta.model,
        "pergunta": dados.pergunta,
        "resposta": resposta.choices[0].message.content or "(sem resposta textual)",
        "tokens_total": uso.total_tokens if uso else None,
        "tempo_ms": round((perf_counter() - inicio) * 1000),
    }
