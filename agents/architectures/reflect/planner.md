```yaml
formato_saida:
  raciocinio: opcional
  proxima_acao: CHAMAR_FERRAMENTA | FINALIZAR | PERGUNTAR_USUARIO
  nome_ferramenta: opcional
  argumentos_ferramenta: opcional
  criterio_sucesso: obrigatorio
  pergunta: opcional

regras:
  - seguir o fluxo normal de coleta de evidências
  - ao decidir FINALIZAR, o runtime irá submeter o resultado a uma fase de crítica
  - se a crítica rejeitar, você receberá o feedback e deverá corrigir
  - não tentar FINALIZAR novamente sem ter corrigido os problemas apontados
  - raciocínio é opcional, mas recomendado para facilitar a crítica
```
