from typing import Annotated
from fastapi import APIRouter, Depends, Path, HTTPException,Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from datetime import date

from starlette.responses import RedirectResponse

from database import SessionLocal
from models import Reservation
from routers.user import get_current_user
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/res",
    tags=["reservations"],
    responses={404: {"description": "Not found"}},
)

templates=Jinja2Templates(directory="templates")

class ReservationRequest(BaseModel):
    room_id: int
    check_in: date
    check_out: date
    total_price: float
    status: str

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
    user=await get_current_user(request.cookies.get("access_token"))
    if user is None:
        return redirect_to_login()
    ress=db.query(Reservation).filter(Reservation.user_id == user.get("id")).all()
    return templates.TemplateResponse("res.html",{"request":request,"user":user,"ress":ress})

@router.get("/create_res")
async def render_create_res_page(request: Request):
    user=await get_current_user(request.cookies.get("access_token"))
    if user is None:
        return redirect_to_login()
    return templates.TemplateResponse("add-res.html",{"request":request,"user":user})

@router.get("/edit_res/{res_id}")
async def render_create_res_page(request: Request,db: db_dependency,res_id:int=Path(gt=0)):
    user=await get_current_user(request.cookies.get("access_token"))
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

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_res(user:user_dependency,db: db_dependency, resrequest: ReservationRequest):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User not found")
    res =Reservation(**resrequest.model_dump(),user_id=user.get("id"))
    db.add(res)
    db.commit()

@router.put("/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_res(user:user_dependency,db: db_dependency, resrequest: ReservationRequest, res_id: int=Path(gt=0)):
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
