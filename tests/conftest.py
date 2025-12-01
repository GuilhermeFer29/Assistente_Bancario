import importlib
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _reload_modules():
    clientes_mod = importlib.import_module("services.clientes")
    services_pkg = importlib.import_module("services")
    tools_mod = importlib.import_module("tools.tools")
    agents_mod = importlib.import_module("agent.agents")

    clientes_mod = importlib.reload(clientes_mod)
    services_pkg = importlib.reload(services_pkg)
    tools_mod = importlib.reload(tools_mod)
    agents_mod = importlib.reload(agents_mod)

    return clientes_mod, services_pkg, tools_mod, agents_mod


@pytest.fixture
def csv_environment(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("AGNO_DATA_DIR", str(data_dir))

    clientes_mod, services_pkg, tools_mod, agents_mod = _reload_modules()

    # Popular CSVs básicos
    pd.DataFrame(
        [
            {
                "cpf": "12345678901",
                "nome": "Cliente Teste",
                "dt_nascimento": "1995-02-13",
                "score_credito": 700,
                "renda_mensal": 5000,
                "limite_credito": 10000,
            },
            {
                "cpf": "98765432100",
                "nome": "Cliente Secundário",
                "dt_nascimento": "1990-08-12",
                "score_credito": 450,
                "renda_mensal": 3000,
                "limite_credito": 3000,
            },
        ]
    ).to_csv(clientes_mod._CLIENTES_CSV, index=False)

    pd.DataFrame(
        [
            {"score_min": 0, "score_max": 499, "limite_maximo": 5000},
            {"score_min": 500, "score_max": 799, "limite_maximo": 20000},
            {"score_min": 800, "score_max": 1000, "limite_maximo": 40000},
        ]
    ).to_csv(clientes_mod._SCORES_CSV, index=False)

    pd.DataFrame(
        columns=[
            "cpf_cliente",
            "data_hora_solicitacao",
            "limite_atual",
            "novo_limite_solicitado",
            "status_pedido",
        ]
    ).to_csv(clientes_mod._SOLICITACOES_CSV, index=False)

    return {
        "data_dir": data_dir,
        "clientes_mod": clientes_mod,
        "services": services_pkg,
        "tools": tools_mod,
        "agents": agents_mod,
    }


@pytest.fixture
def tools_module(csv_environment):
    return csv_environment["tools"]


@pytest.fixture
def services_module(csv_environment):
    return csv_environment["services"]


@pytest.fixture
def agents_module(csv_environment):
    return csv_environment["agents"]


@pytest.fixture
def api_client(csv_environment):
    from fastapi.testclient import TestClient

    main_mod = importlib.import_module("main")
    main_mod = importlib.reload(main_mod)
    return TestClient(main_mod.app)
