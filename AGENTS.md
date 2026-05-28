# AGENTS.md — Hydrodynamic Simulator (FastAPI)

## Run
```bash
source /home/ed_ubuntu/.virtualenvs/fastApiProject/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Dependencies
- Virtual env: `/home/ed_ubuntu/.virtualenvs/fastApiProject/`
- All deps installed (`fastapi`, `uvicorn`, `jinja2`, `numpy`, `scipy`, `matplotlib`, `xtgeo`, etc.)
- `requirements.txt` exists — update with `pip freeze > requirements.txt`

## App overview
- Single-file FastAPI app (`main.py`) — Russian-language hydrodynamic (reservoir) simulator
- Entrypoint: `main:app`
- Templates: Jinja2 in `templates/` (Bootstrap 5 via CDN)
- Static files: `static/plots/` — plots saved to `static/plots/<model_name>/`
- Uploads: `uploads/<model_name>/` — `.DAT` files with `.mgrid` / `.minit` include files
- `xtgeo` is imported but not actively used in the current code

## Endpoints
- `GET /` — home page, lists uploaded files and model params
- `POST /upload` — upload a `.DAT` file, parses keywords (`SPECGRID`, `INCL`, etc.), stores state
- `POST /upload_include` — upload include files (`.mgrid`, `.minit`) to the current model dir
- `POST /delete_file` — delete a file from the current model dir
- `GET /calculate` — main pipeline: reads `.mgrid`/`.minit`, parses grid/init data, computes cell volumes via ConvexHull
- `GET /plot` — generates mean‑map plots (permeability, porosity, NTG, saturation, volumes) to `static/plots/`

## State management
- `MODEL_STATE` global dict holds all runtime state (current model, params, grid data)
- **State is lost on server restart** — in-memory only, no persistence

## Model file format
- `.DAT` files use keyword-based sections: `SPECGRID`, `INCL`, `COOR`, `ZCOR`, `PORO`, etc.
- `INCL` references include files (`.mgrid`, `.minit`, etc.) stored in the same model dir
- Parsed by `file_processing()` — handles `*` repeat-count notation (e.g. `3*0.25`)

## Known quirks
- `templates.TemplateResponse(request, name, context)` — Starlette 1.1.0 requires `request` as the **first** positional argument. Older code used `TemplateResponse(name, {"request": request, ...})`.

## Tests
- No test suite. Manual testing via browser only.

## Git
- Branch: `main`
- `.gitignore` excludes: `__pycache__/`, `.idea/`, `static/plots/`, `uploads/`

## Language
- Ask the human questions in Russian. Accept answers in Russian or English. Write all files in English.

## Custom tools
- `run-server` — OpenCode custom tool (`.opencode/tools/run-server.ts`). Actions: `start`, `stop`, `restart`, `status`, `logs`.
## Project skills
- `code-review` — OpenCode skill (`.opencode/skills/code-review/SKILL.md`). Review code changes following project standards.

## MCP servers
- `playwright` — browser automation MCP server (`@playwright/mcp` via npx). Provides browser tools: navigate, click, type, screenshot, snapshot. Runs headed (visible browser window) by default.
