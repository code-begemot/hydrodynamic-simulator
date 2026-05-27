# AGENTS.md — Hydrodynamic Simulator (FastAPI)

## Run
```bash
source /home/ed_ubuntu/.virtualenvs/fastApiProject/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Dependencies
- Virtual env: `/home/ed_ubuntu/.virtualenvs/fastApiProject/`
- All deps installed (`fastapi`, `uvicorn`, `jinja2`, `numpy`, `scipy`, `matplotlib`, `xtgeo`, etc.)
- `requirements.txt` generated — update with `pip freeze > requirements.txt`

## App overview
- Single-file FastAPI app (`main.py`, 434 lines) — Russian-language hydrodynamic (reservoir) simulator
- Entrypoint: `main:app`
- Templates: Jinja2 in `templates/` (Bootstrap 5 via CDN)
- Static files: `static/plots/` for generated plots
- Uploads: `uploads/<model_name>/` — `.DAT` files with `.mgrid` / `.minit` include files

## Model file format
- `.DAT` files use keyword-based sections: `SPECGRID`, `INCL`, `COOR`, `ZCOR`, `PORO`, etc.
- `INCL` references include files (`.mgrid`, `.minit`, etc.) stored in the same model dir
- Parsed by `file_processing()` — handles `*` repeat-count notation (e.g. `3*0.25`)

## State management
- `MODEL_STATE` global dict holds all runtime state (current model, params, grid data)
- **State is lost on server restart** — in-memory only, no persistence

## Known issues
- `numpy` and `scipy` are installed and working

## Tests
- No test suite. Only `test_main.http` for manual HTTP testing via IDE (JetBrains HTTP Client).
- No CI/CD, no Dockerfile, no README.

## Git
- No `.gitignore` — recommend adding: `__pycache__/`, `.idea/`, `static/plots/`, `uploads/`
- IntelliJ IDEA project files present (`.idea/`)

## Language
- Ask the human questions in Russian. Accept answers in Russian or English. Write all files in English.
