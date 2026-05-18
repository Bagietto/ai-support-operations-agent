# rules.md

Governança, limites, obrigatoriedades e restrições.

```yaml
ferramentas_obrigatorias:
  - classificar_ticket
  - calcular_prioridade
  - analisar_sentimento
  - buscar_documentacao
  - buscar_tickets_similares
  - consultar_incidentes
  - gerar_draft_resposta
  - sugerir_roteamento
  - gerar_veredito_suporte
  - registrar_auditoria

limites:
  max_etapas: 12
  sem_progresso: 3
  limite_tempo_segundos: 90
  max_tokens: 4000
  chamadas_ferramenta:
    classificar_ticket: 1
    calcular_prioridade: 1
    analisar_sentimento: 1
    buscar_documentacao: 3
    buscar_tickets_similares: 2
    consultar_incidentes: 2
    gerar_draft_resposta: 1
    sugerir_roteamento: 1
    gerar_veredito_suporte: 1
    registrar_auditoria: 1
    total: 12
  rate_limit_global:
    chamadas_por_minuto: 60
    custo_maximo_centavos: 50

acoes_sensiveis:
  - enviar_resposta_cliente
  - alterar_prioridade_critica
  - escalar_incidente
  - reatribuir_ticket
  - executar_automacao_externa
  - atualizar_status_operacional_sensivel

acoes_proibidas:
  - fechar_ticket_automaticamente
  - enviar_resposta_sem_aprovacao
  - alterar_dados_cliente
  - prometer_sla
  - assumir_causa_raiz_sem_evidencia
  - executar_acao_destrutiva
  - tomar_decisao_financeira
  - inventar_contexto
  - ocultar_falha_de_ferramenta
  - responder_sem_contexto_rag

politicas:
  - validar entrada mínima antes de qualquer classificação
  - buscar_documentacao é obrigatória antes de gerar_draft_resposta
  - consultar_incidentes e buscar_tickets_similares devem ocorrer antes de gerar_veredito_suporte
  - calcular_prioridade deve considerar impacto, urgência e risco operacional
  - gerar_draft_resposta nunca pode prometer SLA, resolução ou causa raiz não confirmada
  - toda afirmação operacional relevante deve ter evidência associada
  - confidence_score menor que 0.85 exige necessita_aprovacao_humana igual a true
  - prioridade alta ou crítica exige necessita_aprovacao_humana igual a true
  - possível incidente de segurança, impacto financeiro ou impacto contratual exige aprovação humana
  - comunicação externa exige aprovação humana no MVP
  - se nenhuma documentação for encontrada, reduzir confidence_score e registrar warning
  - se a classificação estiver ambígua, solicitar complemento ou finalizar como human_intervention_required
  - registrar_auditoria deve ser a última ferramenta antes de FINALIZAR

politicas_memoria:
  - memória de execução pode guardar classificação, prioridade, documentos consultados, warnings e hipóteses
  - memória longa só aceita conhecimento operacional sanitizado e validado por humano
  - nunca persistir tokens, credenciais, senhas, dados pessoais, CPF, telefone, e-mail privado ou payload sensível
  - antes de persistir memória longa, detectar PII, mascarar dados e anonimizar cliente
  - aprendizados precisam de aprovação humana, evidência confirmada ou ticket resolvido
```
