from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, request, send_file, url_for

from .catalog import DataEntry, filter_entries, mime_for_format, scan_catalog

SUPPORTED_TYPES = ("nuts", "lau")


def _parse_level(raw_level: str | None) -> tuple[int | None, str | None]:
    if raw_level is None:
        return None, None
    try:
        return int(raw_level), None
    except ValueError:
        return None, "Query parameter 'level' muss eine ganze Zahl sein."


def _validate_type(raw_type: str | None) -> tuple[str | None, str | None]:
    if raw_type is None:
        return None, None
    normalized = raw_type.lower()
    if normalized not in SUPPORTED_TYPES:
        return None, f"Unsupported type '{raw_type}'. Erlaubt: {', '.join(SUPPORTED_TYPES)}."
    return normalized, None


def _serialize_entry(entry: DataEntry) -> dict:
    payload = entry.to_dict()
    payload["download_url"] = url_for(
        "get_data",
        dataset_type=entry.dataset_type,
        data_format=entry.data_format,
        version=entry.version,
        level=entry.level,
        filename=entry.filename,
        _external=False,
    )
    return payload


def create_app() -> Flask:
    app = Flask(__name__)
    base_dir = Path(__file__).resolve().parent.parent
    data_root = Path(os.getenv("DATA_ROOT", str(base_dir / "geodata_clean"))).resolve()
    catalog = scan_catalog(data_root)

    @app.get("/health")
    def health() -> tuple[dict, int]:
        return {
            "status": "ok",
            "data_root": str(data_root),
            "files_indexed": len(catalog),
        }, 200

    @app.get("/api/v1/meta")
    def meta() -> tuple[dict, int]:
        available_types = sorted({e.dataset_type for e in catalog})
        available_formats = sorted({e.data_format for e in catalog})
        versions_by_type: dict[str, list[str]] = {}
        for dataset_type in sorted(set(available_types + list(SUPPORTED_TYPES))):
            versions_by_type[dataset_type] = sorted(
                {e.version for e in catalog if e.dataset_type == dataset_type}
            )

        return {
            "supported_types": list(SUPPORTED_TYPES),
            "available_types": available_types,
            "available_formats": available_formats,
            "versions_by_type": versions_by_type,
        }, 200

    @app.get("/api/v1/catalog")
    def get_catalog() -> tuple[dict, int]:
        dataset_type, type_error = _validate_type(request.args.get("type"))
        if type_error:
            return {"error": type_error}, 400

        raw_level = request.args.get("level")
        level, level_error = _parse_level(raw_level)
        if level_error:
            return {"error": level_error}, 400

        filtered = filter_entries(
            catalog,
            dataset_type=dataset_type,
            data_format=request.args.get("format"),
            version=request.args.get("version"),
            level=level,
            filename=request.args.get("filename"),
        )
        return {"count": len(filtered), "items": [_serialize_entry(e) for e in filtered]}, 200

    @app.get("/api/v1/versions/<dataset_type>/<data_format>")
    def versions(dataset_type: str, data_format: str) -> tuple[dict, int]:
        normalized_type, type_error = _validate_type(dataset_type)
        if type_error:
            return {"error": type_error}, 400

        entries = filter_entries(
            catalog,
            dataset_type=normalized_type,
            data_format=data_format.lower(),
        )
        versions_list = sorted({e.version for e in entries})
        levels_list = sorted({e.level for e in entries if e.level is not None})
        return {
            "type": normalized_type,
            "format": data_format.lower(),
            "versions": versions_list,
            "levels": levels_list,
            "count": len(entries),
        }, 200

    @app.get("/api/v1/data/<dataset_type>/<data_format>/<version>")
    def get_data(dataset_type: str, data_format: str, version: str):
        normalized_type, type_error = _validate_type(dataset_type)
        if type_error:
            return {"error": type_error}, 400

        raw_level = request.args.get("level")
        level, level_error = _parse_level(raw_level)
        if level_error:
            return {"error": level_error}, 400

        matches = filter_entries(
            catalog,
            dataset_type=normalized_type,
            data_format=data_format.lower(),
            version=version,
            level=level,
            filename=request.args.get("filename"),
        )
        if not matches:
            return {
                "error": "Keine Datei gefunden.",
                "hint": "Pruefe type/format/version/level in /api/v1/catalog.",
            }, 404

        if len(matches) > 1:
            return {
                "error": "Mehrere Dateien gefunden.",
                "hint": "Fuege 'level' oder 'filename' als Query-Parameter hinzu.",
                "matches": [_serialize_entry(e) for e in matches],
            }, 409

        entry = matches[0]
        return send_file(
            entry.absolute_path,
            as_attachment=True,
            download_name=entry.filename,
            mimetype=mime_for_format(entry.data_format, entry.filename),
        )

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    app.run(host=host, port=port, debug=False)
