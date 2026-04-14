---
title: Legacy Feature Archive
doc_kind: feature
doc_function: index
purpose: Индекс исторических feature-материалов, созданных до текущего governed feature-flow. Читать только для справки или миграции в canonical package.
derived_from:
  - ../../dna/governance.md
  - ../../flows/feature-flow.md
status: active
audience: humans_and_agents
---

# Legacy Feature Archive

Каталог `memory-bank/features/legacy/` хранит pre-governance материалы ранних задач. Эти документы:

- не являются canonical feature packages текущего flow;
- не заменяют `FT-XXX/README.md`, `feature.md` и `implementation-plan.md`;
- могут использоваться как исторический источник при миграции в актуальную схему.

## Archived Materials

- `001/` — ранняя документация по каталогу товаров
- `002/` — ранняя документация по изображениям в карточке товара
- `003/` — ранняя документация по корзине

## Migration Map

- `001/brief.md` и `001/spec.md` мигрированы в [`../../use-cases/UC-001-browse-catalog-and-open-product.md`](../../use-cases/UC-001-browse-catalog-and-open-product.md), [`../../domain/problem.md`](../../domain/problem.md) и [`../../domain/frontend.md`](../../domain/frontend.md).
- `002/brief.md` и `002/spec.md` мигрированы в [`../../use-cases/UC-001-browse-catalog-and-open-product.md`](../../use-cases/UC-001-browse-catalog-and-open-product.md) и [`../../domain/frontend.md`](../../domain/frontend.md) как часть канонического контракта карточки товара.
- `003/brief.md` и `003/spec.md` мигрированы в [`../../use-cases/UC-002-manage-cart.md`](../../use-cases/UC-002-manage-cart.md), [`../../domain/problem.md`](../../domain/problem.md) и [`../../domain/frontend.md`](../../domain/frontend.md).
- `*/plan.md` остаются только в архиве как исторические implementation artifacts и не являются authoritative источником для новых изменений.
