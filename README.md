# bingo

A small Python WSGI web app for christianvinter.dk/bingo. It serves a styled technical bingo board, supports deterministic board generation from a seed, and is set up for Passenger on Azehosting.

## Project structure

- `app.py`: WSGI application, HTML rendering, and JSON card API.
- `passenger_wsgi.py`: Passenger entrypoint.
- `.htaccess`: Passenger configuration for the `/bingo` mount.
- `static/site.css`: visual design for the page and board.
- `static/site.js`: client-side board rendering, seed generation, and local state.
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

## GitHub

Create the repository as `bingo` on GitHub, then connect the local repo and push:

```powershell
git init -b main
git remote add origin https://github.com/<your-user>/bingo.git
git add .
git commit -m "Initial scaffold"
git push -u origin main
```
