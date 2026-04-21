#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_DOC_KINDS = {
    "governance",
    "project",
    "domain",
    "engineering",
    "ops",
    "feature",
    "adr",
    "prd",
    "use_case",
}
ALLOWED_DOC_FUNCTIONS = {"canonical", "index", "template", "derived", "convention"}
ALLOWED_STATUS = {"draft", "active", "archived"}
ALLOWED_DELIVERY_STATUS = {"planned", "in_progress", "done", "cancelled"}
ALLOWED_DECISION_STATUS = {"proposed", "accepted", "superseded", "rejected"}
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@dataclass(frozen=True)
class ValidationMessage:
    path: Path
    line: int
    message: str

    def render(self, root: Path) -> str:
        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        return f"{display_path}:{self.line}: {self.message}"


@dataclass
class Document:
    path: Path
    content: str
    frontmatter: dict[str, Any]
    frontmatter_lines: dict[str, int]
    status_line: int

    @property
    def status(self) -> Any:
        return self.frontmatter.get("status")


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    return strip_quotes(value)


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], dict[str, int]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter opening delimiter '---'")

    closing_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        raise ValueError("missing YAML frontmatter closing delimiter '---'")

    frontmatter: dict[str, Any] = {}
    line_numbers: dict[str, int] = {}
    current_key: str | None = None
    current_list_item: dict[str, Any] | None = None

    for relative_index, raw_line in enumerate(lines[1:closing_index], start=2):
        if not raw_line.strip():
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()

        if indent == 0:
            if ":" not in stripped:
                raise ValueError(f"invalid frontmatter line: {stripped}")
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_list_item = None
            line_numbers[key] = relative_index
            if value:
                frontmatter[key] = parse_scalar(value)
                current_key = None
            else:
                frontmatter[key] = []
                current_key = key
            continue

        if current_key is None:
            raise ValueError(f"unexpected indentation in frontmatter: {stripped}")

        current_value = frontmatter[current_key]
        if not isinstance(current_value, list):
            raise ValueError(f"frontmatter key '{current_key}' does not support nested values")

        if stripped.startswith("- "):
            item_body = stripped[2:].strip()
            if ":" in item_body:
                nested_key, nested_value = item_body.split(":", 1)
                current_list_item = {nested_key.strip(): parse_scalar(nested_value.strip())}
                current_value.append(current_list_item)
            else:
                current_value.append(parse_scalar(item_body))
                current_list_item = None
            continue

        if current_list_item is None or ":" not in stripped:
            raise ValueError(f"invalid nested frontmatter line: {stripped}")

        nested_key, nested_value = stripped.split(":", 1)
        current_list_item[nested_key.strip()] = parse_scalar(nested_value.strip())

    return frontmatter, line_numbers


def load_documents(memory_bank_root: Path) -> tuple[list[Document], list[ValidationMessage]]:
    messages: list[ValidationMessage] = []
    documents: list[Document] = []

    for path in sorted(memory_bank_root.rglob("*.md")):
        try:
            frontmatter, line_numbers = parse_frontmatter(path)
        except ValueError as error:
            relative_path = path.relative_to(memory_bank_root)
            if relative_path.parts[:2] == ("features", "legacy") and path.name != "README.md":
                continue
            messages.append(ValidationMessage(path, 1, str(error)))
            continue

        content = path.read_text(encoding="utf-8")
        documents.append(
            Document(
                path=path,
                content=content,
                frontmatter=frontmatter,
                frontmatter_lines=line_numbers,
                status_line=line_numbers.get("status", 1),
            )
        )

    return documents, messages


