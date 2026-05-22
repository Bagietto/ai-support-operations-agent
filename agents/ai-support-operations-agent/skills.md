# skills.md

Ferramentas disponíveis para o agente. As habilidades centrais usam implementação `local`, com regras determinísticas do domínio de suporte operacional. Integrações externas podem ser conectadas por `rest`, `database` ou `mcp` sem alterar o contrato do agente.

```yaml
habilidades:
  - nome: classificar_ticket
    descricao: classifica o ticket por categoria, subcategoria, domínio e campos ausentes relevantes
    tipo_implementacao: local
    entrada:
      ticket_id: string
      titulo: string
      descricao: string
      produto: string
      canal: string
    saida:
      categoria: string
      subcategoria: string
      dominio: string
      campos_ausentes: list
      evidencias_classificacao: list
    conexao:
      rules_path: agents/ai-support-operations-agent/knowledge/classification_rules.yaml
    limites:
      chamadas_por_minuto: 30

  - nome: calcular_prioridade
    descricao: calcula prioridade por impacto, urgência, risco operacional, ambiente e plano do cliente
    tipo_implementacao: local
    entrada:
      ticket_id: string
      categoria: string
      descricao: string
      ambiente: string
      plano_cliente: string
    saida:
      prioridade: string
      impacto_detectado: string
      urgencia_detectada: string
      risco_operacional: string
      justificativa_prioridade: string
    conexao:
      rules_path: agents/ai-support-operations-agent/knowledge/priority_rules.yaml
    limites:
      chamadas_por_minuto: 30

  - nome: analisar_sentimento
    descricao: avalia sentimento, frustração, urgência emocional e risco de churn
    tipo_implementacao: local
    entrada:
      ticket_id: string
      descricao: string
      historico_conversa: list
    saida:
      sentimento: string
      risco_churn: string
      sinais_detectados: list
    limites:
      chamadas_por_minuto: 30

  - nome: buscar_documentacao
    descricao: consulta base de conhecimento, runbooks, FAQ e documentação técnica antes de qualquer resposta
    tipo_implementacao: rag
    entrada:
      produto: string
      categoria: string
      termos_busca: list
      idioma: string
    saida:
      documentos_consultados: list
      trechos_relevantes: list
      encontrou_contexto: bool
      warnings: list
    conexao:
      tipo_banco: sqlite
      seed_path: agents/ai-support-operations-agent/knowledge/documentation_seed.json
      modo: read_only
    limites:
      chamadas_por_minuto: 30
      max_resultados: 5

  - nome: buscar_tickets_similares
    descricao: recupera tickets parecidos em base SQLite para contexto operacional e padrões recorrentes
    tipo_implementacao: database
    entrada:
      categoria: string
      subcategoria: string
      produto: string
      descricao: string
    saida:
      tickets_similares: list
      resolucoes_validadas: list
      confianca_similaridade: float
    conexao:
      tipo_banco: sqlite
      query_template: >
        SELECT
          json_group_array(
            json_object(
              'ticket_id', ticket_id,
              'categoria', categoria,
              'subcategoria', subcategoria,
              'produto', produto,
              'resumo', resumo,
              'time_responsavel', time_responsavel,
              'prioridade', prioridade,
              'resolucao', resolucao
            )
          ) AS tickets_similares,
          json_group_array(resolucao) AS resolucoes_validadas,
          CASE
            WHEN COUNT(*) >= 2 THEN 0.92
            WHEN COUNT(*) = 1 THEN 0.72
            ELSE 0.0
          END AS confianca_similaridade
        FROM tickets_historicos
        WHERE categoria = :categoria
          AND subcategoria = :subcategoria
          AND produto = :produto
        ORDER BY atualizado_em DESC
        LIMIT 5
      modo: read_only
      timeout_segundos: 5
    limites:
      chamadas_por_minuto: 20
      max_resultados: 5

  - nome: consultar_incidentes
    descricao: verifica incidentes ativos ou históricos relacionados ao produto, categoria e ambiente
    tipo_implementacao: rest
    entrada:
      produto: string
      ambiente: string
      categoria: string
      janela_tempo_horas: int
    saida:
      incidentes_relacionados: list
      incidente_ativo: bool
      severidade_incidente: string
      evidencias_incidente: list
    conexao:
      endpoint: /api/incidents/search
      metodo: GET
      timeout_segundos: 5
      retries: 1
    limites:
      chamadas_por_minuto: 20

  - nome: gerar_draft_resposta
    descricao: gera resposta sugerida para cliente, sem envio automático e sem promessa de SLA
    tipo_implementacao: local
    entrada:
      ticket_id: string
      resumo_ticket: string
      documentos_consultados: list
      prioridade: string
      necessita_aprovacao_humana: bool
    saida:
      sugestao_resposta: string
      tom: string
      ressalvas: list
      aprovado_para_envio_automatico: bool
    limites:
      chamadas_por_minuto: 30

  - nome: sugerir_roteamento
    descricao: sugere time responsável, fila, tags e necessidade de escalonamento humano
    tipo_implementacao: local
    entrada:
      categoria: string
      subcategoria: string
      prioridade: string
      produto: string
      incidente_ativo: bool
    saida:
      time_recomendado: string
      fila_recomendada: string
      tags_sugeridas: list
      necessita_escalonamento: bool
      justificativa_roteamento: string
    limites:
      chamadas_por_minuto: 30

  - nome: gerar_veredito_suporte
    descricao: consolida classificação, prioridade, contexto RAG, roteamento, confidence score e decisão final
    tipo_implementacao: local
    entrada:
      ticket_id: string
      evidencias: object
      documentos_consultados: list
      prioridade: string
      sentimento: string
      time_recomendado: string
    saida:
      confidence_score: float
      justificativa_confidence: string
      necessita_aprovacao_humana: bool
      decisao_final: string
      acoes_sugeridas: list
      comentario_interno: string
      warnings: list
    limites:
      chamadas_por_minuto: 20

  - nome: registrar_auditoria
    descricao: registra trilha auditável da execução, ferramentas usadas, warnings, falhas e decisão final
    tipo_implementacao: audit
    entrada:
      ticket_id: string
      ferramentas_utilizadas: list
      classificacao_final: object
      prioridade_final: string
      confidence_score: float
      necessidade_aprovacao: bool
      decisao_final: string
    saida:
      auditoria_id: string
      status: string
      eventos_registrados: list
      horario_registro: string
    conexao:
      tipo_banco: sqlite
      modo: append_only
    limites:
      chamadas_por_minuto: 20
```
