import logging
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton

from data.config import ADMIN_ID
from keyboards.inline.products_from_cart import product_markup, product_cb
from aiogram.utils.callback_data import CallbackData
from keyboards.default.markups import *
from aiogram.types.chat import ChatActions
from states import CheckoutState
from loader import dp, db, bot
from filters import IsUser
from .menu import cart


@dp.message_handler(IsUser(), text=cart)
async def process_cart(message: Message, state: FSMContext):
    cart_data = db.fetchall(
        'SELECT * FROM cart WHERE cid=?', (message.chat.id,))

    if len(cart_data) == 0:

        await message.answer('Ваша корзина пуста.')

    else:

        await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
        async with state.proxy() as data:
            data['products'] = {}

        order_cost = 0

        for _, idx, count_in_cart in cart_data:

            product = db.fetchone('SELECT * FROM products WHERE idx=?', (idx,))

            if product == None:

                db.query('DELETE FROM cart WHERE idx=?', (idx,))

            else:
                _, title, body, image, price, _ = product
                order_cost += price

                async with state.proxy() as data:
                    data['products'][idx] = [title, price, count_in_cart]

                markup = product_markup(idx, count_in_cart)
                text = f'<b>{title}</b>\n\n{body}\n\nЦена: {price}₽.'

                await message.answer_photo(photo=image,
                                           caption=text,
                                           reply_markup=markup)

        if order_cost != 0:
            markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add('📦 Оформить заказ', '🧹Очистить корзину')

            await message.answer('Перейти к оформлению?',
                                 reply_markup=markup)


@dp.callback_query_handler(IsUser(), product_cb.filter(action='count'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='increase'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='decrease'))
async def product_callback_handler(query: CallbackQuery, callback_data: dict, state: FSMContext):
    idx = callback_data['id']
    action = callback_data['action']

    if 'count' == action:

        async with state.proxy() as data:

            if 'products' not in data.keys():

                await process_cart(query.message, state)

            else:

                await query.answer('Количество - ' + data['products'][idx][2])

    else:

        async with state.proxy() as data:

            if 'products' not in data.keys():

                await process_cart(query.message, state)

            else:

                data['products'][idx][2] += 1 if 'increase' == action else -1
                count_in_cart = data['products'][idx][2]

                if count_in_cart == 0:

                    db.query('''DELETE FROM cart
                    WHERE cid = ? AND idx = ?''', (query.message.chat.id, idx))

                    await query.message.delete()
                else:

                    db.query('''UPDATE cart 
                    SET quantity = ? 
                    WHERE cid = ? AND idx = ?''', (count_in_cart, query.message.chat.id, idx))

                    await query.message.edit_reply_markup(product_markup(idx, count_in_cart))


@dp.message_handler(IsUser(), text='📦 Оформить заказ')
async def process_checkout(message: Message, state: FSMContext):
    await CheckoutState.check_cart.set()
    await checkout(message, state)


async def checkout(message, state):
    answer = ''
    total_price = 0

    async with state.proxy() as data:
        for title, price, count_in_cart in data['products'].values():
            tp = count_in_cart * price
            answer += f'<b>{title}</b> * {count_in_cart}шт. = {tp}₽\n'
            total_price += tp

    await message.answer(f'{answer}\nОбщая сумма заказа: {total_price}₽.',
                         reply_markup=check_markup())


@dp.message_handler(IsUser(), lambda message: message.text not in [all_right_message, back_message],
                    state=CheckoutState.check_cart)
async def process_check_cart_invalid(message: Message):
    await message.reply('Такого варианта не было.')


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.check_cart)
async def process_check_cart_back(message: Message, state: FSMContext):
    await state.finish()
    await process_cart(message, state)


@dp.message_handler(IsUser(), text=all_right_message, state=CheckoutState.check_cart)
async def process_check_cart_all_right(message: Message, state: FSMContext):
    await CheckoutState.next()
    await message.answer('Укажите свое имя.',
                         reply_markup=back_markup())


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.name)
async def process_name_back(message: Message, state: FSMContext):
    await CheckoutState.check_cart.set()
    await checkout(message, state)


@dp.message_handler(IsUser(), state=CheckoutState.name)
async def process_name(message: Message, state: FSMContext):
    async with state.proxy() as data:

        markup_del = ReplyKeyboardMarkup(selective=True)
        markup_del.add('Курьером', 'Самовывоз')
        markup_del.add(back_message)

        data['name'] = message.text

        if 'delivery_c' in data.keys():

            await confirm(message)
            await CheckoutState.confirm.set()

        else:

            await CheckoutState.next()
            await message.answer('Выберите способ доставки.',
                                 reply_markup=markup_del)


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.delivery_choice)
async def process_address_back(message: Message, state: FSMContext):
    async with state.proxy() as data:
        await message.answer('Изменить имя с <b>' + data['name'] + '</b>? Введите новое.',
                             reply_markup=back_markup())

    await CheckoutState.name.set()


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.delivery_choice)
async def process_name_back(message: Message, state: FSMContext):
    await CheckoutState.check_cart.set()
    await checkout(message, state)


