from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import mimetypes
import re
from typing import Any


_LEVEL_RE = re.compile(r"_level_(\d+)", re.IGNORECASE)
_NAMESPACE_LEVEL_RE = re.compile(r"^[A-Z]+_(\d+)$")


@dataclass(frozen=True)
class DataEntry:
    dataset_type: str
    data_format: str
    version: str
    filename: str
    relative_path: str
    absolute_path: Path
    size_bytes: int
    level: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.dataset_type,
            "format": self.data_format,
            "version": self.version,
            "filename": self.filename,
            "path": self.relative_path,
            "size_bytes": self.size_bytes,
        }
        if self.level is not None:
            payload["level"] = self.level
        return payload


def _normalize_type(raw_namespace: str) -> tuple[str, int | None]:
    upper = raw_namespace.upper()
    level: int | None = None

    if upper.startswith("NUTS"):
        dataset_type = "nuts"
    elif upper.startswith("LAU"):
        dataset_type = "lau"
    elif upper.startswith("LOR"):
        dataset_type = "lor"
    else:
        dataset_type = raw_namespace.lower()

    match = _NAMESPACE_LEVEL_RE.match(upper)
    if match:
        level = int(match.group(1))
    return dataset_type, level


def _extract_level(namespace_level: int | None, filename: str) -> int | None:
    if namespace_level is not None:
        return namespace_level
    match = _LEVEL_RE.search(filename)
    if match:
        return int(match.group(1))
    return None


def scan_catalog(data_root: Path) -> list[DataEntry]:
    if not data_root.exists():
        return []

    entries: list[DataEntry] = []
    for file_path in data_root.rglob("*"):
        if not file_path.is_file():
            continue

        rel_parts = file_path.relative_to(data_root).parts
        if len(rel_parts) < 4:
            continue

        data_format = rel_parts[0].lower()
        namespace = rel_parts[1]
        version = rel_parts[2]
        filename = rel_parts[-1]
        dataset_type, namespace_level = _normalize_type(namespace)
        level = _extract_level(namespace_level, filename)

        try:
            size_bytes = file_path.stat().st_size
        except OSError:
            size_bytes = 0

        entries.append(
            DataEntry(
                dataset_type=dataset_type,
                data_format=data_format,
                version=version,
                filename=filename,
                relative_path=str(file_path.relative_to(data_root)),
                absolute_path=file_path.resolve(),
                size_bytes=size_bytes,
                level=level,
            )
        )
    return sorted(
        entries,
        key=lambda e: (
            e.dataset_type,
            e.data_format,
            e.version,
            e.level if e.level is not None else -1,
            e.filename,
        ),
    )


def filter_entries(
    entries: list[DataEntry],
    *,
    dataset_type: str | None = None,
    data_format: str | None = None,
    version: str | None = None,
    level: int | None = None,
    filename: str | None = None,
) -> list[DataEntry]:
    filtered = entries
    if dataset_type is not None:
        filtered = [e for e in filtered if e.dataset_type == dataset_type.lower()]
    if data_format is not None:
        filtered = [e for e in filtered if e.data_format == data_format.lower()]
    if version is not None:
        filtered = [e for e in filtered if e.version == version]
    if level is not None:
        filtered = [e for e in filtered if e.level == level]
    if filename is not None:
        filtered = [e for e in filtered if e.filename == filename]
    return filtered


def mime_for_format(data_format: str, filename: str) -> str:
    fmt = data_format.lower()
    if fmt == "csv":
        return "text/csv"
    if fmt == "geojson":
        return "application/geo+json"

    guessed = mimetypes.guess_type(filename)[0]
    return guessed or "application/octet-stream"
