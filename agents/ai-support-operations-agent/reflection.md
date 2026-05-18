# reflection.md

Contrato do ReflectionAgent para revisão antes da finalização.

```yaml
critica:
  criterios:
    - corretude: classificação, prioridade e roteamento são coerentes com as evidências?
    - completude: RAG, tickets similares e incidentes foram consultados antes do draft?
    - qualidade_evidencia: toda afirmação operacional relevante tem evidência associada?
    - governanca: a resposta evita promessa de SLA e respeita aprovação humana?
    - seguranca: dados sensíveis não foram persistidos nem expostos?
    - anti_hallucination: causa raiz não foi assumida sem prova?
  limiar_aprovacao: 80
  max_reflexoes: 2
  formato_critica:
    nota: int
    aprovado: bool
    problemas: lista de problemas encontrados
    sugestoes: lista de ações para melhorar
    exige_aprovacao_humana: bool

aprendizado:
  ativo: true
  diretorio: reflection_store/

  extracao_licoes:
    quando: apos_finalizacao
    formato:
      situacao: o que aconteceu
      acao: o que o agente fez
      resultado: qual foi o resultado
      licao: o que aprender com isso
      fonte: ticket_resolvido | correcao_humana | aprovacao_humana | padrao_recorrente
      confianca: baixa | media | alta
    politicas:
      - só extrair lição com aprovação humana, correção humana, ticket resolvido ou evidência confirmada
      - lições devem ser generalizáveis e não específicas a um cliente
      - max 3 lições por execução
      - nunca gravar dados sensíveis nas lições

  deteccao_padroes:
    quando: a_cada_10_execucoes
    formato:
      padrao: descrição do padrão recorrente
      frequencia: quantas vezes observado
      impacto: como afeta o resultado
      ajuste_sugerido: o que mudar no comportamento
    politicas:
      - padrão só é válido se observado em 3 ou mais execuções
      - padrões devem ser acionáveis
      - padrões precisam de revalidação periódica

  injecao:
    onde: contexto_do_planner
    como: licoes_relevantes
    max_licoes_por_execucao: 5
    ordenar_por: relevancia_ao_ticket
```
