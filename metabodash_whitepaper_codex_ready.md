# MetaboDash Whitepaper (Codex-ready, Frontend/Backend Separated) — v0.2

> 目标：你把这份 Markdown 交给 Codex（vibe coding）后，它可以 **按文件路径生成完整工程骨架**，并且可运行（Docker 一键起），可测试（pytest + Playwright），接口可复用（OpenAPI 契约 + 前端 typed client）。

---

## 0) 总览

### 0.1 产品模块（Dashboard）
1. **健康情况（Health）**
   - 血糖曲线（24h/7d/30d）
   - 关键指标：平均、min/max、TIR(70–180)、波动（CV 或 IQR）
   - 今日摄入卡路里（来自 meal 事件的 kcal 汇总）
   - 数据质量提示（缺口时长、异常值比例）

2. **饮食上传（Meals）**
   - 上传食物照片（S3/R2 presigned url）
   - 后端异步：图片识别 → 食物项/份量粗估/总 kcal/置信度
   - **用餐时间确定**：用户确认优先；否则 EXIF；否则根据上传时间附近血糖变点推断
   - 支持用户修正 kcal/时间/标签（形成标注闭环）

3. **Chatbot**
   - 用户提问健康问题
   - 后端构建 **用户上下文 ContextJSON**（压缩/最小化/可测试）
   - 调用 **OpenAI Responses API 或 Gemini generateContent**（可切换）
   - 支持 **SSE 流式输出**
   - 输出结构化（JSON Schema），便于前端稳定渲染 + 回归测试

---

## 1) 架构与原则

### 1.1 前后端分离
- `frontend/`：Vite + React + TS + Tailwind + React Query + Recharts
- `backend/`：FastAPI + Pydantic v2 + SQLAlchemy + Alembic + Postgres + Redis + Celery
- `docker-compose.yml`：一键起 Postgres / Redis / backend / worker / frontend

### 1.2 核心原则（必须落实）
- **可解释、可回放**：所有推断（用餐时间、kcal）都保存来源与置信度
- **可测试**：业务逻辑函数纯函数化；provider 适配层可 mock
- **可审计**：LLM 调用写 audit log（provider/model/latency/token/context_hash）
- **最小化上下文**：Chatbot 不直接塞时序原始数据，先生成 ContextJSON
- **用户同意**：未同意“AI 处理个人数据”时，Chatbot 直接返回 403 并提示开启

---

## 2) 运行方式（Docker）

### 2.1 环境变量（.env）
> 生产请用 Secret Manager。MVP 先用 .env。

**backend/.env.example**
```bash
APP_ENV=dev
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/metabodash
REDIS_URL=redis://redis:6379/0

# Object storage (S3 compatible)
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET=metabodash
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGION=us-east-1
S3_PUBLIC_BASE_URL=http://localhost:9000/metabodash

# LLM
LLM_PROVIDER=openai   # openai | gemini
OPENAI_API_KEY=...
OPENAI_MODEL_TEXT=gpt-4.1-mini
OPENAI_MODEL_VISION=gpt-4.1-mini
GEMINI_API_KEY=...
GEMINI_MODEL_TEXT=gemini-1.5-pro
GEMINI_MODEL_VISION=gemini-1.5-pro

# Auth
JWT_SECRET=change_me
JWT_EXPIRES_MIN=1440

# CORS
CORS_ORIGINS=http://localhost:5173
```

**frontend/.env.example**
```bash
VITE_API_BASE_URL=http://localhost:8000
```

### 2.2 启动
```bash
docker compose up --build
# 前端: http://localhost:5173
# 后端: http://localhost:8000/docs
```

---

## 3) 仓库结构（Codex 按文件生成）

