# MathMentor AI — Classes 6–12

A bilingual English/Tamil maths learning prototype with account registration/login, class selection (6–12), adaptive progress scaffolding, daily tasks, a local Ollama chat endpoint, equation solving, and PDF/photo question extraction.

## Important scope notes

- This is a learning prototype, not a production-ready service. The initial daily task plan is a template and does not yet have a complete class-by-class curriculum or validated question bank.
- Tamil Nadu Samacheer Kalvi should be populated and checked against official textbooks for every class before claiming syllabus completeness.
- Authentication returns a signed token, but the prototype does not yet validate that token on every student API. Do not deploy publicly without implementing token verification/authorization, rate limiting, HTTPS, secret management and security testing.
- Local AI chat requires Ollama. Install Ollama, then in a terminal run `ollama pull llama3.2`; ensure Ollama is running at `http://127.0.0.1:11434`.
- PDF text extraction works for text-based PDFs. Scanned PDFs need OCR. Photo OCR requires Tesseract OCR installed locally with English and Tamil language packs; the app returns a helpful message if OCR is unavailable. Maths notation and diagrams should be checked manually.
- Uploads are processed in memory and are not stored permanently by this prototype. Limit is 10 MB.

## 1. Backend setup (Windows PowerShell)

Open a terminal in the `MathMentorAI` project folder:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

If PowerShell blocks virtual environment activation, run this in that terminal first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

API docs: http://127.0.0.1:8000/docs

## 2. Frontend setup

Open a **second** terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, usually http://localhost:5173.

## 3. Enable local AI chat

Install Ollama, then run:

```powershell
ollama pull llama3.2
```

Keep Ollama running. To use another installed model, set `OLLAMA_MODEL` before starting FastAPI, e.g. `$env:OLLAMA_MODEL="llama3.1:8b"`.

## 4. Photo OCR (optional)

Install Tesseract OCR for Windows and the English/Tamil language data. Make sure `tesseract.exe` is on PATH. Restart the backend after installing it. OCR can misread handwritten symbols, so always review extracted text.

## Main API routes

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/curriculum?grade=6`
- `POST /api/daily-tasks`
- `POST /api/chat`
- `POST /api/upload-question`
- `POST /api/solve`
- `POST /api/answer`
- `GET /api/students/{student_id}/profile`
- `GET /api/practice`

## Project layout

- `backend/app/main.py` — API, authentication, chat, upload extraction, daily task endpoint
- `backend/app/database.py` — SQLite profile and answer history
- `backend/app/adaptive.py` — prototype support-level logic
- `backend/app/solver.py` — supported linear equation solver
- `frontend/src/App.tsx` — sign-up/login and student learning interface
- `frontend/src/styles.css` — responsive styling
