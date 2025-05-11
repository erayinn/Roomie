from typing import Annotated
from fastapi import APIRouter, Depends, Path, HTTPException, Request, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from datetime import date, timedelta

from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from database import SessionLocal
from models import Reservation, Room
from routers.user import get_current_user

router = APIRouter(
    prefix="/res",
    tags=["reservations"],
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="templates")

# ---- Form sınıfı ----
class ReservationRequest:
    def __init__(
        self,
        room_id: int = Form(...),
        check_in: date = Form(...),
        check_out: date = Form(...),
        status: str = Form(...)
    ):
        self.room_id = room_id
        self.check_in = check_in
        self.check_out = check_out
        self.status = status

# ---- DB session ----
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# ---- Login yönlendirmesi ----
def redirect_to_login():
    response = RedirectResponse(url="/user/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

# ---- Rezervasyonlarım ----
@router.get("/myres")
async def render_myres_page(request: Request, db: db_dependency):
    user = await get_current_user(request)
    if user is None:
        return redirect_to_login()

    reservations = db.query(Reservation)\
    .filter(Reservation.user_id == user.get("id"))\
    .order_by(Reservation.check_in.desc())\
    .all()
    return templates.TemplateResponse("res.html", {
        "request": request,
        "user": user,
        "ress": reservations
    })

# ---- Rezervasyon oluşturma sayfası ----
@router.get("/create_res")
async def render_create_res_page(
    request: Request,
    db: db_dependency,
    room_id: int = None,
    checkin_date: str = None,
    checkout_date: str = None,
    guests: int = None
):
    token = request.cookies.get("access_token")
    if not token:
        return redirect_to_login()

    user = await get_current_user(request)
    if user is None:
        return redirect_to_login()

    room_price = 0
    booked_dates = []

    if room_id:
        room = db.query(Room).filter(Room.id == room_id).first()
        if room:
            room_price = room.price
            reservations = db.query(Reservation).filter(Reservation.room_id == room_id).all()

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

# ---- Rezervasyon oluşturma ----
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_res(
    request: Request,
    user: user_dependency,
    db: db_dependency,
    resrequest: ReservationRequest = Depends()
):
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    room = db.query(Room).filter(Room.id == resrequest.room_id).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    nights = (resrequest.check_out - resrequest.check_in).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="Çıkış tarihi giriş tarihinden sonra olmalı.")

    total_price = nights * room.price

    res = Reservation(
        room_id=resrequest.room_id,
        user_id=user["id"],
        check_in=resrequest.check_in,
        check_out=resrequest.check_out,
        total_price=total_price,
        status=resrequest.status
    )
    db.add(res)
    db.commit()
    return RedirectResponse(url="/res/myres", status_code=302)

# ---- Rezervasyon güncelleme ----
@router.put("/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_res(
    user: user_dependency,
    db: db_dependency,
    resrequest: ReservationRequest = Depends(),
    res_id: int = Path(gt=0)
):
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    res = db.query(Reservation).filter(
        Reservation.id == res_id,
        Reservation.user_id == user["id"]
    ).first()

    if res is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    res.room_id = resrequest.room_id
    res.check_in = resrequest.check_in
    res.check_out = resrequest.check_out
    res.total_price = (resrequest.check_out - resrequest.check_in).days * db.query(Room).get(resrequest.room_id).price
    res.status = resrequest.status
    db.commit()

# ---- Silme ----
@router.delete("/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_res(user: user_dependency, db: db_dependency, res_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    res = db.query(Reservation).filter(
        Reservation.id == res_id,
        Reservation.user_id == user["id"]
    ).first()

    if res is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    db.delete(res)
    db.commit()
