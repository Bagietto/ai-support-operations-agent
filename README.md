# AI Support Operations Agent

Agent Pack declarativo para operações de suporte técnico. O projeto modela um agente de IA que recebe tickets, coleta evidências, consulta conhecimento operacional, calcula prioridade, sugere roteamento, gera um rascunho de resposta e registra auditoria sem executar ações sensíveis automaticamente.

Ele foi pensado como um laboratório de runtime contract-driven: o comportamento do agente fica descrito em arquivos Markdown/YAML versionáveis, enquanto o runtime interpreta esses contratos para validar, executar, rastrear, comparar arquiteturas e medir qualidade.

## Por que este projeto é relevante

Este repositório demonstra um agente de suporte construído como sistema avaliável, não apenas como um prompt. A proposta é mostrar decisões de engenharia aplicadas a agentes autônomos:

- contratos versionáveis para comportamento, ferramentas, memória, reflexão e governança;
- runtime próprio com CLI, rastreamento, telemetria e replay;
- comparação entre arquiteturas cognitivas (`react`, `plan_execute` e `reflect`);
- guardrails para aprovação humana, baixa confiança e ações sensíveis;
- integração com SQLite usando queries parametrizadas e modo `read_only`;
- evals e benchmarks reproduzíveis em modo determinístico, sem depender de credenciais externas.

## Resultado atual dos benchmarks

Última validação local:

| Arquitetura | Conclusão | Cobertura ferramentas | Etapas médias | Reflexões | Tempo |
|---|---:|---:|---:|---:|---:|
| `react` | 100% | 100% | 11.0 | 0 | 17.05s |
| `plan_execute` | 100% | 100% | 11.0 | 0 | 17.17s |
| `reflect` | 100% | 100% | 11.0 | 4 | 17.31s |

Relatório gerado em `runtime/resultados/report.md`.

## Visão de arquitetura

```text
Entrada do ticket
  -> Runtime CLI
  -> Contratos do Agent Pack
  -> Planejador
  -> Ferramentas declaradas
  -> Avaliação por etapa
  -> Reflexão e guardrails
  -> Auditoria, trace e triagem SQLite
```

O runtime é separado do domínio: a lógica operacional fica no Agent Pack, enquanto o motor interpreta contratos e executa o ciclo `perceber -> planejar -> agir -> avaliar`.

## Índice rápido