```
metabodash/
  docker-compose.yml
  README.md

  backend/
    pyproject.toml
    .env.example
    Dockerfile
    alembic.ini
    app/
      main.py
      core/
        config.py
        logging.py
        security.py
        deps.py
      db/
        session.py
        base.py
        migrations/
          env.py
          versions/
            0001_init.py
      models/
        user.py
        consent.py
        glucose.py
        meal.py
        symptom.py
        audit.py
      schemas/
        user.py
        glucose.py
        meal.py
        symptom.py
        chat.py
        common.py
      routers/
        auth.py
        users.py
        glucose.py
        meals.py
        chat.py
        dashboard.py
      services/
        glucose_service.py
        meal_service.py
        inference_service.py
        context_builder.py
        safety_service.py
      providers/
        base.py
        openai_provider.py
        gemini_provider.py
      workers/
        celery_app.py
        tasks.py
      utils/
        csv_import.py
        time.py
        hash.py
    tests/
      unit/
        test_infer_meal_time.py
        test_glucose_summary.py
        test_context_builder.py
      integration/
        test_api_glucose_import.py
        test_api_meals_flow.py
        test_api_chat_mock.py

  frontend/
    package.json
    vite.config.ts
    tsconfig.json
    tailwind.config.js
    postcss.config.js
    .env.example
    Dockerfile
    src/
      main.tsx
      app.tsx
      routes.tsx
      api/
        client.ts
        types.ts
        hooks.ts
      components/
        layout/
          Sidebar.tsx
          TopBar.tsx
          PageShell.tsx
        health/
          GlucoseChart.tsx
          MetricsCards.tsx
        meals/
          MealUploadCard.tsx
          MealTimeConfirmModal.tsx
          MealsTable.tsx
        chat/
          ChatPanel.tsx
          MessageBubble.tsx
          useSSEChat.ts
      pages/
        HealthPage.tsx
        MealsPage.tsx
        ChatPage.tsx
        SettingsPage.tsx
      styles/
        index.css
    e2e/
      playwright.config.ts
      tests/
        smoke.spec.ts
```

---

## 4) Backend：实现细节（FastAPI）

### 4.1 依赖（backend/pyproject.toml）
**backend/pyproject.toml**
```toml
[project]
name = "metabodash-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "sqlalchemy>=2.0",
  "psycopg[binary]>=3.1",
  "alembic>=1.13",
  "python-multipart>=0.0.9",
  "pyjwt>=2.8",
  "passlib[bcrypt]>=1.7",
  "httpx>=0.27",
  "redis>=5.0",
  "celery>=5.3",
  "boto3>=1.34",
  "python-dateutil>=2.9",
  "orjson>=3.10",
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
]
```

### 4.2 入口与路由（backend/app/main.py）
**backend/app/main.py**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.routers import auth, users, glucose, meals, chat, dashboard

def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="MetaboDash API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(glucose.router, prefix="/api/glucose", tags=["glucose"])
    app.include_router(meals.router, prefix="/api/meals", tags=["meals"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

    return app

app = create_app()
```

---

## 5) Backend：数据库与模型

### 5.1 SQLAlchemy Base 与 Session
**backend/app/db/base.py**
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

**backend/app/db/session.py**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
```

### 5.2 Models（关键字段）
> Codex 要按以下文件创建 SQLAlchemy model + index。

**backend/app/models/user.py**
```python
import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

**backend/app/models/consent.py**
```python
import uuid
from sqlalchemy import Column, Boolean, DateTime, func, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Consent(Base):
    __tablename__ = "consents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)

    # user toggles
    allow_ai_chat = Column(Boolean, default=False, nullable=False)
    allow_data_upload = Column(Boolean, default=True, nullable=False)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    version = Column(String, default="v1", nullable=False)
```

**backend/app/models/glucose.py**
```python
import uuid
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, String, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base

class GlucoseReading(Base):
    __tablename__ = "glucose_readings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    ts = Column(DateTime(timezone=True), index=True, nullable=False)
    glucose_mgdl = Column(Integer, nullable=False)
    source = Column(String, default="manual_import", nullable=False)
    meta = Column(JSONB, default=dict, nullable=False)

Index("ix_glucose_user_ts", GlucoseReading.user_id, GlucoseReading.ts)
```

**backend/app/models/meal.py**
```python
import uuid
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, String, Float, Enum, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.db.base import Base
import enum

class PhotoStatus(str, enum.Enum):
    uploaded = "uploaded"
    processed = "processed"
    failed = "failed"

class MealTsSource(str, enum.Enum):
    user_confirmed = "user_confirmed"
    exif = "exif"
    inferred_from_glucose = "inferred_from_glucose"
    uploaded_at = "uploaded_at"

class MealPhoto(Base):
    __tablename__ = "meal_photos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    image_object_key = Column(String, nullable=False)
    exif_ts = Column(DateTime(timezone=True), nullable=True)

    status = Column(Enum(PhotoStatus), default=PhotoStatus.uploaded, nullable=False)
    vision_json = Column(JSONB, default=dict, nullable=False)
    calorie_estimate_kcal = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)

class Meal(Base):
    __tablename__ = "meals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)

    meal_ts = Column(DateTime(timezone=True), index=True, nullable=False)
    meal_ts_source = Column(Enum(MealTsSource), default=MealTsSource.uploaded_at, nullable=False)

    kcal = Column(Integer, nullable=False)
    tags = Column(ARRAY(String), default=list, nullable=False)
    notes = Column(Text, nullable=True)

    photo_id = Column(UUID(as_uuid=True), ForeignKey("meal_photos.id"), nullable=True)

Index("ix_meals_user_ts", Meal.user_id, Meal.meal_ts)
```

**backend/app/models/symptom.py**（MVP 可简单）
```python
import uuid
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Symptom(Base):
    __tablename__ = "symptoms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    ts = Column(DateTime(timezone=True), index=True, nullable=False)
    severity = Column(Integer, nullable=False)  # 0-5
    text = Column(Text, nullable=False)

Index("ix_symptoms_user_ts", Symptom.user_id, Symptom.ts)
```

**backend/app/models/audit.py**
```python
import uuid
from sqlalchemy import Column, DateTime, func, ForeignKey, String, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base

class LLMAuditLog(Base):
    __tablename__ = "llm_audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    provider = Column(String, nullable=False)  # openai|gemini
    model = Column(String, nullable=False)
    latency_ms = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)

    context_hash = Column(String, nullable=False)
    meta = Column(JSONB, default=dict, nullable=False)
