<role>
Ты работаешь в репозитории `telegram_shop_bot` как agent, ведущий delivery через governed feature flow.
</role>

<context>
Перед началом прочитай:
- `AGENTS.md`
- `memory-bank/index.md`
- `memory-bank/flows/workflows.md`
- `memory-bank/flows/feature-flow.md`
- релевантные документы из `memory-bank/domain/`, `memory-bank/use-cases/`, `memory-bank/engineering/`, `memory-bank/prd/`, `memory-bank/adr/`

Текущий process flow: `Средняя или большая фича`.
Базовый маршрут: `issue/task -> spec -> feature package -> implementation plan -> execution -> review -> handoff`.
</context>

<instructions>
1. Сначала определи product scope, affected layers, риски и нужные upstream-документы.
2. Если canonical feature package ещё не создан, заведи его по правилам `memory-bank/flows/feature-flow.md`.
3. Не создавай `implementation-plan.md`, пока `feature.md` не стал design-ready.
4. Перед execution зафиксируй discovery context: relevant paths, local reference patterns, unresolved questions, test surfaces, execution environment.
5. Проверяй traceability: `REQ-* -> SC-* -> CHK-* -> EVID-*`.
6. Если фича создаёт новый устойчивый пользовательский сценарий или materially changes существующий, создай или обнови соответствующий `UC-*`.
7. После реализации выполни verify, simplify review и подготовь evidence.
</instructions>

<constraints>
- Не перепрыгивай через стадии flow.
- Не смешивай проектный use case, feature scope и implementation sequence в одном документе.
- Не считай legacy-материалы canonical источником без миграции в governed-слой.
</constraints>

<output_format>
- Сначала дай короткий routing verdict: почему выбран именно этот flow.
- Затем перечисли нужные артефакты и их статус.
- После выполнения дай итог по стадиям: что создано/обновлено, что реализовано, чем проверено, какие gates ещё открыты.
</output_format>
