def test_validando_cliente_sucesso(tools_module):
    resultado = tools_module.validando_cliente("123.456.789-01", "13/02/1995")
    assert resultado["status"] == "ok"
    assert resultado["nome"] == "Cliente Teste"


def test_validando_cliente_falha(tools_module):
    resultado = tools_module.validando_cliente("00011122233", "2000-01-01")
    assert resultado["status"] == "erro"


def test_consultando_limite(tools_module):
    resposta = tools_module.consultando_limite("12345678901")
    assert resposta["status"] == "ok"
    assert resposta["limite_atual"] == 10000


def test_solicitacao_limite_aprovada(tools_module, services_module):
    resposta = tools_module.solicitacao_de_limite("12345678901", 15000)
    assert resposta["status"] == "ok"
    cliente = services_module.buscar_cliente_por_cpf("12345678901")
    assert cliente["limite_credito"] == 15000


def test_solicitacao_limite_rejeitada(tools_module):
    resposta = tools_module.solicitacao_de_limite("12345678901", 40000)
    assert resposta["status"] == "erro"
    assert "excede" in resposta["mensagem"].lower()


def test_atualizar_score_cliente_sucesso(tools_module, services_module):
    resposta = tools_module.atualizar_score_cliente(
        cpf="12345678901",
        renda=6000,
        tipo_emprego="formal",
        despesas_mensais=2000,
        dependentes=1,
        tem_dividas="nao",
    )
    assert resposta["status"] == "ok"
    cliente = services_module.buscar_cliente_por_cpf("12345678901")
    assert cliente["score_credito"] == resposta["novo_score"]


def test_atualizar_score_cliente_entrada_invalida(tools_module):
    resposta = tools_module.atualizar_score_cliente(
        cpf="12345678901",
        renda="abc",
        tipo_emprego="formal",
        despesas_mensais=2000,
        dependentes=1,
        tem_dividas="nao",
    )
    assert resposta["status"] == "erro"
