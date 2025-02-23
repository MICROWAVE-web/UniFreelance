from decouple import config
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, desc, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from telegram_bot.celery_worker import notify_users

# Создание базового класса для моделей
Base = declarative_base()


# Модель для таблицы 'orders'
class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    task_id = Column(String, unique=True)
    title = Column(String)
    payment = Column(String)
    description = Column(String)
    direct_url = Column(String)
    platform = Column(String)

    # Связь с таблицей 'files'
    files = relationship("File", back_populates="order")


# Модель для таблицы 'files'
class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    url = Column(String)
    order_id = Column(Integer, ForeignKey('orders.id'))

    # Связь с таблицей 'orders'
    order = relationship("Order", back_populates="files")


# Функция для получения подключения
def get_engine():
    database_url = config("DATABASE_URL")
    return create_engine(database_url)


# Функция для создания таблиц
def create_parser_database():
    # Создание подключения
    engine = get_engine()

    # Создание всех таблиц, если их нет
    Base.metadata.create_all(engine)


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


def send_notify(channel: str, payload: str):
    """
    Отправка уведомления через NOTIFY.
    """
    # Создаём сессию
    with get_session() as session:
        # Выполняем SQL-команду NOTIFY
        session.execute(text(f"NOTIFY {channel}, :order_data"), {"order_data": payload})
        session.commit()  # Подтверждаем изменения


def get_all_task_id():
    session = get_session()
    result = [obj.task_id for obj in session.query(Order).all()]
    session.close()
    return result


def get_task_by_id(task_id):
    session = get_session()
    result = session.query(Order).filter_by(id=task_id).first()
    session.close()
    return result


def save_to_db(orders, platform):
    session = get_session()

    all_task_id = get_all_task_id()
    for order in orders:
        if order.task_id in all_task_id:
            continue
        db_order = Order(
            task_id=order.task_id,
            title=order.title,
            payment=order.payment,
            description=order.description,
            direct_url=order.direct_url,
            platform=platform
        )
        if order.additional_files:
            for file_url in order.additional_files:
                db_file = File(
                    url=file_url,
                )
                db_order.files.append(db_file)

        session.add(db_order)
        session.flush()
        session.refresh(db_order)

        super_dict = order.to_dict()
        super_dict["order_db_id"] = db_order.id
        notify_users.apply_async((super_dict,))
        # Добавляем данные в сессию


    # Сохраняем изменения
    session.commit()

    session.close()
    session = get_session()  # Создаем новую сессию
    # Сохраняем последние 333 записи
    for index, order in enumerate(session.query(Order).order_by(desc(Order.id)).all()):
        if index >= 333:
            order_to_delete = session.query(Order).get(order.id)
            session.delete(order_to_delete)
            session.commit()
    session.close()
    return True


if __name__ == '__main__':
    create_parser_database()
