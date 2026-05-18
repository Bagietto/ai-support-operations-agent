# toolbox.md

Ferramentas autorizadas para o agente.

```yaml
ferramentas:
  - nome: classificar_ticket
    entrada:
      ticket_id: string
      titulo: string
      descricao: string
      produto: string
      canal: string

  - nome: calcular_prioridade
    entrada:
      ticket_id: string
      categoria: string
      descricao: string
      ambiente: string
      plano_cliente: string

  - nome: analisar_sentimento
    entrada:
      ticket_id: string
      descricao: string
      historico_conversa: list

  - nome: buscar_documentacao
    entrada:
      produto: string
      categoria: string
      termos_busca: list
      idioma: string

  - nome: buscar_tickets_similares
    entrada:
      categoria: string
      subcategoria: string
      produto: string
      descricao: string

  - nome: consultar_incidentes
    entrada:
      produto: string
      ambiente: string
      categoria: string
      janela_tempo_horas: int

  - nome: gerar_draft_resposta
    entrada:
      ticket_id: string
      resumo_ticket: string
      documentos_consultados: list
      prioridade: string
      necessita_aprovacao_humana: bool

  - nome: sugerir_roteamento
    entrada:
      categoria: string
      subcategoria: string
      prioridade: string
      produto: string
      incidente_ativo: bool

  - nome: gerar_veredito_suporte
    entrada:
      ticket_id: string
      evidencias: object
      documentos_consultados: list
      prioridade: string
      sentimento: string
      time_recomendado: string

  - nome: registrar_auditoria
    entrada:
      ticket_id: string
      ferramentas_utilizadas: list
      classificacao_final: object
      prioridade_final: string
      confidence_score: float
      necessidade_aprovacao: bool
      decisao_final: string
```
