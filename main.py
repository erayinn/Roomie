from fastapi import FastAPI
from models import Base
from database import engine
from routers.user import router as user_router

app=FastAPI()
app.include_router(user_router)

Base.metadata.create_all(bind=engine)
