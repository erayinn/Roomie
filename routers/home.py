from typing import Optional, Annotated
from routers.user import get_current_user
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Hotel

router = APIRouter()

templates = Jinja2Templates(directory="templates")

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# Ana sayfa
@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: db_dependency):
    token = request.cookies.get("access_token")
    user = None
    try:
        user = await get_current_user(request)  # ✅ sadece request gönderiyoruz
    except:
        user = None

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user
        }
    )

# Arama sonucu
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
        guests = int(guests) if guests else 1
    except ValueError:
        guests = 1

    hotels = db.query(Hotel).filter(Hotel.location.ilike(f"%{location}%")).all()

    hotel_data = []
    for hotel in hotels:
        if hotel.rooms:
            available_rooms = [room for room in hotel.rooms if room.availability and room.capacity >= guests]
            if available_rooms:
                min_price = min(room.price for room in available_rooms)
            else:
                min_price = None
        else:
            min_price = None

        hotel_data.append({
            "id": hotel.id,
            "name": hotel.name,
            "location": hotel.location,
            "image_url": hotel.image_url if hotel.image_url else "https://via.placeholder.com/400x200",
            "min_price": min_price
        })

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "hotels": hotel_data,
            "search_done": True
        }
    )

