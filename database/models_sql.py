from sqlalchemy import Column, BigInteger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    telegram_id = Column(BigInteger, primary_key=True)