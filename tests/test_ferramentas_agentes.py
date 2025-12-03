"""
Testes para as ferramentas dos agentes (tools/ferramentas_agentes.py).
Cobre: Todas as ferramentas de sessão usadas pelos agentes.
"""
import pytest
from tools.ferramentas_agentes import (
    get_session_state,
    limpar_estado_sessao,
    obter_cpf_autenticado,
    criar_ferramenta_registrar_cpf,
    criar_ferramenta_registrar_data_nascimento,
    criar_ferramenta_autenticacao,
    criar_ferramenta_verificar_auth,
    criar_ferramenta_consultar_limite,
    criar_ferramenta_solicitar_limite,
    criar_ferramenta_entrevista_credito,
    session_states,
)


@pytest.fixture
def session_id():
    """Fixture que retorna um ID de sessão único e limpa após uso."""
    sid = "test-session-ferramentas"
    yield sid
    # Cleanup
    if sid in session_states:
        del session_states[sid]


class TestSessionState:
    """Testes para gerenciamento de estado de sessão."""
    
    def test_get_session_state_nova_sessao(self, session_id):
        state = get_session_state(session_id)
        
        assert state["autenticado"] is False
        assert state["bloqueado"] is False
        assert state["cpf"] is None
        assert state["nome"] is None
        assert state["cpf_pendente"] is None
        assert state["data_nascimento_pendente"] is None
    
    def test_get_session_state_persistencia(self, session_id):
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["nome"] = "Teste"
        
        # Deve retornar o mesmo estado
        state2 = get_session_state(session_id)
        assert state2["autenticado"] is True
        assert state2["nome"] == "Teste"
    
    def test_limpar_estado_sessao(self, session_id):
        state = get_session_state(session_id)
        state["autenticado"] = True
        
        limpar_estado_sessao(session_id)
        
        # Nova sessão deve ter valores padrão
        state2 = get_session_state(session_id)
        assert state2["autenticado"] is False


class TestRegistrarCpf:
    """Testes para a ferramenta registrar_cpf."""
    
    def test_registrar_cpf_sucesso(self, session_id, csv_environment):
        registrar_cpf = criar_ferramenta_registrar_cpf(session_id)
        
        resultado = registrar_cpf("12345678901")
        
        assert "CPF" in resultado or "REGISTRADO" in resultado
        state = get_session_state(session_id)
        assert state["cpf_pendente"] == "12345678901"
    
    def test_registrar_cpf_com_formatacao(self, session_id, csv_environment):
        registrar_cpf = criar_ferramenta_registrar_cpf(session_id)
        
        resultado = registrar_cpf("123.456.789-01")
        
        state = get_session_state(session_id)
        assert state["cpf_pendente"] == "12345678901"
    
    def test_registrar_cpf_ja_autenticado(self, session_id, csv_environment):
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["nome"] = "Cliente Teste"
        
        registrar_cpf = criar_ferramenta_registrar_cpf(session_id)
        resultado = registrar_cpf("12345678901")
        
        assert "JA_AUTENTICADO" in resultado
    
    def test_registrar_cpf_sessao_bloqueada(self, session_id, csv_environment):
        state = get_session_state(session_id)
        state["bloqueado"] = True
        
        registrar_cpf = criar_ferramenta_registrar_cpf(session_id)
        resultado = registrar_cpf("12345678901")
        
        assert "BLOQUEADO" in resultado


class TestRegistrarDataNascimento:
    """Testes para a ferramenta registrar_data_nascimento."""
    
    def test_registrar_data_sem_cpf(self, session_id, csv_environment):
        registrar_data = criar_ferramenta_registrar_data_nascimento(session_id)
        
        resultado = registrar_data("13/02/1995")
        
        state = get_session_state(session_id)
        assert state["data_nascimento_pendente"] is not None
    
    def test_registrar_data_com_cpf_pendente_autentica(self, session_id, csv_environment):
        # Primeiro registra CPF
        state = get_session_state(session_id)
        state["cpf_pendente"] = "12345678901"
        
        registrar_data = criar_ferramenta_registrar_data_nascimento(session_id)
        resultado = registrar_data("13/02/1995")
        
        # Deve autenticar automaticamente
        state = get_session_state(session_id)
        assert state["autenticado"] is True
        assert "SUCESSO" in resultado


class TestAutenticacao:
    """Testes para a ferramenta autenticar_cliente."""
    
    def test_autenticar_sucesso(self, session_id, csv_environment):
        autenticar = criar_ferramenta_autenticacao(session_id)
        
        resultado = autenticar("12345678901", "13/02/1995")
        
        state = get_session_state(session_id)
        assert state["autenticado"] is True
        assert "SUCESSO" in resultado
    
    def test_autenticar_dados_invalidos(self, session_id, csv_environment):
        autenticar = criar_ferramenta_autenticacao(session_id)
        
        resultado = autenticar("00000000000", "01/01/2000")
        
        state = get_session_state(session_id)
        assert state["autenticado"] is False
        assert "INVALIDOS" in resultado or "DADOS" in resultado
    
    def test_autenticar_bloqueia_apos_3_tentativas(self, session_id, csv_environment):
        autenticar = criar_ferramenta_autenticacao(session_id)
        
        # 3 tentativas falhas
        for _ in range(3):
            autenticar("00000000000", "01/01/2000")
        
        state = get_session_state(session_id)
        assert state["bloqueado"] is True
        
        # Próxima tentativa deve retornar bloqueado
        resultado = autenticar("12345678901", "13/02/1995")
        assert "BLOQUEADO" in resultado


