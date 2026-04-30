# bingo

A small Python WSGI web app for christianvinter.dk/bingo. It supports both offline plate generation with PDF export and an online mode with Microsoft sign-in, assigned plates, per-cell image uploads, and an admin review page.

## Project structure

- `app.py`: WSGI application, Microsoft auth flow, SQLite persistence, HTML rendering, board generation API, assignment management, submission uploads, and PDF export.
- `passenger_wsgi.py`: Passenger entrypoint.
- `.htaccess`: Passenger configuration for the `/bingo` mount.
- `static/site.css`: visual design for the landing, management, player, and printable plate views.
- `static/site.js`: legacy client-side generation flow for offline board generation and PDF download.
- `.github/copilot-instructions.md`: project-specific instructions for hosting and deploy flow.
- `.vscode/tasks.json`: local compile check and production deploy tasks.

## Local run

```powershell
python app.py
```

Then open `http://127.0.0.1:8000`.

## Compile check

```powershell
python -m compileall -q .
```

## Offline usage notes

- Enter at least 25 unique lines.
- The page starts with an empty question list and a default plate count of 22.
- The app removes duplicate lines case-insensitively.
- PDF export reuses the same generated set currently shown in the preview.

## Online mode

### Roles

- Anonymous users land on a sign-in page.
- Admin users can open `/manage`, assign one plate per email address, and review all plate progress and uploaded images.
- Regular users can open `/my-plate`, cross off cells, and upload one image per square.

### Data storage

- SQLite database: `tmp/data/bingo.sqlite3`
- Uploaded images: `tmp/data/uploads/`

### Microsoft sign-in setup

Register a web app in the Microsoft identity platform with these settings:

1. Supported account types: include both personal Microsoft accounts and work or school accounts.
2. Platform type: Web.
3. Redirect URI: `https://christianvinter.dk/bingo/auth/callback`

The app expects these environment variables on the server:

- `BINGO_MS_CLIENT_ID`: Microsoft application client ID
- `BINGO_MS_CLIENT_SECRET`: Microsoft application client secret
- `BINGO_SESSION_SECRET`: long random secret used to sign cookies
- `BINGO_ADMIN_EMAILS`: comma-separated list of admin email addresses
- `BINGO_COOKIE_SECURE`: optional; defaults to secure cookies enabled and should only be set to `0` for local HTTP testing

### Assignment format

On the management page, enter one assignee per line.

Example:

```text
alice@example.com
bob@example.com | Bob
```

Each line creates one assigned plate. If a user already has an active plate, the old one is archived and the new one becomes active.

## Deploy target

The app is intended for Passenger at `https://christianvinter.dk/bingo`.

Expected server location:

- app root: `/home/christi2/public_html/bingo`
- base URI: `/bingo`
- python: `/home/christi2/virtualenv/openclaw/3.9/bin/python`

Recommended server flow:

```bash
cd /home/christi2/public_html/bingo
git pull --ff-only
/home/christi2/virtualenv/openclaw/3.9/bin/python -m compileall -q .
touch tmp/restart.txt
```

Before the online mode can work in production, configure the Microsoft credentials and admin email list in the Passenger environment on the server.
