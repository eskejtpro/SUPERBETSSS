"""Live FIFA Analyzer — lokalny panel WWW i odbiornik danych live z Chrome."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


APP_DIR = Path(__file__).resolve().parent
WEB_DIR = APP_DIR / "web"
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "live_matches.sqlite3"
SETTINGS_PATH = DATA_DIR / "settings.json"
HOST, PORT = "127.0.0.1", 8765
MAX_BODY_BYTES = 1_000_000
DEFAULT_SETTINGS = {
    "ui_refresh_seconds": 5,
    "theme": "dark",
    "default_sort": "remaining",
    "compact_mode": False,
    "show_paused": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def remaining_seconds(match: dict[str, Any]) -> int | None:
    duration = parse_int(match.get("format_minutes"))
    clock = parse_int(match.get("clock_seconds"))
    half = parse_int(match.get("half"))
    if not duration or not half or clock is None:
        return None
    return max(duration * 60 - min(clock, duration * 60), 0)


def normalize_match(raw: dict[str, Any], observed_at: str) -> dict[str, Any]:
    home = str(raw.get("home") or "").strip()
    away = str(raw.get("away") or "").strip()
    if not home or not away:
        raise ValueError("Brak nazw drużyn")
    source_url = str(raw.get("url") or "").strip()
    match = {
        "key": f"{source_url}|{home}|{away}",
        "competition": str(raw.get("competition") or "e-Piłka nożna live").strip(),
        "format_minutes": parse_int(raw.get("formatMinutes")),
        "home": home,
        "away": away,
        "home_score": parse_int(raw.get("homeScore")),
        "away_score": parse_int(raw.get("awayScore")),
        "half": parse_int(raw.get("half")),
        "clock_seconds": parse_int(raw.get("clock")),
        "clock_label": str(raw.get("clockLabel") or ""),
        "status": str(raw.get("status") or "brak"),
        "source_url": source_url,
        "observed_at": observed_at,
    }
    match["remaining_seconds"] = remaining_seconds(match)
    match["score_label"] = (
        f"{match['home_score']}:{match['away_score']}"
        if match["home_score"] is not None and match["away_score"] is not None
        else "brak"
    )
    match["half_label"] = f"{match['half']}. połowa" if match["half"] else "brak"
    return match


class MatchDatabase:
    def __init__(self, path: Path) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        self.path = path
        with self.connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY,
                    observed_at TEXT NOT NULL,
                    match_key TEXT NOT NULL,
                    payload TEXT NOT NULL
                )"""
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_key_time ON snapshots(match_key, id DESC)")

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=5)

    def save_many(self, matches: list[dict[str, Any]]) -> None:
        if not matches:
            return
        rows = [
            (item["observed_at"], item["key"], json.dumps(item, ensure_ascii=False))
            for item in matches
        ]
        with self.connect() as connection:
            connection.executemany(
                "INSERT INTO snapshots(observed_at, match_key, payload) VALUES (?, ?, ?)", rows
            )

    def history(self, match_key: str, limit: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM snapshots WHERE match_key = ? ORDER BY id DESC LIMIT ?",
                (match_key, limit),
            ).fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]


