import asyncio
import datetime
from typing import Sequence

from pydantic import json
from sqlalchemy import create_engine, ForeignKey, Date, String, DateTime, \
    Float, UniqueConstraint, Integer, LargeBinary, BLOB, select, ARRAY, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils.functions import database_exists, create_database

from config_data.bot_conf import conf, get_my_loggers, tz, BASE_DIR

logger, err_log = get_my_loggers()

# db_url = f"postgresql+psycopg2://{conf.db.db_user}:{conf.db.db_password}@{conf.db.db_host}:{conf.db.db_port}/{conf.db.database}"
db_path = BASE_DIR / 'base.sqlite'
db_url = f"sqlite:///{db_path}"
engine = create_engine(db_url, echo=False)
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    def set(self, key, value):
        _session = Session(expire_on_commit=False)
        with _session:
            setattr(self, key, value)
            _session.add(self)
            _session.commit()
            logger.debug(f'Изменено значение {key} на {value}')
            return self


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True)
    tg_id: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    register_date: Mapped[datetime.datetime] = mapped_column(DateTime(), nullable=True)
    birthday: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    create_date: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    inn: Mapped[int] = mapped_column(Integer(), nullable=True)
    fio: Mapped[str] = mapped_column(String(200), nullable=True)
    cash: Mapped[int] = mapped_column(Integer(), default=60)
    is_active: Mapped[int] = mapped_column(Integer(), default=0)
    analyse_count: Mapped[int] = mapped_column(Integer(), default=0)

    def __str__(self):
        return f'{self.id}. {self.username or "-"} ({self.fio}). Баланс {self.cash}'

    def __repr__(self):
        return f'{self.id}. {self.username or "-"} ({self.fio})'


if not database_exists(db_url):
    create_database(db_url)
Base.metadata.create_all(engine)
