from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import sqlite3
import textwrap
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default as email_policy_default
from html import escape
from http.cookies import SimpleCookie
from pathlib import Path
from random import Random
from secrets import token_hex

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
TMP_DIR = ROOT / "tmp"
DATA_DIR = TMP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "bingo.sqlite3"
GRID_SIZE = 5
MIN_QUESTIONS = GRID_SIZE * GRID_SIZE
MAX_PLATES = 100
DEFAULT_PLATE_COUNT = 22
SESSION_COOKIE_NAME = "bingo_session"
AUTH_COOKIE_NAME = "bingo_auth"
SESSION_MAX_AGE = 60 * 60 * 24 * 14
AUTH_MAX_AGE = 60 * 10
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MICROSOFT_OPENID_CONFIGURATION_URL = "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
MICROSOFT_AUTH_SCOPES = "openid profile email"
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
PDF_CAMERA_MARK = "\ue000"
PDF_VEHICLE_MARK = "\ue001"
PDF_DRINK_MARK = "\ue002"
PDF_MUSIC_MARK = "\ue003"
PDF_MONEY_MARK = "\ue004"
PDF_MAGNET_MARK = "\ue005"
PDF_TRANSIT_MARK = "\ue006"
PDF_SELFIE_MARK = "\ue007"
PDF_SCREEN_MARK = "\ue008"
PDF_SPORT_MARK = "\ue009"
PDF_GENERIC_MARK = "\ue00a"
PDF_ICON_MARKERS = {
    PDF_CAMERA_MARK,
    PDF_VEHICLE_MARK,
    PDF_DRINK_MARK,
    PDF_MUSIC_MARK,
    PDF_MONEY_MARK,
    PDF_MAGNET_MARK,
    PDF_TRANSIT_MARK,
    PDF_SELFIE_MARK,
    PDF_SCREEN_MARK,
    PDF_SPORT_MARK,
    PDF_GENERIC_MARK,
}
PDF_ICON_PATTERN_NAMES = {
    PDF_CAMERA_MARK: "camera",
    PDF_VEHICLE_MARK: "vehicle",
    PDF_DRINK_MARK: "drink",
    PDF_MUSIC_MARK: "music",
    PDF_MONEY_MARK: "money",
    PDF_MAGNET_MARK: "magnet",
    PDF_TRANSIT_MARK: "transit",
    PDF_SELFIE_MARK: "selfie",
    PDF_SCREEN_MARK: "screen",
    PDF_SPORT_MARK: "sport",
    PDF_GENERIC_MARK: "generic",
}
PDF_ICON_PATTERNS = {
    "camera": [
        "................",
        "....######......",
        "..##########....",
        ".############...",
        ".##..####..##...",
        ".##.######.##...",
        ".##.######.##...",
        ".##..####..##...",
        ".############...",
        "..##########....",
        "....######......",
        "................",
    ],
    "vehicle": [
        "................",
        "................",
        "...##########...",
        "..############..",
        ".##############.",
        ".##..######..##.",
        "################",
        "################",
        "..##........##..",
        ".####......####.",
        ".####......####.",
        "................",
    ],
    "drink": [
        "................",
        "..##........##..",
        "...##......##...",
        "....##....##....",
        ".....######.....",
        "......####......",
        ".......##.......",
        ".......##.......",
        "......####......",
        ".....######.....",
        "................",
        "................",
    ],
    "music": [
        ".........###....",
        ".........###....",
        ".........###....",
        ".........#####..",
        ".........#####..",
        "....###..###....",
        "...#####.###....",
        "...#####.###....",
        "....###..###....",
        "..........###...",
        "................",
        "................",
    ],
    "money": [
        "................",
        "..############..",
        ".##############.",
        ".##..........##.",
        ".##..######..##.",
        ".##..##..##..##.",
        ".##..######..##.",
        ".##..........##.",
        ".##############.",
        "..############..",
        "................",
        "................",
    ],
    "magnet": [
        "....##....##....",
        "...####..####...",
        "...####..####...",
        "...####..####...",
        "...####..####...",
        "...####..####...",
        "...##########...",
        "....########....",
        ".....######.....",
        "......####......",
        "................",
        "................",
    ],
    "transit": [
        "................",
        "...##########...",
        "..############..",
        "..##..##..##....",
        "..##..##..##....",
        "..############..",
        "..############..",
        "..############..",
        "...##......##...",
        "..####....####..",
        "................",
        "................",
    ],
    "selfie": [
        ".....####.......",
        "....######......",
        "....######......",
        "....######......",
        "....######......",
        "....######......",
        ".....#######....",
        ".......######...",
        "........#####...",
        ".........###....",
        "................",
        "................",
    ],
    "screen": [
        "................",
        ".##############.",
        ".##..........##.",
        ".##..######..##.",
        ".##..#....#..##.",
        ".##..######..##.",
        ".##..........##.",
        ".##############.",
        ".....######.....",
        "....########....",
        "................",
        "................",
    ],
    "sport": [
        "................",
        ".....######.....",
        "....########....",
        "...###.##.###...",
        "...##.####.##...",
        "...##.####.##...",
        "...###.##.###...",
        "....########....",
        ".....######.....",
        "................",
        "................",
        "................",
    ],
    "generic": [
        "................",
        "....###..###....",
        "....###..###....",
        "................",
        "......####......",
        ".....######.....",
        ".....######.....",
        "......####......",
        "................",
        "....###..###....",
        "....###..###....",
        "................",
    ],
}
_OIDC_CONFIGURATION_CACHE: dict[str, object] | None = None
_OIDC_CONFIGURATION_FETCHED_AT = 0.0


def application(environ, start_response):
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    path = environ.get("PATH_INFO") or "/"
    method = (environ.get("REQUEST_METHOD") or "GET").upper()
    conn = _connect_db()

    try:
        user = _get_current_user(environ, conn)

        if path.startswith("/static/"):
            return _serve_static(path, start_response)

        if path.startswith("/media/"):
            return _handle_media_request(environ, start_response, conn, user)

        if path == "/auth/login":
            return _handle_auth_login(environ, start_response)

        if path == "/auth/callback":
            return _handle_auth_callback(environ, start_response, conn)

        if path == "/auth/logout":
            return _handle_auth_logout(environ, start_response, script_name)

        if path == "/api/boards":
            if method != "POST":
                return _respond_json_error(start_response, "Method not allowed", status="405 Method Not Allowed")
            return _handle_generate_boards(environ, start_response)

        if path == "/api/export.pdf":
            if method != "POST":
                return _respond_json_error(start_response, "Method not allowed", status="405 Method Not Allowed")
            return _handle_export_pdf(environ, start_response)

        if path == "/manage":
            guard = _require_admin(environ, start_response, user, script_name)
            if guard is not None:
                return guard
            return _respond_html(start_response, _render_manage_page(environ, conn, user))

        if path == "/manage/create":
            guard = _require_admin(environ, start_response, user, script_name)
            if guard is not None:
                return guard
            if method != "POST":
                return _redirect(start_response, _join_base(script_name, "/manage"))
            return _handle_manage_create(environ, start_response, conn, user)

        if path == "/my-plate":
            guard = _require_authenticated(environ, start_response, user, script_name)
            if guard is not None:
                return guard
            return _respond_html(start_response, _render_player_page(environ, conn, user))

        if path == "/plate/update":
            guard = _require_authenticated(environ, start_response, user, script_name)
            if guard is not None:
                return guard
            if method != "POST":
                return _redirect(start_response, _join_base(script_name, "/my-plate"))
            return _handle_plate_update(environ, start_response, conn, user)

        if path == "/":
            if user:
                destination = "/manage" if user["is_admin"] else "/my-plate"
                return _redirect(start_response, _join_base(script_name, destination))
            return _respond_html(start_response, _render_landing_page(environ))

        return _respond_not_found(start_response, script_name, user=user)
    finally:
        conn.close()