```

---

## 6) Backend：Auth / Security / Dependencies

### 6.1 配置（backend/app/core/config.py）
**backend/app/core/config.py**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "dev"
    DATABASE_URL: str
    REDIS_URL: str

    S3_ENDPOINT_URL: str
    S3_BUCKET: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_BASE_URL: str

    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL_TEXT: str = "gpt-4.1-mini"
    OPENAI_MODEL_VISION: str = "gpt-4.1-mini"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL_TEXT: str = "gemini-1.5-pro"
    GEMINI_MODEL_VISION: str = "gemini-1.5-pro"

    JWT_SECRET: str
    JWT_EXPIRES_MIN: int = 1440
    CORS_ORIGINS: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

settings = Settings()
```

### 6.2 JWT（backend/app/core/security.py）
**backend/app/core/security.py**
```python
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return pwd_ctx.verify(pw, hashed)

def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRES_MIN)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
```

### 6.3 Dependencies（backend/app/core/deps.py）
**backend/app/core/deps.py**
```python
from fastapi import Depends, Header, HTTPException
from app.db.session import SessionLocal
from app.core.security import decode_token

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user_id(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## 7) Backend：Schemas（Pydantic v2）

### 7.1 Common
**backend/app/schemas/common.py**
```python
from pydantic import BaseModel

class APIError(BaseModel):
    error_code: str
    message: str
    details: dict | None = None
    trace_id: str | None = None
```

### 7.2 Glucose
**backend/app/schemas/glucose.py**
```python
from pydantic import BaseModel, Field
from datetime import datetime

class GlucosePoint(BaseModel):
    ts: datetime
    glucose_mgdl: int = Field(ge=20, le=600)

class GlucoseImportResponse(BaseModel):
    inserted: int
    skipped: int
    errors: list[dict]  # {row:int, reason:str}

class GlucoseSummary(BaseModel):
    window: str
    avg: float | None
    min: int | None
    max: int | None
    tir_70_180_pct: float | None
    variability: str  # low|medium|high|unknown
    gaps_hours: float