class LiveState:
    def __init__(self, database: MatchDatabase) -> None:
        self.database = database
        self._lock = threading.Lock()
        self._matches: dict[str, dict[str, Any]] = {}
        self._analysis: dict[str, str] = {}
        self._received_at: str | None = None
        self._last_source_count = 0

    def ingest(self, raw_matches: list[dict[str, Any]]) -> int:
        received_at = utc_now()
        normalized: list[dict[str, Any]] = []
        for raw in raw_matches:
            if not isinstance(raw, dict):
                continue
            try:
                normalized.append(normalize_match(raw, received_at))
            except ValueError:
                continue
        with self._lock:
            previous = self._matches
            current = {item["key"]: item for item in normalized}
            self._analysis = {
                key: self._describe_change(item, previous.get(key))
                for key, item in current.items()
            }
            self._matches = current
            self._received_at = received_at
            self._last_source_count = len(raw_matches)
        self.database.save_many(normalized)
        return len(normalized)

    @staticmethod
    def _describe_change(match: dict[str, Any], old: dict[str, Any] | None) -> str:
        score = (
            f"{match['home_score']}:{match['away_score']}"
            if match["home_score"] is not None and match["away_score"] is not None
            else "brak wyniku"
        )
        base = f"{match['home']} — {match['away']}: {score}; {match['half'] or 'brak'}. połowa; czas {match['clock_label'] or 'brak'}."
        if old is None:
            return base + " Nowy mecz wykryty w źródle live."
        old_score = f"{old['home_score']}:{old['away_score']}"
        updates: list[str] = []
        if score != old_score:
            updates.append(f"wynik zmienił się z {old_score} na {score}")
        if match["half"] != old["half"]:
            updates.append("zmiana połowy")
        if match["status"] != old["status"]:
            updates.append(f"status: {match['status']}")
        return base + (" Zmiana: " + "; ".join(updates) + "." if updates else " Brak istotnej zmiany od poprzedniego odczytu.")

    def live_payload(self) -> dict[str, Any]:
        with self._lock:
            matches = []
            for match in self._matches.values():
                item = dict(match)
                item["analysis"] = self._analysis.get(item["key"], "Brak analizy.")
                matches.append(item)
            received_at = self._received_at
            source_count = self._last_source_count
        matches.sort(key=self._remaining_sort_key)
        return {
            "matches": matches,
            "count": len(matches),
            "source_count": source_count,
            "received_at": received_at,
            "source_interval_seconds": 20,
        }

    @staticmethod
    def _remaining_sort_key(match: dict[str, Any]) -> tuple[int, int, str]:
        seconds = match["remaining_seconds"]
        if seconds is not None:
            return (0, seconds, match["home"])
        phase = 0 if match["half"] == 2 else 1 if match["half"] == 1 else 2
        return (1, phase * 100_000 - (match["clock_seconds"] or 0), match["home"])


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._settings = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            saved = {}
        return {**DEFAULT_SETTINGS, **{key: saved[key] for key in DEFAULT_SETTINGS if key in saved}}

    def get(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._settings)

    def update(self, candidate: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "ui_refresh_seconds": lambda value: isinstance(value, int) and 2 <= value <= 60,
            "theme": lambda value: value in {"dark", "light"},
            "default_sort": lambda value: value in {"remaining", "clock", "name", "score"},
            "compact_mode": lambda value: isinstance(value, bool),
            "show_paused": lambda value: isinstance(value, bool),
        }
        with self._lock:
            for key, validator in allowed.items():
                if key in candidate and validator(candidate[key]):
                    self._settings[key] = candidate[key]
            self.path.write_text(json.dumps(self._settings, ensure_ascii=False, indent=2), encoding="utf-8")
            return dict(self._settings)


DATABASE = MatchDatabase(DB_PATH)
STATE = LiveState(DATABASE)
SETTINGS = SettingsStore(SETTINGS_PATH)


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "LiveFifaAnalyzer/0.2"

    def log_message(self, *_: Any) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/live":
            self.respond_json(STATE.live_payload())
        elif parsed.path == "/api/health":
            payload = STATE.live_payload()
            self.respond_json({"ok": True, "received_at": payload["received_at"], "match_count": payload["count"]})
        elif parsed.path == "/api/history":
            query = parse_qs(parsed.query)
            key = query.get("match_key", [""])[0]
            try:
                limit = min(max(int(query.get("limit", ["30"])[0]), 1), 100)
            except ValueError:
                limit = 30
            self.respond_json({"history": DATABASE.history(key, limit) if key else []})
        elif parsed.path == "/api/settings":
            self.respond_json(SETTINGS.get())
        elif parsed.path == "/api/export.json":
            self.respond_json(STATE.live_payload(), attachment="live-matches.json")
        elif parsed.path == "/api/export.csv":
            self.respond_csv(STATE.live_payload()["matches"])
        else:
            self.serve_static(parsed.path)

    def do_PUT(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/settings":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            self.respond_json(SETTINGS.update(self.read_json()))
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Niepoprawne ustawienia")

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/snapshot":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self.read_json()
            matches = payload["matches"]
            if not isinstance(matches, list):
                raise ValueError
            accepted = STATE.ingest(matches)
            self.respond_json({"accepted": accepted}, status=HTTPStatus.ACCEPTED)
        except (KeyError, ValueError, TypeError):
            self.send_error(HTTPStatus.BAD_REQUEST, "Niepoprawna migawka")

    def read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError from error
        if not 0 < length <= MAX_BODY_BYTES:
            raise ValueError
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as error:
            raise ValueError from error
        if not isinstance(payload, dict):
            raise ValueError
        return payload

    def respond_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK, attachment: str | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        self.wfile.write(body)

    def respond_csv(self, matches: list[dict[str, Any]]) -> None:
        buffer = io.StringIO()
        fields = ["competition", "home", "away", "home_score", "away_score", "half", "clock_label", "format_minutes", "status", "observed_at"]
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader(); writer.writerows(matches)
        body = buffer.getvalue().encode("utf-8-sig")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", 'attachment; filename="live-matches.csv"')
        self.end_headers(); self.wfile.write(body)

    def serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        candidate = (WEB_DIR / relative).resolve()
        if WEB_DIR.resolve() not in candidate.parents and candidate != WEB_DIR.resolve():
            self.send_error(HTTPStatus.NOT_FOUND); return
        if not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND); return
        content_types = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_types.get(candidate.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)


def main() -> None:
    if not WEB_DIR.is_dir():
        raise RuntimeError("Brakuje katalogu web z panelem lokalnym.")
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"Live FIFA Analyzer działa pod {url}")
    webbrowser.open(url, new=1)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
