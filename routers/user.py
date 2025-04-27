from fastapi import APIRouter, Depends, Path, HTTPException, Request
from pydantic import BaseModel
from starlette import status
from models import User
from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import timedelta, datetime,timezone
from fastapi.templating import Jinja2Templates

router=APIRouter(
    prefix="/user",
    tags=["user"]
)
templates=Jinja2Templates(directory="templates")
SECRET_KEY="80vwx3bgm23981qgu5upww9gg8oh98ykb8av22squzejcbu7trk2qokxpl6c2roo"
ALGORITHM="HS256"

bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/user/token")

class UserRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    phone_number: str
    user_type: str

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(email: str,user_id:int,user_type:str,expires_delta:timedelta):
    payload={"sub":email,"id":user_id,"user_type":user_type}
    expires=datetime.now(timezone.utc)+expires_delta
    payload["exp"]=int(expires.timestamp())
    return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)


def auth_user(email: str, password: str,db):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not bcrypt.verify(password, user.hashed_password):
        return None
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        email:str=payload.get("sub")
        user_id:int=payload.get("id")
        user_type:str=payload.get("user_type")
        if email is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Email or id is missing")
        return {"email":email,"id":user_id,"user_type":user_type}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token is invalid")
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
db_dependency = Annotated[Session, Depends(get_db)]

@router.get("/login")
def render_login_page(request: Request):
    return templates.TemplateResponse("login.html",{"request":request})

@router.get("/register")
def render_register_page(request: Request):
    return templates.TemplateResponse("register.html",{"request":request})

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user_request: UserRequest):
    user = User(
        first_name=user_request.first_name,
        last_name=user_request.last_name,
        email=user_request.email,
        hashed_password=bcrypt.hash(user_request.password),
        phone_number=user_request.phone_number,
        user_type=user_request.user_type
    )
    db.add(user)
    db.commit()

@router.post("/token",response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user=auth_user(form_data.username,form_data.password,db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Credentials")
    token=create_access_token(user.email,user.id,user.user_type,timedelta(hours=24))
    return {"access_token":token,"token_type":"bearer"}