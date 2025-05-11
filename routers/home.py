from typing import Optional, Annotated
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal
from models import Hotel
from routers.user import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Veritabanı bağımlılığı
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# ---------- Ana Sayfa ----------
@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: db_dependency):
    try:
        user = await get_current_user(request)
    except:
        user = None

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user
    })

# ---------- Arama Sayfası ----------
@router.get("/search", response_class=HTMLResponse)
async def show_search_form(request: Request):
    try:
        user = await get_current_user(request)
    except:
        user = None

    return templates.TemplateResponse("search.html", {
        "request": request,
        "user": user,
        "search_done": False
    })

# ---------- Arama İşleme ----------
@router.post("/search", response_class=HTMLResponse)
async def search_hotels(
    request: Request,
    location: str = Form(...),
    checkin_date: str = Form(...),
    checkout_date: str = Form(...),
    guests: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request)
    except:
        user = None

    try:
        checkin_date_obj = datetime.strptime(checkin_date, "%Y-%m-%d").date()
        checkout_date_obj = datetime.strptime(checkout_date, "%Y-%m-%d").date()
    except ValueError:
        return templates.TemplateResponse("search.html", {
            "request": request,
            "user": user,
            "error": "Geçerli bir tarih giriniz.",
            "search_done": True
        })

    guests = int(guests) if guests else 1
    hotels = db.query(Hotel).filter(Hotel.location.ilike(f"%{location}%")).all()

    filtered_hotels = []

    for hotel in hotels:
        available_rooms = []
        for room in hotel.rooms:
            if room.capacity < guests:
                continue

            is_available = True
            for res in room.reservations:
                if not (res.check_out <= checkin_date_obj or res.check_in >= checkout_date_obj):
                    is_available = False
                    break

            if is_available:
                available_rooms.append(room)

        if available_rooms:
            filtered_hotels.append({
                "id": hotel.id,
                "name": hotel.name,
                "location": hotel.location,
                "image_url": hotel.image_url or "https://via.placeholder.com/400x200",
                "min_price": min(r.price for r in available_rooms)
            })

    return templates.TemplateResponse("search.html", {
        "request": request,
        "user": user,
        "hotels": filtered_hotels,
        "search_done": True,
        "checkin_date": checkin_date_obj,
        "checkout_date": checkout_date_obj,
        "guests": guests,
        "location": location
    })
