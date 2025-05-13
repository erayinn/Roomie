from typing import Annotated
from fastapi import APIRouter, Depends, Path, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, timedelta

from database import SessionLocal
from models import Reservation, Room, Hotel
from routers.user import get_current_user

router = APIRouter(
    prefix="/res",
    tags=["reservations"],
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="templates")

# ----------------- DB ve User Bağımlılıkları -----------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

def redirect_to_login(request: Request = None):
    response = RedirectResponse(url="/user/login", status_code=302)
    response.delete_cookie("access_token")

    if request:
        path = request.url.path
        if path not in ["/user/login", "/user/register"]:
            response.set_cookie("redirect_after_login", path, max_age=300)

    return response

# ----------------- Form Modeli -----------------

class ReservationRequest:
    def __init__(
        self,
        room_id: int = Form(...),
        check_in: date = Form(...),
        check_out: date = Form(...)
    ):
        self.room_id = room_id
        self.check_in = check_in
        self.check_out = check_out

# ----------------- Kullanıcı: Rezervasyonlarım -----------------

@router.get("/myres")
async def render_myres_page(request: Request, db: db_dependency):
    user = await get_current_user(request)
    if user is None:
        return redirect_to_login()

    reservations = db.query(Reservation)\
        .filter(Reservation.user_id == user["id"])\
        .all()

    # "pending" olanları en üste taşı
    reservations = sorted(reservations, key=lambda r: (r.status != "pending", -r.check_in.toordinal()))

    return templates.TemplateResponse("res.html", {
        "request": request,
        "user": user,
        "ress": reservations
    })

# ----------------- Rezervasyon Oluşturma -----------------

@router.get("/create_res")
async def render_create_res_page(request: Request, db: db_dependency, room_id: int = None,
                                 checkin_date: str = None, checkout_date: str = None, guests: int = None):
    user = await get_current_user(request)
    if user is None:
        return redirect_to_login()

    room_price = 0
    booked_dates = []

    if room_id:
        room = db.query(Room).filter(Room.id == room_id).first()
        if room:
            room_price = room.price
            reservations = db.query(Reservation).filter(
                Reservation.room_id == room_id,
                Reservation.status.in_(["pending", "approved"])
            ).all()
            for r in reservations:
                current = r.check_in
                while current <= r.check_out:
                    booked_dates.append(current.strftime('%Y-%m-%d'))
                    current += timedelta(days=1)

    return templates.TemplateResponse("add-res.html", {
        "request": request,
        "user": user,
        "room_id": room_id,
        "checkin_date": checkin_date,
        "checkout_date": checkout_date,
        "guests": guests,
        "room_price": room_price,
        "booked_dates": booked_dates
    })


