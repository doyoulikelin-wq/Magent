from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.meal import MealPhoto, PhotoStatus
from app.services.meal_service import process_photo_sync

logger = get_task_logger(__name__)


from app.workers.celery_app import celery_app


@celery_app.task(name="process_meal_photo")
def process_meal_photo(photo_id: str) -> None:
    db = SessionLocal()
    photo = None
    try:
        photo = db.execute(select(MealPhoto).where(MealPhoto.id == photo_id)).scalars().first()
        if photo is None:
            logger.warning("photo not found", extra={"photo_id": photo_id})
            return

        process_photo_sync(db, photo)
    except Exception:  # noqa: BLE001
        logger.exception("meal photo processing failed", extra={"photo_id": photo_id})
        if photo is not None:
            photo.status = PhotoStatus.failed
            db.add(photo)
            db.commit()
    finally:
        db.close()
