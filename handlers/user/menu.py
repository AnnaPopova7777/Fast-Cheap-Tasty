from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup
from loader import dp
from filters import IsAdmin, IsUser

catalog = '🛍️ Каталог'
balance = '💰 Баланс'
cart = '🛒 Корзина'
about_Us = '🧑🏼‍🍳 О нас'
connect_us = '📞Связаться с нами'


@dp.message_handler(IsUser(), commands='menu')
async def user_menu(message: Message):
    markup = ReplyKeyboardMarkup(selective=True)
    markup.add(catalog)
    markup.add(cart)
    markup.add(about_Us)
    markup.add(connect_us)

    await message.answer('Меню. Если нужна помощь в пользовании ботом введите команду /help'
                         '\n Оплата заказа производится картой или наличными при получении.'
                         '\nДоставка курьером стоит 150 рублей', reply_markup=markup)
