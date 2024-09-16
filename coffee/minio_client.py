# your_app/minio_client.py
import os
from datetime import timedelta
from minio import Minio

# Получаем данные из переменных окружения
MINIO_ACCESS_KEY = os.getenv("minio")
MINIO_SECRET_KEY = os.getenv("minio124")

# Создаем клиента Minio
minio_client = Minio(
    'localhost:9000',
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # Если не используете SSL
)

# Функция для получения presigned URL для изображения
def get_image_url(bucket_name, object_name):
    return minio_client.presigned_get_object(bucket_name, object_name, expires=timedelta(hours=1))
