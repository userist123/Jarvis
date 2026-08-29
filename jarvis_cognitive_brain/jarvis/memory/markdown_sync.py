"""Bidirectional Obsidian Markdown synchronization for the JARVIS memory layer."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from jarvis.memory.invariants import (
    Lifecycle,
    NoteFrontmatter,
    NoteType,
)
from jarvis.memory.sqlite_engine import SQLiteStorageEngine

FOLDER_TYPE_MAP = {
    NoteType.KNOWLEDGE.value: "01_KNOWLEDGE",
    NoteType.PROJECT.value: "02_PROJECTS",
    NoteType.PROCEDURE.value: "03_PROCEDURES",
    NoteType.ERROR.value: "04_MEMORY/Errors",
    NoteType.LESSON.value: "04_MEMORY/Lessons",
    NoteType.EXPERIENCE.value: "04_MEMORY/Experiences",
    NoteType.DECISION.value: "04_MEMORY/Decisions",
    NoteType.PREFERENCE.value: "04_MEMORY/Preferences",
    NoteType.HYPOTHESIS.value: "04_MEMORY/Hypotheses",
    NoteType.RESOURCE.value: "05_RESOURCES",
    NoteType.SYSTEM.value: "99_SYSTEM",
    NoteType.CORE.value: "00_CORE",
}

EXCLUDED_FOLDERS = {"06_INBOX", "90_TEMPLATES", ".agents", ".checkpoints", ".git", ".obsidian"}


class MarkdownSyncEngine:
    """Read, validate, index, and export canonical Obsidian Markdown notes."""

    def __init__(self, vault_root: Path):
        self.vault_root = Path(vault_root).expanduser()
        os.makedirs(self.vault_root, exist_ok=True)

    @staticmethod
    def parse_markdown(file_content: str) -> Tuple[Dict[str, Any], str]:
        pattern = r"^---\s*\n(.*?)\n---\s*\n?(.*)$"
        match = re.search(pattern, file_content, re.DOTALL)
        if not match:
            return {}, file_content.strip()
        yaml_str, body = match.group(1), match.group(2)
        try:
            frontmatter = yaml.safe_load(yaml_str) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Failed to parse YAML frontmatter: {exc}") from exc
        return frontmatter, body.strip()

    @staticmethod
    def format_markdown(frontmatter: Dict[str, Any], content: str) -> str:
        yaml_str = yaml.safe_dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return f"---\n{yaml_str}---\n\n{content.strip()}\n"

    def read_note(self, file_path: Path) -> Dict[str, Any]:
        raw = file_path.read_text(encoding="utf-8")
        frontmatter, content = self.parse_markdown(raw)
        validated = NoteFrontmatter.model_validate(frontmatter)
        note = validated.model_dump(mode="json")
        note["content"] = content
        return note

    def write_note_atomic(self, note_dict: Dict[str, Any], subfolder: Optional[str] = None, filename: Optional[str] = None) -> Path:
        data = dict(note_dict)
        content = data.pop("content", "")
        data.pop("raw_json", None)
        validated = NoteFrontmatter.model_validate(data)
        fm = validated.model_dump(mode="json")
        target_subfolder = subfolder or FOLDER_TYPE_MAP.get(fm.get("type"), "01_KNOWLEDGE")
        dest_dir = self.vault_root / target_subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe_name = filename or f"{fm.get('category', 'note')}_{fm['id'][:8]}.md"
        if not safe_name.endswith(".md"):
            safe_name += ".md"
        target = dest_dir / safe_name
        fd, tmp = tempfile.mkstemp(dir=dest_dir, prefix=".tmp_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(self.format_markdown(fm, content))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return target

    save_note_atomic = write_note_atomic

    def sync_vault_to_sqlite(self, sqlite_engine: SQLiteStorageEngine) -> int:
        count = 0
        for root, dirs, files in os.walk(self.vault_root):
            rel = os.path.relpath(root, self.vault_root)
            if rel != "." and rel.split(os.sep)[0] in EXCLUDED_FOLDERS:
                dirs[:] = []
                continue
            for file_name in files:
                if not file_name.endswith(".md") or file_name.startswith("."):
                    continue
                try:
                    note = self.read_note(Path(root) / file_name)
                    sqlite_engine.set_note_atomic(note)
                    count += 1
                except Exception:
                    continue
        return count

    def export_sqlite_to_vault(self, sqlite_engine: SQLiteStorageEngine) -> int:
        count = 0
        for note in sqlite_engine.query(limit=10000):
            if note.get("lifecycle") == Lifecycle.RAW.value:
                continue
            self.write_note_atomic(note)
            count += 1
        return count
