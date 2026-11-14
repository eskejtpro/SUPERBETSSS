"""Live FIFA Analyzer — lokalny panel WWW i odbiornik danych live z Chrome."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
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
    "ui_refresh_seconds": 20,
    "theme": "dark",
    "default_sort": "remaining",
    "compact_mode": False,
    "show_paused": True,
    "highlight_enabled": True,
    "highlight_goal_difference": 3,
    "highlight_remaining_seconds": 90,
    "highlight_row_tint": True,
    "highlight_color": "#dc2626",
    "potential_enabled": True,
    "potential_goal_difference": 2,
    "potential_remaining_seconds": 300,
    "potential_min_total_goals": 2,
    "potential_color": "#f59e0b",
    "high_scoring_enabled": True,
    "high_scoring_min_goals": 5,
    "high_scoring_color": "#8b5cf6",
    "close_finish_enabled": True,
    "close_finish_remaining_seconds": 120,
    "close_finish_color": "#0ea5e9",
    "notify_enabled": True,
    "notify_potential": True,
    "notify_primary": True,
    "notify_high_scoring": False,
    "notify_close_finish": False,
    "notify_sound": True,
    "notify_cooldown_seconds": 120,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def remaining_seconds(match: dict[str, Any]) -> int | None:
    total_minutes = parse_int(match.get("format_minutes"))
    clock = parse_int(match.get("clock_seconds"))
    half = parse_int(match.get("half"))
    if total_minutes is None or total_minutes <= 0 or total_minutes % 2:
        return None
    if half not in (1, 2) or clock is None or clock < 0:
        return None
    half_seconds = (total_minutes // 2) * 60
    if clock > half_seconds:
        return None
    regular = max((2 - half) * half_seconds + (half_seconds - clock), 0)
    added = max(0, parse_int(match.get("added_time_seconds")) or 0)
    break_seconds = max(0, parse_int(match.get("break_seconds")) or 0)
    return regular + added + (break_seconds if half == 1 else 0)


def match_is_expired(match: dict[str, Any], now: datetime | None = None) -> bool:
    """Return True when the estimated match end has passed since its last source snapshot."""
    remaining = parse_int(match.get("remaining_seconds"))
    if remaining is None:
        return False
    if remaining <= 0:
        return True
    try:
        observed = datetime.fromisoformat(str(match.get("observed_at") or ""))
    except ValueError:
        return False
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    elapsed = max(0.0, (current - observed).total_seconds())
    return elapsed >= remaining


def normalize_match(raw: dict[str, Any], observed_at: str) -> dict[str, Any]:
    home = str(raw.get("home") or "").strip()
    away = str(raw.get("away") or "").strip()
    if not home or not away:
        raise ValueError("Brak nazw drużyn")
    source_url = str(raw.get("url") or "").strip()
    half = parse_int(raw.get("half"))
    clock_seconds = parse_int(raw.get("clock"))
    if half not in (1, 2) or clock_seconds is None or clock_seconds < 0:
        raise ValueError("Spotkanie nie ma potwierdzonego statusu LIVE")
    match = {
        "key": f"{source_url}|{home}|{away}",
        "competition": str(raw.get("competition") or "e-Piłka nożna live").strip(),
        "format_minutes": parse_int(raw.get("formatMinutes")),
        "home": home,
        "away": away,
        "home_score": parse_int(raw.get("homeScore")),
        "away_score": parse_int(raw.get("awayScore")),
        "half": half,
        "clock_seconds": clock_seconds,
        "clock_label": str(raw.get("clockLabel") or ""),
        "status": str(raw.get("status") or "aktywny"),
        "is_live": True,
        "source_url": source_url,
        "observed_at": observed_at,
        "added_time_seconds": max(0, parse_int(raw.get("addedTimeSeconds", raw.get("addedTime", raw.get("extraSeconds")))) or 0),
        "break_seconds": max(0, parse_int(raw.get("breakSeconds", raw.get("halftimeBreakSeconds"))) or 0),
        "added_time_note": str(raw.get("addedTimeNote") or "").strip(),
    }
    match["remaining_seconds"] = remaining_seconds(match)
    observed_dt = datetime.fromisoformat(observed_at)
    half_seconds = (match["format_minutes"] // 2) * 60 if match["format_minutes"] and match["format_minutes"] > 0 and match["format_minutes"] % 2 == 0 else 0
    elapsed_from_start = ((half - 1) * half_seconds + min(clock_seconds, half_seconds) + (match["break_seconds"] if half == 2 else 0)) if half_seconds else clock_seconds
    match["started_at"] = str(raw.get("startedAt") or (observed_dt - timedelta(seconds=elapsed_from_start)).isoformat())
    match["estimated_end_at"] = (observed_dt + timedelta(seconds=match["remaining_seconds"])).isoformat() if match["remaining_seconds"] is not None else None
    if not match["added_time_note"]:
        note_parts = []
        if match["added_time_seconds"]:
            note_parts.append(f"Doliczony czas: +{match['added_time_seconds']} s")
        if match["break_seconds"]:
            note_parts.append(f"Przerwa w połowie: {match['break_seconds']} s")
        match["added_time_note"] = " · ".join(note_parts) if note_parts else "Brak doliczonego czasu i przerw"
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
        now = datetime.now(timezone.utc)
        with self._lock:
            matches = []
            for match in self._matches.values():
                if match_is_expired(match, now):
                    continue
                item = dict(match)
                item["analysis"] = self._analysis.get(item["key"], "Brak analizy.")
                matches.append(item)
            received_at = self._received_at
            source_count = self._last_source_count
        for item in matches:
            history = self.database.history(item["key"], 100)
            for index in range(len(history) - 1, 0, -1):
                current, previous = history[index], history[index - 1]
                if current.get("home_score") is None or previous.get("home_score") is None or current.get("away_score") is None or previous.get("away_score") is None:
                    continue
                if current["home_score"] > previous["home_score"]:
                    item["last_scorer_side"] = "home"
                    break
                if current["away_score"] > previous["away_score"]:
                    item["last_scorer_side"] = "away"
                    break
            else:
                item["last_scorer_side"] = None
        matches.sort(key=self._remaining_sort_key)
        age_seconds = None
        if received_at:
            try:
                observed = datetime.fromisoformat(received_at)
                age_seconds = max(0, int((now - observed).total_seconds()))
            except (TypeError, ValueError):
                age_seconds = None
        source_online = age_seconds is not None and age_seconds <= 50
        if not source_online:
            matches = []
        return {
            "matches": matches,
            "count": len(matches),
            "source_count": source_count,
            "received_at": received_at,
            "source_age_seconds": age_seconds,
            "source_online": source_online,
            "source_status": "online" if source_online else ("stale" if received_at else "waiting"),
            "source_interval_seconds": 20,
            "server_time": utc_now(),
            "superbet_time": None,
            "superbet_time_label": None,
        }

    @staticmethod
    def _remaining_sort_key(match: dict[str, Any]) -> tuple[int, int, str, str]:
        seconds = match.get("remaining_seconds")
        if seconds is not None:
            return (0, seconds, str(match.get("home") or "").casefold(), str(match.get("key") or ""))
        return (1, 2**31 - 1, str(match.get("home") or "").casefold(), str(match.get("key") or ""))


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
        settings = {**DEFAULT_SETTINGS, **{key: saved[key] for key in DEFAULT_SETTINGS if key in saved}}
        settings["ui_refresh_seconds"] = 20
        return settings

    def get(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._settings)

    def update(self, candidate: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "ui_refresh_seconds": lambda value: value == 20,
            "theme": lambda value: value in {"dark", "light"},
            "default_sort": lambda value: value in {"remaining", "clock", "name", "score"},
            "compact_mode": lambda value: isinstance(value, bool),
            "show_paused": lambda value: isinstance(value, bool),
            "highlight_enabled": lambda value: isinstance(value, bool),
            "highlight_goal_difference": lambda value: isinstance(value, int) and 1 <= value <= 10,
            "highlight_remaining_seconds": lambda value: type(value) is int and 15 <= value <= 600,
            "highlight_row_tint": lambda value: isinstance(value, bool),
            "highlight_color": lambda value: isinstance(value, str) and len(value) == 7 and value.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in value[1:]),
            "potential_enabled": lambda value: isinstance(value, bool),
            "potential_goal_difference": lambda value: type(value) is int and 1 <= value <= 9,
            "potential_remaining_seconds": lambda value: type(value) is int and 30 <= value <= 1200,
            "potential_min_total_goals": lambda value: type(value) is int and 0 <= value <= 20,
            "potential_color": lambda value: isinstance(value, str) and len(value) == 7 and value.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in value[1:]),
            "high_scoring_enabled": lambda value: isinstance(value, bool),
            "high_scoring_min_goals": lambda value: type(value) is int and 2 <= value <= 20,
            "high_scoring_color": lambda value: isinstance(value, str) and len(value) == 7 and value.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in value[1:]),
            "close_finish_enabled": lambda value: isinstance(value, bool),
            "close_finish_remaining_seconds": lambda value: type(value) is int and 15 <= value <= 600,
            "close_finish_color": lambda value: isinstance(value, str) and len(value) == 7 and value.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in value[1:]),
            "notify_enabled": lambda value: isinstance(value, bool),
            "notify_potential": lambda value: isinstance(value, bool),
            "notify_primary": lambda value: isinstance(value, bool),
            "notify_high_scoring": lambda value: isinstance(value, bool),
            "notify_close_finish": lambda value: isinstance(value, bool),
            "notify_sound": lambda value: isinstance(value, bool),
            "notify_cooldown_seconds": lambda value: type(value) is int and 0 <= value <= 3600,
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
        fields = ["competition", "home", "away", "home_score", "away_score", "half", "clock_label", "format_minutes", "added_time_seconds", "break_seconds", "started_at", "estimated_end_at", "status", "observed_at"]
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
