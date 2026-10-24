import os


def get_db_path() -> str:
    return os.environ.get("APP_DB_PATH", "app.db")
