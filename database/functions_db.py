from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models_sql import Base, User
from database.DB_CONN import connect_to_db

engine = create_engine('postgresql+psycopg2://', creator=connect_to_db)
Base.metadata.create_all(engine)  # Создание таблиц

Session = sessionmaker(bind=engine)

def register_user(telegram_id: int):
    session = Session()
    try:
        if not session.query(User).filter_by(telegram_id=telegram_id).first():
            new_user = User(telegram_id=telegram_id)
            session.add(new_user)
            session.commit()
            print(f"User {telegram_id} registered")
        else:
            print(f"User {telegram_id} already exists")
    except Exception as e:
        session.rollback()
        print(f"Database error: {e}")
    finally:
        session.close()
