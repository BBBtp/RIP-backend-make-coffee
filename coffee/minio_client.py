from minio import Minio
from minio.error import S3Error

# Настройки для подключения к MinIO
minio_client = Minio(
    "localhost:9000",  # Ваш MinIO endpoint
    access_key="minio",  # Ваш MinIO access key
    secret_key="minio124",  # Ваш MinIO secret key
    secure=False  # Использовать HTTPS или нет
)

# Проверяем, существует ли бакет
bucket_name = "coffe-recipes"
found = minio_client.bucket_exists(bucket_name)
if not found:
    minio_client.make_bucket(bucket_name)
else:
    print(f"Bucket '{bucket_name}' already exists")

