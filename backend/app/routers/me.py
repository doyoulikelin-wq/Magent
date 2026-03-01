from fastapi import APIRouter, Depends

from app.core.deps import get_current_user_id, get_db
from app.routers.users import me as me_impl

router = APIRouter()


@router.get('/me')
def me_alias(user_id: str = Depends(get_current_user_id), db=Depends(get_db)):
    return me_impl(user_id=user_id, db=db)