```

### 7.3 Meals
**backend/app/schemas/meal.py**
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class PresignResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int

class MealVisionItem(BaseModel):
    name: str
    portion_text: str
    kcal: int = Field(ge=0, le=5000)

class MealVisionResult(BaseModel):
    items: list[MealVisionItem]
    total_kcal: int = Field(ge=0, le=20000)
    confidence: float = Field(ge=0, le=1)
    notes: str = ""

class MealPhotoOut(BaseModel):
    id: str
    uploaded_at: datetime
    status: str
    calorie_estimate_kcal: int | None
    confidence: float | None
    vision_json: dict

class MealCreate(BaseModel):
    meal_ts: datetime
    meal_ts_source: Literal["user_confirmed","exif","inferred_from_glucose","uploaded_at"]
    kcal: int = Field(ge=0, le=20000)
    tags: list[str] = []
    photo_id: str | None = None
    notes: str | None = None

class MealOut(BaseModel):
    id: str
    meal_ts: datetime
    meal_ts_source: str
    kcal: int
    tags: list[str]
    photo_id: str | None
```

### 7.4 Chat
**backend/app/schemas/chat.py**
```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None  # optional: store in db later

class ChatResult(BaseModel):
    answer_markdown: str
    confidence: float = Field(ge=0, le=1)
    followups: list[str] = []
    safety_flags: list[str] = []
    used_context: dict
```

---

## 8) Backend：业务服务（可单测）

### 8.1 血糖摘要（backend/app/services/glucose_service.py）
**backend/app/services/glucose_service.py**
```python
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.glucose import GlucoseReading

def compute_tir(readings: list[int], low: int=70, high: int=180) -> float | None:
    if not readings:
        return None
    inside = sum(1 for g in readings if low <= g <= high)
    return inside / len(readings) * 100.0

def variability_label(readings: list[int]) -> str:
    if len(readings) < 10:
        return "unknown"
    import statistics
    mean = statistics.mean(readings)
    if mean <= 0:
        return "unknown"
    stdev = statistics.pstdev(readings)
    cv = stdev / mean
    if cv < 0.15: return "low"
    if cv < 0.30: return "medium"
    return "high"

def compute_gaps_hours(points_ts: list[datetime], expected_step_min: int=5) -> float:
    if len(points_ts) < 2:
        return 0.0
    points_ts = sorted(points_ts)
    gap = 0.0
    for a, b in zip(points_ts, points_ts[1:]):
        dt_min = (b - a).total_seconds() / 60
        if dt_min > expected_step_min * 2:
            gap += max(0.0, dt_min - expected_step_min) / 60.0
    return gap

def get_glucose_points(db: Session, user_id: str, start: datetime, end: datetime):
    q = select(GlucoseReading).where(
        GlucoseReading.user_id == user_id,
        GlucoseReading.ts >= start,
        GlucoseReading.ts < end
    ).order_by(GlucoseReading.ts.asc())
    return db.execute(q).scalars().all()

def get_glucose_summary(db: Session, user_id: str, window: str):
    now = datetime.now(timezone.utc)
    delta = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}.get(window)
    if not delta:
        raise ValueError("invalid window")
    start = now - delta
    rows = get_glucose_points(db, user_id, start, now)
    readings = [r.glucose_mgdl for r in rows]
    ts = [r.ts for r in rows]
    return {
        "window": window,
        "avg": (sum(readings)/len(readings)) if readings else None,
        "min": min(readings) if readings else None,
        "max": max(readings) if readings else None,
        "tir_70_180_pct": compute_tir(readings),
        "variability": variability_label(readings),
        "gaps_hours": compute_gaps_hours(ts),
    }
```

### 8.2 用餐时间推断（backend/app/services/inference_service.py）
**backend/app/services/inference_service.py**
```python
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.glucose_service import get_glucose_points

def infer_meal_time_from_glucose(db: Session, user_id: str, uploaded_at: datetime) -> tuple[datetime | None, float]:
    """
    在上传附近窗口寻找“上升变点”，返回 (ts, confidence).
    MVP：简单 slope + 累计上升。
    """
    start = uploaded_at - timedelta(hours=2)
    end = uploaded_at + timedelta(hours=2)
    rows = get_glucose_points(db, user_id, start, end)
    if len(rows) < 10:
        return None, 0.0

    best = None
    best_score = 0.0
    for i in range(3, len(rows)):
        g_now = rows[i].glucose_mgdl
        g_prev = rows[i-3].glucose_mgdl
        dt_min = (rows[i].ts - rows[i-3].ts).total_seconds()/60
        if dt_min <= 0:
            continue
        slope = (g_now - g_prev) / dt_min
        rise = g_now - g_prev
        score = max(0.0, slope) * max(0.0, rise)
        if score > best_score:
            best_score = score
            best = rows[i-1].ts
    if not best:
        return None, 0.0
    conf = min(1.0, best_score / 200.0)
    return best, conf
```

