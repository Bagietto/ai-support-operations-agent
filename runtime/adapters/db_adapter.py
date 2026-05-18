"""
Database Adapter — conecta skills a bancos de dados via query parametrizada.

O adapter le do contrato:
  - tipo_banco, query_template, modo (read_only), timeout_segundos

O adapter le do ambiente (.env):
  - DB_CONNECTION_STRING (connection string do banco)

Seguranca:
  - Queries SEMPRE parametrizadas (NUNCA string format / concatenacao)
  - Modo read_only: rejeita queries com INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE
  - LIMIT obrigatorio: vem do contrato (limites.max_resultados)
  - Connection string NUNCA no .md, so no .env
  - Logging: registra query executada SEM dados sensiveis
"""

import os
import re
import time
import json
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(caminho=None, **kw):
        if not caminho:
            return False
        caminho = Path(caminho)
        if not caminho.exists():
            return False
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))
        return True

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

_TOKENS_ZERO = {"prompt": 0, "completion": 0, "total": 0}

# Palavras-chave proibidas em modo read_only
_OPERACOES_ESCRITA = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"}
_OPERACOES_PERIGOSAS = {
    "ATTACH",
    "DETACH",
    "VACUUM",
    "REINDEX",
    "REPLACE",
    "MERGE",
    "GRANT",
    "REVOKE",
    "PRAGMA",
    "EXEC",
    "EXECUTE",
    "CALL",
}


def _validar_read_only(query: str) -> list:
    """Valida se a query e somente leitura. Retorna lista de violacoes."""
    violacoes = []
    query_upper = query.upper().strip()
    if not query_upper:
        return ["query vazia"]
    if not re.match(r"^(SELECT|WITH)\b", query_upper):
        violacoes.append("query read_only deve iniciar com SELECT ou WITH")
    if ";" in query_upper.rstrip(";"):
        violacoes.append("multiplas instrucoes SQL nao sao permitidas")
    if "--" in query or "/*" in query or "*/" in query:
        violacoes.append("comentarios SQL nao sao permitidos")
    for op in _OPERACOES_ESCRITA:
        if re.search(rf'\b{op}\b', query_upper):
            violacoes.append(f"operacao '{op}' proibida em modo read_only")
    for op in _OPERACOES_PERIGOSAS:
        if re.search(rf'\b{op}\b', query_upper):
            violacoes.append(f"operacao '{op}' proibida em modo read_only")
    return violacoes


def _substituir_parametros(query_template: str, argumentos: dict) -> tuple:
    """Substitui parametros nomeados (:nome) por placeholders seguros.

    Retorna (query_com_placeholders, lista_de_valores) para execucao parametrizada.
    NAO usa string format — usa placeholders numerados para evitar SQL injection.
    """
    params_encontrados = []
    valores = []

    def substituir(match):
        param = match.group(1)
        params_encontrados.append(param)
        indice = len(params_encontrados)
        valor = argumentos.get(param)
        if valor is None:
            valor = str(argumentos.get(param, ""))
        valores.append(valor)
        return f"${indice}"

    query_segura = re.sub(r':([A-Za-z_]\w*)', substituir, query_template)
    return query_segura, valores


