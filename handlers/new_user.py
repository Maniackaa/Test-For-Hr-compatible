import asyncio
import datetime

from aiogram import Dispatcher, types, Router, Bot, F
from aiogram.filters import Command, CommandStart, StateFilter, BaseFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, URLInputFile, ReplyKeyboardRemove

from aiogram.fsm.context import FSMContext

from config_data.bot_conf import get_my_loggers, conf
from database.db import User
from keyboards.keyboards import start_kb, contact_kb, custom_kb, menu_kb, not_auth_start_kb, \
    auth_start_kb, demo_start_kb
from lexicon.lexicon import positive_dict, negative_dict, hr_career_dict, hr_conversation_dict
from services.db_func import get_or_create_user, update_user
from services.func import get_positive_quality, get_negative_quality, get_hr_conversation, get_hr_career, \
    specialist_profit

logger, err_log = get_my_loggers()


class IsPrivate(BaseFilter):
    async def __call__(self, message: Message | CallbackQuery) -> bool:
        if isinstance(message, CallbackQuery):
            message = message.message
        # print(f'Проверка на частность: {message.chat.type}\n')
        return message.chat.type == 'private'


class IsActive(BaseFilter):
    async def __call__(self, message: Message | CallbackQuery) -> bool:
        # if isinstance(message, CallbackQuery):
        #     message = message.message
        # print(f'Проверка на частность: {message.chat.type}\n')
        user = get_or_create_user(message.from_user)
        return user.is_active

router: Router = Router()
router.message.filter(IsPrivate())
router.callback_query.filter(IsPrivate())


class FSMAnket(StatesGroup):
    anket = State()
    text = State()
    confirm = State()
    # [('Вопрос', (Варианты,...), Свой вариант - True/False))]
    question_blocks = [
        # (
        #     'Укажите ваши данные: дата рождения в формате "ДД.ММ.ГГГ"',
        #     (),
        #     False,
        #     datetime.date
        # ),
        (
            """Для старта, укажите дату создания компании в формате "ДД.ММ.ГГГГ" """,
            (),
            False,
            datetime.date
        ),
        # (
        #     'Укажите ИНН предприятия',
        #     (),
        #     False,
        #     int
        # ),

    ]
    answers = {}
    new_analyse = State()


def get_question_kb_button(question__num):
    kb = {}
    for num, answer in enumerate(FSMAnket.question_blocks[question__num][1]):
        kb[answer] = f'answer:{question__num}:{num}'
    reply_markup = custom_kb(1, kb)
    return reply_markup


@router.callback_query(F.data == 'cancel')
async def operation_in(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer('Введите команду /start для начала.')


@router.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext):
    logger.debug('new')
    try:
        await state.clear()
        tg_user = message.from_user
        user: User = get_or_create_user(tg_user)
        if not user.is_active:
            await state.set_state(FSMAnket.anket)
            await state.update_data(question_num=0)
            await message.answer("""Привет! Проверь совместимость твоей компании и сотрудника. 
С помощью нумерологии бот автоматически посчитает: 

    - финансовую эффективность сотрудника в компании
    - положительные черты специалиста
    - отрицательные черты специалиста
    - перспективность и таланты""", reply_markup=not_auth_start_kb)
            kb = get_question_kb_button(0)
            btn = kb.inline_keyboard
            await message.answer(FSMAnket.question_blocks[0][0],
                                 reply_markup=kb)
            if not btn:
                await state.set_state(FSMAnket.text)
        else:
            if user.analyse_count >= 3:
                await message.answer(f'Ваш баланс {user.cash} руб. Стоимость анализа составляет 20 руб.', reply_markup=start_kb)
            else:
                await message.answer(
                    f'Здорово! Теперь мы можем приступить к анализу сотрудников для твоей компании.\n',
                    reply_markup=demo_start_kb)
    except Exception as err:
        logger.error(err)


def format_confirm_text(answers: dict) -> str:
    # {0: 'короткие ролики с вашим баннером', 1: 'от 30 до 50 миллионов',...}
    text = ''
    for num, question_block in enumerate(FSMAnket.question_blocks):
        question = question_block[0]
        answer = answers[num]
        if isinstance(answer, datetime.date):
            answer = answer.strftime('%d.%m.%Y')
        text += f'<b>{question}:</b>\n{answer}\n\n'
    return text


# Анкетирование
@router.callback_query(F.data.startswith('answer'))
async def answer_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    print(callback.data)
    split_data = callback.data.split(':')
    question_num = int(split_data[1])
    answer_num = int(split_data[2])
    print(question_num, answer_num)
    question_blocks = FSMAnket.question_blocks
    # Сохраняем ответ
    answer = question_blocks[question_num][1][answer_num]
    print('Ответ:', answer)
    FSMAnket.answers[question_num] = answer

    if question_num + 1 < len(question_blocks):
        # Следующий вопрос:
        new_question_block = question_blocks[question_num + 1]
        new_question = new_question_block[0]
        new_answers = new_question_block[1]
        print(f'Следующий вопрос: {new_question}')
        print(f'Следующие ответы: {new_answers}')
        if new_answers:
            await callback.message.edit_text(text=new_question, reply_markup=get_question_kb_button(question_num + 1))
        else:
            print('Вопрос без вариантов ответа')
            await state.set_state(FSMAnket.text)
            await callback.message.delete()
            await callback.message.answer(new_question)
            await state.update_data(question_num=question_num + 1)
    else:
        # Вопросы кончились
        print('Вопросы кончились')
        await callback.message.delete()
        text = format_confirm_text(FSMAnket.answers)
        confirm_btn = {
            'Отменить': 'cancel',
            'Отправить': 'confirm'
        }
        await callback.message.answer(text, reply_markup=custom_kb(2, confirm_btn))
        await state.set_state(FSMAnket.confirm)
    print(f'Все ответы: {FSMAnket.answers}')


