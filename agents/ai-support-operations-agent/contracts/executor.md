# executor.md

Política de execução, validação, retry e pós-execução.

```yaml
execucao:
  validar_entrada: true
  tentar_novamente_em_falha: true
  max_retentativas_por_ferramenta: 2
  timeout_por_ferramenta_segundos: 15
  fallback_em_falha:
    buscar_documentacao:
      - cache_local
      - mock
      - arquivo
    buscar_tickets_similares:
      - mock
      - arquivo
    consultar_incidentes:
      - mock
      - arquivo

pos_execucao:
  avaliar_resultado: true
  registrar_warning_em_falha: true
  reduzir_confidence_em_falha: true
  atualizar_memoria_execucao: true

criterios_sem_progresso:
  - repeticao_da_mesma_ferramenta
  - confidence_score_estagnado
  - nenhum_documento_encontrado
  - campos_obrigatorios_vazios
  - repeticao_da_mesma_hipotese
  - timeout_de_execucao
  - excesso_de_retentativas
```