def _normalizar_limite(valor, padrao: int, minimo: int = 1, maximo: int = 1000) -> int:
    """Converte limites vindos de contrato para inteiro dentro de uma faixa segura."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        numero = padrao
    return max(minimo, min(numero, maximo))


def criar_funcao_database(habilidade: dict):
    """Cria funcao que executa query parametrizada em banco de dados.

    Le query_template, modo e timeout do bloco 'conexao'.
    Retorna resultado no formato padrao do harness.
    """
    nome = habilidade.get("nome", "")
    conexao = habilidade.get("conexao", {})
    campos_saida = habilidade.get("saida", {})
    limites = habilidade.get("limites", {})

    query_template = conexao.get("query_template", "")
    tipo_banco = conexao.get("tipo_banco", "postgresql")
    modo = conexao.get("modo", "read_only")
    timeout = _normalizar_limite(conexao.get("timeout_segundos", 5), 5, minimo=1, maximo=120)
    max_resultados = _normalizar_limite(limites.get("max_resultados", 100), 100, minimo=1, maximo=1000)

    def funcao(argumentos):
        # 1. Validar modo read_only
        if modo == "read_only":
            violacoes = _validar_read_only(query_template)
            if violacoes:
                return {
                    "sucesso": False,
                    "erro": f"violacao de read_only: {'; '.join(violacoes)}",
                    "_adapter": "database",
                    "_tokens": _TOKENS_ZERO.copy(),
                }

        # 2. Preparar query parametrizada (NUNCA string format)
        query_segura, valores = _substituir_parametros(query_template, argumentos or {})

        # 3. Verificar connection string
        conn_string = os.environ.get("DB_CONNECTION_STRING", "")

        if not conn_string:
            # Sem banco configurado: simular execucao com dados didaticos
            # Em producao, isso seria um erro. Aqui e para o aluno ver o fluxo.
            inicio = time.time()
            dados_simulados = _simular_query(nome, argumentos, campos_saida, max_resultados)
            latencia_ms = round((time.time() - inicio) * 1000, 1)

            return {
                "sucesso": True,
                "dados": dados_simulados,
                "_adapter": "database",
                "_modo": modo,
                "_query_segura": query_segura,
                "_parametros_count": len(valores),
                "_simulado": True,
                "_latencia_ms": latencia_ms,
                "_tokens": _TOKENS_ZERO.copy(),
            }

        # 4. Executar query real (com driver do banco)
        try:
            inicio = time.time()
            resultados = _executar_query_real(
                conn_string, tipo_banco, query_segura, valores, timeout, max_resultados
            )
            latencia_ms = round((time.time() - inicio) * 1000, 1)

            # parsear para formato de saida
            dados = _parsear_resultados(resultados, campos_saida)
            dados["_entrada"] = argumentos

            return {
                "sucesso": True,
                "dados": dados,
                "_adapter": "database",
                "_modo": modo,
                "_query_segura": query_segura,
                "_simulado": False,
                "_latencia_ms": latencia_ms,
                "_tokens": _TOKENS_ZERO.copy(),
            }
        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"erro no banco: {e}",
                "_adapter": "database",
                "_tokens": _TOKENS_ZERO.copy(),
            }

    return funcao


def _simular_query(nome: str, argumentos: dict, campos_saida: dict, max_resultados: int) -> dict:
    """Simula resultado de query quando nao ha banco configurado.

    Retorna dados didaticos realistas para o aluno ver o fluxo completo.
    """
    servico = "desconhecido"
    for v in (argumentos or {}).values():
        if isinstance(v, str) and len(v) > 2:
            servico = v
            break

    if "eventos" in campos_saida or "logs" in campos_saida:
        return {
            "eventos": [
                {"timestamp": "2024-01-15T10:32:00Z", "nivel": "ERROR", "mensagem": f"connection timeout em {servico}", "servico": servico},
                {"timestamp": "2024-01-15T10:28:00Z", "nivel": "WARN", "mensagem": f"pool de conexoes esgotado em {servico}", "servico": servico},
                {"timestamp": "2024-01-15T10:25:00Z", "nivel": "ERROR", "mensagem": f"query lenta detectada em {servico}: 4500ms", "servico": servico},
            ][:max_resultados],
            "contagem_total": min(3, max_resultados),
            "_entrada": argumentos,
        }

    # fallback generico
    dados = {}
    for campo, tipo in campos_saida.items():
        if tipo == "list":
            dados[campo] = [{"item": f"resultado_db_{i}"} for i in range(1, min(4, max_resultados + 1))]
        elif tipo == "int":
            dados[campo] = min(3, max_resultados)
        else:
            dados[campo] = f"{campo}_do_banco"
    dados["_entrada"] = argumentos
    return dados


def _executar_query_real(conn_string: str, tipo_banco: str, query: str, valores: list, timeout: int, max_resultados: int) -> list:
    """Executa query real no banco de dados.

    Suporta PostgreSQL (psycopg2) e SQLite (sqlite3).
    Outros bancos podem ser adicionados.
    """
    if tipo_banco == "sqlite":
        import sqlite3
        # path relativo e resolvido a partir da raiz do gabarito (onde fica o .env),
        # para que o aluno nao dependa do cwd ao rodar o agente
        db_path = Path(conn_string)
        if not db_path.is_absolute():
            db_path = Path(__file__).resolve().parent.parent / conn_string
        # converter placeholders $N para ? (sqlite)
        query_sqlite = re.sub(r'\$\d+', '?', query)
        timeout_ms = _normalizar_limite(timeout, 5, minimo=1, maximo=120) * 1000
        limite_resultados = _normalizar_limite(max_resultados, 100, minimo=1, maximo=1000)
        conn = sqlite3.connect(str(db_path))
        conn.execute(f"PRAGMA busy_timeout = {timeout_ms}")
        cursor = conn.execute(query_sqlite, valores)
        colunas = [desc[0] for desc in cursor.description] if cursor.description else []
        resultados = [dict(zip(colunas, row)) for row in cursor.fetchmany(limite_resultados)]
        conn.close()
        return resultados

    if tipo_banco == "postgresql":
        try:
            import psycopg2
            timeout_segundos = _normalizar_limite(timeout, 5, minimo=1, maximo=120)
            limite_resultados = _normalizar_limite(max_resultados, 100, minimo=1, maximo=1000)
            conn = psycopg2.connect(conn_string, connect_timeout=timeout_segundos)
            cursor = conn.cursor()
            cursor.execute(query, valores)
            colunas = [desc[0] for desc in cursor.description] if cursor.description else []
            resultados = [dict(zip(colunas, row)) for row in cursor.fetchmany(limite_resultados)]
            cursor.close()
            conn.close()
            return resultados
        except ImportError:
            raise RuntimeError("psycopg2 nao instalado. Instale com: pip install psycopg2-binary")

    raise RuntimeError(f"tipo_banco '{tipo_banco}' nao suportado. Use 'postgresql' ou 'sqlite'.")


def _parsear_resultados(resultados: list, campos_saida: dict) -> dict:
    """Converte lista de rows do banco pro formato de saida do contrato."""
    dados = {}
    primeira_linha = resultados[0] if resultados else {}
    for campo, tipo in campos_saida.items():
        if tipo == "list":
            if campo in primeira_linha:
                dados[campo] = _parsear_lista(primeira_linha.get(campo))
            else:
                dados[campo] = resultados
        elif tipo == "int":
            dados[campo] = _parsear_int(primeira_linha.get(campo), len(resultados))
        elif tipo == "float":
            dados[campo] = _parsear_float(primeira_linha.get(campo), 0.0)
        elif tipo == "bool":
            dados[campo] = _parsear_bool(primeira_linha.get(campo), False)
        else:
            dados[campo] = str(primeira_linha.get(campo, "")) if resultados else ""
    return dados 


def _parsear_lista(valor):
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return []
        try:
            parsed = json.loads(texto)
            return parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            return [texto]
    return [valor]


def _parsear_float(valor, padrao: float) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _parsear_int(valor, padrao: int) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _parsear_bool(valor, padrao: bool) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    if isinstance(valor, str):
        return valor.strip().lower() in {"1", "true", "sim", "yes", "y"}
    return padrao
