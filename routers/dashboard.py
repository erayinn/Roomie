# routers/dashboard.py

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Annotated

from database import SessionLocal
from models import Hotel, Room, Reservation
from routers.user import get_current_user

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="templates")

# --- DB ve kullanıcı bağımlılıkları ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

def redirect_to_login():
    response = RedirectResponse(url="/user/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# ----------------- HTML Dashboard Sayfası -----------------

@router.get("/", response_class=HTMLResponse)
async def manager_dashboard(request: Request, db: db_dependency):
    user = await get_current_user(request)
    if user.get("user_type") != "manager":
        return redirect_to_login()

    hotel = db.query(Hotel).filter(Hotel.manager_id == user["id"]).first()

    # Eğer otel yoksa veya henüz onaylanmamışsa sadece bilgilendirme mesajı göster
    if not hotel:
        return RedirectResponse(url="/hotels/create", status_code=302)

    if not hotel.is_approved:
        return templates.TemplateResponse("pending_approval.html", {
            "request": request,
            "user": user,
            "message": "Otelinizin onaylanması bekleniyor. Yönetici paneline erişim için lütfen onay sürecini tamamlayın."
        })

    # Otel onaylıysa normal dashboard içeriğini göster
    rooms = hotel.rooms
    reservations = [r for room in rooms for r in room.reservations]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "hotel": hotel,
        "rooms": rooms,
        "reservations": reservations
    })

# ----------------- JSON API: Gerçek Zamanlı Dashboard Verisi -----------------

@router.get("/data", response_class=JSONResponse)
async def dashboard_data(user: user_dependency, db: db_dependency):
    if not user or user.get("user_type") != "manager":
        return JSONResponse(status_code=403, content={"error": "Yetkisiz erişim"})

    hotel = db.query(Hotel).filter(Hotel.manager_id == user["id"]).first()
    if not hotel:
        return {
            "total_rooms": 0,
            "total_reservations": 0,
            "pending_reservations": 0,
            "total_income": 0,
            "avg_price": 0,
            "reservations_per_day": {"labels": [], "counts": []}
        }

    rooms = db.query(Room).filter(Room.hotel_id == hotel.id).all()
    room_ids = [room.id for room in rooms]

    reservations = db.query(Reservation).filter(Reservation.room_id.in_(room_ids)).all()

    # ✅ Sadece onaylılar
    approved_reservations = [r for r in reservations if r.status == "approved"]

    # Metrikler
    total_rooms = len(rooms)
    total_reservations = len(approved_reservations)  # ✅ sadece approved
    pending_reservations = sum(1 for r in reservations if r.status == "pending")
    total_income = sum(r.total_price for r in approved_reservations)
    avg_price = round(sum(room.price for room in rooms) / total_rooms, 2) if total_rooms else 0

    # ✅ Günlük grafik: check-in ile check-out arasındaki her günü say
    reservations_per_day = defaultdict(int)
    for r in approved_reservations:
        current = r.check_in
        while current <= r.check_out:
            date_str = current.strftime('%Y-%m-%d')
            reservations_per_day[date_str] += 1
            current += timedelta(days=1)

    sorted_daily = sorted(reservations_per_day.items())
    labels = [d[0] for d in sorted_daily]
    counts = [d[1] for d in sorted_daily]

    return {
        "total_rooms": total_rooms,
        "total_reservations": total_reservations,
        "pending_reservations": pending_reservations,
        "total_income": total_income,
        "avg_price": avg_price,
        "reservations_per_day": {
            "labels": labels,
            "counts": counts
        }
    }
