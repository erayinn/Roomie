from typing import Annotated
from fastapi import APIRouter, Depends, Path, HTTPException,Request,Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from datetime import date

from starlette.responses import RedirectResponse

from database import SessionLocal
from models import Reservation, Room
from routers.user import get_current_user
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/res",
    tags=["reservations"],
    responses={404: {"description": "Not found"}},
)

templates=Jinja2Templates(directory="templates")

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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def redirect_to_login():
    redirect_response=RedirectResponse(url="/user/login",status_code=status.HTTP_302_FOUND)
    redirect_response.delete_cookie("access_token")
    return redirect_response

@router.get("/myres")
async def render_myres_page(request: Request,db: db_dependency):
    user = await get_current_user(request)
    if user is None:
        return redirect_to_login()
    ress=db.query(Reservation).filter(Reservation.user_id == user.get("id")).all()
    return templates.TemplateResponse("res.html",{"request":request,"user":user,"ress":ress})

@router.get("/create_res")
async def render_create_res_page(request: Request, room_id: int = None):
    token = request.cookies.get("access_token")
    if not token:
        return redirect_to_login()

    user = await get_current_user(request)

    if user is None:
        return redirect_to_login()
    return templates.TemplateResponse("add-res.html", {"request": request, "user": user, "room_id": room_id})


@router.get("/edit_res/{res_id}")
async def render_create_res_page(request: Request,db: db_dependency,res_id:int=Path(gt=0)):
    token = request.cookies.get("access_token")
    if not token:
        return redirect_to_login()

    user = await get_current_user(request)
    if user is None:
        return redirect_to_login()

    if user is None:
        return redirect_to_login()
    res=db.query(Reservation).filter(Reservation.id == res_id).filter(Reservation.user_id == user.get("id")).first()
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Reservation not found")
    return templates.TemplateResponse("add-res.html",{"request":request,"user":user,res:"res"})

@router.get("/")
async def read_all(user:user_dependency,db: db_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User not found")
    return db.query(Reservation).filter(Reservation.user_id == user.get("id")).all()

@router.get("/{reservation_id}", status_code=status.HTTP_200_OK)
async def read_by_id(user:user_dependency,db: db_dependency,reservation_id: int=Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User not found")
    user = db.query(Reservation).filter(Reservation.id == reservation_id).filter(Reservation.user_id == user.get("id")).first()
    if user is not None:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,)


@router.post("/", status_code=status.HTTP_201_CREATED,response_model=None)
async def create_res(
    request: Request,
    user: user_dependency,
    db: db_dependency,
    resrequest: ReservationRequest = Depends()
):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    room = db.query(Room).filter(Room.id == resrequest.room_id).first()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Gece sayısını hesapla
    nights = (resrequest.check_out - resrequest.check_in).days
    if nights <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Checkout date must be after checkin date")

    total_price = nights * room.price

    res = Reservation(
        room_id=resrequest.room_id,
        user_id=user.get("id"),
        check_in=resrequest.check_in,
        check_out=resrequest.check_out,
        total_price=total_price,
        status=resrequest.status
    )
    db.add(res)
    db.commit()
    return RedirectResponse(url="/res/myres", status_code=status.HTTP_302_FOUND)


@router.put("/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_res(
    user: user_dependency,
    db: db_dependency,
    resrequest: ReservationRequest = Depends(),
    res_id: int = Path(gt=0)
):

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User not found")
    res = db.query(Reservation).filter(Reservation.id == res_id).filter(Reservation.user_id == user.get("id")).first()
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Reservation not found")
    res.room_id = resrequest.room_id
    res.check_in = resrequest.check_in
    res.check_out = resrequest.check_out
    res.total_price = resrequest.total_price
    res.status = resrequest.status
    db.add(res)
    db.commit()

@router.delete("/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_res(user:user_dependency,db: db_dependency, res_id: int=Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User not found")
    res = db.query(Reservation).filter(Reservation.id == res_id).filter(Reservation.user_id == user.get("id")).first()
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Reservation not found")
    db.query(Reservation).filter(Reservation.id == res_id).filter(Reservation.user_id == user.get("id")).delete()
    db.commit()
