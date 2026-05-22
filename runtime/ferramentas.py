"""
Ferramentas e Evidencias.

Resolve skills declarados em skills.md para implementacoes reais via adapters.
O campo tipo_implementacao define como resolver:
  - local   → regras deterministicas do dominio do Agent Pack
  - mock    → LLM/fallback tecnico para testes e compatibilidade
  - rest    → rest_adapter.py chama API HTTP
  - database → db_adapter.py executa query parametrizada
  - rag     → rag_adapter.py consulta SQLite FTS
  - audit   → audit_adapter.py persiste auditoria SQLite
  - mcp     → mcp_adapter.py conecta a MCP server

Se tipo_implementacao nao esta definido, usa mock (backward compatible).
"""

import json
import os
import random
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass

load_dotenv(Path(__file__).parent / ".env")

_TOKENS_ZERO = {"prompt": 0, "completion": 0, "total": 0}
_SUPPORT_TOOLS = {
    "classificar_ticket",
    "calcular_prioridade",
    "analisar_sentimento",
    "buscar_documentacao",
    "buscar_tickets_similares",
    "consultar_incidentes",
    "gerar_draft_resposta",
    "sugerir_roteamento",
    "gerar_veredito_suporte",
    "registrar_auditoria",
}


def _chamar_llm_ferramenta(prompt_sistema: str, prompt_usuario: str, campos_saida: dict) -> tuple:
    """Chama a LLM para gerar a saida de uma ferramenta.

    Retorna (dados, uso_tokens). dados=None se falhar ou sem API key.
    """
    chave_api = os.environ.get("OPENAI_API_KEY")
    if not chave_api:
        return None, _TOKENS_ZERO.copy()

    from openai import OpenAI

    cliente = OpenAI(api_key=chave_api)
    resposta = cliente.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario},
        ],
    )

    uso_tokens = _TOKENS_ZERO.copy()
    if resposta.usage:
        uso_tokens = {
            "prompt": resposta.usage.prompt_tokens or 0,
            "completion": resposta.usage.completion_tokens or 0,
            "total": resposta.usage.total_tokens or 0,
        }

    try:
        return json.loads(resposta.choices[0].message.content), uso_tokens
    except (json.JSONDecodeError, IndexError):
        return None, uso_tokens


def construir_ferramenta(habilidade: dict):
    """Cria uma funcao que usa a LLM para gerar dados reais."""
    nome = habilidade.get("nome", "")
    descricao = habilidade.get("descricao", "")
    campos_saida = habilidade.get("saida", {})
    campos_entrada = habilidade.get("entrada", {})

    texto_saida = "\n".join(f"  - {campo}: {tipo}" for campo, tipo in campos_saida.items())

    prompt_sistema = f"""Voce e uma ferramenta chamada '{nome}'.
Funcao: {descricao}

Voce DEVE retornar APENAS JSON valido com exatamente estes campos:
{texto_saida}

Regras:
- Gere dados realistas e coerentes com os argumentos recebidos
- Para campos do tipo 'list', retorne uma lista de objetos com detalhes reais
- Para campos do tipo 'object', retorne um objeto estruturado com dados reais
- Para campos do tipo 'string', retorne texto descritivo e especifico
- NUNCA use placeholders como 'mock', 'exemplo', 'teste' — gere conteudo real
- Os dados devem ser coerentes entre si e com o contexto fornecido
- Responda em portugues"""

    def funcao(argumentos):
        modo_mock = os.environ.get("AGENT_MOCK_MODE", "deterministic").strip().lower()
        if modo_mock != "llm" and nome in _SUPPORT_TOOLS:
            dados = _executar_suporte_local(nome, argumentos or {})
            dados["_entrada"] = argumentos or {}
            return {"sucesso": True, "dados": dados, "_tokens": _TOKENS_ZERO.copy()}

        prompt_usuario = f"Argumentos recebidos:\n{json.dumps(argumentos, indent=2, ensure_ascii=False)}"

        dados_llm, uso_tokens = _chamar_llm_ferramenta(prompt_sistema, prompt_usuario, campos_saida)

        if dados_llm:
            dados_llm["_entrada"] = argumentos
            return {"sucesso": True, "dados": dados_llm, "_tokens": uso_tokens}

        # fallback mock simples
        dados = {}
        for nome_campo, tipo_campo in campos_saida.items():
            dados[nome_campo] = _gerar_valor_fallback(tipo_campo, nome_campo)
        dados["_entrada"] = argumentos
        return {"sucesso": True, "dados": dados, "_tokens": _TOKENS_ZERO.copy()}

    return funcao


