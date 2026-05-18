# memory.md

Política de memória curta, longa, episódica e contextual.

```yaml
tipos_memoria:
  curta:
    ativo: true
    tipo_implementacao: local
    guardar:
      - classificacao_atual
      - prioridade_calculada
      - documentos_rag_consultados
      - ferramentas_executadas
      - warnings_execucao
      - confidence_score_parcial
      - hipoteses_levantadas
    descartar:
      - prompt_sistema_completo
      - dados_sensiveis
      - payloads_brutos_com_pii
    max_registros: 25

  longa:
    ativo: true
    tipo_implementacao: arquivo
    diretorio: memory_store/longa/
    formato: yaml
    max_entradas: 500
    guardar:
      - padroes_recorrentes_de_erro
      - resolucoes_validadas
      - documentos_frequentemente_utilizados
      - decisoes_aprovadas_por_humanos
      - classificacoes_confirmadas
      - estrategias_de_roteamento
      - incidentes_recorrentes
      - runbooks_utilizados
    descartar:
      - tokens
      - credenciais
      - senhas
      - access_keys
      - dados_pessoais
      - emails_privados
      - cpf
      - telefone
      - contratos
      - valores_financeiros
      - payloads_sensiveis
    politicas:
      - só gravar aprendizado com aprovação humana ou evidência confirmada
      - anonimizar cliente antes de persistir
      - atualizar conhecimento existente em vez de duplicar
      - expirar incidentes após 30 dias
      - expirar runbooks não revalidados após 90 dias
      - expirar roteamentos não revalidados após 180 dias

  episodica:
    ativo: true
    tipo_implementacao: arquivo
    diretorio: memory_store/episodica/
    formato: yaml
    max_episodios: 100
    resumo_por_episodio:
      max_linhas: 10
      campos:
        - ticket_id
        - objetivo
        - ferramentas_chamadas
        - resultado_final
        - warnings
        - intervencao_humana
        - licoes_aprendidas
    politicas:
      - resumir episódio ao final de cada execução
      - não persistir histórico completo da conversa
      - episódios com falha crítica ficam retidos para auditoria

  contextual:
    ativo: false
    tipo_implementacao: embedding
    diretorio: memory_store/contextual/
    modelo_embedding: text-embedding-3-small
    max_fragmentos_por_consulta: 5
    limiar_similaridade: 0.7
    fontes:
      - memoria_longa
      - memoria_episodica
      - documentos_indexados
      - runbooks
      - base_conhecimento
    politicas:
      - ativar somente em testes específicos de memória contextual ou quando o índice já estiver preparado
      - recuperar fragmentos antes da etapa de planejamento quando ativo
      - injetar contexto no planner como conhecimento_relevante
      - max tokens de contexto recuperado por execução: 2000
      - se nenhum fragmento acima do limiar, registrar warning e não inventar contexto

resumo_final:
  max_linhas: 8
  campos:
    - ticket_id
    - categoria
    - prioridade
    - ferramentas_chamadas
    - documentos_consultados
    - decisao_final
    - necessidade_aprovacao
    - proximos_passos
    - licoes_aprendidas
```
