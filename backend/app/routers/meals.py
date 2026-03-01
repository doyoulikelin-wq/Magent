from datetime import datetime
import os

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.models.meal import Meal, MealPhoto, MealTsSource
from app.schemas.meal import (
    MealCreate,
    MealOut,
    MealPhotoOut,
    MealUpdate,
    PhotoCompleteRequest,
    PresignRequest,
    PresignResponse,
)
from app.services.meal_service import (
    build_mock_upload_url,
    create_photo_record,
    ensure_local_storage_path,
    generate_object_key,
    process_photo_sync,
)
from app.workers.tasks import process_meal_photo

router = APIRouter()


@router.post("/photo/upload-url", response_model=PresignResponse)
def meal_photo_upload_url(
    payload: PresignRequest,
    user_id: str = Depends(get_current_user_id),
):
    object_key = generate_object_key(user_id, payload.filename)
    return PresignResponse(upload_url=build_mock_upload_url(object_key), object_key=object_key, expires_in=900)


@router.put("/photo/mock-upload/{object_key:path}")
async def mock_photo_upload(
    object_key: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    if f"/{user_id}/" not in f"/{object_key}/":
        raise HTTPException(status_code=403, detail={"error_code": "FORBIDDEN_KEY", "message": "Object key mismatch"})

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail={"error_code": "EMPTY_FILE", "message": "File is empty"})

    local_path = ensure_local_storage_path(object_key)
    with open(local_path, "wb") as f:
        f.write(content)

    return {"ok": True, "object_key": object_key, "bytes": os.path.getsize(local_path)}


@router.post("/photo/complete", response_model=MealPhotoOut)
def meal_photo_complete(
    payload: PhotoCompleteRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    photo = create_photo_record(db, user_id, payload.object_key, payload.exif_ts)

    # Celery async; fallback sync if broker isn't available.
    try:
        process_meal_photo.delay(str(photo.id))
    except Exception:  # noqa: BLE001
        photo = process_photo_sync(db, photo)

    suggested_ts = None
    suggested_conf = None
    if isinstance(photo.vision_json, dict):
        raw_ts = photo.vision_json.get("inferred_meal_ts")
        if raw_ts:
            suggested_ts = datetime.fromisoformat(raw_ts)
            suggested_conf = photo.vision_json.get("inferred_confidence")

    return MealPhotoOut(
        id=str(photo.id),
        uploaded_at=photo.uploaded_at,
        status=photo.status.value,
        calorie_estimate_kcal=photo.calorie_estimate_kcal,
        confidence=photo.confidence,
        vision_json=photo.vision_json,
        suggested_meal_ts=suggested_ts,
        suggested_confidence=suggested_conf,
    )


@router.get("/photo/{photo_id}", response_model=MealPhotoOut)
def get_photo(
    photo_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    photo = db.execute(
        select(MealPhoto).where(MealPhoto.id == photo_id, MealPhoto.user_id == user_id)
    ).scalars().first()
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    suggested_ts = None
    suggested_conf = None
    if isinstance(photo.vision_json, dict):
        raw_ts = photo.vision_json.get("inferred_meal_ts")
        if raw_ts:
            suggested_ts = datetime.fromisoformat(raw_ts)
            suggested_conf = photo.vision_json.get("inferred_confidence")

    return MealPhotoOut(
        id=str(photo.id),
        uploaded_at=photo.uploaded_at,
        status=photo.status.value,
        calorie_estimate_kcal=photo.calorie_estimate_kcal,
        confidence=photo.confidence,
        vision_json=photo.vision_json,
        suggested_meal_ts=suggested_ts,
        suggested_confidence=suggested_conf,
    )


@router.post("", response_model=MealOut)
def create_meal(
    payload: MealCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    meal = Meal(
        user_id=user_id,
        meal_ts=payload.meal_ts,
        meal_ts_source=MealTsSource(payload.meal_ts_source),
        kcal=payload.kcal,
        tags=payload.tags,
        photo_id=payload.photo_id,
        notes=payload.notes,
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)

    return MealOut(
        id=str(meal.id),
        meal_ts=meal.meal_ts,
        meal_ts_source=meal.meal_ts_source.value,
        kcal=meal.kcal,
        tags=meal.tags,
        notes=meal.notes,
        photo_id=str(meal.photo_id) if meal.photo_id else None,
    )


@router.patch("/{meal_id}", response_model=MealOut)
def update_meal(
    meal_id: str,
    payload: MealUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    meal = db.execute(select(Meal).where(Meal.id == meal_id, Meal.user_id == user_id)).scalars().first()
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal not found")

    if payload.meal_ts is not None:
        meal.meal_ts = payload.meal_ts
    if payload.meal_ts_source is not None:
        meal.meal_ts_source = MealTsSource(payload.meal_ts_source)
    if payload.kcal is not None:
        meal.kcal = payload.kcal
    if payload.tags is not None:
        meal.tags = payload.tags
    if payload.notes is not None:
        meal.notes = payload.notes

    db.add(meal)
    db.commit()
    db.refresh(meal)

    return MealOut(
        id=str(meal.id),
        meal_ts=meal.meal_ts,
        meal_ts_source=meal.meal_ts_source.value,
        kcal=meal.kcal,
        tags=meal.tags,
        notes=meal.notes,
        photo_id=str(meal.photo_id) if meal.photo_id else None,
    )


@router.get("", response_model=list[MealOut])
def list_meals(
    from_ts: datetime = Query(alias="from"),
    to_ts: datetime = Query(alias="to"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Meal)
        .where(
            Meal.user_id == user_id,
            Meal.meal_ts >= from_ts,
            Meal.meal_ts < to_ts,
        )
        .order_by(Meal.meal_ts.desc())
    ).scalars().all()

    return [
        MealOut(
            id=str(m.id),
            meal_ts=m.meal_ts,
            meal_ts_source=m.meal_ts_source.value,
            kcal=m.kcal,
            tags=m.tags,
            notes=m.notes,
            photo_id=str(m.photo_id) if m.photo_id else None,
        )
        for m in rows
    ]
