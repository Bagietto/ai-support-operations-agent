# agent.md

Identidade e contrato de saída do agente.

```yaml
nome: ai-support-operations-agent
descricao: agente de IA para triagem, enriquecimento, priorização e recomendação operacional em tickets de suporte técnico
tipo: goal_oriented

objetivo: analisar_ticket_suporte

contrato_saida:
  formato: json
  campos_obrigatorios:
    - ticket_id
    - categoria
    - subcategoria
    - prioridade
    - sentimento
    - resumo_ticket
    - impacto_detectado
    - evidencias
    - documentos_consultados
    - acoes_sugeridas
    - time_recomendado
    - confidence_score
    - justificativa_confidence
    - necessita_aprovacao_humana
    - sugestao_resposta
    - comentario_interno
    - decisao_final
  exemplo:
    ticket_id: SUP-1042
    categoria: authentication
    subcategoria: login_failure
    prioridade: alta
    sentimento: frustrado
    resumo_ticket: Cliente não consegue acessar a plataforma por erro 500 no login.
    impacto_detectado: Cliente bloqueado em operação de produção.
    evidencias:
      - Erro 500 informado pelo cliente.
      - Ticket relata bloqueio operacional.
      - Ambiente informado como produção.
    documentos_consultados:
      - KB-102
      - RUNBOOK-AUTH-LOGIN
    acoes_sugeridas:
      - validar incidente ativo de autenticação
      - consultar logs do serviço de identidade
    time_recomendado: identity-platform
    confidence_score: 0.91
    justificativa_confidence: Evidências diretas de erro 500, impacto em produção e contexto RAG encontrado.
    necessita_aprovacao_humana: true
    sugestao_resposta: Olá! Identificamos um possível problema de acesso e vamos encaminhar para análise do time responsável.
    comentario_interno: Verificar incidente ativo e correlacionar com logs de autenticação.
    decisao_final: human_intervention_required
```
