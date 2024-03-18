import asyncio
import datetime

from sqlalchemy import select, delete

from config_data.bot_conf import get_my_loggers
from database.db import Session, User

logger, err_log = get_my_loggers()


def check_user(id):
    """Возвращает найденных пользователей по tg_id"""
    # logger.debug(f'Ищем юзера {id}')
    with Session() as session:
        user: User = session.query(User).filter(User.tg_id == str(id)).one_or_none()
        # logger.debug(f'Результат: {user}')
        return user


# def get_user_from_id(pk) -> User:
#     """Возвращает найденного пользователя по id"""
#     # logger.debug(f'Ищем юзера {id}')
#     with Session() as session:
#         user: User = session.query(User).filter(User.id == pk).one_or_none()
#         # logger.debug(f'Результат: {user}')
#         return user


def get_user_from_id(pk) -> User:
    session = Session(expire_on_commit=False)
    with session:
        q = select(User).filter(User.id == pk)
        user = session.execute(q).scalars().one_or_none()
        return user


def get_or_create_user(user) -> User:
    """Из юзера ТГ возвращает сущестующего User ли создает его"""
    try:
        tg_id = user.id
        username = user.username
        logger.debug(f'username {username}')
        old_user = check_user(tg_id)
        if old_user:
            logger.debug('Пользователь есть в базе')
            return old_user
        logger.debug('Добавляем пользователя')
        with Session() as session:
            new_user = User(tg_id=tg_id,
                            username=username,
                            register_date=datetime.datetime.now()
                            )
            session.add(new_user)
            session.commit()
            logger.debug(f'Пользователь создан: {new_user}')
        return new_user
    except Exception as err:
        err_log.error('Пользователь не создан', exc_info=True)


def update_user(user: User, data: dict):
    try:
        logger.debug(f'Обновляем {user}: {data}')
        session = Session()
        with session:
            user: User = session.query(User).filter(User.id == user.id).first()
            for key, val in data.items():
                setattr(user, key, val)
            session.commit()
            logger.debug(f'Юзер обновлен {user}')
    except Exception as err:
        err_log.error(f'Ошибка обновления юзера {user}: {err}')


if __name__ == '__main__':
    pass
