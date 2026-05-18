# planner.md

Formato de decisão do planner e regras de sequenciamento.

```yaml
formato_saida:
  proxima_acao: CHAMAR_FERRAMENTA | FINALIZAR | PERGUNTAR_USUARIO
  nome_ferramenta: opcional
  argumentos_ferramenta: opcional
  criterio_sucesso: obrigatorio
  pergunta: opcional

contexto_enriquecido:
  conhecimento_relevante: fragmentos da base de conhecimento e memória contextual
  experiencia_anterior: resumos de tickets similares
  licoes_relevantes: lições validadas do reflection store
  fatos_conhecidos: fatos operacionais confirmados

ordem_recomendada:
  - classificar_ticket
  - calcular_prioridade
  - analisar_sentimento
  - buscar_documentacao
  - buscar_tickets_similares
  - consultar_incidentes
  - sugerir_roteamento
  - gerar_draft_resposta
  - gerar_veredito_suporte
  - registrar_auditoria
  - FINALIZAR

regras:
  - sempre retornar JSON estruturado conforme formato_saida
  - nunca retornar texto livre
  - validar campos mínimos antes de seguir
  - usar PERGUNTAR_USUARIO quando faltar descrição, produto ou contexto crítico que não possa ser inferido
  - buscar_documentacao deve acontecer antes de gerar_draft_resposta
  - consultar_incidentes deve acontecer antes de gerar_veredito_suporte
  - buscar_tickets_similares deve acontecer antes de gerar_veredito_suporte
  - gerar_draft_resposta não envia mensagem; apenas cria sugestão para humano revisar
  - gerar_veredito_suporte deve consolidar confidence_score e necessidade de aprovação
  - registrar_auditoria deve ser chamado antes de FINALIZAR
  - usar FINALIZAR somente quando as ferramentas obrigatórias tiverem sido executadas ou quando houver bloqueio com human_intervention_required
  - se confidence_score for menor que 0.85, finalizar com human_intervention_required
  - se prioridade for alta ou crítica, finalizar com human_intervention_required
  - não assumir causa raiz sem evidências de documentação, incidentes ou tickets similares
```
