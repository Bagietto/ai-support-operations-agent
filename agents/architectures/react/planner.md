# ReAct Planner

> Arquitetura ReAct (Reason + Act).
> O agente raciocina explicitamente antes de cada ação.
> O raciocínio fica visível no trace.

---

## Campos

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `formato_saida` | objeto | Estrutura JSON que a LLM deve retornar. Inclui campo `raciocinio` obrigatório. |
| `formato_saida.raciocinio` | string | Pensamento explícito do agente antes de decidir. Deve conter: o que sei até agora, o que falta, por que estou escolhendo esta ação. |
| `formato_saida.proxima_acao` | string | Ação escolhida: `CHAMAR_FERRAMENTA`, `FINALIZAR` ou `PERGUNTAR_USUARIO`. |
| `formato_saida.nome_ferramenta` | string | Ferramenta a ser chamada. Obrigatório se `CHAMAR_FERRAMENTA`. |
| `formato_saida.argumentos_ferramenta` | objeto | Parâmetros da ferramenta. |
| `formato_saida.criterio_sucesso` | string | O que define sucesso nesta etapa. |
| `formato_saida.pergunta` | string | Pergunta ao usuário. Obrigatório se `PERGUNTAR_USUARIO`. |
| `regras` | lista | Regras injetadas no prompt da LLM. |

---

```yaml
formato_saida:
  raciocinio: obrigatorio
  proxima_acao: CHAMAR_FERRAMENTA | FINALIZAR | PERGUNTAR_USUARIO
  nome_ferramenta: opcional
  argumentos_ferramenta: opcional
  criterio_sucesso: obrigatorio
  pergunta: opcional

regras:
  - SEMPRE incluir raciocínio antes de decidir a próxima ação
  - o raciocínio deve conter: (1) o que já sei, (2) o que falta, (3) por que escolhi esta ação
  - nunca retornar texto livre fora do JSON
  - cada etapa deve avançar em direção ao objetivo
  - se não houve progresso nas últimas etapas, mudar de estratégia
  - só usar FINALIZAR quando todas as evidências necessárias foram coletadas
```
