from fastapi import APIRouter, Depends, Path, HTTPException, Request,Form
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
from fastapi.responses import RedirectResponse

router=APIRouter(
    prefix="/user",
    tags=["user"]
)
templates=Jinja2Templates(directory="templates")
SECRET_KEY="80vwx3bgm23981qgu5upww9gg8oh98ykb8av22squzejcbu7trk2qokxpl6c2roo"
ALGORITHM="HS256"

bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/user/token")

class UserRequest:
    def __init__(
        self,
        first_name: str = Form(...),
        last_name: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        phone_number: str = Form(...),
        user_type: str = Form(...)
    ):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.phone_number = phone_number
        self.user_type = user_type


class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(email: str, user_id: int, user_type: str, first_name: str, last_name: str, expires_delta: timedelta):
    payload = {
        "sub": email,
        "id": user_id,
        "user_type": user_type,
        "first_name": first_name,
        "last_name": last_name
    }
    expires = datetime.now(timezone.utc) + expires_delta
    payload["exp"] = int(expires.timestamp())
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)



def auth_user(email: str, password: str,db):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not bcrypt.verify(password, user.hashed_password):
        return None
    return user

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    is_browser = request.headers.get("accept", "").startswith("text/html")

    if not token:
        if is_browser:
            return None  # HTML route'larında redirect yapılabilir
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token not found")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("id")
        user_type = payload.get("user_type")
        first_name = payload.get("first_name")
        last_name = payload.get("last_name")

        if email is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        return {
            "email": email,
            "id": user_id,
            "user_type": user_type,
            "first_name": first_name,
            "last_name": last_name
        }

    except JWTError:
        if is_browser:
            return None
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
db_dependency = Annotated[Session, Depends(get_db)]

@router.get("/login")
def render_login_page(request: Request):
    referer = request.headers.get("referer")
    response = templates.TemplateResponse("login.html", {"request": request})

    # ❗ Sadece anlamlı sayfalardan geldiyse yaz
    if referer and all(skip not in referer for skip in ["/user/login", "/user/register", "/user/create"]):
        response.set_cookie("redirect_after_login", referer, max_age=300)

    return response



@router.get("/register")
def render_register_page(request: Request):
    response = templates.TemplateResponse("register.html", {"request": request})
    response.delete_cookie("redirect_after_login")  # Kesin sil
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response
@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_user(
    db: db_dependency,
    user_request: UserRequest = Depends()
):
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

    response = RedirectResponse(url="/user/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("redirect_after_login")  # Kayıt olduysa yönlendirme sıfırlanmalı
    return response



@router.post("/token")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency
):
    user = auth_user(form_data.username, form_data.password, db)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "login_error": "E-posta veya şifre yanlış!"}
        )

    token = create_access_token(
        user.email,
        user.id,
        user.user_type,
        user.first_name,
        user.last_name,
        timedelta(hours=24)
    )

    redirect_url = request.cookies.get("redirect_after_login") or "/"
    if redirect_url in ["/user/login", "/user/register"]:
        redirect_url = "/"

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,
        expires=86400,
        samesite="lax",
        secure=False
    )
    response.delete_cookie("redirect_after_login")
    return response
