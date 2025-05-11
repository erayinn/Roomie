from datetime import datetime
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import SessionLocal
from routers.user import get_current_user
from models import Hotel

router = APIRouter(prefix="/hotels", tags=["hotels"])
templates = Jinja2Templates(directory="templates")

# ----- MODELLER -----
class HotelRequest(BaseModel):
    name: str
    description: str
    location: str
    phone_number: str
    email: str

# ----- DEPENDENCIES -----
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# ----- TÜM OTELLER LİSTESİ -----
@router.get("/", response_class=HTMLResponse)
async def list_all_hotels(request: Request, db: db_dependency):
    user = None
    try:
        user = await get_current_user(request)
    except:
        pass

    hotels = db.query(Hotel).all()
    return templates.TemplateResponse("hotels.html", {
        "request": request,
        "hotels": hotels,
        "user": user
    })

# ----- OTEL GÜNCELLEME -----
@router.put("/{hotel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def updaate_hotel(
    user: user_dependency,
    db: db_dependency,
    hotelrequest: HotelRequest,
    hotel_id: int = Path(gt=0)
):
    if user.get("id") != db.query(Hotel).filter(Hotel.id == hotel_id).first().manager_id:
        raise HTTPException(status_code=401, detail="User is not authorized to update this hotel")

    hotel = db.query(Hotel).filter(Hotel.id == hotel_id, Hotel.manager_id == user.get("id")).first()
    if hotel is None:
        raise HTTPException(status_code=404, detail="Hotel not found")

    for field, value in hotelrequest.dict().items():
        setattr(hotel, field, value)

    db.commit()

# ----- OTEL DETAY + ARAMA VERİLERİ -----
@router.get("/{hotel_id}", response_class=HTMLResponse)
async def get_hotel_detail(
    request: Request,
    db: db_dependency,
    hotel_id: int = Path(gt=0)
):
    try:
        user = await get_current_user(request)
    except:
        user = None

    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()

    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")

    # Query parametreleri al
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

                is_available = True
                for res in room.reservations:
                    if not (res.check_out <= checkin_date or res.check_in >= checkout_date):
                        is_available = False
                        break

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
        "user": user  # ✅ EKLENDİ
    })