def collect_markdown_documents(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.md") if path.is_file())


def normalize_derived_path(document: Document, raw_item: Any) -> Path | None:
    if isinstance(raw_item, str):
        raw_path = raw_item
    elif isinstance(raw_item, dict):
        raw_path = raw_item.get("path")
    else:
        return None

    if not raw_path or not isinstance(raw_path, str):
        return None

    return (document.path.parent / raw_path).resolve()


def parse_link_target(source_path: Path, target: str) -> Path | None:
    clean_target = target.strip().strip("<>")
    if not clean_target or clean_target.startswith("#"):
        return None
    if "://" in clean_target or clean_target.startswith("mailto:"):
        return None

    clean_target = clean_target.split("#", 1)[0]
    line_suffix_match = re.match(r"^(.*\.[A-Za-z0-9_+-]+):\d+$", clean_target)
    if line_suffix_match:
        clean_target = line_suffix_match.group(1)

    if clean_target.startswith("/"):
        return Path(clean_target)

    return (source_path.parent / clean_target).resolve()


def validate_frontmatter(
    documents: list[Document], memory_bank_root: Path
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    root_principles_path = (memory_bank_root / "dna" / "principles.md").resolve()

    for document in documents:
        frontmatter = document.frontmatter
        doc_kind = frontmatter.get("doc_kind")
        doc_function = frontmatter.get("doc_function")
        status = frontmatter.get("status")

        if status not in ALLOWED_STATUS:
            messages.append(
                ValidationMessage(
                    document.path,
                    document.frontmatter_lines.get("status", 1),
                    f"invalid status '{status}'",
                )
            )

        if status == "active":
            if doc_kind not in ALLOWED_DOC_KINDS:
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("doc_kind", 1),
                        f"invalid doc_kind '{doc_kind}'",
                    )
                )
            if doc_function not in ALLOWED_DOC_FUNCTIONS:
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("doc_function", 1),
                        f"invalid doc_function '{doc_function}'",
                    )
                )

            derived_from = frontmatter.get("derived_from")
            if document.path.resolve() != root_principles_path and not derived_from:
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("derived_from", 1),
                        "active non-root document must define derived_from",
                    )
                )

        canonical_for = frontmatter.get("canonical_for")
        if canonical_for and doc_function != "canonical":
            messages.append(
                ValidationMessage(
                    document.path,
                    document.frontmatter_lines.get("canonical_for", 1),
                    "canonical_for is allowed only for doc_function: canonical",
                )
            )

        template_keys = [key for key in frontmatter if key.startswith("template_")]
        if template_keys and doc_function != "template":
            messages.append(
                ValidationMessage(
                    document.path,
                    document.frontmatter_lines.get(template_keys[0], 1),
                    "template_* fields are allowed only for doc_function: template",
                )
            )

        delivery_status = frontmatter.get("delivery_status")
        if delivery_status is not None:
            if doc_kind != "feature" or doc_function != "canonical":
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("delivery_status", 1),
                        "delivery_status is allowed only for canonical feature documents",
                    )
                )
            elif delivery_status not in ALLOWED_DELIVERY_STATUS:
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("delivery_status", 1),
                        f"invalid delivery_status '{delivery_status}'",
                    )
                )

        if doc_kind == "feature" and doc_function == "canonical" and delivery_status is None:
            messages.append(
                ValidationMessage(
                    document.path,
                    document.frontmatter_lines.get("doc_kind", 1),
                    "canonical feature document must define delivery_status",
                )
            )

        decision_status = frontmatter.get("decision_status")
        if decision_status is not None:
            if doc_kind != "adr" or doc_function != "canonical":
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("decision_status", 1),
                        "decision_status is allowed only for canonical ADR documents",
                    )
                )
            elif decision_status not in ALLOWED_DECISION_STATUS:
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("decision_status", 1),
                        f"invalid decision_status '{decision_status}'",
                    )
                )

        if doc_kind == "adr" and doc_function == "canonical" and decision_status is None:
            messages.append(
                ValidationMessage(
                    document.path,
                    document.frontmatter_lines.get("doc_kind", 1),
                    "canonical ADR document must define decision_status",
                )
            )

    return messages


