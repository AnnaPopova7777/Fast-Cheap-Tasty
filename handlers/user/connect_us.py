from aiogram.types import Message
from loader import dp, db
from .menu import connect_us
from filters import IsUser


@dp.message_handler(IsUser(), text=connect_us)
async def contact_with_seller(message: Message):
    await message.answer(f'<b>Мы в телеграм:</b> https://t.me/sluzhba_zaboty1'
                         '\n<b>Мы в вк:</b> https://vk.com/bdv126,'
                         '\n<b>Мы в WhatsApp:</b> +7 928 326-82-09,'
                         '\n<b>Наш телефон:</b> 8‒800‒777‒92‒71,')
