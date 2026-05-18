# commands.md

Comandos operacionais do Agent Pack.

```yaml
comandos:
  - nome: validar
    descricao: valida se os contratos do agente estão completos e consistentes
    argumentos:
      - nome: --agente
        obrigatorio: true
        descricao: caminho para a pasta do agente
    exemplo: "python main.py validar --agente ../agents/ai-support-operations-agent"

  - nome: rodar
    descricao: executa o agente com uma entrada de ticket
    argumentos:
      - nome: --agente
        obrigatorio: true
        descricao: caminho para a pasta do agente
      - nome: --entrada
        obrigatorio: true
        descricao: texto ou JSON do ticket
      - nome: --modo
        obrigatorio: false
        descricao: modo de operação
      - nome: --arquitetura
        obrigatorio: false
        descricao: arquitetura cognitiva react, plan_execute ou reflect
    exemplo: "python main.py rodar --agente ../agents/ai-support-operations-agent --entrada 'SUP-1042 erro 500 no login em produção'"

  - nome: rastreamento
    descricao: exibe o rastreamento da última execução
    argumentos: []
    exemplo: "python main.py rastreamento"

  - nome: replay
    descricao: reexecuta o agente com a mesma entrada da última execução
    argumentos:
      - nome: --agente
        obrigatorio: true
        descricao: caminho para a pasta do agente
    exemplo: "python main.py replay --agente ../agents/ai-support-operations-agent"

  - nome: benchmark
    descricao: executa suíte de qualidade contra cenários do agente
    argumentos:
      - nome: --agente
        obrigatorio: true
      - nome: --suite
        obrigatorio: true
    exemplo: "python main.py benchmark --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/quality.yaml"

  - nome: tool-eval
    descricao: avalia precisão de seleção de ferramentas
    argumentos:
      - nome: --agente
        obrigatorio: true
      - nome: --suite
        obrigatorio: true
    exemplo: "python main.py tool-eval --agente ../agents/ai-support-operations-agent --suite ../agents/ai-support-operations-agent/evals/tool_selection.yaml"
```