def _texto_argumentos(argumentos: dict) -> str:
    partes = []
    for chave in ("_entrada_texto", "descricao", "titulo", "produto", "categoria", "subcategoria"):
        valor = argumentos.get(chave)
        if valor:
            partes.append(str(valor))
    if not partes:
        partes.append(json.dumps(argumentos, ensure_ascii=False))
    return " ".join(partes).lower()


def _ticket_id(argumentos: dict) -> str:
    texto = _texto_argumentos(argumentos)
    match = re.search(r"\bSUP-\d+\b", texto, flags=re.IGNORECASE)
    return match.group(0).upper() if match else str(argumentos.get("ticket_id") or "SUP-0000")


def _resolver_arquivo_contrato(caminho: str) -> Path:
    path = Path(caminho)
    if path.is_absolute():
        return path
    candidatos = [
        (Path.cwd() / path).resolve(),
        (Path(__file__).resolve().parents[1] / path).resolve(),
        (Path(__file__).resolve().parent / path).resolve(),
    ]
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    return candidatos[0]


def _carregar_yaml(path: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _classificar_contexto(argumentos: dict, habilidade: dict = None) -> dict:
    if habilidade:
        caminho_regras = habilidade.get("conexao", {}).get("rules_path")
        if caminho_regras:
            regras = _carregar_yaml(_resolver_arquivo_contrato(caminho_regras))
            contexto = _classificar_por_regras(argumentos, regras)
            if contexto:
                return contexto

    texto = _texto_argumentos(argumentos)
    if any(t in texto for t in ("login", "sso", "autentic", "senha", "acesso")):
        return {
            "categoria": "authentication",
            "subcategoria": "login_failure",
            "dominio": "identity",
            "time": "identity-platform",
            "fila": "support.identity",
        }
    if any(t in texto for t in ("cobrado", "cobranca", "cartao", "pagamento", "reembolso", "cancelar uma das cobrancas")):
        return {
            "categoria": "billing",
            "subcategoria": "duplicate_charge",
            "dominio": "finance",
            "time": "financeiro",
            "fila": "support.billing",
        }
    if any(t in texto for t in ("pedido de venda", "novo pedido", "gerar pedido", "ordem de venda", "sales order")):
        return {
            "categoria": "sales_order",
            "subcategoria": "order_creation_failure",
            "dominio": "sales_operations",
            "time": "sales-operations",
            "fila": "support.sales-orders",
        }
    if any(t in texto for t in ("lento", "lentidao", "30 segundos", "dashboard", "performance")):
        return {
            "categoria": "performance",
            "subcategoria": "slow_dashboard",
            "dominio": "platform",
            "time": "platform-operations",
            "fila": "support.platform",
        }
    if any(t in texto for t in ("export", "pdf", "relatorio", "como ")):
        return {
            "categoria": "product_usage",
            "subcategoria": "report_export",
            "dominio": "product",
            "time": "customer-success",
            "fila": "support.howto",
        }
    return {
        "categoria": "indefinida",
        "subcategoria": "indefinida",
        "dominio": "unknown",
        "time": "triage",
        "fila": "support.triage",
    }


def _classificar_por_regras(argumentos: dict, regras: dict) -> dict:
    texto = _texto_argumentos(argumentos)
    for regra in regras.get("regras_classificacao", []):
        palavras = [str(p).lower() for p in regra.get("palavras_chave", [])]
        if any(palavra in texto for palavra in palavras):
            contexto = {
                "categoria": regra.get("categoria", "indefinida"),
                "subcategoria": regra.get("subcategoria", "indefinida"),
                "dominio": regra.get("dominio", "unknown"),
                "time": regra.get("time", "triage"),
                "fila": regra.get("fila", "support.triage"),
                "_evidencias_regra": regra.get("evidencias", []),
            }
            return contexto

    fallback = regras.get("fallback", {})
    if fallback:
        return {
            "categoria": fallback.get("categoria", "indefinida"),
            "subcategoria": fallback.get("subcategoria", "indefinida"),
            "dominio": fallback.get("dominio", "unknown"),
            "time": fallback.get("time", "triage"),
            "fila": fallback.get("fila", "support.triage"),
            "_evidencias_regra": fallback.get("evidencias", []),
        }
    return {}


def _prioridade(argumentos: dict, contexto: dict, habilidade: dict = None) -> dict:
    if habilidade:
        caminho_regras = habilidade.get("conexao", {}).get("rules_path")
        if caminho_regras:
            regras = _carregar_yaml(_resolver_arquivo_contrato(caminho_regras))
            prioridade = _prioridade_por_regras(argumentos, contexto, regras)
            if prioridade:
                return prioridade

    texto = _texto_argumentos(argumentos)
    categoria = str(argumentos.get("categoria") or contexto["categoria"]).lower()
    ambiente = str(argumentos.get("ambiente") or "").lower()
    plano = str(argumentos.get("plano_cliente") or "").lower()
    impacto_alto = any(t in texto for t in ("todos os usuarios", "bloqueados", "producao", "production", "erro 500"))

    if categoria == "authentication" and impacto_alto:
        prioridade = "critica"
        impacto = "usuarios bloqueados em producao"
        urgencia = "imediata"
        risco = "alto"
    elif categoria in {"billing", "performance", "sales_order"}:
        prioridade = "alta"
        if categoria == "billing":
            impacto = "cliente impactado em operacao sensivel"
        elif categoria == "sales_order":
            impacto = "bloqueio em fluxo operacional de venda"
        else:
            impacto = "degradacao relevante de experiencia"
        urgencia = "alta"
        risco = "medio"
    elif categoria == "product_usage":
        prioridade = "baixa"
        impacto = "duvida operacional sem bloqueio"
        urgencia = "baixa"
        risco = "baixo"
    elif categoria == "indefinida":
        prioridade = "baixa"
        impacto = "impacto nao determinado por falta de contexto"
        urgencia = "baixa"
        risco = "baixo"
    else:
        prioridade = "media"
        impacto = "impacto parcialmente identificado"
        urgencia = "media"
        risco = "medio"

    if plano == "enterprise" and ambiente in {"production", "producao"} and prioridade == "alta":
        prioridade = "critica"

    return {
        "prioridade": prioridade,
        "impacto_detectado": impacto,
        "urgencia_detectada": urgencia,
        "risco_operacional": risco,
        "justificativa_prioridade": f"Prioridade {prioridade} por categoria {categoria}, impacto '{impacto}' e urgencia {urgencia}.",
    }


def _prioridade_por_regras(argumentos: dict, contexto: dict, regras: dict) -> dict:
    texto = _texto_argumentos(argumentos)
    categoria = str(argumentos.get("categoria") or contexto["categoria"]).lower()
    ambiente = str(argumentos.get("ambiente") or "").lower()
    plano = str(argumentos.get("plano_cliente") or "").lower()

    selecionada = None
    for regra in regras.get("regras_prioridade", []):
        if str(regra.get("categoria", "")).lower() != categoria:
            continue
        termos = [str(t).lower() for t in regra.get("requer_qualquer_termo", [])]
        if termos and not any(termo in texto for termo in termos):
            continue
        selecionada = regra
        break

    if selecionada:
        resultado = {
            "prioridade": selecionada.get("prioridade", "media"),
            "impacto_detectado": selecionada.get("impacto_detectado", ""),
            "urgencia_detectada": selecionada.get("urgencia_detectada", ""),
            "risco_operacional": selecionada.get("risco_operacional", ""),
        }
    else:
        padrao = regras.get("padrao", {})
        if not padrao:
            return {}
        resultado = {
            "prioridade": padrao.get("prioridade", "media"),
            "impacto_detectado": padrao.get("impacto_detectado", "impacto parcialmente identificado"),
            "urgencia_detectada": padrao.get("urgencia_detectada", "media"),
            "risco_operacional": padrao.get("risco_operacional", "medio"),
        }

    for ajuste in regras.get("ajustes", []):
        quando = ajuste.get("quando", {})
        ambientes = [str(a).lower() for a in quando.get("ambiente", [])]
        if (
            str(quando.get("plano_cliente", "")).lower() == plano
            and ambiente in ambientes
            and str(quando.get("prioridade_atual", "")).lower() == resultado["prioridade"]
        ):
            resultado["prioridade"] = ajuste.get("prioridade", resultado["prioridade"])

    resultado["justificativa_prioridade"] = (
        f"Prioridade {resultado['prioridade']} por categoria {categoria}, "
        f"impacto '{resultado['impacto_detectado']}' e urgencia {resultado['urgencia_detectada']}."
    )
    return resultado


def _executar_suporte_local(nome: str, argumentos: dict, habilidade: dict = None) -> dict:
    contexto = _classificar_contexto(argumentos, habilidade if nome == "classificar_ticket" else None)
    ticket_id = _ticket_id(argumentos)
    texto = _texto_argumentos(argumentos)

    if nome == "classificar_ticket":
        campos_ausentes = []
        if not argumentos.get("produto"):
            campos_ausentes.append("produto")
        if contexto["categoria"] == "indefinida":
            campos_ausentes.extend(["erro_reportado", "ambiente", "passos_para_reproduzir"])
        return {
            "categoria": contexto["categoria"],
            "subcategoria": contexto["subcategoria"],
            "dominio": contexto["dominio"],
            "campos_ausentes": campos_ausentes,
            "evidencias_classificacao": _evidencias_classificacao(texto, contexto["categoria"], contexto),
        }

    if nome == "calcular_prioridade":
        return _prioridade(argumentos, contexto, habilidade)

    if nome == "analisar_sentimento":
        if any(t in texto for t in ("bloqueados", "urgente", "erro 500", "cancelar", "cobrado")):
            sentimento = "urgente" if "erro 500" in texto or "bloqueados" in texto else "frustrado"
            risco_churn = "medio"
        else:
            sentimento = "neutro"
            risco_churn = "baixo"
        return {
            "sentimento": sentimento,
            "risco_churn": risco_churn,
            "sinais_detectados": _sinais_sentimento(texto, sentimento),
        }

    if nome == "buscar_documentacao":
        docs = _documentos_para_categoria(contexto["categoria"])
        encontrou = contexto["categoria"] != "indefinida"
        return {
            "documentos_consultados": docs if encontrou else [],
            "trechos_relevantes": _trechos_para_categoria(contexto["categoria"]) if encontrou else [],
            "encontrou_contexto": encontrou,
            "warnings": ["sem warnings"] if encontrou else ["nenhum contexto RAG confiavel encontrado para ticket ambiguo"],
        }

    if nome == "buscar_tickets_similares":
        if contexto["categoria"] == "indefinida":
            return {
                "tickets_similares": [],
                "resolucoes_validadas": [],
                "confianca_similaridade": 0.22,
            }
        return {
            "tickets_similares": [
                {"ticket_id": f"{ticket_id}-SIM-1", "categoria": contexto["categoria"], "resumo": f"caso similar de {contexto['subcategoria']}"},
                {"ticket_id": f"{ticket_id}-SIM-2", "categoria": contexto["categoria"], "resumo": f"roteamento anterior para {contexto['time']}"},
            ],
            "resolucoes_validadas": _resolucoes_para_categoria(contexto["categoria"]),
            "confianca_similaridade": 0.88 if contexto["categoria"] in {"authentication", "product_usage"} else 0.76,
        }

    if nome == "consultar_incidentes":
        incidente_ativo = contexto["categoria"] in {"authentication", "performance"} and any(t in texto for t in ("erro 500", "producao", "dashboard", "lento"))
        return {
            "incidentes_relacionados": [{"id": "INC-443", "status": "investigating", "categoria": contexto["categoria"]}] if incidente_ativo else [],
            "incidente_ativo": incidente_ativo,
            "severidade_incidente": "alta" if incidente_ativo else "nenhuma",
            "evidencias_incidente": ["sinal operacional compativel com incidente ativo"] if incidente_ativo else [],
        }

    if nome == "gerar_draft_resposta":
        prioridade = str(argumentos.get("prioridade") or _prioridade(argumentos, contexto)["prioridade"]).lower()
        precisa_aprovacao = bool(argumentos.get("necessita_aprovacao_humana")) or prioridade in {"alta", "critica"}
        return {
            "sugestao_resposta": _draft_para_categoria(contexto["categoria"], precisa_aprovacao),
            "tom": "profissional e cuidadoso",
            "ressalvas": ["nao prometer SLA", "nao afirmar causa raiz sem evidencia"],
            "aprovado_para_envio_automatico": False if precisa_aprovacao else contexto["categoria"] == "product_usage",
        }

    if nome == "sugerir_roteamento":
        prioridade = str(argumentos.get("prioridade") or _prioridade(argumentos, contexto)["prioridade"]).lower()
        incidente_ativo = bool(argumentos.get("incidente_ativo"))
        return {
            "time_recomendado": contexto["time"],
            "fila_recomendada": contexto["fila"],
            "tags_sugeridas": [contexto["categoria"], contexto["subcategoria"], prioridade],
            "necessita_escalonamento": prioridade in {"alta", "critica"} or incidente_ativo,
            "justificativa_roteamento": f"Categoria {contexto['categoria']} e subcategoria {contexto['subcategoria']} pertencem ao time {contexto['time']}.",
        }

    if nome == "gerar_veredito_suporte":
        prioridade = str(argumentos.get("prioridade") or _prioridade(argumentos, contexto)["prioridade"]).lower()
        docs = argumentos.get("documentos_consultados") or _documentos_para_categoria(contexto["categoria"])
        encontrou_docs = bool(docs) and contexto["categoria"] != "indefinida"
        confidence = _confidence(contexto["categoria"], prioridade, encontrou_docs)
        necessita_aprovacao = confidence < 0.85 or prioridade in {"alta", "critica"} or contexto["categoria"] in {"billing", "indefinida"}
        return {
            "confidence_score": confidence,
            "justificativa_confidence": _justificativa_confidence(contexto["categoria"], confidence, encontrou_docs),
            "necessita_aprovacao_humana": necessita_aprovacao,
            "decisao_final": "human_intervention_required" if necessita_aprovacao else "completed",
            "acoes_sugeridas": _acoes_para_categoria(contexto["categoria"]),
            "comentario_interno": _comentario_interno(contexto["categoria"], prioridade),
            "warnings": ["sem warnings"] if encontrou_docs else ["saida com baixa confianca por falta de contexto RAG"],
        }

    if nome == "registrar_auditoria":
        return {
            "auditoria_id": f"AUD-{ticket_id}",
            "status": "registrado",
            "eventos_registrados": [
                "classificacao",
                "prioridade",
                "consulta_rag",
                "roteamento",
                "veredito",
            ],
            "horario_registro": "2026-05-18T12:00:00-03:00",
        }

    return {}


def _evidencias_classificacao(texto: str, categoria: str, contexto: dict = None) -> list:
    evidencias = []
    if contexto:
        evidencias.extend(contexto.get("_evidencias_regra", []))
    if "erro 500" in texto:
        evidencias.append("descricao menciona erro 500")
    if "login" in texto or "sso" in texto:
        evidencias.append("descricao menciona falha de login/autenticacao")
    if "cobrado" in texto or "cartao" in texto:
        evidencias.append("descricao menciona cobranca ou cartao")
    if "pedido" in texto or "venda" in texto or "sales order" in texto:
        evidencias.append("descricao menciona falha em pedido de venda")
    if "pdf" in texto or "export" in texto:
        evidencias.append("descricao menciona duvida de exportacao")
    if "lento" in texto or "dashboard" in texto:
        evidencias.append("descricao menciona lentidao no dashboard")
    if not evidencias:
        evidencias.append("ticket sem detalhes suficientes para classificacao precisa")
    evidencias.append(f"categoria inferida: {categoria}")
    return evidencias


def _sinais_sentimento(texto: str, sentimento: str) -> list:
    sinais = []
    if "bloqueados" in texto:
        sinais.append("cliente relata bloqueio operacional")
    if "cobrado" in texto:
        sinais.append("cliente relata impacto financeiro")
    if "urgente" in texto:
        sinais.append("cliente usa linguagem de urgencia")
    if not sinais:
        sinais.append(f"tom classificado como {sentimento}")
    return sinais


def _documentos_para_categoria(categoria: str) -> list:
    return {
        "authentication": ["KB-102", "RUNBOOK-AUTH-LOGIN", "INCIDENT-443"],
        "billing": ["KB-BILLING-201", "POLICY-REFUND-APPROVAL"],
        "sales_order": ["KB-SALES-ORDER-301", "RUNBOOK-SALES-ORDER-CREATE"],
        "performance": ["RUNBOOK-PERF-DASHBOARD", "SLO-DASHBOARD-01"],
        "product_usage": ["KB-EXPORT-PDF", "FAQ-REPORTS-03"],
    }.get(categoria, [])


def _trechos_para_categoria(categoria: str) -> list:
    return {
        "authentication": ["Falhas 5xx no login devem ser correlacionadas com incidentes ativos e logs do identity-service."],
        "billing": ["Acoes financeiras exigem revisao humana; o agente pode apenas orientar e encaminhar."],
        "sales_order": ["Falhas ao gerar pedido de venda devem validar cadastro do cliente, permissao comercial, estoque e integracao ERP antes de assumir causa raiz."],
        "performance": ["Lentidao acima de 30 segundos no dashboard deve ser tratada como degradacao operacional."],
        "product_usage": ["Relatorios podem ser exportados pelo menu Relatorios > Exportar > PDF quando a permissao esta habilitada."],
    }.get(categoria, [])


def _resolucoes_para_categoria(categoria: str) -> list:
    return {
        "authentication": ["verificar incidente ativo", "coletar logs do identity-service", "encaminhar para identity-platform"],
        "billing": ["validar duplicidade", "encaminhar para financeiro", "nao executar reembolso automaticamente"],
        "sales_order": ["validar cadastro do cliente", "verificar permissao comercial", "consultar integracao ERP", "encaminhar para sales-operations"],
        "performance": ["validar metricas do dashboard", "checar incidentes de plataforma", "encaminhar para platform-operations"],
        "product_usage": ["responder com passos de exportacao", "encaminhar para customer-success se permissao estiver ausente"],
    }.get(categoria, [])


def _draft_para_categoria(categoria: str, precisa_aprovacao: bool) -> str:
    if categoria == "authentication":
        return "Ola! Identificamos um possivel problema de acesso e vamos encaminhar para analise do time responsavel. Ainda estamos validando as evidencias antes de confirmar a causa."
    if categoria == "billing":
        return "Ola! Recebemos seu relato de cobranca duplicada. Vamos encaminhar para revisao do time financeiro e manteremos a analise registrada no ticket."
    if categoria == "sales_order":
        return "Ola! Recebemos o erro ao gerar pedido de venda. Vamos validar os dados operacionais e encaminhar para o time responsavel antes de confirmar a causa."
    if categoria == "performance":
        return "Ola! Obrigado pelo aviso. Vamos correlacionar a lentidao informada com os indicadores da plataforma e encaminhar para o time responsavel."
    if categoria == "product_usage" and not precisa_aprovacao:
        return "Ola! Para exportar o relatorio em PDF, acesse Relatorios, selecione o relatorio desejado e use a opcao Exportar > PDF."
    return "Ola! Precisamos de mais detalhes para analisar corretamente este ticket. Pode informar produto, ambiente, erro exibido e passos para reproduzir?"


def _confidence(categoria: str, prioridade: str, encontrou_docs: bool) -> float:
    if categoria == "indefinida":
        return 0.42
    base = 0.91 if encontrou_docs else 0.72
    if prioridade in {"alta", "critica"} and encontrou_docs:
        return 0.9
    if categoria == "product_usage":
        return 0.93
    return base


def _justificativa_confidence(categoria: str, confidence: float, encontrou_docs: bool) -> str:
    if categoria == "indefinida":
        return "Baixa confianca porque a descricao nao contem produto, erro especifico ou impacto mensuravel."
    fonte = "com contexto RAG encontrado" if encontrou_docs else "sem contexto RAG suficiente"
    return f"Confianca {confidence:.2f} baseada em classificacao {categoria}, evidencias do ticket e {fonte}."


def _acoes_para_categoria(categoria: str) -> list:
    return {
        "authentication": ["validar incidente ativo", "consultar logs do identity-service", "manter aprovacao humana antes da resposta"],
        "billing": ["encaminhar para financeiro", "validar duplicidade de cobranca", "nao executar reembolso automaticamente"],
        "sales_order": ["validar cadastro do cliente", "verificar permissao comercial", "consultar integracao ERP", "manter aprovacao humana antes de alterar pedido"],
        "performance": ["verificar metricas do dashboard", "consultar incidentes de plataforma", "priorizar analise operacional"],
        "product_usage": ["enviar orientacao de exportacao PDF", "validar permissao do usuario se o menu nao aparecer"],
        "indefinida": ["solicitar complemento", "manter triagem humana", "reduzir confidence score"],
    }.get(categoria, ["solicitar revisao humana"])


def _comentario_interno(categoria: str, prioridade: str) -> str:
    if categoria == "indefinida":
        return "Ticket ambiguo; solicitar produto, ambiente, mensagem de erro e impacto antes de prosseguir."
    return f"Classificacao {categoria} com prioridade {prioridade}; revisar evidencias antes de comunicacao externa."


def _gerar_valor_fallback(tipo_campo: str, nome_campo: str):
    """Fallback quando nao ha API key — gera valores minimos."""
    tipo_normalizado = tipo_campo.lower() if isinstance(tipo_campo, str) else "string"
    if tipo_normalizado == "float":
        return round(random.uniform(0.01, 100.0), 2)
    if tipo_normalizado == "int":
        return random.randint(1, 500)
    if tipo_normalizado == "bool":
        return random.choice([True, False])
    if tipo_normalizado == "list":
        return [{"item": f"{nome_campo}_1"}, {"item": f"{nome_campo}_2"}]
    if tipo_normalizado == "object":
        return {"campo": nome_campo, "valor": "sem_api_key"}
    return f"{nome_campo}_sem_api_key"

def _resolver_adapter(habilidade):
    tipo = habilidade.get("tipo_implementacao", "mock")

    if tipo == "local":
        try:
            from adapters.support_ops_adapter import criar_funcao_support_ops
            return criar_funcao_support_ops(habilidade)
        except ImportError:
            return construir_ferramenta(habilidade)

    if tipo == "rest":
        try:
            from adapters.rest_adapter import criar_funcao_rest
            return criar_funcao_rest(habilidade)
        except ImportError:
            return construir_ferramenta(habilidade)  # fallback mock

    if tipo == "database":
        try:
            from adapters.db_adapter import criar_funcao_database
            return criar_funcao_database(habilidade)
        except ImportError:
            return construir_ferramenta(habilidade)

    if tipo == "rag":
        try:
            from adapters.rag_adapter import criar_funcao_rag
            return criar_funcao_rag(habilidade)
        except ImportError:
            return construir_ferramenta(habilidade)

    if tipo == "audit":
        try:
            from adapters.audit_adapter import criar_funcao_audit
            return criar_funcao_audit(habilidade)
        except ImportError:
            return construir_ferramenta(habilidade)

    if tipo == "mcp":
        try:
            from adapters.mcp_adapter import criar_funcao_mcp
            return criar_funcao_mcp(habilidade)
        except ImportError:
            return construir_ferramenta(habilidade)

    # mock (padrão)
    return construir_ferramenta(habilidade)


def construir_ferramentas_dos_contratos(contratos: dict) -> dict:
    """Constroi o registro de ferramentas a partir dos contratos (habilidades).

    Despacha cada skill para o adapter correto via tipo_implementacao.
    Se o adapter nao existe, faz fallback para mock (backward compatible).
    """
    habilidades = contratos.get("habilidades", {}).get("habilidades", [])
    ferramentas = {}
    for habilidade in habilidades:
        nome = habilidade.get("nome")
        if nome:
            tipo = habilidade.get("tipo_implementacao", "mock")
            ferramentas[nome] = _resolver_adapter(habilidade)
            if tipo != "mock":
                print(f"  [ferramentas] {nome} → {tipo}")
    return ferramentas


def extrair_evidencias_do_historico(historico: list) -> dict:
    """Extrai evidencias coletadas do historico de forma generica."""
    evidencias = {}
    for registro in historico:
        plano = registro.get("plano", {})
        resultado = registro.get("resultado_acao")
        nome_ferramenta = plano.get("nome_ferramenta")
        if resultado and resultado.get("sucesso") and nome_ferramenta:
            evidencias[nome_ferramenta] = resultado.get("dados", {})
    return evidencias


def _entrada_do_historico(historico: list) -> str:
    for registro in historico or []:
        percepcao = registro.get("percepcao") or ""
        for linha in str(percepcao).splitlines():
            if linha.startswith("Alerta: "):
                return linha.replace("Alerta: ", "", 1).strip()
    return ""


def _valor_de_evidencias(evidencias: dict, *chaves, default=None):
    for dados in evidencias.values():
        if not isinstance(dados, dict):
            continue
        for chave in chaves:
            valor = dados.get(chave)
            if valor not in (None, "", []):
                return valor
    return default


def _extrair_ticket_id_texto(texto: str) -> str:
    match = re.search(r"\bSUP-\d+\b", texto or "", flags=re.IGNORECASE)
    return match.group(0).upper() if match else "SUP-0000"


def montar_argumentos_mock(habilidade: dict, historico: list, entrada_texto: str = "") -> dict:
    """Monta argumentos para uma ferramenta usando evidencias do historico."""
    argumentos = {}
    evidencias = extrair_evidencias_do_historico(historico)
    entrada_texto = entrada_texto or _entrada_do_historico(historico)
    contexto = _classificar_contexto({"_entrada_texto": entrada_texto})
    prioridade_info = _prioridade({"_entrada_texto": entrada_texto, "categoria": contexto["categoria"]}, contexto)
    ticket_id = _extrair_ticket_id_texto(entrada_texto)

    for nome_campo, tipo_campo in habilidade.get("entrada", {}).items():
        tipo_normalizado = tipo_campo.lower() if isinstance(tipo_campo, str) else "string"

        if nome_campo == "ticket_id":
            argumentos[nome_campo] = ticket_id
        elif nome_campo == "titulo":
            argumentos[nome_campo] = entrada_texto.split(":", 1)[-1].strip()[:80] if entrada_texto else "ticket de suporte"
        elif nome_campo == "descricao":
            argumentos[nome_campo] = entrada_texto
        elif nome_campo == "produto":
            argumentos[nome_campo] = _inferir_produto(entrada_texto, contexto)
        elif nome_campo == "canal":
            argumentos[nome_campo] = "portal"
        elif nome_campo == "ambiente":
            argumentos[nome_campo] = "production" if any(t in entrada_texto.lower() for t in ("producao", "production", "prod")) else "unknown"
        elif nome_campo == "plano_cliente":
            argumentos[nome_campo] = "enterprise" if "enterprise" in entrada_texto.lower() else "basic"
        elif nome_campo == "categoria":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "categoria", default=contexto["categoria"])
        elif nome_campo == "subcategoria":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "subcategoria", default=contexto["subcategoria"])
        elif nome_campo == "prioridade":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "prioridade", default=prioridade_info["prioridade"])
        elif nome_campo == "sentimento":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "sentimento", default="neutro")
        elif nome_campo == "time_recomendado":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "time_recomendado", default=contexto["time"])
        elif nome_campo == "resumo_ticket":
            argumentos[nome_campo] = _resumir_ticket(entrada_texto, contexto)
        elif nome_campo == "documentos_consultados":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "documentos_consultados", default=_documentos_para_categoria(contexto["categoria"]))
        elif nome_campo == "necessita_aprovacao_humana":
            prioridade = str(_valor_de_evidencias(evidencias, "prioridade", default=prioridade_info["prioridade"])).lower()
            argumentos[nome_campo] = prioridade in {"alta", "critica"} or contexto["categoria"] in {"billing", "indefinida"}
        elif nome_campo == "incidente_ativo":
            argumentos[nome_campo] = bool(_valor_de_evidencias(evidencias, "incidente_ativo", default=False))
        elif nome_campo == "historico_conversa":
            argumentos[nome_campo] = []
        elif nome_campo == "termos_busca":
            argumentos[nome_campo] = _termos_busca(contexto, entrada_texto)
        elif nome_campo == "idioma":
            argumentos[nome_campo] = "pt-BR"
        elif nome_campo == "janela_tempo_horas":
            argumentos[nome_campo] = 24
        elif nome_campo == "ferramentas_utilizadas":
            argumentos[nome_campo] = list(evidencias.keys())
        elif nome_campo == "classificacao_final":
            argumentos[nome_campo] = {
                "categoria": _valor_de_evidencias(evidencias, "categoria", default=contexto["categoria"]),
                "subcategoria": _valor_de_evidencias(evidencias, "subcategoria", default=contexto["subcategoria"]),
            }
        elif nome_campo == "prioridade_final":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "prioridade", default=prioridade_info["prioridade"])
        elif nome_campo == "confidence_score":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "confidence_score", default=_confidence(contexto["categoria"], prioridade_info["prioridade"], True))
        elif nome_campo == "necessidade_aprovacao":
            prioridade = str(_valor_de_evidencias(evidencias, "prioridade", default=prioridade_info["prioridade"])).lower()
            argumentos[nome_campo] = prioridade in {"alta", "critica"} or contexto["categoria"] in {"billing", "indefinida"}
        elif nome_campo == "decisao_final":
            argumentos[nome_campo] = _valor_de_evidencias(evidencias, "decisao_final", default="human_intervention_required")
        elif tipo_normalizado == "object" and evidencias:
            argumentos[nome_campo] = evidencias
        else:
            argumentos[nome_campo] = _gerar_valor_fallback(tipo_campo, nome_campo)

    if entrada_texto:
        argumentos["_entrada_texto"] = entrada_texto
    return argumentos


