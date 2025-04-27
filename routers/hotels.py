from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from database import SessionLocal
from routers.user import get_current_user
from models import Hotel
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

router = APIRouter(prefix="/hotels", tags=["hotels"])
templates = Jinja2Templates(directory="templates")

class HotelRequest(BaseModel):
    name: str
    description: str
    location: str
    phone_number: str
    email: str
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.put("/{hotel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def updaate_hotel(user:user_dependency,db: db_dependency, hotelrequest: HotelRequest, hotel_id: int=Path(gt=0)):
    if user.get("id")!=db.query(Hotel).filter(Hotel.id ==hotel_id).first().manager_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User is not authorized to update this hotel")
    hotel = db.query(Hotel).filter(Hotel.id ==hotel_id).filter(Hotel.manager_id == user.get("id")).first()
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Hotel not found")
    hotel.name = hotelrequest.name
    hotel.description = hotelrequest.description
    hotel.location = hotelrequest.location
    hotel.phone_number = hotelrequest.phone_number
    hotel.email = hotelrequest.email
    db.add(hotel)
    db.commit()
@router.get("/{hotel_id}", response_class=HTMLResponse)
async def get_hotel_detail(request: Request, db: db_dependency,hotel_id: int = Path(gt=0)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()

    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")

    return templates.TemplateResponse(
        "hotel_detail.html",
        {
            "request": request,
            "hotel": hotel,
            "rooms": hotel.rooms
        }
    )
