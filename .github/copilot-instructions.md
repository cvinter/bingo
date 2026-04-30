# Copilot instructions (bingo)

## Context
- This repo is deployed to Azehosting (cp04) at `/home/christi2/public_html/bingo`.
- The app is mounted under `PassengerBaseURI /bingo`.
- Public URL is `https://christianvinter.dk/bingo`.
- Production deploy is pull-only: the server runs `git pull --ff-only` from `main`.

## Hard constraints
- Must compile before deploy:
  - `python -m compileall -q .`
- Respect Passenger base URI:
  - Any internal links or API URLs must include the base path.
  - Use WSGI `SCRIPT_NAME` as `base_url`.
- Avoid fragile giant f-strings or escaping-heavy HTML strings.
- Prefer Python standard library unless the project later states otherwise.
- Keep code compatible with Passenger Python 3.9 on the server.

## Operations / governance
- Do not edit production files directly on the server.
- Work on a branch, commit, push, then fast-forward `main`.
- Deploy steps (server):
  - `cd /home/christi2/public_html/bingo`
  - `git pull --ff-only`
  - `python3 -m compileall -q .`
  - `touch tmp/restart.txt`
- If errors occur, inspect Passenger or stderr logs in the app folder.
