from typing import Annotated

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import SupportTicket
from models import User
from routers.user import get_current_user
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/support", tags=["support"])
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[User, Depends(get_current_user)]

# Destek formunu ve kullanıcının önceki taleplerini gösterir
@router.get("/", response_class=HTMLResponse)
def show_support_form(request: Request, db: db_dependency, user: user_dependency):
    tickets = db.query(SupportTicket).filter(SupportTicket.user_id == user["id"]).all()
    return templates.TemplateResponse("support.html", {"request": request, "tickets": tickets,"user":user})

# Yeni destek talebi gönderme
@router.post("/")
def submit_ticket(db: db_dependency, user: user_dependency, subject: str = Form(...), message: str = Form(...)):
    ticket = SupportTicket(subject=subject, message=message, user_id=user["id"])
    db.add(ticket)
    db.commit()
    return RedirectResponse("/support", status_code=303)
