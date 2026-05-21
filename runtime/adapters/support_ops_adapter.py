"""
Support Operations Adapter.

Executa as skills de dominio do agente de suporte com regras locais
deterministicas. Este adapter e usado para demonstracao e portfolio sem
credenciais externas, mas nao e um mock: ele implementa politicas de
classificacao, prioridade, roteamento, resposta e auditoria do dominio.
"""

_TOKENS_ZERO = {"prompt": 0, "completion": 0, "total": 0}


def criar_funcao_support_ops(habilidade: dict):
    """Cria funcao local para uma skill de suporte operacional."""
    nome = habilidade.get("nome", "")

    def funcao(argumentos):
        # Import tardio evita ciclo de importacao com runtime.ferramentas.
        from ferramentas import _executar_suporte_local

        dados = _executar_suporte_local(nome, argumentos or {})
        dados["_entrada"] = argumentos or {}
        return {
            "sucesso": True,
            "dados": dados,
            "_adapter": "support_ops",
            "_modo": "local",
            "_tokens": _TOKENS_ZERO.copy(),
        }

    return funcao
