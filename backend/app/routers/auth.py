import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.consent import Consent
from app.models.glucose import GlucoseReading
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.user import (
    AuthResponse,
    LoginRequest,
    SignupRequest,
    SubjectInfo,
    SubjectLoginRequest,
)
from app.services.etl.glucose_etl import _parse_clarity_csv  # noqa: PLC2701

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Resolve data directories ───────────────────────────────

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_LIVER_DIR = Path(__file__).resolve().parents[3] / "fatty_liver_data_raw"


def _discover_subjects() -> list[SubjectInfo]:
    """Scan filesystem for available SC / Liver subjects."""
    subjects: list[SubjectInfo] = []

    # SC subjects — one Clarity CSV per subject
    glucose_dir = _DATA_DIR / "glucose"
    if glucose_dir.is_dir():
        for f in sorted(glucose_dir.glob("Clarity_Export_SC*.csv")):
            m = re.search(r"SC\d+", f.name)
            if m:
                subjects.append(
                    SubjectInfo(
                        subject_id=m.group(),
                        cohort="cgm",
                        has_meals=True,
                        has_glucose=True,
                    )
                )

    # Liver subjects — xls files in 监测数据
    monitor_dir = _LIVER_DIR / "监测数据"
    if monitor_dir.is_dir():
        seen: set[str] = set()
        for f in sorted(monitor_dir.iterdir()):
            m = re.search(r"Liver-\d+", f.name)
            if m and m.group() not in seen:
                seen.add(m.group())
                subjects.append(
                    SubjectInfo(
                        subject_id=m.group(),
                        cohort="liver",
                        has_meals=False,
                        has_glucose=True,
                    )
                )

    return subjects


# ── Subject listing ──────────────────────────────────────────


@router.get("/subjects", response_model=list[SubjectInfo])
def list_subjects():
    """Return all available study subjects from the data directory."""
    return _discover_subjects()


# ── Subject login (no password) ──────────────────────────────


@router.post("/login-subject", response_model=AuthResponse)
def login_subject(payload: SubjectLoginRequest, db: Session = Depends(get_db)):
    """Log in as a study subject.  Creates user + profile on first login."""
    sid = payload.subject_id.strip()

    # Validate subject exists on disk
    known = {s.subject_id: s for s in _discover_subjects()}
    if sid not in known:
        raise HTTPException(status_code=404, detail=f"Subject {sid} not found")

    info = known[sid]

    # Find existing profile
    profile = db.execute(
        select(UserProfile).where(UserProfile.subject_id == sid)
    ).scalars().first()

    if profile and profile.user_id:
        # Already has a linked user → auto-import if needed, then return token
        _auto_import_glucose(db, profile.user_id, sid, info.cohort)
        return AuthResponse(access_token=create_access_token(str(profile.user_id)))

    # Create user (use subject_id as email placeholder)
    email_placeholder = f"{sid.lower()}@metabodash.local"
    user = db.execute(select(User).where(User.email == email_placeholder)).scalars().first()
    if not user:
        user = User(
            email=email_placeholder,
            password_hash=hash_password(uuid.uuid4().hex),  # random password
        )
        db.add(user)
        db.flush()

        consent = Consent(
            id=uuid.uuid4(),
            user_id=user.id,
            allow_ai_chat=True,
            allow_data_upload=True,
        )
        db.add(consent)

    # Create or link profile
    if not profile:
        profile = UserProfile(
            subject_id=sid,
            user_id=user.id,
            cohort=info.cohort,
        )
        db.add(profile)
    else:
        profile.user_id = user.id

    db.commit()

    # Auto-import glucose data for the subject on first login
    _auto_import_glucose(db, user.id, sid, info.cohort)

    return AuthResponse(access_token=create_access_token(str(user.id)))


def _auto_import_glucose(db: Session, user_id: uuid.UUID, subject_id: str, cohort: str) -> None:
    """If the user has no glucose data, import from the subject's CSV."""
    count = db.execute(
        select(func.count()).select_from(GlucoseReading).where(GlucoseReading.user_id == user_id)
    ).scalar() or 0
    if count > 0:
        return  # Already has data

    if cohort == "cgm":
        csv_path = _DATA_DIR / "glucose" / f"Clarity_Export_{subject_id}.csv"
        if csv_path.is_file():
            rows = _parse_clarity_csv(csv_path)
            for row in rows:
                db.add(GlucoseReading(
                    user_id=user_id,
                    ts=row["ts"],
                    glucose_mgdl=row["glucose_mgdl"],
                    source="auto_import",
                    meta={},
                ))
            db.commit()
            logger.info("Auto-imported %d glucose readings for %s", len(rows), subject_id)


# ── Classic email / password ─────────────────────────────────


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.email == payload.email)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail={"error_code": "EMAIL_EXISTS", "message": "Email already exists"})

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()

    consent = Consent(id=uuid.uuid4(), user_id=user.id, allow_ai_chat=False, allow_data_upload=True)
    db.add(consent)
    db.commit()
    db.refresh(user)

    return AuthResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalars().first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid credentials"})

    return AuthResponse(access_token=create_access_token(str(user.id)))


@router.post("/logout")
def logout():
    return {"ok": True}
