---
title: "FT-NTF-001: Implementation Plan"
doc_kind: feature
doc_function: derived
purpose: "Execution-план реализации buyer notifications о смене статуса заказа с grounded discovery context, sequencing и verify strategy."
derived_from:
  - feature.md
status: archived
audience: humans_and_agents
must_not_define:
  - ft_ntf_001_scope
  - ft_ntf_001_architecture
  - ft_ntf_001_acceptance_criteria
  - ft_ntf_001_blocker_state
---

# План имплементации

## Цель текущего плана

Замкнуть уже существующий order lifecycle между `FT-OPS-001` и `FT-TRK-001`: после operator/admin status update покупатель должен получать проактивное Telegram-уведомление без риска потерять commit при ошибке доставки.

## Current State / Reference Points

| Path / module | Current role | Why relevant | Reuse / mirror |
| --- | --- | --- | --- |
| `app/handlers/operator_orders.py` | Entry point operator/admin workflow смены статуса | Именно здесь появляется post-commit notification step | Сохранить safe error handling и текущий callback UX |
| `app/services/order.py` | Канонический service update статуса заказа | Нужно различать фактический transition и no-op update | Расширить contract без поломки existing callers |
| `app/services/order_text.py` | Централизованный status mapping | Notification обязан reuse тот же mapping | Добавить отдельный text-builder рядом с existing formatters |
| `tests/handlers/test_operator_orders.py` | Existing regression для operator flow | Нужны happy path, no-op и delivery failure cases | Следовать current AsyncMock/SimpleNamespace pattern |
| `tests/test_order_service.py` | Service integration regression | Нужен contract для changed/no-op metadata | Добавить focused tests на update result |

## Test Strategy

| Test surface | Canonical refs | Planned automated coverage | Required local suites / commands | Manual-only gap / justification |
| --- | --- | --- | --- | --- |
| `app/handlers/operator_orders.py` | `REQ-01`, `REQ-03`, `REQ-04`, `SC-01`, `SC-02`, `NEG-01`, `CHK-01` | Handler tests на notification send, no-op skip и safe failure | `pytest tests/handlers/test_operator_orders.py -v` | `none` |
| `app/services/order.py` | `REQ-03`, `REQ-05`, `CHK-02` | Service tests на changed/no-op metadata | `pytest tests/test_order_service.py -v` | `none` |
| `app/services/order_text.py` | `REQ-02`, `REQ-05`, `CHK-03` | Unit test на notification text contract | `pytest tests/test_ui_texts.py -v -m unit` | `none` |

## Open Questions / Ambiguities

| Open Question ID | Question | Why unresolved | Blocks | Default action / escalation owner |
| --- | --- | --- | --- | --- |
| `OQ-01` | Нужен ли durable audit/retry слой для недоставленных уведомлений | В текущем scope explicitly non-scope | `none` | Ограничиться logging-only и поднять retry как отдельную feature |

## Preconditions

| Precondition ID | Canonical ref | Required state | Used by steps | Blocks start |
| --- | --- | --- | --- | --- |
| `PRE-01` | `REQ-01`-`REQ-05` | `feature.md` active и design-ready | `STEP-01`-`STEP-04` | yes |

## Порядок работ

| Step ID | Actor | Implements | Goal | Touchpoints | Verifies | Evidence IDs |
| --- | --- | --- | --- | --- | --- | --- |
| `STEP-01` | agent | `REQ-03`, `CTR-01` | Расширить service contract смены статуса метаданными о фактическом transition | `app/services/order.py`, `tests/test_order_service.py` | `CHK-02` | `EVID-02` |
| `STEP-02` | agent | `REQ-02`, `CTR-02` | Добавить text-builder buyer notification на базе existing status mapping | `app/services/order_text.py`, `app/ui_texts.json`, `tests/test_ui_texts.py` | `CHK-03` | `EVID-03` |
| `STEP-03` | agent | `REQ-01`, `REQ-04` | Отправлять buyer notification из operator handler после commit и изолировать send failures | `app/handlers/operator_orders.py`, `tests/handlers/test_operator_orders.py` | `CHK-01` | `EVID-01` |
| `STEP-04` | agent | `REQ-05` | Прогнать verify suites, выполнить simplify review и закрыть docs | `memory-bank/features/FT-NTF-001/*` | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` |

## Stop Conditions / Fallback

| Stop ID | Related refs | Trigger | Immediate action | Safe fallback state |
| --- | --- | --- | --- | --- |
| `STOP-01` | `NEG-01`, `REQ-04` | Выясняется, что notification path вмешивается в commit semantics | Остановить closure и вернуть separation post-commit side effect от persistence | Feature остается `in_progress` до корректного разделения write и notify |

## Готово для приемки

План считается исчерпанным, когда service отличает transition от no-op, handler отправляет buyer notification только после реального update, send failure не ломает operator workflow, а `CHK-01`/`CHK-02`/`CHK-03` проходят зелёно.
