from fastapi import FastAPI,Request
from starlette.responses import RedirectResponse

from models import Base
from database import engine
from fastapi.staticfiles import StaticFiles
from routers.user import router as user_router
from routers.reservations import router as reservation_router
from routers.hotels import router as hotel_router
from routers.rooms import router as room_router
from routers.home import router as home_router

app=FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(user_router)
app.include_router(reservation_router)
app.include_router(hotel_router)
app.include_router(room_router)
app.include_router(home_router)

Base.metadata.create_all(bind=engine)