- [O que a ferramenta se propõe a fazer](#o-que-a-ferramenta-se-propoe-a-fazer)
- [Demo rápida](#demo-rapida)
- [Escopo do MVP](#escopo-do-mvp)
- [Estrutura](#estrutura)
- [Requisitos](#requisitos)
- [Validar contratos](#validar-contratos)
- [Executar uma triagem](#executar-uma-triagem)
- [Rodar testes](#rodar-testes)
- [Quando a categoria não está mapeada](#quando-a-categoria-nao-esta-mapeada)
- [Como diagnosticar problemas de classificação](#como-diagnosticar-problemas-de-classificacao)
- [Avaliações](#avaliacoes)
- [Governança operacional](#governanca-operacional)
- [Segurança contra SQL injection](#seguranca-contra-sql-injection)
- [Guia técnico de integração](#guia-tecnico-de-integracao)
- [Variáveis de ambiente](#variaveis-de-ambiente)
- [Integração REST](#integracao-rest)
- [Integração com GitHub](#integracao-com-github)
- [Integração com Azure DevOps](#integracao-com-azure-devops)
- [Integração com banco de dados](#integracao-com-banco-de-dados)
- [Checklist de implementação](#checklist-de-implementacao)

## O que a ferramenta se propõe a fazer

- Triar tickets de suporte a partir de texto livre ou JSON.
- Classificar categoria e subcategoria do problema.
- Calcular prioridade considerando impacto, urgência, ambiente e risco operacional.
- Analisar sentimento e sinais de risco do cliente.
- Buscar documentação, tickets similares e incidentes relacionados antes de sugerir uma resposta.
- Recomendar time/fila de atendimento com justificativa.
- Consolidar evidências, confidence score e decisão final.
- Gerar apenas um draft de resposta para revisão humana.
- Registrar auditoria da execução.
- Bloquear ou marcar para aprovação humana casos de baixa confiança, prioridade alta/crítica, comunicação externa e ações sensíveis.

## Demo rápida

Use `docs/demo.md` para uma demonstração guiada com três cenários: incidente crítico de login, erro em pedido de venda e categoria não mapeada indo para triagem humana.

## Escopo do MVP

O MVP roda localmente com ferramentas mock determinísticas para permitir testes sem credenciais externas. Quando `OPENAI_API_KEY` estiver disponível, o runtime pode usar LLM no planejamento e em ferramentas mock configuradas para modo LLM.

A ferramenta não fecha tickets, não envia resposta ao cliente, não altera dados do cliente, não promete SLA e não executa automações externas. A saída é uma recomendação operacional auditável para apoiar o humano responsável pelo atendimento.

## Estrutura

```text
agents/
  ai-support-operations-agent/
    agent.md              # identidade e contrato de saída
    rules.md              # governança, limites e políticas
    skills.md             # ferramentas/habilidades declaradas
    memory.md             # política de memória curta, longa, episódica e contextual
    reflection.md         # revisão crítica antes da finalização
    commands.md           # comandos operacionais do Agent Pack
    contracts/            # contratos do planner, executor, loop e toolbox
    evals/                # suítes e datasets de avaliação
  architectures/
    react/
    plan_execute/
    reflect/
runtime/
  main.py                 # CLI
  ciclo.py                # loop de execução
  planejador.py           # decisão da próxima ação
  executor.py             # execução das ferramentas
  ferramentas.py          # mocks e adapters
  validador.py            # validação dos contratos
  benchmark.py            # benchmark de qualidade
  tool_eval.py            # avaliação de seleção de ferramentas
  memory_eval.py          # avaliação de impacto de memória
```

## Requisitos

- Python 3.11+
- Dependências em `runtime/requirements.txt`
- Opcional: `OPENAI_API_KEY` para execuções com LLM

Instalação:

```powershell
cd runtime
python -m pip install -r requirements.txt
```

## Validar contratos

```powershell
cd runtime
python main.py validar --agente ../agents/ai-support-operations-agent
```

Use este comando depois de alterar `agent.md`, `rules.md`, `skills.md`, `memory.md`, `reflection.md` ou qualquer arquivo em `contracts/`.

## Executar uma triagem

```powershell
cd runtime
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "SUP-1042: cliente enterprise não consegue fazer login em produção, erro 500 desde hoje cedo"
```

Exemplo com arquitetura alternativa:

```powershell
cd runtime
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "dashboard muito lento desde ontem" --arquitetura reflect
```

Arquiteturas disponíveis:

- `react`
- `plan_execute`
- `reflect`

Sem `--arquitetura`, o runtime usa o baseline interno do Agent Pack. O comando `comparar` foca nas três arquiteturas acima; use `--incluir-padrao` somente quando quiser medir esse baseline.

## Saída esperada

A execução finaliza com JSON estruturado contendo, entre outros campos:

- `ticket_id`
- `categoria`
- `subcategoria`
- `prioridade`
- `sentimento`
- `impacto_detectado`
- `evidencias`
- `documentos_consultados`
- `acoes_sugeridas`
- `time_recomendado`
- `confidence_score`
- `necessita_aprovacao_humana`
- `sugestao_resposta`
- `comentario_interno`
- `decisao_final`

O contrato completo fica em `agents/ai-support-operations-agent/agent.md`.

## Rodar testes

Os testes usam `unittest`, da biblioteca padrão do Python.

```powershell
python -m unittest discover -s tests
```

Eles cobrem:

- carregamento dos contratos do Agent Pack;
- classificação do cenário de pedido de venda;
- bloqueio de templates SQL perigosos em modo `read_only`;
- substituição segura de parâmetros nomeados;
- tentativa real de SQL injection contra SQLite.

## Quando a categoria não está mapeada

Se a entrada do ticket não bater nas categorias conhecidas pelo classificador local, o agente não deixa de processar o ticket. Ele executa o fluxo, mas classifica o caso como ambíguo e exige ação humana.

Exemplo de categoria mapeada para pedido de venda:

```powershell
cd runtime
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "SUP-1043: erro ao gerar novo pedido de venda"
```

Esse caso deve gerar `sales_order / order_creation_failure`, consultar históricos de `dados/suporte.db` e encaminhar para `support.sales-orders` com aprovação humana.

Quando uma entrada realmente não bate em nenhuma categoria conhecida, ela tende a gerar:

- `categoria=indefinida`
- `subcategoria=indefinida`
- `time_recomendado=triage`
- `fila_recomendada=support.triage`
- `confidence_score` baixo
- `necessita_aprovacao_humana=True`
- `decisao_final=human_intervention_required`
- draft solicitando complemento de produto, ambiente, erro exibido e passos para reproduzir
- registro em `triagens_pendentes` no SQLite

Isso significa que o agente gerou um diagnóstico, mas não tem conhecimento suficiente para resolver ou rotear automaticamente. No MVP, `triage` é uma recomendação persistida em SQLite. O runtime tenta usar `dados/suporte.db`; se o arquivo estiver somente leitura, usa `runtime/operacional.db` como fallback. Ainda não existe tela visual para essa fila.

As categorias reconhecidas pelo mock determinístico ficam em `runtime/ferramentas.py`, na função `_classificar_contexto`. Hoje o classificador local cobre:

- `authentication / login_failure`
- `billing / duplicate_charge`
- `performance / slow_dashboard`
- `product_usage / report_export`
- `sales_order / order_creation_failure`
- `indefinida / indefinida` para casos sem mapeamento

Para cadastrar um novo domínio, o caminho mínimo é:

1. Adicionar a regra de classificação em `_classificar_contexto`.
2. Incluir documentos em `_documentos_para_categoria`.
3. Incluir trechos em `_trechos_para_categoria`.
4. Incluir resoluções em `_resolucoes_para_categoria`.
5. Incluir draft em `_draft_para_categoria`.
6. Incluir ações em `_acoes_para_categoria`.
7. Adicionar exemplos históricos em `dados/suporte.db`, se a ferramenta `buscar_tickets_similares` estiver usando banco.
8. Criar ou atualizar casos de avaliação em `agents/ai-support-operations-agent/evals/`.

## Como diagnosticar problemas de classificação

Use este roteiro quando o agente classificar incorretamente um ticket, cair em `indefinida`, usar uma fila inesperada ou falhar durante a execução.

1. Rode o ticket em modo local previsível:

```powershell
cd runtime
$env:PYTHON_DOTENV_DISABLED="1"
$env:OPENAI_API_KEY=""
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "SUP-1043: erro ao gerar novo pedido de venda"
```

2. Veja o trace da última execução:

```powershell
python main.py rastreamento
```

3. Abra `runtime/trace.json` e procure as etapas:

- `classificar_ticket`: mostra `categoria`, `subcategoria`, `dominio` e evidências da classificação.
- `buscar_documentacao`: mostra se houve contexto RAG/documentação.
- `buscar_tickets_similares`: mostra se o banco trouxe histórico parecido.
- `sugerir_roteamento`: mostra `time_recomendado` e `fila_recomendada`.
- `gerar_veredito_suporte`: mostra `confidence_score`, `necessita_aprovacao_humana` e `decisao_final`.

4. Confira se existem históricos no SQLite:

```powershell
cd ..
python -c "import sqlite3; c=sqlite3.connect('dados/suporte.db'); print(c.execute('select categoria, subcategoria, produto, count(*) from tickets_historicos group by categoria, subcategoria, produto').fetchall())"
```

5. Consulte a fila de triagem persistida:

```powershell
python -c "import sqlite3; c=sqlite3.connect('dados/suporte.db'); print(c.execute('select ticket_id, categoria, subcategoria, fila_recomendada, decisao_final from triagens_pendentes order by criado_em desc').fetchall())"
```

Se a execução informou `runtime/operacional.db`, consulte:

```powershell
cd runtime
python -c "import sqlite3; c=sqlite3.connect('operacional.db'); print(c.execute('select ticket_id, categoria, subcategoria, fila_recomendada, decisao_final from triagens_pendentes order by criado_em desc').fetchall())"
```

6. Se a execução falhar com erro de conexão OpenAI, o runtime faz fallback para o planner mock. Para isolar completamente a regra local, rode com `PYTHON_DOTENV_DISABLED=1` e `OPENAI_API_KEY` vazio, como no primeiro passo.

Sinais comuns:

- `categoria=indefinida`: falta regra de classificação para esse tipo de ticket.
- `documentos_consultados=[]`: não existe contexto/documentação para a categoria.
- `tickets_similares=[]` ou resultados genéricos: o histórico no banco não cobre esse caso.
- `confidence_score < 0.85`: o agente deve exigir aprovação humana.
- `decisao_final=human_intervention_required`: o agente não deve concluir sozinho.

## Rastreabilidade e replay

Exibir o trace da última execução:

```powershell
cd runtime
python main.py rastreamento
```

Reexecutar com a mesma entrada:

```powershell
cd runtime
python main.py replay --agente ../agents/ai-support-operations-agent
```

O trace registra etapas, ferramentas chamadas, resultados, avaliações, tokens, métricas de saúde e dados de performance.

## Avaliações

Benchmark de qualidade:

```powershell
cd runtime
python main.py benchmark --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/quality.yaml
```

Avaliação de seleção de ferramentas:

```powershell
cd runtime
python main.py tool-eval --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/tool_selection.yaml
```

Comparar arquiteturas:

```powershell
cd runtime
python main.py comparar --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/quality.yaml
```

Esse comando compara `react`, `plan_execute` e `reflect`. Para incluir o baseline interno do Agent Pack:

```powershell
python main.py comparar --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/quality.yaml --incluir-padrao
```

Avaliação de impacto de memória:

```powershell
cd runtime
python main.py memory-eval --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/memory_impact.yaml
```

## Governança operacional

O agente segue regras explícitas:

- Toda resposta relevante deve estar apoiada em evidências.
- Documentação deve ser consultada antes do draft de resposta.
- Incidentes e tickets similares devem ser consultados antes do veredito.
- `confidence_score` menor que `0.85` exige aprovação humana.
- Prioridade alta ou crítica exige aprovação humana.
- Comunicação externa exige aprovação humana no MVP.
- Dados sensíveis não devem ser persistidos em memória.
- Causa raiz não pode ser assumida sem evidência.

Essas regras estão em `rules.md`, `planner.md`, `executor.md` e `reflection.md`.

## Segurança contra SQL injection

As ferramentas do tipo `database` usam `runtime/adapters/db_adapter.py`. O adapter aplica uma camada de segurança antes de executar qualquer query:

- aceita somente queries `SELECT` ou `WITH` em modo `read_only`;
- bloqueia `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `PRAGMA`, `ATTACH`, `DETACH`, `VACUUM`, `REINDEX`, `EXEC`, `CALL` e operações similares;
- rejeita múltiplas instruções SQL e comentários SQL em templates;
- transforma parâmetros nomeados, como `:categoria`, em placeholders seguros;
- envia valores separadamente ao driver do banco, sem concatenar strings;
- limita `timeout` e `max_resultados` para faixas controladas.

Exemplo seguro:

```yaml
query_template: >
  SELECT id, categoria, subcategoria, produto, resumo, resolucao
  FROM tickets_historicos
  WHERE categoria = :categoria
    AND subcategoria = :subcategoria
  ORDER BY atualizado_em DESC
  LIMIT 10
modo: read_only
```

Mesmo que um valor de entrada tente injetar SQL, ele é tratado como valor literal do parâmetro, não como comando executável.

## Guia técnico de integração

O runtime resolve ferramentas a partir de `agents/ai-support-operations-agent/skills.md`. Cada item em `habilidades` declara:

- `nome`: nome usado pelo planner e pelo trace.
- `tipo_implementacao`: `mock`, `rest`, `database` ou `mcp`.
- `entrada`: schema de argumentos que o planner deve montar.
- `saida`: schema mínimo que o adapter deve devolver.
- `conexao`: configuração técnica do adapter.
- `limites`: rate limit, retries e limites de resultado.

O ponto de despacho fica em `runtime/ferramentas.py`. Para uma integração nova, o caminho recomendado é:

1. Definir ou ajustar a ferramenta em `skills.md`.
2. Garantir que a mesma ferramenta exista em `contracts/toolbox.md`.
3. Se for obrigatória, listar em `rules.md`.
4. Implementar ou configurar o adapter.
5. Rodar `validar`, `rodar`, `tool-eval` e `benchmark`.

Atalhos desta seção:

- [Variáveis de ambiente](#variaveis-de-ambiente)
- [REST](#integracao-rest)
- [GitHub](#integracao-com-github)
- [Azure DevOps](#integracao-com-azure-devops)
- [Banco de dados](#integracao-com-banco-de-dados)
- [Checklist de implementação](#checklist-de-implementacao)
- [Modelo de evolução recomendado](#modelo-de-evolucao-recomendado)

### Variáveis de ambiente

Crie ou edite:

```text
runtime/.env
```

Nunca coloque tokens, PATs, connection strings ou secrets em arquivos `.md`.

Exemplo:

```env
OPENAI_API_KEY=

API_BASE_URL=http://localhost:8100
API_KEY=

DB_CONNECTION_STRING=

GITHUB_TOKEN=
GITHUB_OWNER=
GITHUB_REPO=

AZURE_DEVOPS_ORG=https://dev.azure.com/sua-org
AZURE_DEVOPS_PROJECT=seu-projeto
AZURE_DEVOPS_PAT=
```

### Integração REST

Use `tipo_implementacao: rest` quando existir uma API HTTP interna ou externa para consultar tickets, incidentes, documentos, clientes ou auditoria.

O adapter atual fica em:

```text
runtime/adapters/rest_adapter.py
```

Ele lê do contrato:

- `conexao.endpoint`
- `conexao.metodo`
- `conexao.timeout_segundos`
- `conexao.retries`
- `conexao.autenticacao`

Ele lê do `.env`:

- `API_BASE_URL`
- `API_KEY`, quando `autenticacao: header_api_key`

Exemplo para consultar incidentes por REST:

```yaml
- nome: consultar_incidentes
  descricao: verifica incidentes ativos ou históricos relacionados ao produto, categoria e ambiente
  tipo_implementacao: rest
  entrada:
    produto: string
    ambiente: string
    categoria: string
    janela_tempo_horas: int
  saida:
    incidentes_relacionados: list
    incidente_ativo: bool
    severidade_incidente: string
    evidencias_incidente: list
  conexao:
    endpoint: /api/v1/incidents/search
    metodo: GET
    timeout_segundos: 10
    retries: 2
    autenticacao: header_api_key
  limites:
    chamadas_por_minuto: 20
```

Contrato esperado da API:

- Receber query params derivados dos campos de `entrada`.
- Responder JSON com os campos declarados em `saida`.
- Retornar erro HTTP quando a consulta falhar; o runtime registra falha e segue as políticas de retry/fallback.

### Integração com GitHub

Há duas formas recomendadas.

Use REST quando você quer chamar diretamente a API do GitHub ou uma API interna que encapsula GitHub:

```yaml
- nome: buscar_tickets_similares
  descricao: busca issues similares no GitHub para contexto operacional
  tipo_implementacao: rest
  entrada:
    categoria: string
    subcategoria: string
    produto: string
    descricao: string
  saida:
    tickets_similares: list
    resolucoes_validadas: list
    confianca_similaridade: float
  conexao:
    endpoint: /github/issues/similar
    metodo: POST
    timeout_segundos: 15
    retries: 2
    autenticacao: header_api_key
  limites:
    chamadas_por_minuto: 20
```

Neste desenho, `API_BASE_URL` aponta para uma API sua, por exemplo `http://localhost:8100`, e essa API é responsável por chamar GitHub usando `GITHUB_TOKEN`.

Use MCP quando você já tem ou quer expor ferramentas GitHub via Model Context Protocol:

```yaml
- nome: buscar_tickets_similares
  descricao: busca issues similares via MCP GitHub
  tipo_implementacao: mcp
  entrada:
    categoria: string
    subcategoria: string
    produto: string
    descricao: string
  saida:
    tickets_similares: list
    resolucoes_validadas: list
    confianca_similaridade: float
  conexao:
    mcp_server: github-mcp
    tool_name: buscar_issues_similares
  limites:
    chamadas_por_minuto: 20
```

Configure o server em:

```text
mcp/config.json
```

Exemplo:

```json
{
  "mcpServers": {
    "github-mcp": {
      "command": "python",
      "args": ["mcp/github_server.py"]
    }
  }
}
```

A tool MCP deve receber os argumentos declarados em `entrada` e devolver JSON compatível com `saida`.

### Integração com Azure DevOps

Para Azure DevOps, existem três caminhos.

O caminho mais simples é REST via API intermediária:

```yaml
- nome: buscar_tickets_similares
  descricao: busca work items similares no Azure DevOps
  tipo_implementacao: rest
  entrada:
    categoria: string
    subcategoria: string
    produto: string
    descricao: string
  saida:
    tickets_similares: list
    resolucoes_validadas: list
    confianca_similaridade: float
  conexao:
    endpoint: /azure-devops/work-items/similar
    metodo: POST
    timeout_segundos: 15
    retries: 2
    autenticacao: header_api_key
  limites:
    chamadas_por_minuto: 20
```

Nesse modelo, a API intermediária usa:

```env
AZURE_DEVOPS_ORG=https://dev.azure.com/sua-org
AZURE_DEVOPS_PROJECT=seu-projeto
AZURE_DEVOPS_PAT=...
```

O segundo caminho é MCP:

```yaml
- nome: registrar_auditoria
  descricao: adiciona comentário interno auditável em um work item do Azure DevOps
  tipo_implementacao: mcp
  entrada:
    ticket_id: string
    ferramentas_utilizadas: list
    classificacao_final: object
    prioridade_final: string
    confidence_score: float
    necessidade_aprovacao: bool
    decisao_final: string
  saida:
    auditoria_id: string
    status: string
    eventos_registrados: list
    horario_registro: string
  conexao:
    mcp_server: azure-devops-mcp
    tool_name: adicionar_comentario_work_item
  limites:
    chamadas_por_minuto: 20
```

O terceiro caminho é criar um adapter dedicado, por exemplo:

```text
runtime/adapters/azure_devops_adapter.py
```

E registrar em `runtime/ferramentas.py`:

```python
if tipo == "azure_devops":
    from adapters.azure_devops_adapter import criar_funcao_azure_devops
    return criar_funcao_azure_devops(habilidade)
```

Use adapter dedicado quando você precisa controlar WIQL, comentários, campos customizados, retries e erros do Azure DevOps sem criar uma API intermediária.

Mapeamento sugerido:

```text
ticket_id                    -> System.Id ou ExternalId
categoria/subcategoria       -> System.Tags ou campos customizados
prioridade                   -> Microsoft.VSTS.Common.Priority
time_recomendado             -> System.AreaPath ou tag operacional
comentario_interno           -> Work Item Comments API
necessita_aprovacao_humana   -> tag needs-human-approval
decisao_final                -> comentário/auditoria, não status automático no MVP
```

No MVP, prefira somente leitura e comentário interno. Não altere `State`, `AssignedTo`, prioridade crítica ou area path sem aprovação humana explícita.

### Integração com banco de dados

Use `tipo_implementacao: database` quando a ferramenta precisa consultar logs, histórico de tickets, catálogos internos, tabelas de auditoria ou bases locais.

O adapter atual fica em:

```text
runtime/adapters/db_adapter.py
```

Ele suporta:

- `sqlite`
- `postgresql`, se `psycopg2-binary` estiver instalado

Ele lê do contrato:

- `conexao.tipo_banco`
- `conexao.query_template`
- `conexao.modo`
- `conexao.timeout_segundos`
- `limites.max_resultados`

Ele lê do `.env`:

- `DB_CONNECTION_STRING`

Este projeto já inclui um banco SQLite de exemplo para testar `buscar_tickets_similares`:

```text
dados/suporte.db
```

Configure no `runtime/.env`:

```env
DB_CONNECTION_STRING=../dados/suporte.db
```

Com essa configuração, a ferramenta `buscar_tickets_similares` deixa de usar mock e passa a consultar a tabela `tickets_historicos`.

Exemplo SQLite:

```env
DB_CONNECTION_STRING=../dados/suporte.db
```

Exemplo PostgreSQL:

```env
DB_CONNECTION_STRING=postgresql://usuario:senha@localhost:5432/suporte
```

Skill de exemplo:

```yaml
- nome: buscar_tickets_similares
  descricao: consulta tickets similares em base histórica local
  tipo_implementacao: database
  entrada:
    categoria: string
    subcategoria: string
    produto: string
    descricao: string
  saida:
    tickets_similares: list
    resolucoes_validadas: list
    confianca_similaridade: float
  conexao:
    tipo_banco: sqlite
    query_template: >
      SELECT id, categoria, subcategoria, produto, resumo, resolucao
      FROM tickets_historicos
      WHERE categoria = :categoria
        AND subcategoria = :subcategoria
      ORDER BY atualizado_em DESC
      LIMIT 10
    modo: read_only
    timeout_segundos: 5
  limites:
    chamadas_por_minuto: 20
    max_resultados: 10
```

Regras importantes:

- Use sempre `modo: read_only` para consultas.
- Não use `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE` ou `CREATE` em ferramentas do agente.
- Use parametros nomeados no formato `:categoria`, `:produto`, etc.
- Não monte SQL por concatenação de strings.
- Retorne apenas campos necessários para o agente.
- Nunca grave PII, tokens ou credenciais em memória longa.

Teste rápido do SQLite:

```powershell
cd runtime
$env:AGENT_MOCK_MODE="deterministic"
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "SUP-1042: erro 500 no login em produção"
```

No `trace.json`, a etapa `buscar_tickets_similares` deve trazer `_adapter: database`, `_simulado: false` e tickets vindos de `dados/suporte.db`.

### Checklist de implementação

Antes de considerar uma integração pronta:

```powershell
cd runtime
python main.py validar --agente ../agents/ai-support-operations-agent
python main.py rodar --agente ../agents/ai-support-operations-agent --entrada "SUP-1042: erro 500 no login em produção"
python main.py tool-eval --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/tool_selection.yaml
python main.py benchmark --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/quality.yaml
```

Também valide manualmente:

- falha de credencial ausente;
- timeout;
- erro HTTP 401/403/500;
- resposta sem campos obrigatórios;
- consulta sem resultados;
- tentativa de ação sensível sem aprovação humana;
- payload com PII.

### Modelo de evolução recomendado

1. Comece com `mock` deterministico para estabilizar regras.
2. Troque uma ferramenta por vez para `rest`, `database` ou `mcp`.
3. Mantenha `registrar_auditoria` como mock até a leitura estar confiável.
4. Habilite comentário interno em GitHub/Azure DevOps.
5. Depois, e somente com aprovação humana, habilite atualizações operacionais não destrutivas.

Na prática, o Agent Pack pode crescer de um simulador local para um copiloto operacional integrado a help desk, GitHub, Azure DevOps, banco de dados, base de conhecimento e sistemas internos, mantendo o mesmo modelo de contratos, avaliação e auditoria.
