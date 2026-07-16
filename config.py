import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or "dev-secret-change-me"  # เปลี่ยนก่อน deploy จริง
    DB_PATH = "queue.db"
    DEFAULT_ADMIN_USERNAME = "adminmax"
    DEFAULT_ADMIN_PASSWORD = "@!Maxnumber1"