def _connect_db() -> sqlite3.Connection:
    _ensure_storage()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            microsoft_sub TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            last_login_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignee_email TEXT NOT NULL,
            assignee_name TEXT NOT NULL DEFAULT '',
            created_by_user_id INTEGER,
            generation_seed TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(created_by_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS plate_cells (
            plate_id INTEGER NOT NULL,
            cell_index INTEGER NOT NULL,
            label TEXT NOT NULL,
            is_checked INTEGER NOT NULL DEFAULT 0,
            image_path TEXT,
            updated_at TEXT,
            PRIMARY KEY (plate_id, cell_index),
            FOREIGN KEY(plate_id) REFERENCES plates(id) ON DELETE CASCADE
        );
        """
    )
    return conn


def _ensure_storage() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _serve_static(path: str, start_response):
    file_path = (ROOT / path.lstrip("/")).resolve()
    if STATIC_DIR not in file_path.parents or not file_path.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not found"]

    content_type, _ = mimetypes.guess_type(file_path.name)
    start_response("200 OK", [("Content-Type", content_type or "application/octet-stream")])
    return [file_path.read_bytes()]


def _handle_generate_boards(environ, start_response):
    try:
        request_payload = _read_json_body(environ)
        response_payload = _build_generation_payload(request_payload)
    except ValueError as exc:
        return _respond_json_error(start_response, str(exc))

    return _respond_json(start_response, response_payload)


def _handle_export_pdf(environ, start_response):
    try:
        request_payload = _read_json_body(environ)
        response_payload = _build_generation_payload(request_payload)
    except ValueError as exc:
        return _respond_json_error(start_response, str(exc))

    pdf_bytes = _build_pdf_document(response_payload["boards"])
    filename = f'bingo-plates-{response_payload["count"]}.pdf'
    start_response(
        "200 OK",
        [
            ("Content-Type", "application/pdf"),
            ("Content-Disposition", f'attachment; filename="{filename}"'),
            ("Cache-Control", "no-store"),
            ("Content-Length", str(len(pdf_bytes))),
        ],
    )
    return [pdf_bytes]


def _handle_auth_login(environ, start_response):
    if not _auth_is_configured():
        return _respond_html(
            start_response,
            _render_message_page(environ, "Authentication is not configured", "Set the Microsoft app credentials and session secret before signing in."),
            status="500 Internal Server Error",
        )

    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    query = _read_query_params(environ)
    next_path = _normalize_next_path(query.get("next", ["/"])[0] or "/")
    state = token_hex(16)
    nonce = token_hex(16)
    cookie_value = _encode_signed_payload({"state": state, "nonce": nonce, "next": next_path})
    oidc_config = _get_oidc_configuration()
    authorize_params = {
        "client_id": _required_setting("BINGO_MS_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": _absolute_app_url(environ, "/auth/callback"),
        "response_mode": "query",
        "scope": MICROSOFT_AUTH_SCOPES,
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",
    }
    location = f"{oidc_config['authorization_endpoint']}?{urllib.parse.urlencode(authorize_params)}"
    cookie_header = _build_cookie_header(AUTH_COOKIE_NAME, cookie_value, max_age=AUTH_MAX_AGE)
    return _redirect(start_response, location, extra_headers=[("Set-Cookie", cookie_header)])


def _handle_auth_callback(environ, start_response, conn: sqlite3.Connection):
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    query = _read_query_params(environ)
    if query.get("error"):
        message = query.get("error_description", [query["error"][0]])[0]
        return _respond_html(start_response, _render_message_page(environ, "Sign-in failed", message), status="400 Bad Request")

    code = query.get("code", [""])[0]
    state = query.get("state", [""])[0]
    auth_cookie = _get_signed_cookie(environ, AUTH_COOKIE_NAME, AUTH_MAX_AGE)
    if not code or not state or not auth_cookie or auth_cookie.get("state") != state:
        return _respond_html(start_response, _render_message_page(environ, "Sign-in failed", "The Microsoft login state could not be verified."), status="400 Bad Request")

    oidc_config = _get_oidc_configuration()
    token_payload = _post_form(
        str(oidc_config["token_endpoint"]),
        {
            "client_id": _required_setting("BINGO_MS_CLIENT_ID"),
            "client_secret": _required_setting("BINGO_MS_CLIENT_SECRET"),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _absolute_app_url(environ, "/auth/callback"),
            "scope": MICROSOFT_AUTH_SCOPES,
        },
    )
    access_token = str(token_payload.get("access_token") or "")
    if not access_token:
        return _respond_html(start_response, _render_message_page(environ, "Sign-in failed", "Microsoft did not return an access token."), status="400 Bad Request")

    userinfo = _fetch_json(
        str(oidc_config["userinfo_endpoint"]),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    id_token_claims = _decode_jwt_claims(str(token_payload.get("id_token") or ""))
    expected_nonce = str(auth_cookie.get("nonce") or "")
    if expected_nonce and id_token_claims and str(id_token_claims.get("nonce") or "") not in {"", expected_nonce}:
        return _respond_html(start_response, _render_message_page(environ, "Sign-in failed", "The returned Microsoft identity token did not match the login request."), status="400 Bad Request")

    identifier = _normalize_identifier(
        str(userinfo.get("email") or userinfo.get("preferred_username") or id_token_claims.get("email") or id_token_claims.get("preferred_username") or userinfo.get("sub") or "")
    )
    display_name = str(userinfo.get("name") or id_token_claims.get("name") or identifier or "Microsoft user")
    microsoft_sub = str(userinfo.get("sub") or id_token_claims.get("sub") or "")
    if not identifier or not microsoft_sub:
        return _respond_html(start_response, _render_message_page(environ, "Sign-in failed", "The Microsoft account did not provide a stable identifier."), status="400 Bad Request")

    user = _upsert_user(conn, microsoft_sub=microsoft_sub, email=identifier, display_name=display_name)
    session_cookie = _build_cookie_header(SESSION_COOKIE_NAME, _encode_signed_payload({"user_id": user["id"]}), max_age=SESSION_MAX_AGE)
    clear_auth_cookie = _build_cookie_header(AUTH_COOKIE_NAME, "", max_age=0)
    next_path = _normalize_next_path(str(auth_cookie.get("next") or "/"))
    return _redirect(
        start_response,
        _join_base(script_name, next_path),
        extra_headers=[("Set-Cookie", session_cookie), ("Set-Cookie", clear_auth_cookie)],
    )


def _handle_auth_logout(environ, start_response, script_name: str):
    clear_session = _build_cookie_header(SESSION_COOKIE_NAME, "", max_age=0)
    clear_auth = _build_cookie_header(AUTH_COOKIE_NAME, "", max_age=0)
    return _redirect(start_response, _join_base(script_name, "/"), extra_headers=[("Set-Cookie", clear_session), ("Set-Cookie", clear_auth)])


def _handle_manage_create(environ, start_response, conn: sqlite3.Connection, user: sqlite3.Row):
    try:
        form = _read_urlencoded_form(environ)
        questions_text = form.get("questions_text", "")
        assignees_text = form.get("assignees_text", "")
        questions = _normalize_questions(questions_text)
        assignees = _normalize_assignees(assignees_text)
        generation_seed = token_hex(8)
        boards = _generate_boards(questions, len(assignees), generation_seed)
        for assignee, board in zip(assignees, boards):
            _create_plate(conn, assignee, board, user["id"], generation_seed)
        conn.commit()
    except ValueError as exc:
        return _respond_html(
            start_response,
            _render_manage_page(
                environ,
                conn,
                user,
                form_values={"questions_text": form.get("questions_text", ""), "assignees_text": form.get("assignees_text", "")},
                error_message=str(exc),
            ),
            status="400 Bad Request",
        )

    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    return _redirect(start_response, _join_base(script_name, f"/manage?created={len(assignees)}"))


def _handle_plate_update(environ, start_response, conn: sqlite3.Connection, user: sqlite3.Row):
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    try:
        fields, files = _read_multipart_form(environ)
        plate_id = int(fields.get("plate_id", "0"))
        cell_index = int(fields.get("cell_index", "-1"))
        checked = fields.get("checked", "0") == "1"
        clear_image = fields.get("clear_image", "0") == "1"
    except (TypeError, ValueError):
        return _redirect(start_response, _join_base(script_name, "/my-plate?error=1"))

    plate = conn.execute(
        "SELECT * FROM plates WHERE id = ?",
        (plate_id,),
    ).fetchone()
    if not plate:
        return _redirect(start_response, _join_base(script_name, "/my-plate?error=1"))

    if _normalize_identifier(plate["assignee_email"]) != _normalize_identifier(user["email"]) and not user["is_admin"]:
        return _respond_html(start_response, _render_message_page(environ, "Access denied", "You can only update your own assigned plate."), status="403 Forbidden")

    cell = conn.execute(
        "SELECT * FROM plate_cells WHERE plate_id = ? AND cell_index = ?",
        (plate_id, cell_index),
    ).fetchone()
    if not cell:
        return _redirect(start_response, _join_base(script_name, "/my-plate?error=1"))

    new_image_path = cell["image_path"]
    upload_item = files.get("image")

    try:
        if clear_image and cell["image_path"]:
            _delete_upload_file(str(cell["image_path"]))
            new_image_path = None

        if upload_item is not None and upload_item.get("filename"):
            if new_image_path:
                _delete_upload_file(str(new_image_path))
            new_image_path = _store_uploaded_image(upload_item, plate_id, cell_index)
    except ValueError:
        return _redirect(start_response, _join_base(script_name, "/my-plate?error=1"))

    conn.execute(
        "UPDATE plate_cells SET is_checked = ?, image_path = ?, updated_at = ? WHERE plate_id = ? AND cell_index = ?",
        (1 if checked else 0, new_image_path, _utc_now(), plate_id, cell_index),
    )
    conn.commit()
    return _redirect(start_response, _join_base(script_name, "/my-plate?saved=1"))


def _handle_media_request(environ, start_response, conn: sqlite3.Connection, user: sqlite3.Row | None):
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    if user is None:
        return _redirect_to_login(environ, start_response, script_name)

    path = environ.get("PATH_INFO") or "/"
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) != 3 or parts[0] != "media":
        return _respond_not_found(start_response, script_name, user=user)

    try:
        plate_id = int(parts[1])
        cell_index = int(parts[2])
    except ValueError:
        return _respond_not_found(start_response, script_name, user=user)

    row = conn.execute(
        """
        SELECT p.assignee_email, c.image_path
        FROM plate_cells c
        JOIN plates p ON p.id = c.plate_id
        WHERE c.plate_id = ? AND c.cell_index = ?
        """,
        (plate_id, cell_index),
    ).fetchone()
    if not row or not row["image_path"]:
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not found"]

    if _normalize_identifier(row["assignee_email"]) != _normalize_identifier(user["email"]) and not user["is_admin"]:
        return _respond_html(start_response, _render_message_page(environ, "Access denied", "You cannot view this submission."), status="403 Forbidden")

    file_path = UPLOAD_DIR / str(row["image_path"])
    if not file_path.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not found"]

    content_type, _ = mimetypes.guess_type(file_path.name)
    start_response(
        "200 OK",
        [
            ("Content-Type", content_type or "application/octet-stream"),
            ("Cache-Control", "private, max-age=60"),
            ("Content-Length", str(file_path.stat().st_size)),
        ],
    )
    return [file_path.read_bytes()]


def _get_current_user(environ, conn: sqlite3.Connection) -> sqlite3.Row | None:
    payload = _get_signed_cookie(environ, SESSION_COOKIE_NAME, SESSION_MAX_AGE)
    if not payload:
        return None
    user_id = int(payload.get("user_id") or 0)
    if user_id <= 0:
        return None
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def _upsert_user(conn: sqlite3.Connection, microsoft_sub: str, email: str, display_name: str) -> sqlite3.Row:
    now = _utc_now()
    is_admin = 1 if email in _admin_emails() else 0
    existing = conn.execute("SELECT id FROM users WHERE microsoft_sub = ?", (microsoft_sub,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE users SET email = ?, display_name = ?, is_admin = ?, last_login_at = ? WHERE id = ?",
            (email, display_name, is_admin, now, existing["id"]),
        )
        conn.commit()
        return conn.execute("SELECT * FROM users WHERE id = ?", (existing["id"],)).fetchone()

    conn.execute(
        "INSERT INTO users (microsoft_sub, email, display_name, is_admin, created_at, last_login_at) VALUES (?, ?, ?, ?, ?, ?)",
        (microsoft_sub, email, display_name, is_admin, now, now),
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE microsoft_sub = ?", (microsoft_sub,)).fetchone()


def _create_plate(conn: sqlite3.Connection, assignee: dict[str, str], board: list[str], created_by_user_id: int, generation_seed: str) -> None:
    now = _utc_now()
    conn.execute(
        "UPDATE plates SET is_active = 0 WHERE assignee_email = ? AND is_active = 1",
        (assignee["email"],),
    )
    cursor = conn.execute(
        "INSERT INTO plates (assignee_email, assignee_name, created_by_user_id, generation_seed, created_at, is_active) VALUES (?, ?, ?, ?, ?, 1)",
        (assignee["email"], assignee["name"], created_by_user_id, generation_seed, now),
    )
    plate_id = int(cursor.lastrowid)
    for index, label in enumerate(board):
        conn.execute(
            "INSERT INTO plate_cells (plate_id, cell_index, label, is_checked, image_path, updated_at) VALUES (?, ?, ?, 0, NULL, NULL)",
            (plate_id, index, label),
        )


def _read_json_body(environ) -> dict[str, object]:
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as exc:
        raise ValueError("Invalid request body") from exc

    raw_body = environ["wsgi.input"].read(content_length) if content_length > 0 else b""
    try:
        return json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc


def _read_urlencoded_form(environ) -> dict[str, str]:
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as exc:
        raise ValueError("Invalid form body") from exc

    raw_body = environ["wsgi.input"].read(content_length) if content_length > 0 else b""
    parsed = urllib.parse.parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in parsed.items()}


def _read_multipart_form(environ) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as exc:
        raise ValueError("Invalid form body") from exc

    content_type = environ.get("CONTENT_TYPE") or ""
    if "multipart/form-data" not in content_type:
        raise ValueError("Expected multipart form data")

    raw_body = environ["wsgi.input"].read(content_length) if content_length > 0 else b""
    mime_message = (
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + raw_body
    )
    message = BytesParser(policy=email_policy_default).parsebytes(mime_message)
    fields: dict[str, str] = {}
    files: dict[str, dict[str, object]] = {}

    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename() or ""
        if filename:
            files[name] = {
                "filename": filename,
                "content_type": part.get_content_type(),
                "data": payload,
            }
            continue
        charset = part.get_content_charset() or "utf-8"
        fields[name] = payload.decode(charset, errors="replace")

    return fields, files


def _build_generation_payload(payload: dict[str, object]) -> dict[str, object]:
    questions_text = str(payload.get("questionsText") or "")
    count = _normalize_plate_count(payload.get("count"))
    questions = _normalize_questions(questions_text)
    generation_seed = str(payload.get("generationSeed") or token_hex(8))
    boards = _generate_boards(questions, count, generation_seed)
    return {
        "count": count,
        "questions": questions,
        "questionCount": len(questions),
        "generationSeed": generation_seed,
        "boards": boards,
    }


def _normalize_plate_count(raw_value: object) -> int:
    try:
        count = int(raw_value or DEFAULT_PLATE_COUNT)
    except (TypeError, ValueError) as exc:
        raise ValueError("Plate count must be an integer") from exc

    if count < 1 or count > MAX_PLATES:
        raise ValueError(f"Plate count must be between 1 and {MAX_PLATES}")
    return count


def _normalize_questions(questions_text: str) -> list[str]:
    unique_questions: list[str] = []
    seen: set[str] = set()

    for line in questions_text.splitlines():
        question = " ".join(line.strip().split())
        if not question:
            continue
        folded = question.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        unique_questions.append(question)

    if len(unique_questions) < MIN_QUESTIONS:
        raise ValueError(f"Add at least {MIN_QUESTIONS} unique questions to build a 5x5 bingo plate")

    return unique_questions


def _normalize_assignees(assignees_text: str) -> list[dict[str, str]]:
    assignees: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw_line in assignees_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        email_part, separator, name_part = line.partition("|")
        email = _normalize_identifier(email_part)
        if "@" not in email:
            raise ValueError(f"Each assignee line must contain an email address. Invalid line: {line}")
        if email in seen:
            raise ValueError(f"Duplicate assignee email: {email}")
        seen.add(email)
        assignees.append({"email": email, "name": name_part.strip() if separator else ""})

    if not assignees:
        raise ValueError("Add at least one assignee email, one per line")

    return assignees


def _generate_boards(questions: list[str], count: int, generation_seed: str) -> list[list[str]]:
    rng = Random(generation_seed)
    boards: list[list[str]] = []
    seen_layouts: set[tuple[str, ...]] = set()
    max_attempts = max(60, count * 20)
    attempts = 0

    while len(boards) < count and attempts < max_attempts:
        attempts += 1
        board = rng.sample(questions, MIN_QUESTIONS)
        signature = tuple(board)
        if signature in seen_layouts:
            continue
        seen_layouts.add(signature)
        boards.append(board)

    if len(boards) != count:
        raise ValueError("Could not generate enough unique plates from the provided questions")

    return boards


def _respond_html(start_response, html: str, status: str = "200 OK", headers: list[tuple[str, str]] | None = None):
    body = html.encode("utf-8")
    response_headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    if headers:
        response_headers.extend(headers)
    start_response(status, response_headers)
    return [body]


def _respond_json(start_response, payload: dict[str, object]):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        "200 OK",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Cache-Control", "no-store"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _respond_json_error(start_response, message: str, status: str = "400 Bad Request"):
    body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Cache-Control", "no-store"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _respond_not_found(start_response, script_name: str, user: sqlite3.Row | None = None):
    home_url = _join_base(script_name, "/")
    html = _render_document(
        title="Page not found",
        script_name=script_name,
        user=user,
        body=(
            '<main class="layout layout--narrow">'
            '<section class="panel panel--soft">'
            '<p class="eyebrow">404</p>'
            '<h1>Page not found</h1>'
            '<p>The page does not exist. Return to the bingo workspace.</p>'
            f'<a class="button button--primary" href="{home_url}">Back</a>'
            '</section>'
            '</main>'
        ),
    )
    return _respond_html(start_response, html, status="404 Not Found")


def _redirect(start_response, location: str, status: str = "303 See Other", extra_headers: list[tuple[str, str]] | None = None):
    headers = [("Location", location)]
    if extra_headers:
        headers.extend(extra_headers)
    start_response(status, headers)
    return [b""]


def _require_authenticated(environ, start_response, user: sqlite3.Row | None, script_name: str):
    if user is not None:
        return None
    return _redirect_to_login(environ, start_response, script_name)


def _require_admin(environ, start_response, user: sqlite3.Row | None, script_name: str):
    if user is None:
        return _redirect_to_login(environ, start_response, script_name)
    if user["is_admin"]:
        return None
    return _respond_html(start_response, _render_message_page(environ, "Access denied", "This page is only available to administrators."), status="403 Forbidden")


def _redirect_to_login(environ, start_response, script_name: str):
    next_path = _normalize_next_path(_request_relative_url(environ))
    login_url = _join_base(script_name, f"/auth/login?next={urllib.parse.quote(next_path, safe='/?=&')}")
    return _redirect(start_response, login_url)


def _render_landing_page(environ) -> str:
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    login_url = _join_base(script_name, "/auth/login")
    auth_ready = _auth_is_configured()
    cta = (
        f'<a class="button button--primary" href="{login_url}">Sign in with Microsoft</a>'
        if auth_ready
        else '<p class="form-error">Authentication is not configured yet. Set the Microsoft client ID, client secret, and session secret on the server first.</p>'
    )
    body = "".join(
        [
            '<main class="layout">',
            '<section class="hero">',
            '<div class="hero__copy">',
            '<p class="eyebrow">Online Bingo</p>',
            '<h1>Assigned plates with Microsoft sign-in.</h1>',
            '<p class="lead">Admins assign one plate to each email address. Players sign in with their Microsoft account, cross off cells on their own plate, and upload proof images. Managers can review every plate and submission in one place.</p>',
            '<div class="composer__actions">',
            cta,
            '</div>',
            '<div class="info-stack">',
            '<p><strong>Player flow:</strong> sign in, open your plate, tick cells, and upload images per square.</p>',
            '<p><strong>Admin flow:</strong> sign in as an approved admin, assign plates by email, and review every submission.</p>',
            '</div>',
            '</div>',
            '<aside class="panel panel--soft stat-panel">',
            '<p class="stat-panel__label">Requirements</p>',
            '<p class="stat-panel__value">Microsoft OAuth</p>',
            '<p class="stat-panel__meta">Supports work, school, and personal Microsoft accounts through the common endpoint.</p>',
            '<p class="stat-panel__hint">Configure redirect URI, client ID, client secret, session secret, and admin emails before going live.</p>',
            '</aside>',
            '</section>',
            '</main>',
        ]
    )
    return _render_document("Bingo", script_name, body)


def _render_manage_page(
    environ,
    conn: sqlite3.Connection,
    user: sqlite3.Row,
    form_values: dict[str, str] | None = None,
    error_message: str = "",
) -> str:
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    query = _read_query_params(environ)
    created_count = query.get("created", [""])[0]
    flash_message = f"Created and assigned {created_count} plate(s)." if created_count else ""
    values = form_values or {"questions_text": "", "assignees_text": ""}
    plates = _list_plates(conn, script_name)

    if plates:
        plate_markup = "".join(_render_manage_plate_card(plate) for plate in plates)
    else:
        plate_markup = '<section class="panel panel--soft empty-state"><p>No assigned plates yet.</p></section>'

    body = "".join(
        [
            '<main class="layout">',
            '<section class="hero hero--stacked">',
            '<div class="hero__copy">',
            '<p class="eyebrow">Management</p>',
            '<h1>Assign plates to users.</h1>',
            '<p class="lead">Paste 25 or more prompts, then add one Microsoft email per line. You can optionally write <code>email@example.com | Name</code> to store a label beside the assignment.</p>',
            flash_message and f'<p class="success-note">{escape(flash_message)}</p>' or "",
            error_message and f'<p class="form-error">{escape(error_message)}</p>' or "",
            f'<form class="composer" method="post" action="{_join_base(script_name, "/manage/create")}">',
            '<label class="field field--stack">',
            '<span>Questions, one per line</span>',
            f'<textarea name="questions_text" rows="14" spellcheck="false">{escape(values.get("questions_text", ""))}</textarea>',
            '</label>',
            '<label class="field field--stack">',
            '<span>Assignees, one per line</span>',
            f'<textarea name="assignees_text" rows="10" spellcheck="false" placeholder="alice@example.com&#10;bob@example.com | Bob">{escape(values.get("assignees_text", ""))}</textarea>',
            '</label>',
            '<div class="composer__actions">',
            '<button class="button button--primary" type="submit">Create assigned plates</button>',
            '</div>',
            '</form>',
            '</div>',
            '<aside class="panel panel--soft stat-panel">',
            '<p class="stat-panel__label">Signed in</p>',
            f'<p class="stat-panel__value">{escape(user["display_name"])}</p>',
            f'<p class="stat-panel__meta">{escape(user["email"])}</p>',
            f'<p class="stat-panel__hint">{len(plates)} active or archived assignments stored.</p>',
            '</aside>',
            '</section>',
            '<section class="result-section">',
            '<div class="result-section__header">',
            '<div>',
            '<p class="eyebrow">Review</p>',
            '<h2>Plates and submissions</h2>',
            '</div>',
            '<p class="result-section__note">Each card shows assignment status, crossed cells, and any uploaded images.</p>',
            '</div>',
            f'<div class="manage-list">{plate_markup}</div>',
            '</section>',
            '</main>',
        ]
    )
    return _render_document("Manage plates", script_name, body, user=user)


def _render_player_page(environ, conn: sqlite3.Connection, user: sqlite3.Row) -> str:
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    query = _read_query_params(environ)
    success_message = "Saved your latest update." if query.get("saved") else ""
    error_message = "Could not save that update." if query.get("error") else ""
    plate = _get_active_plate_for_user(conn, user["email"], script_name)

    if plate is None:
        body = "".join(
            [
                '<main class="layout layout--narrow">',
                '<section class="panel panel--soft empty-state">',
                '<p class="eyebrow">My plate</p>',
                '<h1>No plate assigned yet.</h1>',
                '<p>Your Microsoft account is signed in, but no active plate matches your email address yet.</p>',
                '<p>Ask the administrator to assign a plate to <strong>',
                escape(user["email"]),
                '</strong>.</p>',
                '</section>',
                '</main>',
            ]
        )
        return _render_document("My plate", script_name, body, user=user)

    cells_markup = "".join(_render_player_cell(script_name, plate, cell) for cell in plate["cells"])
    checked_count = sum(1 for cell in plate["cells"] if cell["is_checked"])
    body = "".join(
        [
            '<main class="layout">',
            '<section class="hero hero--stacked">',
            '<div class="hero__copy">',
            '<p class="eyebrow">My plate</p>',
            '<h1>Your assigned bingo plate.</h1>',
            '<p class="lead">Tick a field when you have completed it. You can attach one image per square as proof and replace or clear it later.</p>',
            success_message and f'<p class="success-note">{escape(success_message)}</p>' or "",
            error_message and f'<p class="form-error">{escape(error_message)}</p>' or "",
            '</div>',
            '<aside class="panel panel--soft stat-panel">',
            '<p class="stat-panel__label">Progress</p>',
            f'<p class="stat-panel__value">{checked_count}/25</p>',
            f'<p class="stat-panel__meta">Assigned to {escape(plate["assignee_email"])}</p>',
            f'<p class="stat-panel__hint">Created {escape(_format_timestamp(plate["created_at"]))}</p>',
            '</aside>',
            '</section>',
            f'<section class="player-grid">{cells_markup}</section>',
            '</main>',
        ]
    )
    return _render_document("My plate", script_name, body, user=user)


def _render_message_page(environ, title: str, message: str) -> str:
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    body = "".join(
        [
            '<main class="layout layout--narrow">',
            '<section class="panel panel--soft">',
            f'<p class="eyebrow">{escape(title)}</p>',
            f'<h1>{escape(title)}</h1>',
            f'<p>{escape(message)}</p>',
            f'<a class="button button--primary" href="{_join_base(script_name, "/")}">Back</a>',
            '</section>',
            '</main>',
        ]
    )
    return _render_document(title, script_name, body)


def _render_manage_plate_card(plate: dict[str, object]) -> str:
    progress = f"{plate['checked_count']}/{MIN_QUESTIONS}"
    cells_markup = "".join(
        _render_manage_cell(cell)
        for cell in plate["cells"]
    )
    archived_badge = '<span class="badge">Archived</span>' if not plate["is_active"] else '<span class="badge badge--solid">Active</span>'
    assignee_name = f" ({escape(str(plate['assignee_name']))})" if plate["assignee_name"] else ""
    return "".join(
        [
            '<article class="panel panel--soft manage-card">',
            '<div class="manage-card__header">',
            f'<div><p class="eyebrow">Plate #{plate["id"]}</p><h3>{escape(str(plate["assignee_email"]))}{assignee_name}</h3></div>',
            f'<div class="manage-card__meta">{archived_badge}<span>{escape(progress)} checked</span></div>',
            '</div>',
            f'<p class="manage-card__submeta">Created {escape(_format_timestamp(str(plate["created_at"])))}</p>',
            f'<div class="plate-grid plate-grid--manage">{cells_markup}</div>',
            '</article>',
        ]
    )


def _render_manage_cell(cell: dict[str, object]) -> str:
    classes = ["plate-cell", "plate-cell--manage"]
    if cell["is_checked"]:
        classes.append("plate-cell--checked")
    image_markup = f'<img class="submission-image" src="{escape(str(cell["image_url"]))}" alt="Uploaded proof">' if cell["image_url"] else '<span class="submission-placeholder">No image</span>'
    updated = f'<p class="cell-meta">Updated {escape(_format_timestamp(str(cell["updated_at"])))}</p>' if cell["updated_at"] else '<p class="cell-meta">Not submitted yet</p>'
    return "".join(
        [
            f'<div class="{" ".join(classes)}">',
            f'<strong>{escape(str(cell["label"]))}</strong>',
            updated,
            image_markup,
            '</div>',
        ]
    )


def _render_player_cell(script_name: str, plate: dict[str, object], cell: dict[str, object]) -> str:
    classes = ["plate-cell", "plate-cell--player"]
    if cell["is_checked"]:
        classes.append("plate-cell--checked")
    image_markup = f'<img class="submission-image" src="{escape(str(cell["image_url"]))}" alt="Uploaded proof">' if cell["image_url"] else '<span class="submission-placeholder">No image uploaded</span>'
    checked_attr = " checked" if cell["is_checked"] else ""
    clear_markup = (
        '<label class="field field--check"><input type="checkbox" name="clear_image" value="1"><span>Remove current image</span></label>'
        if cell["image_url"]
        else ""
    )
    return "".join(
        [
            f'<article class="{" ".join(classes)}">',
            f'<h3>{escape(str(cell["label"]))}</h3>',
            '<form class="player-cell__form" method="post" enctype="multipart/form-data" action="',
            escape(_join_base(script_name, "/plate/update")),
            '">',
            f'<input type="hidden" name="plate_id" value="{plate["id"]}">',
            f'<input type="hidden" name="cell_index" value="{cell["cell_index"]}">',
            '<input type="hidden" name="checked" value="0">',
            '<label class="field field--check">',
            f'<input type="checkbox" name="checked" value="1"{checked_attr}>',
            '<span>Cross out this field</span>',
            '</label>',
            '<label class="field field--stack field--file">',
            '<span>Upload image</span>',
            '<input type="file" name="image" accept="image/*">',
            '</label>',
            clear_markup,
            '<button class="button button--primary" type="submit">Save field</button>',
            '</form>',
            image_markup,
            '</article>',
        ]
    )


def _render_document(title: str, script_name: str, body: str, user: sqlite3.Row | None = None) -> str:
    home_url = _join_base(script_name, "/")
    css_url = _static_asset_url(script_name, "site.css")
    nav_links = []
    if user is not None:
        if user["is_admin"]:
            nav_links.append(f'<a href="{_join_base(script_name, "/manage")}">Manage</a>')
        nav_links.append(f'<a href="{_join_base(script_name, "/my-plate")}">My plate</a>')
        nav_links.append(f'<a href="{_join_base(script_name, "/auth/logout")}">Sign out</a>')
    else:
        nav_links.append(f'<a href="{_join_base(script_name, "/auth/login")}">Sign in</a>')

    nav_html = f'<nav class="site-nav">{"".join(nav_links)}</nav>' if nav_links else ""
    return "".join(
        [
            '<!doctype html>',
            '<html lang="en">',
            '<head>',
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f'<title>{escape(title)} | Bingo</title>',
            '<meta name="description" content="Assigned bingo plates with Microsoft sign-in and image submissions.">',
            f'<link rel="stylesheet" href="{css_url}">',
            '</head>',
            '<body>',
            '<div class="page-backdrop"></div>',
            '<header class="site-header">',
            '<div class="site-header__inner">',
            f'<a class="brand" href="{home_url}">',
            '<span class="brand__chip">5x5</span>',
            '<span class="brand__text">Bingo Online</span>',
            '</a>',
            nav_html,
            '</div>',
            '</header>',
            body,
            '</body>',
            '</html>',
        ]
    )


def _list_plates(conn: sqlite3.Connection, script_name: str) -> list[dict[str, object]]:
    plate_rows = conn.execute(
        "SELECT * FROM plates ORDER BY created_at DESC, id DESC"
    ).fetchall()
    plates: list[dict[str, object]] = []
    for plate_row in plate_rows:
        cells = conn.execute(
            "SELECT * FROM plate_cells WHERE plate_id = ? ORDER BY cell_index",
            (plate_row["id"],),
        ).fetchall()
        cell_dicts = []
        for cell in cells:
            cell_dicts.append(
                {
                    "cell_index": cell["cell_index"],
                    "label": cell["label"],
                    "is_checked": bool(cell["is_checked"]),
                    "updated_at": cell["updated_at"],
                    "image_url": _media_url(script_name, plate_row["id"], cell["cell_index"], cell["updated_at"]) if cell["image_path"] else "",
                }
            )

        plates.append(
            {
                "id": plate_row["id"],
                "assignee_email": plate_row["assignee_email"],
                "assignee_name": plate_row["assignee_name"],
                "created_at": plate_row["created_at"],
                "is_active": bool(plate_row["is_active"]),
                "checked_count": sum(1 for cell in cell_dicts if cell["is_checked"]),
                "cells": cell_dicts,
            }
        )
    return plates


def _get_active_plate_for_user(conn: sqlite3.Connection, email: str, script_name: str) -> dict[str, object] | None:
    plate = conn.execute(
        "SELECT * FROM plates WHERE assignee_email = ? AND is_active = 1 ORDER BY created_at DESC, id DESC LIMIT 1",
        (_normalize_identifier(email),),
    ).fetchone()
    if not plate:
        return None

    cells = conn.execute(
        "SELECT * FROM plate_cells WHERE plate_id = ? ORDER BY cell_index",
        (plate["id"],),
    ).fetchall()
    return {
        "id": plate["id"],
        "assignee_email": plate["assignee_email"],
        "created_at": plate["created_at"],
        "cells": [
            {
                "cell_index": cell["cell_index"],
                "label": cell["label"],
                "is_checked": bool(cell["is_checked"]),
                "updated_at": cell["updated_at"],
                "image_url": _media_url(script_name, plate["id"], cell["cell_index"], cell["updated_at"]) if cell["image_path"] else "",
            }
            for cell in cells
        ],
    }


def _media_url(script_name: str, plate_id: int, cell_index: int, updated_at: str | None) -> str:
    version = urllib.parse.quote(updated_at or "0", safe="")
    return f'{_join_base(script_name, f"/media/{plate_id}/{cell_index}")}?v={version}'


def _store_uploaded_image(upload_item: dict[str, object], plate_id: int, cell_index: int) -> str:
    raw = bytes(upload_item.get("data") or b"")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded image is too large")

    content_type = str(upload_item.get("content_type") or "").lower()
    suffix = ALLOWED_IMAGE_TYPES.get(content_type)
    if suffix is None:
        guessed_type, _ = mimetypes.guess_type(str(upload_item.get("filename") or ""))
        suffix = ALLOWED_IMAGE_TYPES.get((guessed_type or "").lower())
    if suffix is None:
        raise ValueError("Only JPG, PNG, GIF, and WebP uploads are supported")

    file_name = f"plate-{plate_id}-cell-{cell_index}-{token_hex(8)}{suffix}"
    (UPLOAD_DIR / file_name).write_bytes(raw)
    return file_name


def _delete_upload_file(file_name: str) -> None:
    file_path = UPLOAD_DIR / file_name
    if file_path.exists():
        file_path.unlink()


def _read_query_params(environ) -> dict[str, list[str]]:
    return urllib.parse.parse_qs(environ.get("QUERY_STRING") or "", keep_blank_values=True)


def _join_base(script_name: str, path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{script_name}{path}" if script_name else path


def _absolute_app_url(environ, path: str) -> str:
    scheme = environ.get("HTTP_X_FORWARDED_PROTO") or environ.get("wsgi.url_scheme") or "https"
    host = environ.get("HTTP_X_FORWARDED_HOST") or environ.get("HTTP_HOST") or environ.get("SERVER_NAME") or "localhost"
    return f"{scheme}://{host}{_join_base((environ.get('SCRIPT_NAME') or '').rstrip('/'), path)}"


def _static_asset_url(script_name: str, asset_name: str) -> str:
    asset_path = STATIC_DIR / asset_name
    version = asset_path.stat().st_mtime_ns
    return f'{_join_base(script_name, f"/static/{asset_name}")}?v={version}'


def _normalize_next_path(value: str) -> str:
    if not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


def _normalize_identifier(value: str) -> str:
    return value.strip().casefold()


def _request_relative_url(environ) -> str:
    path = environ.get("PATH_INFO") or "/"
    query = environ.get("QUERY_STRING") or ""
    return f"{path}?{query}" if query else path


def _auth_is_configured() -> bool:
    return all(os.getenv(name) for name in ("BINGO_MS_CLIENT_ID", "BINGO_MS_CLIENT_SECRET", "BINGO_SESSION_SECRET"))


def _required_setting(name: str) -> str:
    value = os.getenv(name) or ""
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value


def _admin_emails() -> set[str]:
    raw_value = os.getenv("BINGO_ADMIN_EMAILS") or ""
    return {_normalize_identifier(part) for part in raw_value.split(",") if part.strip()}


def _encode_signed_payload(payload: dict[str, object]) -> str:
    data = dict(payload)
    data["ts"] = int(time.time())
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = _base64url_encode(raw)
    signature = _base64url_encode(_sign_bytes(encoded.encode("ascii")))
    return f"{encoded}.{signature}"


def _get_signed_cookie(environ, cookie_name: str, max_age: int) -> dict[str, object] | None:
    cookie_header = environ.get("HTTP_COOKIE") or ""
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    morsel = cookie.get(cookie_name)
    if morsel is None:
        return None
    return _decode_signed_payload(morsel.value, max_age)


def _decode_signed_payload(token: str, max_age: int) -> dict[str, object] | None:
    try:
        encoded, provided_signature = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _base64url_encode(_sign_bytes(encoded.encode("ascii")))
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    try:
        payload = json.loads(_base64url_decode(encoded).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    timestamp = int(payload.get("ts") or 0)
    if not timestamp or int(time.time()) - timestamp > max_age:
        return None
    return payload


def _build_cookie_header(name: str, value: str, max_age: int) -> str:
    parts = [f"{name}={value}", "Path=/", f"Max-Age={max_age}", "HttpOnly", "SameSite=Lax"]
    if max_age == 0:
        parts.append("Expires=Thu, 01 Jan 1970 00:00:00 GMT")
    if os.getenv("BINGO_COOKIE_SECURE", "1") != "0":
        parts.append("Secure")
    return "; ".join(parts)


def _sign_bytes(value: bytes) -> bytes:
    secret = _required_setting("BINGO_SESSION_SECRET").encode("utf-8")
    return hmac.new(secret, value, hashlib.sha256).digest()


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - (len(value) % 4)) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _decode_jwt_claims(token: str) -> dict[str, object]:
    if not token:
        return {}
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    try:
        return json.loads(_base64url_decode(parts[1]).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}


def _get_oidc_configuration() -> dict[str, object]:
    global _OIDC_CONFIGURATION_CACHE, _OIDC_CONFIGURATION_FETCHED_AT
    if _OIDC_CONFIGURATION_CACHE and time.time() - _OIDC_CONFIGURATION_FETCHED_AT < 3600:
        return _OIDC_CONFIGURATION_CACHE
    payload = _fetch_json(MICROSOFT_OPENID_CONFIGURATION_URL)
    _OIDC_CONFIGURATION_CACHE = payload
    _OIDC_CONFIGURATION_FETCHED_AT = time.time()
    return payload


def _fetch_json(url: str, headers: dict[str, str] | None = None) -> dict[str, object]:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_form(url: str, data: dict[str, str]) -> dict[str, object]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _format_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _build_pdf_document(boards: list[list[str]]) -> bytes:
    page_width = 595
    page_height = 842
    icon_objects = _build_pdf_icon_objects()
    objects: list[bytes | None] = [None, None]
    page_object_ids: list[int] = []
    icon_object_ids: dict[str, int] = {}

    for icon_name, icon_stream in icon_objects.items():
        icon_object_ids[icon_name] = len(objects) + 1
        objects.append(icon_stream)

    font_object_id = len(objects) + 1
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    xobject_entries = " ".join(
        f"/{_pdf_icon_resource_name(icon_name)} {object_id} 0 R"
        for icon_name, object_id in icon_object_ids.items()
    )
    resources = (
        f"<< /Font << /F1 {font_object_id} 0 R >> /XObject << {xobject_entries} >> >>"
    ).encode("ascii")

    for board in boards:
        content_stream = _build_pdf_page_stream(board, page_height)
        content_object_id = len(objects) + 1
        objects.append(_pdf_stream_object(content_stream))
        page_object_id = len(objects) + 1
        page_object_ids.append(page_object_id)
        page_object = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources {resources.decode('ascii')} /Contents {content_object_id} 0 R >>"
        ).encode("ascii")
        objects.append(page_object)

    page_refs = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{page_refs}] /Count {len(page_object_ids)} >>".encode("ascii")
    return _assemble_pdf(objects)


def _build_pdf_page_stream(board: list[str], page_height: int) -> bytes:
    margin_x = 40
    grid_width = 515
    cell_width = grid_width / GRID_SIZE
    cell_height = 110
    grid_top = page_height - 120
    commands = [
        "1 1 1 rg 32 72 531 698 re f",
        "0 0 0 RG 1 w",
    ]

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            index = (row * GRID_SIZE) + col
            x = margin_x + (col * cell_width)
            y = grid_top - ((row + 1) * cell_height)
            label = board[index]
            commands.append(f"0 0 0 RG {x:.2f} {y:.2f} {cell_width:.2f} {cell_height:.2f} re S")

            font_size = 9.5
            lines = _wrap_pdf_text(label, max_width=cell_width - 16, font_size=font_size)
            line_height = font_size + 2
            block_height = line_height * len(lines)
            first_line_y = y + ((cell_height + block_height) / 2) - font_size

            for line_index, line in enumerate(lines):
                line_y = first_line_y - (line_index * line_height)
                commands.extend(_pdf_text_commands(x + 8, line_y, line, font_size))

    return "\n".join(commands).encode("cp1252", "replace")


def _wrap_pdf_text(text: str, max_width: float, font_size: float) -> list[str]:
    safe_text = _sanitize_pdf_text(text)
    approx_chars = max(4, int(max_width / (font_size * 0.52)))
    lines = _wrap_pdf_text_with_hyphenation(safe_text, approx_chars)
    if not lines:
        return [""]
    if len(lines) > 6:
        lines = lines[:6]
        lines[-1] = lines[-1][: max(1, len(lines[-1]) - 1)].rstrip() + "..."
    return lines


def _wrap_pdf_text_with_hyphenation(text: str, width: int) -> list[str]:
    if not text:
        return []

    wrapper = textwrap.TextWrapper(
        width=width,
        break_long_words=False,
        break_on_hyphens=True,
        drop_whitespace=True,
        replace_whitespace=False,
    )
    lines: list[str] = []

    for paragraph in text.split("\n"):
        tokens = paragraph.split()
        if not tokens:
            continue
        current_line = ""
        for token in tokens:
            if len(token) <= width:
                candidate = token if not current_line else f"{current_line} {token}"
                if len(candidate) <= width:
                    current_line = candidate
                    continue
                if current_line:
                    lines.append(current_line)
                current_line = token
                continue

            if current_line:
                lines.append(current_line)
                current_line = ""

            remaining = token
            while len(remaining) > width:
                chunk = remaining[: max(1, width - 1)]
                lines.append(f"{chunk}-")
                remaining = remaining[len(chunk) :]
            current_line = remaining

        if current_line:
            lines.append(current_line)

    return lines


def _sanitize_pdf_text(text: str) -> str:
    sanitized_parts: list[str] = []

    for char in text:
        if char in PDF_ICON_MARKERS:
            sanitized_parts.append(char)
            continue
        icon_marker = _pdf_icon_marker_for_char(char)
        if icon_marker:
            sanitized_parts.append(icon_marker)
            continue
        try:
            char.encode("cp1252")
        except UnicodeEncodeError:
            replacement = _pdf_fallback_for_char(char)
            if replacement:
                sanitized_parts.append(replacement)
        else:
            sanitized_parts.append(char)

    return "".join(sanitized_parts)


def _pdf_icon_marker_for_char(char: str) -> str:
    if char in {"\ufe0f", "\u200d"}:
        return ""

    name = unicodedata.name(char, "")
    if not name:
        return PDF_GENERIC_MARK
    if "CAMERA" in name:
        return PDF_CAMERA_MARK
    if any(keyword in name for keyword in ("METRO", "TRAIN", "RAILWAY", "LOCOMOTIVE", "SUBWAY")):
        return PDF_TRANSIT_MARK
    if any(keyword in name for keyword in ("SELFIE", "MOBILE PHONE", "PHONE", "TELEPHONE", "CALLING")):
        return PDF_SELFIE_MARK
    if any(keyword in name for keyword in ("TELEVISION", "PICTURE", "FRAME", "PHOTO", "SCREEN", "MONITOR", "TV")):
        return PDF_SCREEN_MARK
    if any(keyword in name for keyword in ("SOCCER", "FOOTBALL", "BALL", "SPORT")):
        return PDF_SPORT_MARK
    if any(keyword in name for keyword in ("BUS", "CAR", "AUTOMOBILE", "TRUCK", "TAXI", "TRAM", "BICYCLE", "MOTOR")):
        return PDF_VEHICLE_MARK
    if any(keyword in name for keyword in ("DRINK", "COCKTAIL", "BEER", "WINE", "BOTTLE", "GLASS", "TUMBLER", "CUP")):
        return PDF_DRINK_MARK
    if any(keyword in name for keyword in ("EURO", "BANKNOTE", "MONEY", "COIN", "DOLLAR", "POUND", "YEN", "CURRENCY")):
        return PDF_MONEY_MARK
    if any(keyword in name for keyword in ("MUSIC", "MUSICAL", "NOTE", "HEADPHONE", "SPEAKER", "RADIO", "HORN")):
        return PDF_MUSIC_MARK
    if "MAGNET" in name:
        return PDF_MAGNET_MARK
    if any(keyword in name for keyword in ("EMOJI", "SYMBOL", "SIGN", "ARROW", "STAR", "HEART", "FACE", "HAND", "FOOD", "ANIMAL", "BUILDING", "MAP", "FLAG")):
        return PDF_GENERIC_MARK
    return ""


def _pdf_fallback_for_char(char: str) -> str:
    if char in {"\ufe0f", "\u200d"}:
        return ""

    name = unicodedata.name(char, "")
    if not name:
        return "[symbol]"

    return f"[{name.lower()}]"


def _estimate_pdf_text_width(text: str, font_size: float) -> float:
    width = 0.0
    for char in text:
        if char in PDF_ICON_MARKERS:
            width += _pdf_icon_width(font_size)
        else:
            width += font_size * 0.48
    return width


def _pdf_text_commands(
    x: float,
    y: float,
    text: str,
    font_size: float,
    color: tuple[float, float, float] = (0, 0, 0),
) -> list[str]:
    commands: list[str] = []
    cursor_x = x
    text_buffer: list[str] = []

    def flush_text() -> None:
        nonlocal cursor_x
        if not text_buffer:
            return
        chunk = "".join(text_buffer)
        commands.append(_pdf_text_run(cursor_x, y, chunk, font_size, color=color))
        cursor_x += _estimate_pdf_text_width(chunk, font_size)
        text_buffer.clear()

    for char in _sanitize_pdf_text(text):
        if char in PDF_ICON_MARKERS:
            flush_text()
            commands.extend(_pdf_icon_commands(cursor_x, y, font_size, char))
            cursor_x += _pdf_icon_width(font_size)
            continue
        text_buffer.append(char)

    flush_text()
    return commands


def _pdf_text_run(x: float, y: float, text: str, font_size: float, color: tuple[float, float, float] = (0, 0, 0)) -> str:
    escaped_text = _escape_pdf_text(_sanitize_pdf_text(text))
    red, green, blue = color
    return (
        f"BT {red:.2f} {green:.2f} {blue:.2f} rg /F1 {font_size:.2f} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm "
        f"({escaped_text}) Tj ET"
    )


def _pdf_icon_width(font_size: float) -> float:
    return font_size * 1.2


def _pdf_icon_commands(x: float, y: float, font_size: float, marker: str) -> list[str]:
    icon_name = PDF_ICON_PATTERN_NAMES.get(marker, "generic")
    width = _pdf_icon_width(font_size)
    height = font_size * 0.9
    icon_y = y - (font_size * 0.16)
    resource_name = _pdf_icon_resource_name(icon_name)
    return [
        f"q 0.18 0.18 0.18 rg {width:.2f} 0 0 {height:.2f} {x:.2f} {icon_y:.2f} cm /{resource_name} Do Q"
    ]


def _build_pdf_icon_objects() -> dict[str, bytes]:
    return {name: _pdf_image_object_from_pattern(pattern) for name, pattern in PDF_ICON_PATTERNS.items()}


def _pdf_icon_resource_name(icon_name: str) -> str:
    return f"I{icon_name.title()}"


def _pdf_image_object_from_pattern(pattern: list[str]) -> bytes:
    height = len(pattern)
    width = len(pattern[0]) if pattern else 0
    rows = [_pdf_pack_pattern_row(row) for row in pattern]
    data = b"".join(rows)
    dictionary = (
        f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
        f"/ImageMask true /BitsPerComponent 1 /Length {len(data)} >>\nstream\n"
    ).encode("ascii")
    return dictionary + data + b"\nendstream"


def _pdf_pack_pattern_row(row: str) -> bytes:
    padded_row = row + ("." * ((8 - (len(row) % 8)) % 8))
    packed = bytearray()
    for start in range(0, len(padded_row), 8):
        chunk = padded_row[start : start + 8]
        value = 0
        for bit_index, char in enumerate(chunk):
            if char == "#":
                value |= 1 << (7 - bit_index)
        packed.append(value)
    return bytes(packed)


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_stream_object(data: bytes) -> bytes:
    return b"<< /Length %d >>\nstream\n%s\nendstream" % (len(data), data)


def _assemble_pdf(objects: list[bytes | None]) -> bytes:
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj or b"")
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    output.extend(trailer.encode("ascii"))
    return bytes(output)


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    with make_server("127.0.0.1", 8000, application) as server:
        print("Running on http://127.0.0.1:8000")
        server.serve_forever()
