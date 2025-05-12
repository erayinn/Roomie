from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from models import Hotel, Room
from routers.user import get_current_user

router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="templates")

# ---- Bağımlılıklar ----
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# ---- HTML Form Sayfası: Oda Ekleme ----
@router.get("/create", response_class=HTMLResponse)
async def render_create_room_page(request: Request, db: db_dependency, user: user_dependency):
    hotel = db.query(Hotel).filter(Hotel.manager_id == user["id"]).first()
    if not hotel:
        raise HTTPException(status_code=403, detail="Yetkiniz yok")
    return templates.TemplateResponse("room_create.html", {"request": request, "user": user})

# ---- POST: Oda Ekle ----
@router.post("/create", response_class=RedirectResponse)
async def create_room(
    user: user_dependency,
    db: db_dependency,
    room_type: str = Form(...),
    price: int = Form(...),
    capacity: int = Form(...),
    availability: bool = Form(...)
):
    hotel = db.query(Hotel).filter(Hotel.manager_id == user["id"]).first()
    if not hotel:
        raise HTTPException(status_code=401, detail="Yetkisiz")

    new_room = Room(
        hotel_id=hotel.id,
        room_type=room_type,
        price=price,
        capacity=capacity,
        availability=availability
    )
    db.add(new_room)
    db.commit()
    return RedirectResponse(url="/hotels/manage", status_code=302)

# ---- HTML Form Sayfası: Oda Düzenleme ----
@router.get("/edit/{room_id}", response_class=HTMLResponse)
async def render_edit_room_page(
    request: Request,
    user: user_dependency,
    db: db_dependency,
    room_id: int = Path(gt=0)
):
    room = db.query(Room).join(Hotel).filter(
        Room.id == room_id,
        Hotel.manager_id == user["id"]
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Oda bulunamadı veya yetki yok")

    return templates.TemplateResponse("room_edit.html", {
        "request": request,
        "user": user,
        "room": room
    })

# ---- POST: Oda Güncelle ----
@router.post("/update/{room_id}")
async def update_room_post(
    user: user_dependency,
    db: db_dependency,
    room_id: int,
    room_type: str = Form(...),
    price: int = Form(...),
    capacity: int = Form(...),
    availability: bool = Form(...)
):
    room = db.query(Room).join(Hotel).filter(
        Room.id == room_id,
        Hotel.manager_id == user["id"]
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Oda bulunamadı")

    room.room_type = room_type
    room.price = price
    room.capacity = capacity
    room.availability = availability
    db.commit()

    return RedirectResponse(url="/hotels/manage", status_code=302)

# ---- Oda Silme ----
@router.post("/delete/{room_id}")
async def delete_room_post(
    user: user_dependency,
    db: db_dependency,
    room_id: int
):
    room = db.query(Room).join(Hotel).filter(
        Room.id == room_id,
        Hotel.manager_id == user["id"]
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Oda bulunamadı")

    db.delete(room)
    db.commit()
    return RedirectResponse(url="/hotels/manage", status_code=302)
