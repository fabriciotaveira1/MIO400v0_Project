# Arquitetura de Automacao

## Visao geral

O projeto passa a ter um motor central em `app/services/rule_engine.py`.

Fluxo principal:

1. `SocketListener` recebe evento TCP (opcode 30/92).
2. `state_manager` atualiza estado atual de entradas e saidas.
3. `rule_engine.process_input_event(...)` recebe evento de entrada.
4. O `rule_engine` avalia gatilho + condicoes.
5. Se aprovado, executa a sequencia de acoes em ordem.
6. Acoes de saida usam opcode 01 via `device_manager` + `CommboxClient`.

## Rule Engine

Responsabilidades:

- armazenar regras (CRUD em memoria + persistencia JSON)
- normalizar regras antigas para o novo formato
- avaliar gatilhos:
  - `INPUT_CHANGE`
  - `INPUT_ON`
  - `INPUT_OFF`
  - `TIMER`
  - `SCHEDULE`
- avaliar condicoes:
  - `INPUT_STATE`
  - `OUTPUT_STATE`
  - `TIME_RANGE`
- executar acoes:
  - `OUTPUT_ON`
  - `OUTPUT_OFF`
  - `OUTPUT_TOGGLE`
  - `OUTPUT_PULSE`
  - `DELAY`

Persistencia:

- `app/automation/data/automation_rules.json`

## Execucao sequencial

Cada regra pode ter varias acoes e o motor executa em ordem:

1. executa acao atual
2. se for `DELAY`, aguarda o tempo
3. continua para proxima acao

Exemplo:

1. `OUTPUT_ON` em saida 1
2. `DELAY` de 5 segundos
3. `OUTPUT_OFF` em saida 1

## Integracao com estado e dispositivo

- `state_manager` segue como fonte de verdade para estado atual.
- Leitura de entradas/saidas usadas nas condicoes vem do `state_manager`.
- Comandos de atuacao usam `build_output_command(...)` (opcode 01).
- `OUTPUT_PULSE` usa os campos `t_on` e `total_time`.

## API de regras

Novo endpoint principal em `app/api/routes_rules.py`:

- `GET /rules`
- `POST /rules`
- `PUT /rules/{id}`
- `DELETE /rules/{id}`
- `POST /rules/{id}/enable`
- `POST /rules/{id}/disable`

Compatibilidade:

- `app/api/routes_automation.py` continua disponivel com aliases em `/automation/rules`.

## GUI de automacao

`app/gui/automation_tab.py` oferece:

- tabela de regras
- botoes: adicionar, editar, excluir, ativar, desativar
- `RuleEditorDialog` com:
  - QUANDO (gatilho)
  - SE (multiplas condicoes)
  - ENTÃO (multiplas acoes)

A GUI envia/edita regras no novo formato e ainda possui fallback para rotas antigas.
