"""
RAG Adapter.

Consulta uma base local SQLite com FTS5 para recuperar documentos, runbooks e
trechos relevantes declarados em uma skill.
"""

import json
import os
import re
import sqlite3
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass


load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

_TOKENS_ZERO = {"prompt": 0, "completion": 0, "total": 0}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolver_path(valor: str, base: Path = None) -> Path:
    caminho = Path(valor)
    if caminho.is_absolute():
        return caminho
    candidatos = []
    if base:
        candidatos.append((base / caminho).resolve())
    candidatos.append((_repo_root() / caminho).resolve())
    candidatos.append((Path(__file__).resolve().parent.parent / caminho).resolve())
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    return candidatos[0]


def _db_path(conexao: dict) -> Path:
    conn = conexao.get("connection_string") or os.environ.get("DB_CONNECTION_STRING") or "../dados/suporte.db"
    caminho = Path(conn)
    if caminho.is_absolute():
        return caminho
    return (Path(__file__).resolve().parent.parent / caminho).resolve()


def _tokenizar(texto: str) -> list:
    return [t for t in re.findall(r"[\w-]+", (texto or "").lower()) if len(t) > 2]


def _preparar_query_fts(termos: list) -> str:
    tokens = []
    for termo in termos:
        tokens.extend(_tokenizar(str(termo)))
    vistos = []
    for token in tokens:
        if token not in vistos:
            vistos.append(token)
    return " OR ".join(f'"{token.replace(chr(34), chr(34) + chr(34))}"' for token in vistos[:12])


def _inicializar_base(conn: sqlite3.Connection, seed_path: Path):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documentos_suporte (
          documento_id TEXT PRIMARY KEY,
          titulo TEXT NOT NULL,
          produto TEXT NOT NULL,
          categoria TEXT NOT NULL,
          tags TEXT NOT NULL,
          conteudo TEXT NOT NULL,
          atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS documentos_suporte_fts
        USING fts5(documento_id, titulo, produto, categoria, tags, conteudo)
        """
    )

    total = conn.execute("SELECT COUNT(*) FROM documentos_suporte").fetchone()[0]
    if total > 0 or not seed_path.exists():
        return

    documentos = json.loads(seed_path.read_text(encoding="utf-8"))
    for doc in documentos:
        tags = " ".join(doc.get("tags", []))
        conn.execute(
            """
            INSERT OR REPLACE INTO documentos_suporte
            (documento_id, titulo, produto, categoria, tags, conteudo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                doc["documento_id"],
                doc["titulo"],
                doc["produto"],
                doc["categoria"],
                tags,
                doc["conteudo"],
            ),
        )
        conn.execute(
            """
            INSERT INTO documentos_suporte_fts
            (documento_id, titulo, produto, categoria, tags, conteudo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                doc["documento_id"],
                doc["titulo"],
                doc["produto"],
                doc["categoria"],
                tags,
                doc["conteudo"],
            ),
        )
    conn.commit()


def _buscar(conn: sqlite3.Connection, argumentos: dict, max_resultados: int) -> list:
    produto = str(argumentos.get("produto") or "").lower()
    categoria = str(argumentos.get("categoria") or "").lower()
    termos = argumentos.get("termos_busca") or []
    consulta_fts = _preparar_query_fts([produto, categoria, *termos])

    if consulta_fts:
        rows = conn.execute(
            """
            SELECT documento_id, titulo, produto, categoria, conteudo, rank
            FROM documentos_suporte_fts
            WHERE documentos_suporte_fts MATCH ?
              AND (? = '' OR lower(categoria) = ?)
              AND (? = '' OR lower(produto) = ?)
            ORDER BY rank
            LIMIT ?
            """,
            (consulta_fts, categoria, categoria, produto, produto, max_resultados),
        ).fetchall()
        if rows:
            return rows

    like = f"%{' '.join(_tokenizar(' '.join(map(str, termos))))}%"
    return conn.execute(
        """
        SELECT documento_id, titulo, produto, categoria, conteudo, 0 AS rank
        FROM documentos_suporte
        WHERE (? = '' OR lower(categoria) = ?)
          AND (? = '' OR lower(produto) = ?)
          AND (? = '%%' OR lower(conteudo || ' ' || titulo || ' ' || tags) LIKE ?)
        LIMIT ?
        """,
        (categoria, categoria, produto, produto, like, like, max_resultados),
    ).fetchall()


def criar_funcao_rag(habilidade: dict):
    conexao = habilidade.get("conexao", {})
    limites = habilidade.get("limites", {})
    seed_path = _resolver_path(conexao.get("seed_path", "agents/ai-support-operations-agent/knowledge/documentation_seed.json"))
    max_resultados = int(limites.get("max_resultados", 5))

    def funcao(argumentos):
        inicio = time.time()
        db_path = _db_path(conexao)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        try:
            _inicializar_base(conn, seed_path)
            rows = _buscar(conn, argumentos or {}, max_resultados)
        finally:
            conn.close()

        documentos = []
        trechos = []
        for row in rows:
            doc_id, titulo, produto, categoria, conteudo, rank = row
            documentos.append(
                {
                    "documento_id": doc_id,
                    "titulo": titulo,
                    "produto": produto,
                    "categoria": categoria,
                    "score": round(1 / (1 + abs(float(rank or 0))), 4),
                }
            )
            trechos.append(conteudo[:360])

        encontrou = bool(documentos)
        dados = {
            "documentos_consultados": documentos,
            "trechos_relevantes": trechos,
            "encontrou_contexto": encontrou,
            "warnings": ["sem warnings"] if encontrou else ["nenhum contexto RAG encontrado na base SQLite"],
            "_entrada": argumentos or {},
        }
        return {
            "sucesso": True,
            "dados": dados,
            "_adapter": "rag_sqlite",
            "_db_path": str(db_path),
            "_latencia_ms": round((time.time() - inicio) * 1000, 1),
            "_tokens": _TOKENS_ZERO.copy(),
        }

    return funcao
