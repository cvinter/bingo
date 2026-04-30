from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from random import Random
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
BINGO_WORDS = [
    "Algorithm",
    "API",
    "Backlog",
    "Bandwidth",
    "Benchmark",
    "Browser",
    "Bugfix",
    "Cache",
    "Callback",
    "Cloud",
    "Commit",
    "Container",
    "Cookie",
    "Dashboard",
    "Data",
    "Deploy",
    "Docker",
    "Endpoint",
    "Feature",
    "Firewall",
    "Frontend",
    "Git",
    "Hotfix",
    "HTML",
    "Incident",
    "Index",
    "JavaScript",
    "Latency",
    "Launch",
    "Legacy",
    "Merge",
    "Metrics",
    "Migration",
    "Monitor",
    "Pipeline",
    "Pull Request",
    "Python",
    "Refactor",
    "Release",
    "Rollback",
    "Router",
    "Script",
    "Search",
    "Sprint",
    "Staging",
    "Testing",
    "Ticket",
    "Timeout",
    "UI",
    "Webhook",
]


def application(environ, start_response):
    script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
    path = environ.get("PATH_INFO") or "/"

    if path.startswith("/static/"):
        return _serve_static(path, start_response)

    if path == "/api/card":
        query = parse_qs(environ.get("QUERY_STRING") or "")
        seed = query.get("seed", [""])[0]
        payload = _build_card(seed)
        return _respond_json(start_response, payload)

    if path == "/":
        html = _render_homepage(script_name)
        return _respond_html(start_response, html)

    return _respond_not_found(start_response, script_name)


def _serve_static(path: str, start_response):
    file_path = (ROOT / path.lstrip("/")).resolve()
    if STATIC_DIR not in file_path.parents or not file_path.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not found"]

    content_type, _ = mimetypes.guess_type(file_path.name)
    start_response("200 OK", [("Content-Type", content_type or "application/octet-stream")])
    return [file_path.read_bytes()]


def _build_card(seed: str) -> dict[str, object]:
    normalized_seed = seed.strip() or "bingo"
    rng = Random(normalized_seed)
    cells = rng.sample(BINGO_WORDS, 24)
    board = cells[:12] + ["FREE"] + cells[12:]
    return {
        "seed": normalized_seed,
        "board": board,
    }


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


def _respond_not_found(start_response, script_name: str):
    start_response("404 Not Found", [("Content-Type", "text/html; charset=utf-8")])
    home_url = _join_base(script_name, "/")
    html = _render_document(
        title="Page not found",
        script_name=script_name,
        body=(
            '<main class="layout layout--narrow">'
            '<section class="panel panel--soft">'
            '<p class="kicker">404</p>'
            '<h1>Page not found</h1>'
            '<p>The page does not exist. Return to the main board generator.</p>'
            f'<a class="button button--primary" href="{home_url}">Back to bingo</a>'
            '</section>'
            '</main>'
        ),
    )
    return [html.encode("utf-8")]


def _join_base(script_name: str, path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{script_name}{path}" if script_name else path


def _render_homepage(script_name: str) -> str:
    api_url = _join_base(script_name, "/api/card")
    js_url = _join_base(script_name, "/static/site.js")
    initial_payload = json.dumps(_build_card("bingo"), ensure_ascii=False).replace("<", "\\u003c")

    body = (
        '<main class="layout">'
        '<section class="hero">'
        '<div class="hero__copy">'
        '<p class="kicker">christianvinter.dk/bingo</p>'
        '<h1>Technical meeting bingo with a sharper visual style.</h1>'
        '<p class="lead">Generate a fresh board, keep the free square in the middle, and mark live as the room drifts into predictable jargon.</p>'
        '<form id="generator-form" class="generator" autocomplete="off">'
        '<label class="field">'
        '<span>Seed</span>'
        '<input id="seed-input" name="seed" type="text" value="bingo" maxlength="80" placeholder="Type a seed or leave default">'
        '</label>'
        '<div class="hero__actions">'
        '<button class="button button--primary" type="submit">Generate board</button>'
        '<button id="shuffle-button" class="button button--ghost" type="button">Random seed</button>'
        '<button id="clear-button" class="button button--ghost" type="button">Clear marks</button>'
        '</div>'
        '</form>'
        '</div>'
        '<aside class="panel panel--glass status-card">'
        '<p class="status-card__label">Current mode</p>'
        '<p id="seed-label" class="status-card__seed">bingo</p>'
        '<p class="status-card__meta">Marks persist in the browser for each seed, so you can reload without losing the board.</p>'
        '</aside>'
        '</section>'
        '<section class="board-shell">'
        '<div id="bingo-board" class="board" aria-live="polite"></div>'
        '<div class="panel panel--soft sidebar">'
        '<h2>How it works</h2>'
        '<ul class="rules">'
        '<li>Click any square to toggle it.</li>'
        '<li>The center square is always free.</li>'
        '<li>Use a seed to recreate the same board later.</li>'
        '<li>Run it locally or under Passenger at /bingo.</li>'
        '</ul>'
        '</div>'
        '</section>'
        f'<script id="app-config" type="application/json">{{"apiUrl": "{api_url}", "initialCard": {initial_payload}}}</script>'
        f'<script src="{js_url}" defer></script>'
        '</main>'
    )
    return _render_document("Bingo", script_name, body)


def _render_document(title: str, script_name: str, body: str) -> str:
    home_url = _join_base(script_name, "/")
    css_url = _join_base(script_name, "/static/site.css")
    return (
        '<!doctype html>'
        '<html lang="en">'
        '<head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{title} | Bingo</title>'
        '<meta name="description" content="A lightweight Bingo web app deployed under /bingo.">'
        f'<link rel="stylesheet" href="{css_url}">'
        '</head>'
        '<body>'
        '<div class="page-backdrop"></div>'
        '<header class="site-header">'
        '<div class="site-header__inner">'
        f'<a class="brand" href="{home_url}">'
        '<span class="brand__chip">B</span>'
        '<span class="brand__text">Bingo</span>'
        '</a>'
        '<p class="site-header__path">Passenger-ready app for christianvinter.dk/bingo</p>'
        '</div>'
        '</header>'
        f'{body}'
        '</body>'
        '</html>'
    )


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    with make_server("127.0.0.1", 8000, application) as server:
        print("Running on http://127.0.0.1:8000")
        server.serve_forever()
