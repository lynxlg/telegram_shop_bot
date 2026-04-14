<role>
Ты работаешь в репозитории `telegram_shop_bot` как agent, ведущий delivery через governed feature flow.
</role>

<context>
Перед началом прочитай:
- `AGENTS.md`
- `memory-bank/index.md`
- `memory-bank/flows/workflows.md`
- релевантные документы из `memory-bank/domain/`, `memory-bank/engineering/` и `memory-bank/use-cases/`

Текущий process flow: `Малая фича`.
Критерий выбора flow: задача понятна, scope локален, решение помещается в одну сессию или один компактный change set.
</context>

<instructions>
1. Сначала быстро заземлись в текущем коде и существующих паттернах.
2. Используй минимальный workflow: `issue/task -> routing -> implementation -> review -> merge`.
3. Не раздувай задачу до feature package, если локальный change set контролируем и не меняет проектный контракт.
4. Если по ходу работы становится ясно, что меняется контракт, rollout, schema или требуется явный execution plan, остановись и предложи upgrade до `Средней/большой фичи`.
5. Вноси только необходимые изменения.
6. После правок выполни релевантную локальную проверку.
</instructions>

<constraints>
- Не изобретай scope сверх запроса.
- Не создавай `feature package`, PRD или ADR без явного сигнала, что локальный flow уже недостаточен.
- Не ломай существующие canonical use cases и baseline-сценарии.
</constraints>

<output_format>
- Коротко сообщи, что понял из задачи и какой локальный change set выбрал.
- После выполнения дай компактный итог: что изменено, чем проверено, есть ли причина поднять задачу в более тяжёлый flow.
</output_format>
