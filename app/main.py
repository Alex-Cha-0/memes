import os
from fastapi import applications
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html
from sqlalchemy.orm import Session
from uuid import uuid4
import boto3
from botocore.client import Config
from app import database, schemas, dependencies, crud

MINIO_URL = os.getenv("MINIO_URL", "http://minio:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "memes")

# Клиента MinIO
s3 = boto3.client('s3', endpoint_url=MINIO_URL, aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY,
                  config=Config(signature_version='s3v4'))

#  Ускорение загрузки Swagger
def swagger_monkey_patch(*args, **kwargs):
    return get_swagger_ui_html(
        *args, **kwargs,
        swagger_js_url="https://cdn.staticfile.net/swagger-ui/5.1.0/swagger-ui-bundle.min.js",
        swagger_css_url="https://cdn.staticfile.net/swagger-ui/5.1.0/swagger-ui.min.css")


applications.get_swagger_ui_html = swagger_monkey_patch

app = FastAPI()


@app.on_event("startup")
def on_startup():
    database.init_db()
    # Создаем баскет, если его нет
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except:
        s3.create_bucket(Bucket=BUCKET_NAME)

# Создаем директорию temp, если она не существует
os.makedirs("temp", exist_ok=True)

def upload_file(file_path, object_name):
    s3.upload_file(file_path, BUCKET_NAME, object_name)
    return f"{MINIO_URL}/{BUCKET_NAME}/{object_name}"


def delete_file(object_name):
    s3.delete_object(Bucket=BUCKET_NAME, Key=object_name)


@app.get("/memes", response_model=list[schemas.Meme])
def read_memes(skip: int = 0, limit: int = 10, db: Session = Depends(dependencies.get_db)):
    memes = crud.get_memes(db, skip=skip, limit=limit)
    return memes


@app.get("/memes/{meme_id}", response_model=schemas.Meme)
def read_meme(meme_id: int, db: Session = Depends(dependencies.get_db)):
    db_meme = crud.get_meme(db, meme_id=meme_id)
    if db_meme is None:
        raise HTTPException(status_code=404, detail="Meme not found")
    return db_meme


@app.post("/memes", response_model=schemas.Meme)
async def create_meme(text: str, file: UploadFile = File(...), db: Session = Depends(dependencies.get_db)):
    # Генерируем уникальное имя файла
    file_location = f"temp/{uuid4()}_{file.filename}"
    # Сохраняем файл в директорию temp
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    # Загружаем файл в MinIO
    image_url = upload_file(file_location, file.filename)
    # Удаляем локальный файл после загрузки
    os.remove(file_location)

    # Создаем новый мем
    meme = schemas.MemeCreate(image_url=image_url, text=text)
    return crud.create_meme(db, meme=meme)


@app.put("/memes/{meme_id}", response_model=schemas.Meme)
def update_meme(meme_id: int, meme: schemas.MemeUpdate, db: Session = Depends(dependencies.get_db)):
    return crud.update_meme(db, meme_id=meme_id, meme=meme)


@app.delete("/memes/{meme_id}", response_model=schemas.Meme)
def delete_meme(meme_id: int, db: Session = Depends(dependencies.get_db)):
    return crud.delete_meme(db, meme_id=meme_id)
