from sqlalchemy import text

from app.database.engine import engine

try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        print("Database connected successfully!")

except Exception as e:
    print(e)