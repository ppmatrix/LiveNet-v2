from app.core.database import check_database_connection


if __name__ == "__main__":
    if check_database_connection():
        print("DATABASE CONNECTION: OK")
    else:
        raise SystemExit("DATABASE CONNECTION: FAILED")
