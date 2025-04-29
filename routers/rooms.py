from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from models import Hotel,Room
from routers.user import get_current_user

router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
    responses={404: {"description": "Not found"}},
)
class RoomRequest(BaseModel):
    room_type:str
    price: int
    capacity: int
    availability: bool

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/")
async def read_all(db: db_dependency):
    rooms = db.query(Room).filter(Room.availability == True).all()
    return rooms

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_room(user:user_dependency,db: db_dependency, roomrequest: RoomRequest):
    hotel = db.query(Hotel).filter(Hotel.manager_id == user.get("id")).first()
    if not hotel:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized to add a room to this hotel")
    room =Room(**roomrequest.model_dump(),hotel_id=hotel.id)
    db.add(room)
    db.commit()
@router.put("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_room(user:user_dependency,db: db_dependency, roomrequest: RoomRequest, room_id: int=Path(gt=0)):
    hotel = db.query(Hotel).filter(Hotel.manager_id == user.get("id")).first()
    if not hotel:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized to edit room in this hotel")
    room = db.query(Room).filter(Room.id == room_id).filter(hotel.manager_id == user.get("id")).first()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Room not found")
    room.room_type = roomrequest.room_type
    room.price = roomrequest.price
    room.capacity = roomrequest.capacity
    room.availability = roomrequest.availability
    db.add(room)
    db.commit()

@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(user:user_dependency,db: db_dependency, room_id: int=Path(gt=0)):
    hotel = db.query(Hotel).filter(Hotel.manager_id == user.get("id")).first()
    if not hotel:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized to delete a room from this hotel")
    room = db.query(Room).filter(Room.id == room_id).filter(hotel.manager_id == user.get("id")).first()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Reservation not found")
    db.query(Room).filter(Room.id == room_id).filter(hotel.manager_id == user.get("id")).delete()
    db.commit()