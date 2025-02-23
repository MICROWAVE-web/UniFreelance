from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

from decouple import config
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


# Таблица пользователей
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String, unique=True, nullable=False)
    referral = Column(String, nullable=True)
    try_period = Column(Boolean, default=False)
    sale = Column(Integer, default=0)

    subscriptions = relationship('Subscription', back_populates='user')
    filters = relationship('Filter', back_populates='user')


# Таблица подписок
class Subscription(Base):
    __tablename__ = 'subscriptions'

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)
    datetime_operation = Column(DateTime, default=datetime.now)
    datetime_expire = Column(DateTime, nullable=False)
    active = Column(Boolean, default=True)

    user = relationship('User', back_populates='subscriptions')


# Таблица фильтров
class Filter(Base):
    __tablename__ = 'filters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    platform = Column(String, nullable=False)
    query = Column(Text, nullable=False)

    """
    {
        "keywords": [],
        "stopkeywords": [],
        "minprice": 0,
        "maxprice": 1,
        "have_price": True
    }
    """

    # Уникальное ограничение для пары user_id и platform
    __table_args__ = (
        UniqueConstraint('user_id', 'platform', name='uq_user_platform'),
    )
    user = relationship('User', back_populates='filters')


# Функция для получения подключения
def get_engine():
    database_url = config("DATABASE_URL")
    return create_engine(database_url)


# Настройка подключения к БД и создание таблиц
def setup_database():
    engine = create_engine('postgresql+psycopg2://username:password@localhost/dbname')
    Base.metadata.create_all(engine)
    return engine


# Функция для создания таблиц
def create_bot_database():
    # Создание подключения
    engine = get_engine()

    # Создание всех таблиц, если их нет
    Base.metadata.create_all(engine)


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


@contextmanager
def session_scope(commit=False):
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session  # Pass the session to the function
        if commit:
            session.commit()  # Commit the transaction
    except Exception:
        session.rollback()  # Rollback the transaction on error
        raise  # Re-raise the exception to propagate the error
    finally:
        session.close()  # Ensure the session is always closed


# Проверка существования пользователя
def check_user_exists(telegram_id: str):
    with session_scope(False) as session:
        result = session.query(User).filter_by(telegram_id=telegram_id).scalar()

        return result


# Методы для работы с таблицами

def add_user(telegram_id: str, referral=None, try_period=False, sale=0):
    with session_scope(True) as session:
        user = User(telegram_id=telegram_id, referral=referral, try_period=try_period, sale=sale)
        session.add(user)
        return user


def add_subscription(user_id, name, datetime_expire):
    with session_scope(True) as session:
        subscription = Subscription(user_id=user_id, name=name, datetime_expire=datetime_expire)
        session.add(subscription)
        return subscription


def add_filter(user_id, platform, query):
    with session_scope(True) as session:
        filter_ = Filter(user_id=user_id, platform=platform, query=query)
        session.add(filter_)
        return filter_


def delete_filter(user_id, platform):
    with session_scope(True) as session:
        filter_ = session.query(Filter).filter_by(user_id=user_id, platform=platform).first()
        session.delete(filter_)


def get_filters_by_user_id(user_id):
    with session_scope(False) as session:
        result = session.query(Filter).filter_by(user_id=user_id).all()
        return result


def get_filter_by_user_id(user_id, platform):
    with session_scope(False) as session:
        result = session.query(Filter).filter_by(user_id=user_id, platform=platform).first()
        return result


def edit_filter_query_by_user_id(user_id, platform, query):
    with session_scope(True) as session:
        filter_object = session.query(Filter).filter_by(user_id=user_id, platform=platform).first()
        if filter_object:
            filter_object.query = query
            return filter_object
        return None


def get_user_by_telegram_id(telegram_id):
    with session_scope(False) as session:
        result = session.query(User).filter_by(telegram_id=telegram_id).first()
        return result


def get_telegram_id_by_user_id(user_id):
    with session_scope(False) as session:
        result = session.query(User).filter_by(id=user_id).first().telegram_id
        return result


def get_active_subscriptions(user_id):
    with session_scope(False) as session:
        result = session.query(Subscription).filter_by(user_id=user_id, active=True).all()
        return result


def get_inactive_subscriptions(user_id):
    with session_scope(False) as session:
        result = session.query(Subscription).filter_by(user_id=user_id, active=False).all()
        return result


def deactivate_subscription(payment_id):
    with session_scope(True) as session:
        subscription = session.query(Subscription).filter_by(payment_id=payment_id).first()
        if subscription:
            subscription.active = False
            return subscription
        return None


def add_sale_to_user(telegram_id, sale_amount):
    with session_scope(True) as session:
        user_object = session.query(User).filter_by(telegram_id=telegram_id).first()
        user_object.sale += sale_amount


def collect_filters():
    """Собирает фильтры всех пользователей в словарь {<query>: [user1, user2]} без дубликатов"""
    with session_scope(False) as session:
        platform_dict = defaultdict(lambda: defaultdict(set))

        filters = session.query(Filter).all()

        for filter_ in filters:
            platform_dict[filter_.platform][filter_.query].add(filter_.user_id)

        return platform_dict


# Пример использования
if __name__ == "__main__":
    create_bot_database()
    # Добавление пользователя
    user = add_user(telegram_id="123456789", referral="REF123", try_period=True)

    # Добавление подписки
    subscription = add_subscription(user_id=user.id, name="Pro Plan", datetime_expire=datetime(2025, 1, 1))

    # Добавление фильтра
    filter_ = add_filter(user_id=user.id, platform="freelance", query="price>1000")

    # Получение данных
    print(get_user_by_telegram_id("123456789"))
    print(get_active_subscriptions(user.id))
    print(get_filters_by_user_id(user.id))

    # Деактивация подписки
    deactivate_subscription(subscription.payment_id)
