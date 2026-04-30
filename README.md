# bingo

A small Python WSGI web app for christianvinter.dk/bingo. It accepts one bingo prompt per line, generates any number of unique 5x5 plates with a free center square, previews them in the browser, and exports the generated set as a PDF.

## Project structure

- `app.py`: WSGI application, HTML rendering, board generation API, and PDF export.
- `passenger_wsgi.py`: Passenger entrypoint.
- `.htaccess`: Passenger configuration for the `/bingo` mount.
- `static/site.css`: visual design for the builder and printable plate preview.
- `static/site.js`: client-side generation flow and PDF download.
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

## Usage notes

- Enter at least 24 unique lines.
- The app removes duplicate lines case-insensitively.
- PDF export reuses the same generated set currently shown in the preview.

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
