try:
    from .celery import app as celery_app
except ModuleNotFoundError as error:
    if error.name != "celery":
        raise
    celery_app = None

__all__ = ("celery_app",)
