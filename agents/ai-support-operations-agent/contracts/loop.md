# loop.md

Ciclo operacional do agente.

```yaml
objetivo: analisar_ticket_suporte

ciclo:
  max_etapas: 12

etapas_obrigatorias:
  - validar_entrada_minima
  - classificar_ticket
  - calcular_prioridade
  - analisar_sentimento
  - consultar_contexto_rag
  - buscar_tickets_similares
  - consultar_incidentes
  - gerar_draft_resposta
  - sugerir_roteamento
  - gerar_confidence_score
  - definir_aprovacao_humana
  - executar_reflexao_final
  - registrar_auditoria

finalizacao_sucesso:
  obrigatorio:
    - ticket_classificado
    - prioridade_calculada
    - confidence_score_gerado
    - consulta_rag_executada
    - sugestao_roteamento_definida
    - draft_resposta_gerado
    - necessidade_aprovacao_definida
    - auditoria_registrada

estados_finais:
  - completed
  - completed_with_warnings
  - failed
  - human_intervention_required
  - stalled

condicoes_parada:
  - objetivo_alcancado
  - max_etapas_excedido
  - sem_progresso
  - limite_tempo_excedido
  - intervencao_humana_necessaria
```
