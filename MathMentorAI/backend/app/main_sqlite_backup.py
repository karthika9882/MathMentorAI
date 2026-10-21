from contextlib import asynccontextmanager
import os, re, json, hmac, base64, hashlib, secrets, time
from pathlib import Path
from fastapi import UploadFile, File, Form
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .adaptive import choose_support
from .database import connect, get_or_create_student, init_db
from .schemas import AnswerRequest, SolveRequest
from .solver import EquationError, solve_linear_equation
from pydantic import BaseModel, Field

SECRET_KEY = os.getenv("MATHMENTOR_SECRET_KEY", "development-only-change-this-secret").encode()

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    grade: int = Field(ge=6, le=12)
    language: str = "en"

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)

class ChatRequest(BaseModel):
    student_id: str
    grade: int = Field(ge=6, le=12)
    language: str = "en"
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict] = Field(default_factory=list)

class DailyTaskRequest(BaseModel):
    student_id: str
    grade: int = Field(ge=6, le=12)
    language: str = "en"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return _b64(salt) + "$" + _b64(digest)

def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_s, digest_s = stored.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_s + "=" * (-len(salt_s) % 4))
        expected = base64.urlsafe_b64decode(digest_s + "=" * (-len(digest_s) % 4))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def _token(username: str) -> str:
    header = _b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub":username,"exp":int(time.time())+43200}, separators=(",", ":")).encode())
    msg = f"{header}.{payload}".encode()
    sig = _b64(hmac.new(SECRET_KEY, msg, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS user_accounts (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
          email TEXT NOT NULL COLLATE NOCASE UNIQUE,
          password_hash TEXT NOT NULL, grade INTEGER NOT NULL DEFAULT 9,
          language TEXT NOT NULL DEFAULT 'en', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    yield

app = FastAPI(title="MathMentor AI API",
              description="Bilingual adaptive maths tutor prototype for Classes 9–10.",
              version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"message":"MathMentor AI API is running","docs":"/docs",
            "languages":["English","Tamil"],"grades":[9,10]}

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterRequest):
    name, username, email = payload.name.strip(), payload.username.strip(), payload.email.strip().lower()
    if not name or not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
        raise HTTPException(400, "Enter a name and a username using letters, numbers, dot, underscore or hyphen.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Enter a valid email address.")
    if payload.language not in ("en", "ta"):
        raise HTTPException(400, "Language must be en or ta.")
    try:
        with connect() as conn:
            conn.execute("INSERT INTO user_accounts(name,username,email,password_hash,grade,language) VALUES(?,?,?,?,?,?)",
                         (name, username, email, _password_hash(payload.password), payload.grade, payload.language))
            conn.execute("INSERT OR IGNORE INTO student_profiles(student_id,grade,language) VALUES(?,?,?)",
                         (username, payload.grade, payload.language))
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(409, "Username or email is already registered.") from exc
        raise
    return {"message":"Account created. You can now log in.", "username":username}

@app.post("/api/auth/login")
def login(payload: LoginRequest):
    with connect() as conn:
        account = conn.execute("SELECT username,password_hash,grade,language,name FROM user_accounts WHERE username=? COLLATE NOCASE OR email=? COLLATE NOCASE LIMIT 1",
                               (payload.username.strip(), payload.username.strip())).fetchone()
    if not account or not _verify_password(payload.password, account["password_hash"]):
        raise HTTPException(401, "Incorrect username/email or password.")
    return {"access_token":_token(account["username"]), "token_type":"bearer",
            "username":account["username"], "name":account["name"], "grade":account["grade"], "language":account["language"]}

@app.get("/api/curriculum")
def curriculum(grade: int = 6):
    if grade not in range(6, 13):
        raise HTTPException(400, "Choose a class from 6 to 12.")
    return {"grade":grade, "board":"Tamil Nadu Samacheer Kalvi", "subjects":["Mathematics"],
            "note":"Chapter lists and question banks must be validated against the official textbook for each class."}

@app.post("/api/daily-tasks")
def daily_tasks(payload: DailyTaskRequest):
    get_or_create_student(payload.student_id, payload.grade, payload.language)
    with connect() as conn:
        row = conn.execute("SELECT total_answered,total_correct,support_level FROM student_profiles WHERE student_id=?", (payload.student_id,)).fetchone()
    level = row["support_level"] if row else "guided"
    # Prototype tasks are intentionally limited to examples; expand question banks by class/topic before claiming full syllabus coverage.
    tasks = [
      {"id":"warmup", "title_en":"Warm-up: number skills", "title_ta":"தொடக்கப் பயிற்சி: எண் திறன்கள்", "minutes":4, "kind":"practice", "difficulty":"easy"},
      {"id":"learn", "title_en":"Learn one new concept", "title_ta":"ஒரு புதிய கருத்தைக் கற்கவும்", "minutes":8, "kind":"lesson", "difficulty":level},
      {"id":"review", "title_en":"Review a previous mistake", "title_ta":"முந்தைய தவறை மீண்டும் பயிற்சி செய்யவும்", "minutes":5, "kind":"revision", "difficulty":"personalised"},
    ]
    return {"student_id":payload.student_id,"grade":payload.grade,"language":payload.language,
            "target_minutes":17,"tasks":[{**t,"title":t["title_ta"] if payload.language=="ta" else t["title_en"]} for t in tasks],
            "answered_total":row["total_answered"] if row else 0,"accuracy_percent":round(100*row["total_correct"]/row["total_answered"],1) if row and row["total_answered"] else 0,
            "note":"Initial daily plan prototype. Tasks become truly personalised as topic-level history and validated question banks are added."}

@app.post("/api/chat")
def chat(payload: ChatRequest):
    if payload.language not in ("en", "ta"):
        raise HTTPException(400, "Language must be en or ta.")
    try:
        import requests
        base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        lang = "Tamil" if payload.language == "ta" else "English"
        system = (f"You are MathMentor AI, a patient maths tutor for Class {payload.grade}. "
                  f"Answer in {lang}. Explain math step by step at the student's level, ask guiding questions, "
                  "show calculations carefully, and never pretend to know an unverified textbook page. "
                  "If the student is stuck, give a hint before the complete solution.")
        messages = [{"role":"system","content":system}]
        for item in payload.history[-8:]:
            if item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
                messages.append({"role":item["role"],"content":item["content"][:4000]})
        messages.append({"role":"user","content":payload.message})
        response = requests.post(base.rstrip("/")+"/api/chat", json={"model":model,"messages":messages,"stream":False}, timeout=90)
        response.raise_for_status()
        answer = response.json().get("message", {}).get("content", "").strip()
        if not answer:
            raise ValueError("Empty response from Ollama")
        return {"reply":answer,"model":model,"language":payload.language}
    except Exception as exc:
        raise HTTPException(503, "AI chat is unavailable. Start Ollama and pull a model, or check OLLAMA_BASE_URL / OLLAMA_MODEL.") from exc

@app.post("/api/upload-question")
async def upload_question(file: UploadFile = File(...), grade: int = Form(9), language: str = Form("en")):
    if grade not in range(6, 13):
        raise HTTPException(400, "Choose a class from 6 to 12.")
    if language not in ("en", "ta"):
        raise HTTPException(400, "Language must be en or ta.")
    filename = (file.filename or "upload").lower()
    allowed = filename.endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp"))
    if not allowed:
        raise HTTPException(400, "Upload a PDF, PNG, JPG or WEBP file.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum upload size is 10 MB.")
    extracted = ""
    if filename.endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            extracted = "\n".join(page.get_text() for page in doc)[:12000]
            doc.close()
        except Exception as exc:
            raise HTTPException(400, "Could not read this PDF. Try another PDF.") from exc
        if not extracted.strip():
            extracted = "This PDF appears to be scanned or image-only. OCR is not configured for this file yet."
    else:
        # Image OCR requires local Tesseract installation; return clear setup guidance if missing.
        try:
            from PIL import Image
            import pytesseract
            import io
            img = Image.open(io.BytesIO(content))
            extracted = pytesseract.image_to_string(img, lang="eng+tam")[:12000]
        except Exception:
            extracted = "Image received, but OCR is not available yet. Install Tesseract OCR and its English/Tamil language packs to extract text from photos."
    return {"filename":file.filename,"grade":grade,"language":language,"extracted_text":extracted,
            "needs_confirmation":True,"message":"Review the extracted question before asking the tutor to solve it. Diagrams and handwritten maths may need correction."}

@app.post("/api/solve")
def solve(payload: SolveRequest):
    try:
        result = solve_linear_equation(payload.equation, payload.language)
    except EquationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    get_or_create_student(payload.student_id, payload.grade, payload.language)
    return {"student_id":payload.student_id,"grade":payload.grade,
            "language":payload.language,**result}

@app.post("/api/answer")
def check_answer(payload: AnswerRequest):
    is_correct = payload.submitted_answer.strip().lower() == payload.expected_answer.strip().lower()
    profile = get_or_create_student(payload.student_id, payload.grade, payload.language)
    update = choose_support(profile, is_correct)
    with connect() as conn:
        conn.execute("""INSERT INTO answer_history
          (student_id,topic,question,submitted_answer,is_correct) VALUES (?,?,?,?,?)""",
          (payload.student_id,payload.topic,payload.question,payload.submitted_answer,int(is_correct)))
        conn.execute("""UPDATE student_profiles SET grade=?,language=?,support_level=?,
          correct_streak=?,wrong_streak=?,total_answered=total_answered+1,
          total_correct=total_correct+? WHERE student_id=?""",
          (payload.grade,payload.language,update["support_level"],update["correct_streak"],
           update["wrong_streak"],int(is_correct),payload.student_id))
    return {"is_correct":is_correct,
            "feedback_en":"Correct! Well done." if is_correct else f"Not quite. The expected answer is {payload.expected_answer}.",
            "feedback_ta":"சரி! அருமை." if is_correct else f"மீண்டும் முயற்சி செய்யுங்கள். சரியான விடை: {payload.expected_answer}.",
            **update,
            "next_step":"Offer a harder practice question." if update["support_level"]=="independent" else "Offer guided practice."}

@app.get("/api/students/{student_id}/profile")
def student_profile(student_id: str):
    if not student_id.strip() or len(student_id)>80:
        raise HTTPException(status_code=400, detail="Invalid student ID.")
    profile = get_or_create_student(student_id)
    with connect() as conn:
        recent = conn.execute("""SELECT topic,question,submitted_answer,is_correct,created_at
          FROM answer_history WHERE student_id=? ORDER BY id DESC LIMIT 10""",(student_id,)).fetchall()
    data = dict(profile)
    data["recent_answers"] = [dict(row) for row in recent]
    data["accuracy_percent"] = round(100*data["total_correct"]/data["total_answered"],1) if data["total_answered"] else 0
    return data

@app.get("/api/practice")
def practice(grade: int = 9, topic: str = "linear_equations", language: str = "en"):
    if grade not in (9,10):
        raise HTTPException(status_code=400, detail="Grade must be 9 or 10.")
    if language not in ("en","ta"):
        raise HTTPException(status_code=400, detail="language must be en or ta.")
    if topic != "linear_equations":
        raise HTTPException(status_code=404, detail="Only sample linear_equations questions are included.")
    return {"grade":grade,"topic":topic,"language":language,
            "note":"Sample questions only; not a complete official syllabus bank.",
            "questions":[{"question":"x + 5 = 12","answer":"7"},
                         {"question":"2*x + 3 = 11","answer":"4"},
                         {"question":"3*x - 6 = 9","answer":"5"}]}
