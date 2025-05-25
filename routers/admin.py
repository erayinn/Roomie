# routers/admin.py

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Annotated
from collections import defaultdict
from datetime import timedelta
from fastapi import status
from fastapi.responses import RedirectResponse
from database import SessionLocal
from models import Hotel, Room, Reservation,SupportTicket
from routers.user import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}}
)

templates = Jinja2Templates(directory="templates")

# --- DB Bağımlılığı ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

def redirect_to_login():
    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url="/user/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# ------------------ Admin Dashboard ------------------

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: db_dependency):
    user = await get_current_user(request)
    if not user or user.get("user_type") != "admin":
        return redirect_to_login()

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user": user
    })

# ------------------ Dashboard JSON Verisi ------------------

@router.get("/data")
async def admin_dashboard_data(user: user_dependency, db: db_dependency):
    if not user or user.get("user_type") != "admin":
        return {"error": "Yetkisiz erişim"}

    hotels = db.query(Hotel).filter(Hotel.is_approved == True).all()
    hotel_ids = [hotel.id for hotel in hotels]
    rooms = db.query(Room).filter(Room.hotel_id.in_(hotel_ids)).all()
    room_ids = [room.id for room in rooms]
    reservations = db.query(Reservation).filter(Reservation.room_id.in_(room_ids)).all()
    approved_reservations = [r for r in reservations if r.status == "approved"]

    # Metrikler
    total_rooms = len(rooms)
    total_reservations = len(approved_reservations)
    pending_reservations = sum(1 for r in reservations if r.status == "pending")
    total_income = sum(r.total_price for r in approved_reservations)
    avg_price = round(sum(room.price for room in rooms) / total_rooms, 2) if total_rooms else 0

    # Grafik verisi
    reservations_per_day = defaultdict(int)
    for r in approved_reservations:
        current = r.check_in
        while current <= r.check_out:
            date_str = current.strftime('%Y-%m-%d')
            reservations_per_day[date_str] += 1
            current += timedelta(days=1)

    sorted_daily = sorted(reservations_per_day.items())
    labels = [item[0] for item in sorted_daily]
    counts = [item[1] for item in sorted_daily]

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
@router.get("/pending-hotels", response_class=HTMLResponse)
async def pending_hotels(request: Request, db: db_dependency, user: user_dependency):
    if user["user_type"] != "admin":
        return redirect_to_login()

    hotels = db.query(Hotel).filter(Hotel.is_approved == False).all()

    return templates.TemplateResponse("admin_pending_hotels.html", {
        "request": request,
        "user": user,
        "pending_hotels": hotels
    })
@router.post("/approve/{hotel_id}")
async def approve_hotel(hotel_id: int, db: db_dependency, user: user_dependency):
    if user["user_type"] != "admin":
        return redirect_to_login()

    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Otel bulunamadı.")

    hotel.is_approved = True
    db.commit()

    return RedirectResponse(url="/admin/pending-hotels", status_code=status.HTTP_302_FOUND)


@router.post("/reject/{hotel_id}")
async def reject_hotel(hotel_id: int, db: db_dependency, user: user_dependency):
    if user["user_type"] != "admin":
        return redirect_to_login()

    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Otel bulunamadı.")

    db.delete(hotel)
    db.commit()

    return RedirectResponse(url="/admin/pending-hotels", status_code=status.HTTP_302_FOUND)

@router.get("/support", response_class=HTMLResponse)
async def view_support_tickets(request: Request, db: db_dependency):
    user = await get_current_user(request)
    if not user or user.get("user_type") != "admin":
        return redirect_to_login()

    tickets = db.query(SupportTicket).order_by(SupportTicket.created_at.desc()).all()
    return templates.TemplateResponse("admin_support.html", {
        "request": request,
        "user": user,
        "tickets": tickets
    })

@router.post("/support/update", response_class=RedirectResponse)
async def update_ticket_status(
    request: Request,
    db: db_dependency,
    user: user_dependency,
    ticket_id: int = Form(...),
    status: str = Form(...)
):
    if user["user_type"] != "admin":
        return redirect_to_login()

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if ticket:
        ticket.status = status
        db.commit()
    return RedirectResponse(url="/admin/support", status_code=303)
