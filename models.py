from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    phone_number = Column(String(10))
    user_type = Column(String)  # "customer", "manager", "admin"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    hotels = relationship("Hotel", back_populates="manager")
    reservations = relationship("Reservation", back_populates="user")


class Hotel(Base):
    __tablename__ = 'hotels'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(Text)
    location = Column(String(100))
    phone_number = Column(String(20))
    email = Column(String(100))
    manager_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_approved = Column(Boolean, default=False)
    image_url = Column(String)

    manager = relationship("User", back_populates="hotels")
    rooms = relationship("Room", back_populates="hotel")

class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"))
    room_type = Column(String(50))
    price = Column(Integer)
    capacity = Column(Integer)
    availability = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    hotel = relationship("Hotel", back_populates="rooms")
    reservations = relationship("Reservation", back_populates="room")

class Reservation(Base):
    __tablename__ = 'reservations'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    check_in = Column(Date)
    check_out = Column(Date)
    total_price = Column(Integer)
    status = Column(String(50))  # "pending", "approved", "rejected"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")