def _inferir_produto(texto: str, contexto: dict) -> str:
    texto = (texto or "").lower()
    if "dashboard" in texto or "relatorio" in texto:
        return "analytics"
    if "pedido" in texto or "venda" in texto or contexto["categoria"] == "sales_order":
        return "sales"
    if "login" in texto or "sso" in texto:
        return "plataforma-web"
    if contexto["categoria"] == "billing":
        return "billing"
    return "plataforma"


def _resumir_ticket(texto: str, contexto: dict) -> str:
    if contexto["categoria"] == "authentication":
        return "Cliente relata falha de login com possivel impacto em producao."
    if contexto["categoria"] == "billing":
        return "Cliente relata cobranca duplicada e solicita revisao financeira."
    if contexto["categoria"] == "sales_order":
        return "Cliente relata falha ao gerar novo pedido de venda."
    if contexto["categoria"] == "performance":
        return "Cliente relata lentidao relevante na plataforma."
    if contexto["categoria"] == "product_usage":
        return "Cliente solicita orientacao de uso sobre exportacao de relatorio."
    return "Cliente relata problema sem detalhes suficientes para diagnostico."


def _termos_busca(contexto: dict, texto: str) -> list:
    termos = [contexto["categoria"], contexto["subcategoria"]]
    if "erro 500" in (texto or "").lower():
        termos.append("erro 500")
    if "pdf" in (texto or "").lower():
        termos.append("exportar pdf")
    return [t for t in termos if t and t != "indefinida"]
