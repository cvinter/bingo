from __future__ import annotations

import json
import mimetypes
import textwrap
import unicodedata
from html import escape
from pathlib import Path
from random import Random
from secrets import token_hex

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
GRID_SIZE = 5
MIN_QUESTIONS = GRID_SIZE * GRID_SIZE
MAX_PLATES = 100
DEFAULT_PLATE_COUNT = 22
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


def application(environ, start_response):
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    path = environ.get("PATH_INFO") or "/"
    method = (environ.get("REQUEST_METHOD") or "GET").upper()

    if path.startswith("/static/"):
        return _serve_static(path, start_response)

    if path == "/api/boards":
        if method != "POST":
            return _respond_json_error(start_response, "Method not allowed", status="405 Method Not Allowed")
        return _handle_generate_boards(environ, start_response)

    if path == "/api/export.pdf":
        if method != "POST":
            return _respond_json_error(start_response, "Method not allowed", status="405 Method Not Allowed")
        return _handle_export_pdf(environ, start_response)

    if path == "/":
        return _respond_html(start_response, _render_homepage(script_name))

    return _respond_not_found(start_response, script_name)


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


def _respond_html(start_response, html: str):
    body = html.encode("utf-8")
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
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


def _respond_not_found(start_response, script_name: str):
    start_response("404 Not Found", [("Content-Type", "text/html; charset=utf-8")])
    home_url = _join_base(script_name, "/")
    html = _render_document(
        title="Page not found",
        script_name=script_name,
        body=(
            '<main class="layout layout--narrow">'
            '<section class="panel panel--soft">'
            '<p class="eyebrow">404</p>'
            '<h1>Page not found</h1>'
            '<p>The page does not exist. Return to the bingo plate builder.</p>'
            f'<a class="button button--primary" href="{home_url}">Back to builder</a>'
            '</section>'
            '</main>'
        ),
    )
    return [html.encode("utf-8")]


def _join_base(script_name: str, path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{script_name}{path}" if script_name else path


def _static_asset_url(script_name: str, asset_name: str) -> str:
    asset_path = STATIC_DIR / asset_name
    version = asset_path.stat().st_mtime_ns
    return f'{_join_base(script_name, f"/static/{asset_name}")}?v={version}'


def _render_homepage(script_name: str) -> str:
    boards_url = _join_base(script_name, "/api/boards")
    pdf_url = _join_base(script_name, "/api/export.pdf")
    js_url = _static_asset_url(script_name, "site.js")
    config = {
        "boardsUrl": boards_url,
        "pdfUrl": pdf_url,
        "defaultCount": DEFAULT_PLATE_COUNT,
        "initialPayload": {
            "generationSeed": "",
            "boards": [],
            "questionCount": 0,
        },
    }
    config_json = json.dumps(config, ensure_ascii=False).replace("<", "\\u003c")

    body = "".join(
        [
            '<main class="layout">',
            '<section class="hero">',
            '<div class="hero__copy">',
            '<p class="eyebrow">christianvinter.dk/bingo</p>',
            '<h1>Build printable bingo plates from your own questions.</h1>',
            '<p class="lead">Paste one prompt per line, choose how many 5x5 plates you need, preview them in the browser, and export the exact set as a PDF.</p>',
            '<form id="plate-form" class="composer" autocomplete="off">',
            '<label class="field field--stack" for="questions-input">',
            '<span>Questions, one per line</span>',
            '<textarea id="questions-input" name="questions" rows="14" spellcheck="false"></textarea>',
            '</label>',
            '<div class="composer__row">',
            '<label class="field field--compact" for="count-input">',
            '<span>Number of plates</span>',
            f'<input id="count-input" name="count" type="number" min="1" max="{MAX_PLATES}" value="{DEFAULT_PLATE_COUNT}">',
            '</label>',
            '<div class="composer__actions">',
            '<button class="button button--primary" type="submit">Generate plates</button>',
            '<button id="download-button" class="button button--ghost" type="button">Download PDF</button>',
            '</div>',
            '</div>',
            '<p id="form-error" class="form-error" hidden></p>',
            '</form>',
            '</div>',
            '<aside class="panel panel--glass stat-panel">',
            '<p class="stat-panel__label">Current set</p>',
            '<p id="plate-summary" class="stat-panel__value">0 plates</p>',
            '<p id="question-summary" class="stat-panel__meta">0 unique questions available</p>',
            '<p class="stat-panel__hint">Each plate uses 25 of your questions. Add more lines if you want more variation across the set.</p>',
            '</aside>',
            '</section>',
            '<section class="result-section">',
            '<div class="result-section__header">',
            '<div>',
            '<p class="eyebrow">Preview</p>',
            '<h2>Your bingo plates</h2>',
            '</div>',
            '<p class="result-section__note">The PDF export uses the same generated set shown below.</p>',
            '</div>',
            '<div id="boards-root" class="boards-grid" aria-live="polite"></div>',
            '</section>',
            f'<script id="app-config" type="application/json">{config_json}</script>',
            f'<script src="{js_url}" defer></script>',
            '</main>',
        ]
    )
    return _render_document("Bingo", script_name, body)


def _render_document(title: str, script_name: str, body: str) -> str:
    home_url = _join_base(script_name, "/")
    css_url = _static_asset_url(script_name, "site.css")
    return "".join(
        [
            '<!doctype html>',
            '<html lang="en">',
            '<head>',
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f'<title>{title} | Bingo</title>',
            '<meta name="description" content="Create printable bingo plates from your own question list.">',
            f'<link rel="stylesheet" href="{css_url}">',
            '</head>',
            '<body>',
            '<div class="page-backdrop"></div>',
            '<header class="site-header">',
            '<div class="site-header__inner">',
            f'<a class="brand" href="{home_url}">',
            '<span class="brand__chip">5x5</span>',
            '<span class="brand__text">Bingo Builder</span>',
            '</a>',
            '<p class="site-header__path">Passenger-ready app for christianvinter.dk/bingo</p>',
            '</div>',
            '</header>',
            body,
            '</body>',
            '</html>',
        ]
    )


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
        "0.95 0.93 0.88 rg 32 72 531 698 re f",
        "0.47 0.40 0.30 RG 1 w",
    ]

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            index = (row * GRID_SIZE) + col
            x = margin_x + (col * cell_width)
            y = grid_top - ((row + 1) * cell_height)
            label = board[index]
            commands.append(f"0.47 0.40 0.30 RG {x:.2f} {y:.2f} {cell_width:.2f} {cell_height:.2f} re S")

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
    color: tuple[float, float, float] = (0.16, 0.14, 0.11),
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


def _pdf_text_run(x: float, y: float, text: str, font_size: float, color: tuple[float, float, float] = (0.16, 0.14, 0.11)) -> str:
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
