import datetime

from aiogram import Router, Bot
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery, Message, Update
from aiogram import F

from config_data.bot_conf import get_my_loggers, conf
from keyboards.keyboards import start_kb, custom_kb
from services.db_func import get_or_create_user

logger, err_log = get_my_loggers()

router: Router = Router()


class FSMPay(StatesGroup):
    pay_sum = State()


@router.callback_query(F.data == 'balance')
async def pay(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user = get_or_create_user(callback.from_user)
    kb = {'Пополнить': 'pay', 'Назад': 'cancel'}
    await callback.message.edit_text(f'Ваш баланс: {user.cash} руб.\nCтоимость 1 анализа: 20 рублей.', reply_markup=custom_kb(1, kb))


@router.callback_query(F.data == 'pay')
async def pay(callback: CallbackQuery, state: FSMContext, bot: Bot):
    logger.debug('pay')
    await state.clear()
    await callback.message.delete()
    user = get_or_create_user(callback.from_user)
    await callback.message.answer(f'Ваш баланс: {user.cash} руб.')
    await callback.message.answer('Введите сумму. Минимальное пополнение: 100 рублей.')
    await state.set_state(FSMPay.pay_sum)


@router.message(F.text, StateFilter(FSMPay.pay_sum))
async def pay_sum(message: Message, state: FSMContext, bot: Bot):
    try:
        pay_sum = int(message.text.strip().replace(' ', ''))
        if pay_sum < 100:
            await message.answer('Введите сумму от 100 до 10000')
            return
        # await state.update_data(pay_sum=pay_sum)
        price = LabeledPrice(label='Руб', amount=pay_sum * 100)
        await bot.send_invoice(
            chat_id=message.from_user.id,
            title='Оплата бота',
            description='Описание функционала бота',
            payload='pay_bot',
            provider_token=conf.tg_bot.YOOTOKEN,
            currency='RUB',
            start_parameter='start_parameter',
            prices=[price],
        )
        await state.clear()
    except ValueError:
        await message.answer('Введите целое число от 100 до 10000')


@router.pre_checkout_query()
async def pay_check(pre_pay_check: PreCheckoutQuery, bot: Bot):
    logger.debug('pay_check')
    logger.debug(f'paycheck: {pre_pay_check}')
    await bot.answer_pre_checkout_query(pre_pay_check.id, ok=True)


# pay_bot
@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_pay(message: Message, bot: Bot, event_update: Update, *args, **kwargs):
    successful_payment = message.successful_payment
    pay_sum = successful_payment.total_amount / 100
    if message.successful_payment.invoice_payload == 'pay_bot':
        logger.info('Подписка прошла успешно')
        user = get_or_create_user(message.from_user)
        user.set('cash', user.cash + pay_sum)
        user = get_or_create_user(message.from_user)
        await message.answer(f'Оплата прошла успешно. Ваш баланс: {user.cash}', reply_markup=start_kb)

    else:
        logger.info('Неудачно')
        await message.answer('Что-то пошло не так')
