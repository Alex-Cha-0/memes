from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Meme(Base):
    __tablename__ = "memes"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String, index=True)
    text = Column(Text)
