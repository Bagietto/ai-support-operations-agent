```yaml
modo_execucao: plan_execute 

formato_saida:
  plano_completo: obrigatorio (lista de passos ordenados)
  proxima_acao: CHAMAR_FERRAMENTA | FINALIZAR
  nome_ferramenta: obrigatorio
  argumentos_ferramenta: obrigatorio
  criterio_sucesso: obrigatorio

regras:
  - gerar o plano COMPLETO na primeira chamada
  - cada passo do plano deve ter: objetivo, ferramenta, argumentos_ferramenta, criterio_sucesso
  - o plano deve cobrir todas as etapas necessárias até o objetivo final
  - ordenar os passos pela dependência lógica (evidências primeiro, consolidação por último)
  - o primeiro passo do plano deve ser retornado como proxima_acao
  - ferramentas obrigatórias devem estar no plano
  - nunca retornar texto livre fora do JSON
  - se o objetivo for ambíguo demais para planejar, usar PERGUNTAR_USUARIO
```