### 8.3 Context Builder（backend/app/services/context_builder.py）
**backend/app/services/context_builder.py**
```python
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.meal import Meal
from app.models.symptom import Symptom
from app.services.glucose_service import get_glucose_summary

def build_user_context(db: Session, user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    summary_24h = get_glucose_summary(db, user_id, "24h")
    summary_7d = get_glucose_summary(db, user_id, "7d")

    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    meals = db.execute(
        select(Meal).where(Meal.user_id==user_id, Meal.meal_ts>=day_start, Meal.meal_ts<now).order_by(Meal.meal_ts.asc())
    ).scalars().all()

    symptoms = db.execute(
        select(Symptom).where(Symptom.user_id==user_id, Symptom.ts>=now-timedelta(days=7), Symptom.ts<now).order_by(Symptom.ts.desc()).limit(20)
    ).scalars().all()

    kcal_today = sum(m.kcal for m in meals) if meals else 0

    return {
        "profile": {},  # MVP: later join user_profile
        "glucose_summary": {"last_24h": summary_24h, "last_7d": summary_7d},
        "meals_today": [
            {"ts": m.meal_ts.isoformat(), "kcal": m.kcal, "tags": m.tags, "source": m.meal_ts_source.value, "photo_id": str(m.photo_id) if m.photo_id else None}
            for m in meals
        ],
        "symptoms_last_7d": [
            {"ts": s.ts.isoformat(), "severity": s.severity, "text": s.text}
            for s in symptoms
        ],
        "data_quality": {"glucose_gaps_hours": summary_24h["gaps_hours"], "kcal_today": kcal_today},
    }
```

### 8.4 Safety Layer（backend/app/services/safety_service.py）
**backend/app/services/safety_service.py**
```python
EMERGENCY_KEYWORDS = [
    "胸痛","昏厥","呼吸困难","意识模糊","抽搐","严重低血糖","严重高血糖",
    "seizure","faint","chest pain","shortness of breath"
]

def detect_safety_flags(user_message: str) -> list[str]:
    msg = user_message.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw.lower() in msg:
            return ["emergency_symptom"]
    return []

def emergency_template() -> str:
    return (
        "**重要提示：**你描述的情况可能需要及时医疗评估。\n\n"
        "- 如果症状严重或加重，请立即联系当地急救/就医。\n"
        "- 如果你有已知糖尿病或用药史，请遵循医生给你的紧急处理方案。\n"
        "- 你也可以告诉我：症状开始时间、是否伴随出汗/心慌/意识模糊、最近一次进食与血糖读数。"
    )
```

---

## 9) Backend：LLM Provider 适配层（可切换 & 可 mock）
（略：见上文 providers/base.py、openai_provider.py、gemini_provider.py）

---

## 10) Backend：对象存储（S3 presigned upload）
（略：见上文 services/meal_service.py）

---

## 11) Backend：Routers（接口契约）
（略：见上文 routers/auth.py、glucose.py、meals.py、dashboard.py、chat.py）

---

## 12) Frontend：关键 SSE/Upload 组件
（略：见上文 MealUploadCard、MealTimeConfirmModal、useSSEChat、ChatPanel）

---

## 13) Docker Compose & Dockerfile
（略：见上文）

---

## 14) 测试
（略：见上文）

---

## 15) Codex 顶层指令（直接贴给 Codex）
```text
请按此白皮书逐文件生成一个可运行的前后端分离项目。要求：
1) 严格按给定目录结构创建文件；
2) backend 用 FastAPI + SQLAlchemy + Alembic + Celery + Redis + Postgres；
3) frontend 用 Vite + React + TS + Tailwind + React Query；
4) docker-compose 一键启动并能跑通最小闭环：注册登录、导入血糖、上传餐图、创建 meal、Chat SSE 输出；
5) 所有 API 必须实现并符合契约；返回结构一致；错误码规范；
6) LLM provider 适配层必须可切换，并提供 MockProvider 供测试；
7) 完成后补齐 TODO：解析 OpenAI Responses JSON 到结构化对象；Gemini endpoint 按官方文档替换；
8) 写最小的 pytest 单测与 Playwright E2E。
```
