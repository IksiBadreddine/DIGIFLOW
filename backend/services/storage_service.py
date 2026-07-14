# backend/services/storage_service.py

import os
import logging
from io import BytesIO
from typing import Optional, List

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class StorageService:
    """Service de stockage avec MinIO"""
    
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        self.bucket = os.getenv("MINIO_BUCKET", "documents")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Crée le bucket s'il n'existe pas"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"✅ Bucket créé: {self.bucket}")
        except S3Error as e:
            logger.error(f"Erreur de création du bucket: {e}")
    
    def upload_bytes(self, data: bytes, object_path: str, content_type: str = None) -> str:
        """
        Upload des bytes vers MinIO
        """
        try:
            self.client.put_object(
                self.bucket,
                object_path,
                BytesIO(data),
                len(data),
                content_type=content_type
            )
            logger.info(f"✅ Uploadé: {object_path}")
            return object_path
        except S3Error as e:
            logger.error(f"Erreur d'upload: {e}")
            raise
    
    def upload_file(self, file_path: str, object_path: str, content_type: str = None) -> str:
        """
        Upload un fichier depuis le système de fichiers
        """
        try:
            self.client.fput_object(
                self.bucket,
                object_path,
                file_path,
                content_type=content_type
            )
            logger.info(f"✅ Uploadé: {object_path}")
            return object_path
        except S3Error as e:
            logger.error(f"Erreur d'upload: {e}")
            raise
    
    def download_file(self, object_path: str, file_path: str):
        """
        Télécharge un fichier depuis MinIO
        """
        try:
            self.client.fget_object(
                self.bucket,
                object_path,
                file_path
            )
            logger.info(f"✅ Téléchargé: {object_path}")
        except S3Error as e:
            logger.error(f"Erreur de téléchargement: {e}")
            raise
    
    def download_bytes(self, object_path: str) -> Optional[bytes]:
        """
        Télécharge le contenu d'un fichier en mémoire
        """
        try:
            response = self.client.get_object(self.bucket, object_path)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Erreur de téléchargement: {e}")
            return None
    
    def get_presigned_url(self, object_path: str, expires: int = 3600) -> Optional[str]:
        """
        Génère une URL pré-signée pour téléchargement
        """
        try:
            return self.client.presigned_get_object(
                self.bucket, object_path, expires=expires
            )
        except S3Error as e:
            logger.error(f"Erreur d'URL: {e}")
            return None
    
    def delete_file(self, object_path: str):
        """
        Supprime un fichier de MinIO
        """
        try:
            self.client.remove_object(self.bucket, object_path)
            logger.info(f"✅ Supprimé: {object_path}")
        except S3Error as e:
            logger.error(f"Erreur de suppression: {e}")
            raise
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        Liste les fichiers dans le bucket avec un préfixe donné
        """
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Erreur de listage: {e}")
            return []
    
    def get_bucket_info(self) -> dict:
        """Retourne des informations sur le bucket"""
        try:
            objects = self.client.list_objects(self.bucket, recursive=True)
            count = sum(1 for _ in objects)
            return {
                "bucket": self.bucket,
                "count": count,
                "endpoint": self.endpoint
            }
        except S3Error as e:
            logger.error(f"Erreur d'information: {e}")
            return {"bucket": self.bucket, "count": 0, "error": str(e)}