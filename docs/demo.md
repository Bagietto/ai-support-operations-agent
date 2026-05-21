# Demo do AI Support Operations Agent

Este roteiro demonstra o agente como portfólio: triagem com evidências, governança, memória operacional, SQLite e comparação de arquiteturas.

## Preparação

```powershell
cd runtime
python -m pip install -r requirements.txt
$env:PYTHON_DOTENV_DISABLED="1"
$env:OPENAI_API_KEY=""
$env:DB_CONNECTION_STRING="../dados/suporte.db"
```

Essas variáveis deixam a demo local e reproduzível, sem depender de rede ou credenciais externas.

## Caso 1: Incidente crítico de login

```powershell
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "SUP-1042: cliente enterprise informa erro 500 no login em produção para todos os usuários"
```

O que observar:

- `categoria=authentication`
- `subcategoria=login_failure`
- prioridade crítica
- consulta de documentação e tickets históricos
- `necessita_aprovacao_humana=True`
- roteamento para `identity-platform`

## Caso 2: Pedido de venda

```powershell
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "SUP-1043: erro ao gerar novo pedido de venda"
```

O que observar:

- `categoria=sales_order`
- `subcategoria=order_creation_failure`
- históricos vindos de `dados/suporte.db`
- roteamento para `support.sales-orders`
- aprovação humana antes de qualquer alteração operacional

## Caso 3: Categoria não mapeada

```powershell
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "SUP-4001: o sistema não funciona direito"
```

O que observar:

- `categoria=indefinida`
- `fila_recomendada=support.triage`
- `confidence_score` baixo
- `decisao_final=human_intervention_required`
- registro em `triagens_pendentes`

Consultar pendências:

```powershell
cd ..
python -c "import sqlite3; c=sqlite3.connect('dados/suporte.db'); print(c.execute('select ticket_id, categoria, subcategoria, fila_recomendada, decisao_final from triagens_pendentes order by criado_em desc').fetchall())"
cd runtime
```

Se o runtime informar que salvou em `operacional.db`, consulte:

```powershell
python -c "import sqlite3; c=sqlite3.connect('operacional.db'); print(c.execute('select ticket_id, categoria, subcategoria, fila_recomendada, decisao_final from triagens_pendentes order by criado_em desc').fetchall())"
```

## Comparar arquiteturas

```powershell
python main.py comparar --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/quality.yaml
```

O comparativo principal usa:

- `react`
- `plan_execute`
- `reflect`

Para incluir o baseline interno:

```powershell
python main.py comparar --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/quality.yaml --incluir-padrao
```

## O que este projeto mostra

- Modelagem de agente por contratos versionáveis.
- Pipeline operacional com ferramentas obrigatórias.
- Guardrails para baixa confiança, ações sensíveis e aprovação humana.
- SQLite como memória histórica e fila de triagem.
- Evals e benchmark por arquitetura cognitiva.
- Rastreabilidade em `runtime/trace.json`.
