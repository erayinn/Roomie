from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import shutil
import os
from pydantic import BaseModel
from starlette import status

from database import SessionLocal
from routers.user import get_current_user
from models import Hotel, Room

router = APIRouter(prefix="/hotels", tags=["hotels"])
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

class HotelRequest(BaseModel):
    name: str
    description: str
    location: str
    phone_number: str
    email: str

# ------------------ Oteller listesi ------------------
@router.get("/", response_class=HTMLResponse)
async def list_all_hotels(request: Request, db: db_dependency):
    try:
        user = await get_current_user(request)
    except:
        user = None
    hotels = db.query(Hotel).all()
    return templates.TemplateResponse("hotels.html", {
        "request": request,
        "hotels": hotels,
        "user": user
    })
# ------------------ Otel yönetim paneli ------------------
@router.get("/manage", response_class=HTMLResponse)
async def manage_hotel(request: Request, db: db_dependency):
    user = await get_current_user(request)
    if user.get("user_type") != "manager":
        return RedirectResponse(url="/user/login", status_code=302)

    hotel = db.query(Hotel).filter(Hotel.manager_id == user["id"]).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    rooms = hotel.rooms
    return templates.TemplateResponse("manage_hotel.html", {
        "request": request,
        "user": user,
        "hotel": hotel,
        "rooms": rooms
    })

# ------------------ Otel detay sayfası ------------------
@router.get("/{hotel_id}", response_class=HTMLResponse)
async def get_hotel_detail(request: Request, db: db_dependency, hotel_id: int = Path(gt=0)):
    try:
        user = await get_current_user(request)
    except:
        user = None

    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if hotel is None:
        raise HTTPException(status_code=404, detail="Hotel not found")

    checkin_date = request.query_params.get("checkin_date")
    checkout_date = request.query_params.get("checkout_date")
    guests = request.query_params.get("guests")

    available_rooms = []

    if checkin_date and checkout_date:
        try:
            checkin_date = datetime.strptime(checkin_date, "%Y-%m-%d").date()
            checkout_date = datetime.strptime(checkout_date, "%Y-%m-%d").date()
            guests = int(guests) if guests else 1

            for room in hotel.rooms:
                if room.capacity < guests:
                    continue

                is_available = all(res.check_out <= checkin_date or res.check_in >= checkout_date for res in room.reservations)
                if is_available:
                    available_rooms.append(room)
        except:
            available_rooms = hotel.rooms
    else:
        available_rooms = hotel.rooms

    return templates.TemplateResponse("hotel_detail.html", {
        "request": request,
        "hotel": hotel,
        "rooms": available_rooms,
        "checkin_date": checkin_date,
        "checkout_date": checkout_date,
        "guests": guests,
        "user": user
    })
# ------------------ Otel güncelleme ------------------
@router.post("/update/{hotel_id}")
async def update_hotel(
    db: db_dependency,
    user: user_dependency,
    hotel_id: int,
    name: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(...),
    image_file: UploadFile = File(None),

):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id, Hotel.manager_id == user["id"]).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    if image_file:
        filename = f"{hotel_id}_{image_file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        hotel.image_url = f"/{filepath.replace(os.sep, '/')}"

    hotel.name = name
    hotel.description = description
    hotel.location = location
    hotel.phone_number = phone_number
    hotel.email = email

    db.commit()
    return RedirectResponse(url="/hotels/manage", status_code=302)
@router.post("/rooms/create/{hotel_id}")
async def create_room(
    db: db_dependency,
    user: user_dependency,
    hotel_id: int,
    room_type: str = Form(...),
    price: int = Form(...),
    capacity: int = Form(...),
    availability: bool = Form(False),
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id, Hotel.manager_id == user["id"]).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    room = Room(room_type=room_type, price=price, capacity=capacity, availability=availability, hotel_id=hotel_id)
    db.add(room)
    db.commit()
    return RedirectResponse(url="/hotels/manage", status_code=302)


@router.post("/rooms/update/{room_id}")
async def update_room(
    db: db_dependency,
    user: user_dependency,
    room_id: int,
    room_type: str = Form(...),
    price: int = Form(...),
    capacity: int = Form(...),
    availability: bool = Form(False)
):
    room = db.query(Room).join(Hotel).filter(Room.id == room_id, Hotel.manager_id == user["id"]).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    room.room_type = room_type
    room.price = price
    room.capacity = capacity
    room.availability = availability
    db.commit()
    return RedirectResponse(url="/hotels/manage", status_code=302)


@router.post("/rooms/delete/{room_id}")
async def delete_room(room_id: int, db: db_dependency, user: user_dependency):
    room = db.query(Room).join(Hotel).filter(Room.id == room_id, Hotel.manager_id == user["id"]).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    db.delete(room)
    db.commit()
    return RedirectResponse(url="/hotels/manage", status_code=302)
