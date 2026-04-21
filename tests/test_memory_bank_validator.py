from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_validator_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "validate_memory_bank.py"
    spec = importlib.util.spec_from_file_location("validate_memory_bank", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator_module()


def write_doc(path: Path, frontmatter: str, body: str = "# Doc\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")


def build_valid_memory_bank(repo_root: Path) -> None:
    write_doc(
        repo_root / "memory-bank" / "README.md",
        "doc_kind: project\n"
        "doc_function: index\n"
        "purpose: Root index\n"
        "derived_from:\n"
        "  - dna/principles.md\n"
        "status: active\n",
        "# Root\n- [dna/README.md](dna/README.md)\n- [ops/README.md](ops/README.md)\n",
    )
    write_doc(
        repo_root / "memory-bank" / "dna" / "README.md",
        "doc_kind: governance\n"
        "doc_function: index\n"
        "purpose: DNA index\n"
        "derived_from:\n"
        "  - principles.md\n"
        "status: active\n",
        "# DNA\n- [principles.md](principles.md)\n- [governance.md](governance.md)\n",
    )
    write_doc(
        repo_root / "memory-bank" / "dna" / "principles.md",
        "doc_kind: governance\ndoc_function: canonical\npurpose: Principles\nstatus: active\n",
    )
    write_doc(
        repo_root / "memory-bank" / "dna" / "governance.md",
        "doc_kind: governance\n"
        "doc_function: canonical\n"
        "purpose: Governance\n"
        "derived_from:\n"
        "  - principles.md\n"
        "status: active\n",
    )
    write_doc(
        repo_root / "memory-bank" / "ops" / "README.md",
        "doc_kind: ops\n"
        "doc_function: index\n"
        "purpose: Ops index\n"
        "derived_from:\n"
        "  - ../dna/governance.md\n"
        "status: active\n",
        "# Ops\n- [development.md](development.md)\n",
    )
    write_doc(
        repo_root / "memory-bank" / "ops" / "development.md",
        "doc_kind: ops\n"
        "doc_function: canonical\n"
        "purpose: Development\n"
        "derived_from:\n"
        "  - ../dna/governance.md\n"
        "status: active\n",
        "# Development\nSee [governance](../dna/governance.md)\n",
    )


def test_validator_accepts_valid_memory_bank(tmp_path) -> None:
    build_valid_memory_bank(tmp_path)

    messages = validator.validate_memory_bank(tmp_path)

    assert messages == []


def test_validator_rejects_invalid_doc_function(tmp_path) -> None:
    build_valid_memory_bank(tmp_path)
    path = tmp_path / "memory-bank" / "ops" / "development.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("doc_function: canonical", "doc_function: nope"),
        encoding="utf-8",
    )

    messages = validator.validate_memory_bank(tmp_path)

    assert any("invalid doc_function 'nope'" in message.message for message in messages)


def test_validator_requires_derived_from_for_active_non_root(tmp_path) -> None:
    build_valid_memory_bank(tmp_path)
    path = tmp_path / "memory-bank" / "ops" / "development.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("derived_from:\n  - ../dna/governance.md\n", ""),
        encoding="utf-8",
    )

    messages = validator.validate_memory_bank(tmp_path)

    assert any("must define derived_from" in message.message for message in messages)


def test_validator_reports_derived_from_cycle(tmp_path) -> None:
    build_valid_memory_bank(tmp_path)
    path = tmp_path / "memory-bank" / "dna" / "principles.md"
    path.write_text(
        "---\n"
        "doc_kind: governance\n"
        "doc_function: canonical\n"
        "purpose: Principles\n"
        "derived_from:\n"
        "  - governance.md\n"
        "status: active\n"
        "---\n\n# Principles\n",
        encoding="utf-8",
    )

    messages = validator.validate_memory_bank(tmp_path)

    assert any("cycle detected" in message.message for message in messages)


def test_validator_reports_broken_markdown_link(tmp_path) -> None:
    build_valid_memory_bank(tmp_path)
    path = tmp_path / "memory-bank" / "ops" / "development.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "[governance](../dna/governance.md)", "[missing](../dna/missing.md)"
        ),
        encoding="utf-8",
    )

    messages = validator.validate_memory_bank(tmp_path)

    assert any("broken markdown link" in message.message for message in messages)


def test_validator_reports_index_orphans(tmp_path) -> None:
    build_valid_memory_bank(tmp_path)
    write_doc(
        tmp_path / "memory-bank" / "ops" / "release.md",
        "doc_kind: ops\n"
        "doc_function: canonical\n"
        "purpose: Release\n"
        "derived_from:\n"
        "  - ../dna/governance.md\n"
        "status: active\n",
    )

    messages = validator.validate_memory_bank(tmp_path)

    assert any(
        "index does not mention direct child document 'release.md'" in message.message
        for message in messages
    )


def test_validator_enforces_ops_doc_kind(tmp_path) -> None:
    build_valid_memory_bank(tmp_path)
    path = tmp_path / "memory-bank" / "ops" / "development.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("doc_kind: ops", "doc_kind: engineering"),
        encoding="utf-8",
    )

    messages = validator.validate_memory_bank(tmp_path)

    assert any("must use doc_kind: ops" in message.message for message in messages)
