---
doc_kind: governance
doc_function: canonical
purpose: SSoT implementation и правила dependency tree. Отвечает на вопрос — кто владеет каким фактом.
derived_from:
  - principles.md
status: active
---
# Document Governance

`Governed document` — markdown-файл в `memory-bank/` с валидным YAML frontmatter. Принцип SSoT определён в [principles.md](principles.md). Этот документ описывает механизм его исполнения.

## SSoT Implementation

1. Authoritative только `active`-документы. `draft` не переопределяет `active`.
2. Среди допустимых по status побеждает upstream: сначала `canonical_for`, затем dependency tree.
3. Публикационный статус (`status`) отделён от lifecycle сущности (`delivery_status`, `decision_status`).

## Source Dependency Tree

1. Поле `derived_from` перечисляет прямые upstream-документы. Authority течёт upstream → downstream.
2. Корневой документ — `principles.md`, не имеет `derived_from`. Для каждого `active` non-root документа `derived_from` обязательно.
3. Циклические зависимости запрещены. Изменение upstream может потребовать обновления downstream.

## Frontmatter Taxonomy

Governed-документы используют `doc_kind` и `doc_function` как routing-метаданные поверх общей schema (`frontmatter.md`).

| Поле | Значения | Назначение |
|-|-|-|
| `doc_kind` | `governance`, `project`, `domain`, `engineering`, `ops`, `feature`, `adr`, `prd`, `use_case` | Семейство документа и его bounded context |
| `doc_function` | `canonical`, `index`, `template`, `derived`, `convention` | Роль документа: canonical owner факта, навигационный индекс, wrapper-template, derived execution-документ или non-canonical project convention |

Минимальные правила:

1. Для всех `active` governed-документов `doc_kind` и `doc_function` должны быть заданы явно.
2. `canonical_for` задаётся только документам с `doc_function: canonical`.
3. `template_*`-поля задаются только документам с `doc_function: template`.
4. `derived` допустим для downstream execution-документов, которые зависят от canonical owner-а факта и не переопределяют scope, architecture или acceptance criteria.
5. `convention` допустим для project-specific правил, которые не являются canonical owner-ом факта, но входят в authoritative set репозитория.
