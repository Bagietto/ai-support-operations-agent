"""
Audit Adapter.

Persiste auditoria operacional em SQLite em modo append-only.
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass


load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

_TOKENS_ZERO = {"prompt": 0, "completion": 0, "total": 0}


def _db_path(conexao: dict) -> Path:
    conn = conexao.get("connection_string") or os.environ.get("DB_CONNECTION_STRING") or "../dados/suporte.db"
    caminho = Path(conn)
    if caminho.is_absolute():
        return caminho
    return (Path(__file__).resolve().parent.parent / caminho).resolve()


def _inicializar(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auditorias_suporte (
          auditoria_id TEXT PRIMARY KEY,
          ticket_id TEXT NOT NULL,
          prioridade_final TEXT,
          confidence_score REAL,
          necessidade_aprovacao INTEGER,
          decisao_final TEXT,
          payload_json TEXT NOT NULL,
          criado_em TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auditoria_eventos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          auditoria_id TEXT NOT NULL,
          evento TEXT NOT NULL,
          criado_em TEXT NOT NULL,
          FOREIGN KEY (auditoria_id) REFERENCES auditorias_suporte(auditoria_id)
        )
        """
    )
    conn.commit()


def criar_funcao_audit(habilidade: dict):
    conexao = habilidade.get("conexao", {})

    def funcao(argumentos):
        inicio = time.time()
        args = argumentos or {}
        ticket_id = str(args.get("ticket_id") or "SUP-0000")
        criado_em = datetime.now(timezone.utc).isoformat()
        auditoria_id = f"AUD-{ticket_id}-{int(time.time())}"
        eventos = [
            "classificacao",
            "prioridade",
            "consulta_rag",
            "roteamento",
            "veredito",
        ]
        db_path = _db_path(conexao)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        try:
            _inicializar(conn)
            conn.execute(
                """
                INSERT INTO auditorias_suporte
                (auditoria_id, ticket_id, prioridade_final, confidence_score,
                 necessidade_aprovacao, decisao_final, payload_json, criado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    auditoria_id,
                    ticket_id,
                    args.get("prioridade_final"),
                    float(args.get("confidence_score") or 0),
                    1 if args.get("necessidade_aprovacao") else 0,
                    args.get("decisao_final"),
                    json.dumps(args, ensure_ascii=False),
                    criado_em,
                ),
            )
            for evento in eventos:
                conn.execute(
                    "INSERT INTO auditoria_eventos (auditoria_id, evento, criado_em) VALUES (?, ?, ?)",
                    (auditoria_id, evento, criado_em),
                )
            conn.commit()
        finally:
            conn.close()

        dados = {
            "auditoria_id": auditoria_id,
            "status": "persistido",
            "eventos_registrados": eventos,
            "horario_registro": criado_em,
            "_entrada": args,
        }
        return {
            "sucesso": True,
            "dados": dados,
            "_adapter": "audit_sqlite",
            "_db_path": str(db_path),
            "_latencia_ms": round((time.time() - inicio) * 1000, 1),
            "_tokens": _TOKENS_ZERO.copy(),
        }

    return funcao
