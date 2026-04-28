"""Rotas de confirmação Step-Up 2FA: criação API + página HTML."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from assistente_bancario_v2.banking_gateway.app.core.auth_interno import (
    exigir_token_interno,
)
from assistente_bancario_v2.banking_gateway.app.core.rate_limit import limiter
from assistente_bancario_v2.banking_gateway.app.domain.schemas import (
    RequisicaoCriarConfirmacao,
    RespostaCriarConfirmacao,
)
from assistente_bancario_v2.banking_gateway.app.services.confirmacao_service import (
    buscar_confirmacao,
    criar_confirmacao,
    validar_e_executar,
)
from assistente_bancario_v2.packages.shared.utils import formatar_brl

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

roteador = APIRouter(tags=["Confirmação"])


# ── API ────────────────────────────────────────────────────────


@roteador.post(
    "/confirmacao/criar",
    response_model=RespostaCriarConfirmacao,
    dependencies=[Depends(exigir_token_interno)],
)
async def api_criar(req: RequisicaoCriarConfirmacao) -> RespostaCriarConfirmacao:
    """Cria token de confirmação Step-Up (rota interna — exige X-Internal-Token)."""
    resultado = await criar_confirmacao(
        id_cliente=req.id_cliente,
        operacao=req.operacao,
        dados_operacao=req.dados_operacao,
    )
    return RespostaCriarConfirmacao(
        token=resultado["token"], url=resultado["url"], expira_em=resultado["expira_em"]
    )


# ── Página HTML ────────────────────────────────────────────────


def _formatar_dados_operacao(operacao: str, dados: dict) -> dict:  # type: ignore[type-arg]
    """Prepara dicionário amigável para o template."""
    if operacao == "aumento_limite":
        return {
            "titulo": "Aumento de limite",
            "items": [
                ("Novo limite", formatar_brl(dados.get("novo_limite", 0))),
            ],
        }
    if operacao == "criar_transacao":
        return {
            "titulo": "Nova transação",
            "items": [
                ("Tipo", dados.get("tipo", "").replace("_", " ")),
                ("Descrição", dados.get("descricao", "")),
                ("Valor", formatar_brl(dados.get("valor", 0))),
                ("Vencimento", dados.get("data_vencimento", "")),
            ],
        }
    return {"titulo": operacao, "items": list(dados.items())}


@roteador.get("/confirmar/{token}", response_class=HTMLResponse)
async def pagina_confirmacao(token: str, request: Request) -> HTMLResponse:
    confirmacao = await buscar_confirmacao(token)
    if confirmacao is None:
        return templates.TemplateResponse(
            "erro.html",
            {"request": request, "motivo": "Token inválido ou não encontrado."},
            status_code=404,
        )
    if confirmacao["expirado"] or confirmacao["status"] == "EXPIRADA":
        return templates.TemplateResponse(
            "expirado.html", {"request": request, "token": token}, status_code=410
        )
    if confirmacao["status"] == "REJEITADA":
        return templates.TemplateResponse(
            "erro.html",
            {"request": request, "motivo": "Confirmação rejeitada por excesso de tentativas."},
            status_code=403,
        )
    if confirmacao["status"] == "CONFIRMADA":
        return templates.TemplateResponse(
            "sucesso.html",
            {"request": request, "operacao": confirmacao["operacao"], "ja_confirmado": True},
        )

    info = _formatar_dados_operacao(confirmacao["operacao"], confirmacao["dados_operacao"])
    return templates.TemplateResponse(
        "confirmacao.html",
        {
            "request": request,
            "token": token,
            "nome": confirmacao["nome"],
            "operacao_titulo": info["titulo"],
            "items": info["items"],
            "tentativas_restantes": max(0, 3 - confirmacao["tentativas_senha"]),
            "erro": None,
        },
    )


@roteador.post("/confirmar/{token}", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def submit_confirmacao(
    request: Request, token: str, senha: str = Form(...)
) -> HTMLResponse:
    confirmacao = await buscar_confirmacao(token)
    if confirmacao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    resultado = await validar_e_executar(token, senha)
    if resultado["sucesso"]:
        return templates.TemplateResponse(
            "sucesso.html",
            {
                "request": request,
                "operacao": confirmacao["operacao"],
                "resultado": resultado["resultado"],
                "ja_confirmado": False,
            },
        )

    motivo = resultado.get("motivo", "")
    if motivo == "expirado":
        return templates.TemplateResponse(
            "expirado.html", {"request": request, "token": token}, status_code=410
        )
    if motivo in {"status_rejeitada", "status_expirada", "status_confirmada"}:
        return templates.TemplateResponse(
            "erro.html",
            {"request": request, "motivo": "Esta confirmação não está mais ativa."},
            status_code=410,
        )

    # senha_incorreta
    info = _formatar_dados_operacao(confirmacao["operacao"], confirmacao["dados_operacao"])
    tentativas_restantes = resultado.get("tentativas_restantes", 0)
    if tentativas_restantes == 0:
        return templates.TemplateResponse(
            "erro.html",
            {"request": request, "motivo": "Excesso de tentativas. Solicite uma nova confirmação."},
            status_code=403,
        )

    return templates.TemplateResponse(
        "confirmacao.html",
        {
            "request": request,
            "token": token,
            "nome": confirmacao["nome"],
            "operacao_titulo": info["titulo"],
            "items": info["items"],
            "tentativas_restantes": tentativas_restantes,
            "erro": "Senha incorreta. Tente novamente.",
        },
        status_code=400,
    )
