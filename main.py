from fastapi import FastAPI
from models import Base
from database import engine
from routers.user import router as user_router
from routers.reservations import router as reservation_router

app=FastAPI()
app.include_router(user_router)
app.include_router(reservation_router)

Base.metadata.create_all(bind=engine)