def validate_derived_from(
    documents: list[Document], memory_bank_root: Path
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    path_to_document = {document.path.resolve(): document for document in documents}
    graph: dict[Path, list[Path]] = {}

    for document in documents:
        graph[document.path.resolve()] = []
        derived_from = document.frontmatter.get("derived_from")
        if not derived_from:
            continue

        if not isinstance(derived_from, list):
            messages.append(
                ValidationMessage(
                    document.path,
                    document.frontmatter_lines.get("derived_from", 1),
                    "derived_from must be a list",
                )
            )
            continue

        for item in derived_from:
            normalized = normalize_derived_path(document, item)
            if normalized is None:
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("derived_from", 1),
                        "derived_from items must be strings or objects with path",
                    )
                )
                continue

            if not normalized.exists():
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("derived_from", 1),
                        f"derived_from target does not exist: {normalized.relative_to(memory_bank_root.parent)}",
                    )
                )
                continue

            graph[document.path.resolve()].append(normalized)

    visited: set[Path] = set()
    stack: set[Path] = set()

    def dfs(node: Path) -> None:
        visited.add(node)
        stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in path_to_document:
                continue
            if neighbor in stack:
                messages.append(
                    ValidationMessage(
                        path_to_document[node].path,
                        path_to_document[node].frontmatter_lines.get("derived_from", 1),
                        f"derived_from cycle detected via {path_to_document[neighbor].path.relative_to(memory_bank_root.parent)}",
                    )
                )
                continue
            if neighbor not in visited:
                dfs(neighbor)

        stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return messages


def validate_links(documents: list[Document], repo_root: Path) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    for document in documents:
        in_fenced_block = False
        for line_number, line in enumerate(document.content.splitlines(), start=1):
            if line.strip().startswith("```"):
                in_fenced_block = not in_fenced_block
                continue
            if in_fenced_block:
                continue
            for match in MARKDOWN_LINK_RE.finditer(line):
                target_path = parse_link_target(document.path, match.group(1))
                if target_path is None:
                    continue
                if not target_path.exists():
                    messages.append(
                        ValidationMessage(
                            document.path,
                            line_number,
                            f"broken markdown link: {match.group(1)}",
                        )
                    )

    return messages


def validate_indexes(memory_bank_root: Path) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    for directory in sorted(path for path in memory_bank_root.rglob("*") if path.is_dir()):
        readme_path = directory / "README.md"
        if not readme_path.exists():
            continue

        readme_content = readme_path.read_text(encoding="utf-8")

        for child_file in sorted(directory.glob("*.md")):
            if child_file.name == "README.md":
                continue
            if child_file.name not in readme_content:
                messages.append(
                    ValidationMessage(
                        readme_path,
                        1,
                        f"index does not mention direct child document '{child_file.name}'",
                    )
                )

        for child_dir in sorted(path for path in directory.iterdir() if path.is_dir()):
            if not collect_markdown_documents(child_dir):
                continue
            if child_dir.name not in readme_content and f"{child_dir.name}/" not in readme_content:
                messages.append(
                    ValidationMessage(
                        readme_path,
                        1,
                        f"index does not mention child directory '{child_dir.name}/'",
                    )
                )

    return messages


def validate_project_specific_rules(
    documents: list[Document], memory_bank_root: Path
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    for document in documents:
        relative_path = document.path.relative_to(memory_bank_root)
        if relative_path.parts and relative_path.parts[0] == "ops":
            doc_kind = document.frontmatter.get("doc_kind")
            if doc_kind != "ops":
                messages.append(
                    ValidationMessage(
                        document.path,
                        document.frontmatter_lines.get("doc_kind", 1),
                        "documents under memory-bank/ops must use doc_kind: ops",
                    )
                )

    return messages


def validate_memory_bank(repo_root: Path) -> list[ValidationMessage]:
    memory_bank_root = repo_root / "memory-bank"
    if not memory_bank_root.exists():
        return [ValidationMessage(memory_bank_root, 1, "memory-bank directory does not exist")]

    documents, parse_messages = load_documents(memory_bank_root)
    messages = list(parse_messages)
    messages.extend(validate_frontmatter(documents, memory_bank_root))
    messages.extend(validate_derived_from(documents, memory_bank_root))
    messages.extend(validate_links(documents, repo_root))
    messages.extend(validate_indexes(memory_bank_root))
    messages.extend(validate_project_specific_rules(documents, memory_bank_root))

    unique_messages = {
        (message.path.resolve(), message.line, message.message): message for message in messages
    }
    return sorted(
        unique_messages.values(),
        key=lambda message: (str(message.path), message.line, message.message),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate memory-bank governance rules")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to repository root",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    messages = validate_memory_bank(repo_root)

    if messages:
        for message in messages:
            print(message.render(repo_root))
        print(f"\nmemory-bank validation failed: {len(messages)} issue(s)")
        return 1

    print("memory-bank validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
