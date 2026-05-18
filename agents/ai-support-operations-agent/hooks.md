# hooks.md

Hooks declarativos de validação, observabilidade, segurança, memória e auditoria.

```yaml
ganchos:
  antes_da_etapa: log
  apos_etapa: log

  antes_da_acao:
    - log
    - validar_rate_limit
    - verificar_budget
    - validar_payload

  apos_acao:
    - log
    - registrar_latencia
    - registrar_resultado
    - atualizar_memoria_execucao

  em_erro:
    - alerta
    - retry_controlado
    - registrar_warning
    - acionar_fallback

  antes_da_validacao:
    - validar_campos_obrigatorios
    - detectar_pii

  antes_de_resposta:
    - verificar_rag_executado
    - validar_confidence
    - executar_reflection
    - bloquear_promessa_sla

  antes_de_recuperar_contexto:
    - log
    - verificar_cache_embedding

  apos_recuperar_contexto:
    - log
    - registrar_fragmentos_recuperados
    - verificar_relevancia_minima

  antes_de_persistir_memoria:
    - log
    - detectar_pii
    - sanitizar_dados
    - anonimizar_cliente
    - validar_fonte
    - verificar_duplicata

  apos_persistir_memoria:
    - log
    - confirmar_gravacao

  apos_finalizacao:
    - registrar_auditoria
    - calcular_metricas
    - avaliar_aprendizado
```
