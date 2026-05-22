import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
AGENT = ROOT / "agents" / "ai-support-operations-agent"

sys.path.insert(0, str(RUNTIME))

from contratos import carregar_contratos  # noqa: E402
from ferramentas import _classificar_contexto  # noqa: E402
from ferramentas import _executar_suporte_local  # noqa: E402
from adapters.audit_adapter import criar_funcao_audit  # noqa: E402
from adapters.db_adapter import (  # noqa: E402
    _executar_query_real,
    _substituir_parametros,
    _validar_read_only,
    criar_funcao_database,
)
from adapters.rag_adapter import criar_funcao_rag  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_agent_contracts_load(self):
        contratos = carregar_contratos(AGENT)

        self.assertEqual(contratos["agente"]["nome"], "ai-support-operations-agent")
        self.assertIn("classificar_ticket", contratos["regras"]["ferramentas_obrigatorias"])
        self.assertGreaterEqual(len(contratos["habilidades"]["habilidades"]), 10)

    def test_sales_order_classification_is_mapped(self):
        resultado = _classificar_contexto({"descricao": "SUP-1043: erro ao gerar novo pedido de venda"})

        self.assertEqual(resultado["categoria"], "sales_order")
        self.assertEqual(resultado["subcategoria"], "order_creation_failure")
        self.assertEqual(resultado["fila"], "support.sales-orders")

    def test_portfolio_agent_skills_do_not_depend_on_mock_implementations(self):
        contratos = carregar_contratos(AGENT)
        habilidades = contratos["habilidades"]["habilidades"]

        tipos = {habilidade["nome"]: habilidade.get("tipo_implementacao") for habilidade in habilidades}

        self.assertNotIn("mock", tipos.values())
        self.assertEqual(tipos["buscar_tickets_similares"], "database")
        self.assertEqual(tipos["classificar_ticket"], "local")
        self.assertEqual(tipos["buscar_documentacao"], "rag")
        self.assertEqual(tipos["consultar_incidentes"], "rest")
        self.assertEqual(tipos["registrar_auditoria"], "audit")

    def test_classification_and_priority_read_from_contract_files(self):
        contratos = carregar_contratos(AGENT)
        habilidades = {h["nome"]: h for h in contratos["habilidades"]["habilidades"]}
        entrada = {"descricao": "SUP-1042: erro 500 no login em producao para todos os usuarios", "produto": "plataforma-web"}

        classificacao = _executar_suporte_local("classificar_ticket", entrada, habilidades["classificar_ticket"])
        prioridade = _executar_suporte_local(
            "calcular_prioridade",
            {**entrada, "categoria": classificacao["categoria"], "ambiente": "production", "plano_cliente": "enterprise"},
            habilidades["calcular_prioridade"],
        )

        self.assertEqual(classificacao["categoria"], "authentication")
        self.assertEqual(classificacao["subcategoria"], "login_failure")
        self.assertEqual(prioridade["prioridade"], "critica")

    def test_rag_adapter_seeds_and_queries_sqlite(self):
        with tempfile.TemporaryDirectory() as tempdir:
            habilidade = {
                "nome": "buscar_documentacao",
                "saida": {
                    "documentos_consultados": "list",
                    "trechos_relevantes": "list",
                    "encontrou_contexto": "bool",
                    "warnings": "list",
                },
                "conexao": {
                    "connection_string": str(Path(tempdir) / "rag.db"),
                    "seed_path": str(AGENT / "knowledge" / "documentation_seed.json"),
                },
                "limites": {"max_resultados": 3},
            }

            resultado = criar_funcao_rag(habilidade)(
                {"produto": "plataforma-web", "categoria": "authentication", "termos_busca": ["login", "erro 500"]}
            )

            self.assertTrue(resultado["sucesso"])
            self.assertTrue(resultado["dados"]["encontrou_contexto"])
            ids = [doc["documento_id"] for doc in resultado["dados"]["documentos_consultados"]]
            self.assertIn("KB-102", ids)

    def test_audit_adapter_persists_sqlite_rows(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "audit.db"
            habilidade = {"nome": "registrar_auditoria", "conexao": {"connection_string": str(db_path)}}
            resultado = criar_funcao_audit(habilidade)(
                {
                    "ticket_id": "SUP-1042",
                    "prioridade_final": "critica",
                    "confidence_score": 0.9,
                    "necessidade_aprovacao": True,
                    "decisao_final": "human_intervention_required",
                }
            )

            self.assertTrue(resultado["sucesso"])
            conn = sqlite3.connect(db_path)
            total = conn.execute("SELECT COUNT(*) FROM auditorias_suporte WHERE ticket_id = 'SUP-1042'").fetchone()[0]
            eventos = conn.execute("SELECT COUNT(*) FROM auditoria_eventos").fetchone()[0]
            conn.close()

            self.assertEqual(total, 1)
            self.assertGreaterEqual(eventos, 5)


class SqlSecurityTests(unittest.TestCase):
    def test_read_only_rejects_dangerous_templates(self):
        queries_invalidas = [
            "DROP TABLE tickets_historicos",
            "SELECT * FROM tickets_historicos; DROP TABLE tickets_historicos",
            "SELECT * FROM tickets_historicos -- comentario",
            "PRAGMA table_info(tickets_historicos)",
            "UPDATE tickets_historicos SET categoria = 'x'",
        ]

        for query in queries_invalidas:
            with self.subTest(query=query):
                self.assertTrue(_validar_read_only(query))

    def test_named_parameter_substitution_does_not_corrupt_similar_names(self):
        query, valores = _substituir_parametros(
            "SELECT * FROM tickets WHERE id = :id AND id2 = :id2",
            {"id": "A", "id2": "B"},
        )

        self.assertEqual(query, "SELECT * FROM tickets WHERE id = $1 AND id2 = $2")
        self.assertEqual(valores, ["A", "B"])

    def test_sqlite_parameters_prevent_injection(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "support.db"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE tickets (id TEXT PRIMARY KEY, categoria TEXT)")
            conn.execute("INSERT INTO tickets (id, categoria) VALUES (?, ?)", ("SUP-1", "authentication"))
            conn.commit()
            conn.close()

            query, valores = _substituir_parametros(
                "SELECT id, categoria FROM tickets WHERE id = :id",
                {"id": "SUP-1' OR 1=1; DROP TABLE tickets; --"},
            )
            resultados = _executar_query_real(str(db_path), "sqlite", query, valores, 5, 10)

            self.assertEqual(resultados, [])
            conn = sqlite3.connect(db_path)
            tabela_existe = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tickets'"
            ).fetchone()
            conn.close()
            self.assertIsNotNone(tabela_existe)

    def test_database_adapter_rejects_non_read_only_query(self):
        habilidade = {
            "nome": "teste",
            "tipo_implementacao": "database",
            "saida": {"itens": "list"},
            "conexao": {
                "tipo_banco": "sqlite",
                "query_template": "SELECT * FROM tickets; DROP TABLE tickets",
                "modo": "read_only",
                "timeout_segundos": 5,
            },
            "limites": {"max_resultados": 10},
        }

        funcao = criar_funcao_database(habilidade)
        resultado = funcao({})

        self.assertFalse(resultado["sucesso"])
        self.assertIn("read_only", resultado["erro"])


if __name__ == "__main__":
    unittest.main()