@dp.message_handler(IsUser(), state=CheckoutState.delivery_choice)
async def process_name(message: Message, state: FSMContext):
    async with state.proxy() as data:

        data['delivery_c'] = message.text

        if 'number' in data.keys():

            await confirm(message)
            await CheckoutState.confirm.set()

        else:

            await CheckoutState.next()
            await message.answer('Укажите свой номер телефона, '
                                 'что бы менеджер мог связаться с вами и уточнить детали заказа.',
                                 reply_markup=back_markup())


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.number_phone)
async def process_address_back(message: Message, state: FSMContext):
    markup_del = ReplyKeyboardMarkup(selective=True)
    markup_del.add('Курьером', 'Самовывоз')
    markup_del.add(back_message)
    async with state.proxy() as data:
        await message.answer('Изменить способ доставки с <b>' + data['delivery_c'] + '</b>? Выберите новый.',
                             reply_markup=markup_del)

    await CheckoutState.delivery_choice.set()


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.number_phone)
async def process_number_back(message: Message, state: FSMContext):
    await CheckoutState.check_cart.set()
    await checkout(message, state)


@dp.message_handler(IsUser(), state=CheckoutState.number_phone)
async def process_number(message: Message, state: FSMContext):
    async with state.proxy() as data:

        data['number'] = message.text

        if 'address' in data.keys():

            await confirm(message)
            await CheckoutState.confirm.set()

        else:

            await CheckoutState.next()
            await message.answer('Укажите свой адрес места жительства',
                                 reply_markup=back_markup())


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.address)
async def process_address_back(message: Message, state: FSMContext):
    async with state.proxy() as data:
        await message.answer('Изменить номер телефона с <b>' + data['number'] + '</b>? Введите новый.',
                             reply_markup=back_markup())

    await CheckoutState.number_phone.set()


@dp.message_handler(IsUser(), state=CheckoutState.address)
async def process_address(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['address'] = message.text

    await confirm(message)
    await CheckoutState.next()


async def confirm(message):
    await message.answer('Убедитесь, что все правильно оформлено и подтвердите заказ.',
                         reply_markup=confirm_markup())


@dp.message_handler(IsUser(), lambda message: message.text not in [confirm_message, back_message],
                    state=CheckoutState.confirm)
async def process_confirm_invalid(message: Message):
    await message.reply('Такого варианта не было.')


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.confirm)
async def process_confirm(message: Message, state: FSMContext):
    await CheckoutState.address.set()

    async with state.proxy() as data:
        await message.answer('Изменить адрес с <b>' + data['address'] + '</b>? Укажите новый.',
                             reply_markup=back_markup())


@dp.message_handler(IsUser(), text=confirm_message, state=CheckoutState.confirm)
async def process_confirm(message: Message, state: FSMContext):
    enough_money = True  # enough money on the balance sheet
    markup = ReplyKeyboardRemove()
    answer = ''
    total_price = 0

    async with state.proxy() as data:
        for title, price, count_in_cart in data['products'].values():
            tp = count_in_cart * price
            answer += f'<b>{title}</b> * {count_in_cart}шт. = {tp}₽\n'
            total_price += tp
            total_price_cur = total_price + 150

    if enough_money:
        logging.info('Deal was made.')

        async with state.proxy() as data:
            cid = message.chat.id
            products = [idx + '=' + str(quantity)
                        for idx, quantity in db.fetchall('''SELECT idx, quantity FROM cart
            WHERE cid=?''', (cid,))]  # idx=quantity

            db.query('INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)',
                     (cid, data['name'], data['delivery_c'], data['number'], data['address'], ' '.join(products)))

            db.query('DELETE FROM cart WHERE cid=?', (cid,))

            await message.answer(
                'Ок! Ваш заказ уже в пути 🚀\nИмя: <b>' + data['name'] +
                '</b>\nСпособ доставки: <b>' + data['delivery_c'] +
                '</b>\nНомер телефона: <b>' + data['number'] +
                '</b>\nАдрес: <b>' + data['address'] + '</b>',
                reply_markup=markup)

            if data['delivery_c'] == 'Курьером':
                await message.answer(f'{answer}\nОбщая сумма заказа (учитывая доставку курьером): {total_price_cur}₽.')
            elif data['delivery_c'] == 'Самовывоз':
                await message.answer(f'{answer}\nОбщая сумма заказа: {total_price}₽.')

            await message.answer('Отлично! Менеджер свяжется с вами в ближайшие минуты.'
                                 '\n Если вы желаете сейчас изменить или отменить заказ,'
                                 '\n позвоните нам: 8‒800‒777‒92‒71')

            await bot.send_message(ADMIN_ID, 'Ура! Новый заказ 🚀\nИмя: <b>' + data['name'] +
                                   '</b>\nСпособ доставки: <b>' + data['delivery_c'] +
                                   '</b>\nНомер телефона: <b>' + data['number'] +
                                   '</b>\nАдрес: <b>' + data['address'] + '</b>')

            if data['delivery_c'] == 'Курьером':
                await bot.send_message(ADMIN_ID, f'{answer}\nОбщая сумма заказа (учитывая доставку курьером): {total_price_cur}₽.')
            elif data['delivery_c'] == 'Самовывоз':
                await bot.send_message(ADMIN_ID, f'{answer}\nОбщая сумма заказа: {total_price}₽.')

    await state.finish()


@dp.message_handler(IsUser(), text='🧹Очистить корзину')
async def process_cart(message: Message, state: FSMContext):
    async with state.proxy() as data:
        cid = message.chat.id
        db.query('DELETE FROM cart WHERE cid=?', (cid,))

    await message.answer('Окей, ваша корзина очищена. \nЧто бы продолжить работу, нажми сюда /menu')



