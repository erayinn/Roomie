from fastapi import APIRouter, Depends, Path, HTTPException
from pydantic import BaseModel, Field
from starlette import status
from models import Base,User
from database import engine, SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session

router=APIRouter(
    prefix="/user",
    tags=["user"]
)

class UserRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    phone_number: str
    user_type: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
db_dependency = Annotated[Session, Depends(get_db)]

@router.get("/read_all")
async def read_all(db: db_dependency):
    return db.query(User).all()
@router.get("/read_by_id/{user_id}", status_code=status.HTTP_200_OK)
async def read_by_id(db: db_dependency,user_id: int=Path(gt=0)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,)
@router.post("/create_user", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user_request: UserRequest):
    user = User(**user_request.dict())
    db.add(user)
    db.commit()
@router.put("/update_user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_user(db: db_dependency, user_request: UserRequest, user_id: int=Path(gt=0)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    user.first_name = user_request.first_name
    user.last_name = user_request.last_name
    user.email = user_request.email
    user.password = user_request.password
    user.phone_number = user_request.phone_number
    user.user_type = user_request.user_type
    db.add(user)
    db.commit()

@router.delete("/delete_user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(db: db_dependency, user_id: int=Path(gt=0)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    db.query(User).filter(User.id == user_id).delete()
    db.commit()