class TestVerificarAuth:
    """Testes para a ferramenta verificar_autenticacao."""
    
    def test_verificar_nao_autenticado(self, session_id, csv_environment):
        verificar = criar_ferramenta_verificar_auth(session_id)
        
        resultado = verificar()
        
        assert "NAO_AUTENTICADO" in resultado
    
    def test_verificar_autenticado(self, session_id, csv_environment):
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["nome"] = "Cliente Teste"
        state["cpf"] = "12345678901"
        state["score_credito"] = 700
        
        verificar = criar_ferramenta_verificar_auth(session_id)
        resultado = verificar()
        
        assert "AUTENTICADO" in resultado
        assert "Cliente Teste" in resultado


class TestConsultarLimite:
    """Testes para a ferramenta consultar_limite_credito."""
    
    def test_consultar_limite_nao_autenticado(self, session_id, csv_environment):
        consultar = criar_ferramenta_consultar_limite(session_id)
        
        resultado = consultar()
        
        assert "NAO_AUTENTICADO" in resultado
    
    def test_consultar_limite_autenticado(self, session_id, csv_environment):
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["cpf"] = "12345678901"
        
        consultar = criar_ferramenta_consultar_limite(session_id)
        resultado = consultar()
        
        assert "SUCESSO" in resultado
        assert "R$" in resultado


class TestSolicitarLimite:
    """Testes para a ferramenta solicitar_aumento_limite."""
    
    def test_solicitar_nao_autenticado(self, session_id, csv_environment):
        solicitar = criar_ferramenta_solicitar_limite(session_id)
        
        resultado = solicitar(15000)
        
        assert "NAO_AUTENTICADO" in resultado
    
    def test_solicitar_aprovado(self, session_id, csv_environment):
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["cpf"] = "12345678901"
        
        solicitar = criar_ferramenta_solicitar_limite(session_id)
        resultado = solicitar(15000)  # Cliente tem score 700, limite até 20000
        
        assert "APROVADO" in resultado
    
    def test_solicitar_negado(self, session_id, csv_environment):
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["cpf"] = "12345678901"
        
        solicitar = criar_ferramenta_solicitar_limite(session_id)
        resultado = solicitar(50000)  # Acima do limite permitido
        
        assert "NEGADO" in resultado


class TestEntrevistaCredito:
    """Testes para a ferramenta atualizar_score_apos_entrevista."""
    
    def test_entrevista_nao_autenticado(self, session_id, csv_environment):
        entrevista = criar_ferramenta_entrevista_credito(session_id)
        
        resultado = entrevista(
            renda_mensal=5000,
            tipo_emprego="formal",
            despesas_mensais=2000,
            numero_dependentes=1,
            possui_dividas="nao"
        )
        
        assert "NAO_AUTENTICADO" in resultado
    
    def test_entrevista_sucesso(self, session_id, csv_environment):
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["cpf"] = "12345678901"
        
        entrevista = criar_ferramenta_entrevista_credito(session_id)
        resultado = entrevista(
            renda_mensal=6000,
            tipo_emprego="formal",
            despesas_mensais=2000,
            numero_dependentes=1,
            possui_dividas="nao"
        )
        
        assert "SUCESSO" in resultado
        assert state["score_credito"] is not None
    
    def test_entrevista_emprego_invalido(self, session_id, csv_environment):
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["cpf"] = "12345678901"
        
        entrevista = criar_ferramenta_entrevista_credito(session_id)
        resultado = entrevista(
            renda_mensal=5000,
            tipo_emprego="invalido",
            despesas_mensais=2000,
            numero_dependentes=1,
            possui_dividas="nao"
        )
        
        assert "ERRO" in resultado


class TestObterCpfAutenticado:
    """Testes para a função obter_cpf_autenticado (usada na memória do Agno)."""
    
    def test_obter_cpf_nao_autenticado(self, session_id):
        """Deve retornar None quando não autenticado."""
        limpar_estado_sessao(session_id)
        get_session_state(session_id)  # Inicializa sessão
        
        cpf = obter_cpf_autenticado(session_id)
        
        assert cpf is None
    
    def test_obter_cpf_autenticado_sucesso(self, session_id):
        """Deve retornar CPF quando autenticado."""
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["cpf"] = "12345678901"
        state["nome"] = "Cliente Teste"
        
        cpf = obter_cpf_autenticado(session_id)
        
        assert cpf == "12345678901"
    
    def test_obter_cpf_autenticado_sem_cpf(self, session_id):
        """Deve retornar None se autenticado mas sem CPF (caso edge)."""
        state = get_session_state(session_id)
        state["autenticado"] = True
        state["cpf"] = None
        
        cpf = obter_cpf_autenticado(session_id)
        
        assert cpf is None
    
    def test_obter_cpf_sessao_inexistente(self):
        """Deve retornar None para sessão que não existe."""
        cpf = obter_cpf_autenticado("sessao-inexistente-xyz")
        
        assert cpf is None
        
        # Cleanup
        if "sessao-inexistente-xyz" in session_states:
            del session_states["sessao-inexistente-xyz"]
