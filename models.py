from datetime import datetime,timezone

from database import Base
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    phone_number = Column(String(10))
    user_type = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    hotels = relationship("Hotel", back_populates="manager")
    reservations = relationship("Rezervation", back_populates="user")
    comments = relationship("Comment", back_populates="user")


class Hotel(Base):
    __tablename__ = 'hotels'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(Text)
    location = Column(String(100))
    phone_number = Column(String(20))
    email = Column(String(100))
    manager_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime,default=datetime.now)

    manager = relationship("User", back_populates="hotels")
    rooms = relationship("Room", back_populates="hotel")
    comments = relationship("Comment", back_populates="hotel")


class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"))
    room_type = Column(String(50))
    price = Column(Integer)
    capacity = Column(Integer)
    availability = Column(Boolean)
    created_at = Column(DateTime,default=datetime.now)

    hotel = relationship("Hotel", back_populates="rooms")
    reservations = relationship("Rezervation", back_populates="room")


class Rezervation(Base):
    __tablename__ = 'rezervations'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    check_in = Column(Date)
    check_out = Column(Date)
    total_price = Column(Integer)
    status = Column(String(50))
    created_at = Column(DateTime,default=datetime.now)

    user = relationship("User", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    hotel_id = Column(Integer, ForeignKey("hotels.id"))
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime,default=datetime.now)

    user = relationship("User", back_populates="comments")
    hotel = relationship("Hotel", back_populates="comments")