@router.post("/", status_code=201)
async def create_res(request: Request, user: user_dependency, db: db_dependency, resrequest: ReservationRequest = Depends()):
    if user is None:
        return redirect_to_login()

    room = db.query(Room).filter(Room.id == resrequest.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Tarih çakışması kontrolü
    conflict = db.query(Reservation).filter(
        Reservation.room_id == resrequest.room_id,
        Reservation.status.in_(["pending", "approved"]),
        Reservation.check_in <= resrequest.check_out,
        Reservation.check_out >= resrequest.check_in
    ).first()

    if conflict:
        return templates.TemplateResponse("add-res.html", {
            "request": request,
            "user": user,
            "room_id": resrequest.room_id,
            "checkin_date": resrequest.check_in,
            "checkout_date": resrequest.check_out,
            "room_price": room.price,
            "booked_dates": [],  # gerekirse tekrar hesaplanabilir
            "error_message": "Seçilen tarih aralığında başka bir rezervasyon bulunmaktadır."
        })

    nights = (resrequest.check_out - resrequest.check_in).days
    if nights <= 0:
        return templates.TemplateResponse("add-res.html", {
            "request": request,
            "user": user,
            "room_id": resrequest.room_id,
            "checkin_date": resrequest.check_in,
            "checkout_date": resrequest.check_out,
            "room_price": room.price,
            "booked_dates": [],
            "error_message": "Geçersiz tarih aralığı. Giriş tarihi çıkıştan önce olmalı."
        })

    res = Reservation(
        room_id=resrequest.room_id,
        user_id=user["id"],
        check_in=resrequest.check_in,
        check_out=resrequest.check_out,
        total_price=nights * room.price,
        status="pending"
    )
    db.add(res)
    db.commit()
    return RedirectResponse(url="/res/myres", status_code=302)


# ----------------- Düzenleme / Silme -----------------

@router.get("/edit_res/{res_id}", response_class=HTMLResponse)
async def render_edit_res_page(request: Request, db: db_dependency, res_id: int):
    user = await get_current_user(request)
    if user is None:
        return redirect_to_login()

    res = db.query(Reservation).filter(Reservation.id == res_id, Reservation.user_id == user["id"]).first()
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")

    booked_dates = []
    reservations = db.query(Reservation).filter(
        Reservation.room_id == res.room_id,
        Reservation.id != res.id,  # kendi rezervasyonu hariç
        Reservation.status.in_(["pending", "approved"])
    ).all()

    for r in reservations:
        current = r.check_in
        while current <= r.check_out:
            booked_dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

    return templates.TemplateResponse("add-res.html", {
        "request": request,
        "user": user,
        "res": res,
        "room_id": res.room_id,
        "checkin_date": res.check_in,
        "checkout_date": res.check_out,
        "room_price": res.room.price,
        "booked_dates": booked_dates
    })


@router.post("/update/{res_id}")
async def update_res_post(request: Request, user: user_dependency, db: db_dependency, res_id: int, resrequest: ReservationRequest = Depends()):
    if user is None:
        return redirect_to_login()

    res = db.query(Reservation).filter(Reservation.id == res_id, Reservation.user_id == user["id"]).first()
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")

    res.room_id = resrequest.room_id
    res.check_in = resrequest.check_in
    res.check_out = resrequest.check_out
    res.total_price = (resrequest.check_out - resrequest.check_in).days * db.query(Room).get(resrequest.room_id).price
    res.status = "pending"
    db.commit()
    return RedirectResponse(url="/res/myres", status_code=302)

@router.post("/delete/{res_id}")
async def delete_res_post(user: user_dependency, db: db_dependency, res_id: int):
    res = db.query(Reservation).filter(Reservation.id == res_id, Reservation.user_id == user["id"]).first()
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    db.delete(res)
    db.commit()
    return RedirectResponse(url="/res/myres", status_code=302)

# ----------------- Otel Yöneticisi: Yönetim -----------------

@router.get("/manage")
async def manage_reservations(request: Request, db: db_dependency):
    user = await get_current_user(request)
    if user.get("user_type") != "manager":
        return redirect_to_login()

    reservations = db.query(Reservation)\
        .join(Room).join(Room.hotel)\
        .filter(Room.hotel.has(manager_id=user["id"]))\
        .all()

    reservations = sorted(reservations, key=lambda r: (r.status != "pending", -r.check_in.toordinal()))

    return templates.TemplateResponse("manage_res.html", {
        "request": request,
        "user": user,
        "reservations": reservations
    })

@router.post("/approve/{res_id}")
async def approve_reservation(res_id: int, db: db_dependency, user: user_dependency):
    reservation = db.query(Reservation).join(Room).filter(
        Reservation.id == res_id,
        Room.hotel.has(manager_id=user["id"])
    ).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    reservation.status = "approved"
    db.commit()
    return RedirectResponse(url="/res/manage", status_code=302)

@router.post("/reject/{res_id}")
async def reject_reservation(res_id: int, db: db_dependency, user: user_dependency):
    reservation = db.query(Reservation).join(Room).filter(
        Reservation.id == res_id,
        Room.hotel.has(manager_id=user["id"])
    ).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    reservation.status = "rejected"
    db.commit()
    return RedirectResponse(url="/res/manage", status_code=302)


