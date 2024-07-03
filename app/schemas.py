from pydantic import BaseModel


class MemeBase(BaseModel):
    text: str


class MemeCreate(MemeBase):
    image_url: str


class MemeUpdate(MemeBase):
    pass


class Meme(MemeBase):
    id: int
    image_url: str

    class Config:
        orm_mode = True