@router.message(StateFilter(FSMAnket.text))
async def questions_text(message: Message, state: FSMContext, bot: Bot):
    answer = message.text.strip()
    data = await state.get_data()
    question_num = data['question_num']
    print(f'Все ответы: {FSMAnket.answers}')
    question_blocks = FSMAnket.question_blocks
    # Проверка ввода
    try:
        type_question = question_blocks[question_num][3]
        if type_question is datetime.date:
            answer = datetime.datetime.strptime(answer, '%d.%m.%Y').date()
        elif type_question is int:
            answer = int(answer)
    except ValueError:
        await message.answer('Укажите корректное значение в формате "ДД.ММ.ГГГГ"')
        return

    # Сохраняем ответ
    FSMAnket.answers[question_num] = answer
    if question_num + 1 < len(question_blocks):
        # Следующий вопрос:
        new_question_block = question_blocks[question_num + 1]
        new_question = new_question_block[0]
        new_answers = new_question_block[1]
        print(f'Следующий вопрос: {new_question}')
        print(f'Следующие ответы: {new_answers}')
        if new_answers:
            await message.answer(text=new_question, reply_markup=get_question_kb_button(question_num + 1))
            await state.set_state(FSMAnket.anket)
        else:
            print('Вопрос без вариантов ответа')
            await state.set_state(FSMAnket.text)
            await message.answer(new_question)
        await state.update_data(question_num=question_num + 1)
    else:
        # Вопросы кончились
        print('Вопросы кончились')
        text = format_confirm_text(FSMAnket.answers)
        confirm_btn = {
            'Отменить': 'cancel',
            'Отправить': 'confirm'
        }
        await message.answer(text, reply_markup=custom_kb(2, confirm_btn))
        await state.set_state(FSMAnket.confirm)


@router.callback_query(StateFilter(FSMAnket.confirm), F.data == 'confirm')
async def in_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await callback.message.delete_reply_markup()
        user = get_or_create_user(callback.from_user)
        answers = FSMAnket.answers
        user.set('create_date', answers[0])
        # user.set('inn', answers[2])
        user.set('is_active', 1)
        if user.analyse_count >= 3:
            await callback.message.answer(f'Здорово! Теперь мы можем приступить к анализу сотрудников для твоей компании.\n', reply_markup=start_kb)
        else:
            await callback.message.answer(
                f'Здорово! Теперь мы можем приступить к анализу сотрудников для твоей компании.\n',
                reply_markup=demo_start_kb)
        await state.clear()
    except Exception as err:
        logger.error(err)
        raise err


@router.callback_query(F.data == 'analyse')
@router.message(F.text == 'Анализ сотрудника', IsActive())
async def questions_text(message: Message, state: FSMContext, bot: Bot):
    if isinstance(message, CallbackQuery):
        user = get_or_create_user(message.from_user)
        message = message.message
        await message.delete()
    else:
        user = get_or_create_user(message.from_user)
    if user.cash < 20:
        await message.answer(f'Пополните баланс для использования сервиса по проверке совместимости.\nМинимальная сумма пополнения: 100 рублей. Стоимость 1 анализа: 20 рублей.\nВаш баланс: {user.cash} руб.', reply_markup=start_kb)
        return
    await message.answer('Укажите дату рождения кандидата или сотрудника в формате "ДД.ММ.ГГГГ"')
    await state.set_state(FSMAnket.new_analyse)


@router.message(FSMAnket.new_analyse, IsActive())
async def questions_text(message: Message, state: FSMContext, bot: Bot):
    try:
        user = get_or_create_user(message.from_user)
        birthday = datetime.datetime.strptime(message.text.strip(), '%d.%m.%Y').date()
        positive_index = get_positive_quality(birthday)
        negative_index = get_negative_quality(birthday)
        # hr_conversation_index = get_hr_conversation(birthday)
        specialist_profit_index = specialist_profit(birthday, user.create_date)
        hr_career_index = get_hr_career(birthday)
        result_text = (
            f'Результаты совместимости:\n\n'
            f'<b>Шанс на получение прибыли с помощью сотрудника: {specialist_profit_index}%</b>\n\n'
            f'<b>Положительные черты:</b>\n'
            f'{positive_dict[positive_index]}\n\n'
            f'<b>Отрицательные черты:</b>\n'
            f'{negative_dict[negative_index]}\n\n'
            # f'<b>Перспективность сотрудника:</b>\n'
            # f'{hr_career_dict[hr_career_index]}\n\n'
            # f'<b>Экономическая эффективность для вашей компании:</b>\n'
            # f'{hr_conversation_dict[hr_conversation_index]}\n\n'
        )
        await message.answer('Выполняется анализ')
        user = get_or_create_user(message.from_user)
        user.set('cash', user.cash - 20)

        await asyncio.sleep(3)
        if user.analyse_count >= 3:
            await message.answer(result_text, reply_markup=start_kb)
            await message.answer(f'Ваш баланс: {user.cash}')
        else:
            await message.answer(result_text, reply_markup=demo_start_kb)
        user.set('analyse_count', user.analyse_count + 1)

        await state.clear()

    except ValueError as err:
        logger.error(err)
        await message.answer('Введите дату в формате "ДД.ММ.ГГГГ".')

    except Exception as err:
        logger.error(err, exc_info=True)
        await message.answer('Произошла ошибка. Обратитесь к администратору')
        await bot.send_message(chat_id=conf.tg_bot.admin_ids[0], text=f'{message.text}: {err}')
        await state.clear()
