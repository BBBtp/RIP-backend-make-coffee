from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from minio import Minio
from rest_framework.response import *


def process_file_upload(file_object: InMemoryUploadedFile, client, image_name):
    try:
        client.put_object('make-coffee', image_name, file_object, file_object.size)
        return f"http://localhost:9000/make-coffee/{image_name}"
    except Exception as e:
        return {"error": str(e)}


def add_pic(new_ingredient, pic):
    client = Minio(
        endpoint=settings.AWS_S3_ENDPOINT_URL,
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        secure=settings.MINIO_USE_SSL
    )
    i = new_ingredient.id
    img_obj_name = f"{i}.png"

    if not pic:
        return Response({"error": "Нет файла для изображения логотипа."})
    result = process_file_upload(pic, client, img_obj_name)

    if 'error' in result:
        return Response(result)

    new_ingredient.image_url = result
    new_ingredient.save()

    return Response({"message": "success"})


def delete_pic(ingredient):
    client = Minio(
        endpoint=settings.AWS_S3_ENDPOINT_URL,
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        secure=settings.MINIO_USE_SSL
    )

    img_obj_name = f"{ingredient.id}.png"
    try:
        client.remove_object('make-coffee', img_obj_name)
        return True
    except Exception as e:
        print(f"Не удалось удалить изображение: {str(e)}")
        return False
