"""
BookStorage — upload du PDF vers MinIO (dev) ou Cloudflare R2 (prod).

Stratégie :
- Dev : MinIO local (bucket 'mealplanner-pdfs', endpoint configurable via env)
- Prod : Cloudflare R2 via protocole S3-compatible (endpoint R2 Cloudflare)

Sélection automatique via la variable d'env STORAGE_BACKEND (minio | r2).
Par défaut : minio (développement local).

Le client boto3 est réutilisé (singleton) pour les connexions poolées.
"""

from __future__ import annotations

import os

from loguru import logger

# ---- Configuration via variables d'environnement ----
_STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "minio").lower()
_MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
_MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
_MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
_MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "mealplanner-pdfs")

_R2_ENDPOINT: str = os.getenv("R2_ENDPOINT", "")
_R2_ACCESS_KEY: str = os.getenv("R2_ACCESS_KEY", "")
_R2_SECRET_KEY: str = os.getenv("R2_SECRET_KEY", "")
_R2_BUCKET: str = os.getenv("R2_BUCKET", "mealplanner-pdfs")

# Singleton client S3/boto3 — initialisé à la première utilisation
_s3_client: "Any" = None  # type: ignore[type-arg]


def _get_s3_client() -> "Any":
    """
    Retourne le client boto3 singleton.

    Sélectionne MinIO ou R2 selon STORAGE_BACKEND.
    Crée le bucket MinIO si inexistant (développement uniquement).
    """
    global _s3_client

    if _s3_client is not None:
        return _s3_client

    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise ImportError(
            "boto3 non installé. Ajouter 'boto3>=1.34' dans pyproject.toml."
        ) from exc

    if _STORAGE_BACKEND == "r2":
        _s3_client = boto3.client(
            "s3",
            endpoint_url=_R2_ENDPOINT,
            aws_access_key_id=_R2_ACCESS_KEY,
            aws_secret_access_key=_R2_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
        logger.info("book_storage_r2_client_initialized", endpoint=_R2_ENDPOINT)
    else:
        # MinIO (défaut dev)
        _s3_client = boto3.client(
            "s3",
            endpoint_url=_MINIO_ENDPOINT,
            aws_access_key_id=_MINIO_ACCESS_KEY,
            aws_secret_access_key=_MINIO_SECRET_KEY,
            config=Config(
                signature_version="s3v4",
                # Désactive la vérification de région pour MinIO local
                region_name="us-east-1",
            ),
        )
        _ensure_bucket_exists(_s3_client, _MINIO_BUCKET)
        logger.info("book_storage_minio_client_initialized", endpoint=_MINIO_ENDPOINT)

    return _s3_client


def _ensure_bucket_exists(client: "Any", bucket_name: str) -> None:
    """Crée le bucket MinIO si absent (uniquement en dev)."""
    try:
        client.head_bucket(Bucket=bucket_name)
    except Exception:
        try:
            client.create_bucket(Bucket=bucket_name)
            logger.info("book_storage_bucket_created", bucket=bucket_name)
        except Exception as exc:
            logger.warning(
                "book_storage_bucket_create_failed",
                bucket=bucket_name,
                error=str(exc),
            )


class BookStorage:
    """
    Abstraction de stockage objet pour les PDFs de livres de recettes.

    Méthodes principales :
    - upload(key, data) → upload le PDF
    - get_url(key) → URL présignée valable 7 jours
    """

    async def upload(self, key: str, data: bytes) -> str:
        """
        Upload un PDF vers le backend de stockage configuré.

        L'opération est synchrone (boto3 sync) — wrappée dans un executor
        pour ne pas bloquer la boucle asyncio si appelée depuis un contexte async.

        Args:
            key: Clé objet dans le bucket (ex: "{household_id}/{plan_id}-{hash}.pdf").
            data: PDF bytes à uploader.

        Returns:
            Clé de l'objet uploadé (identique à `key`).
        """
        import asyncio
        import functools

        client = _get_s3_client()
        bucket = _MINIO_BUCKET if _STORAGE_BACKEND != "r2" else _R2_BUCKET

        loop = asyncio.get_event_loop()
        put_fn = functools.partial(
            client.put_object,
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType="application/pdf",
        )

        await loop.run_in_executor(None, put_fn)

        logger.info(
            "book_storage_upload_done",
            key=key,
            bucket=bucket,
            backend=_STORAGE_BACKEND,
            size_bytes=len(data),
        )

        return key

    def get_presigned_url(self, key: str, expiry_seconds: int = 604800) -> str:
        """
        Génère une URL présignée valable `expiry_seconds` (défaut 7 jours).

        Args:
            key: Clé objet dans le bucket.
            expiry_seconds: Durée de validité en secondes.

        Returns:
            URL présignée HTTPS.
        """
        client = _get_s3_client()
        bucket = _MINIO_BUCKET if _STORAGE_BACKEND != "r2" else _R2_BUCKET

        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )

        logger.debug(
            "book_storage_presigned_url_generated",
            key=key,
            expiry_seconds=expiry_seconds,
        )

        return url
