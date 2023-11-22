from aiogram.types import Message, InputFile
from loader import dp, db
from .menu import about_Us
from filters import IsUser

photo = InputFile("data/assets/delivery_zone.png")


@dp.message_handler(IsUser(), text=about_Us)
async def contact_with_seller(message: Message):
    await message.answer(f'Мы ценим важность каждого гостя. Именно поэтому мы особым образом подходим к '
                         f'производству блюд — приоритетом является постоянство гармонии вкуса, достигаемое '
                         f'профессиональными навыками поваров и большим объёмом начинки в каждом блюде.'
                         f' Нам есть чем гордиться: у нас очень вкусные суши, wok, роллы от наших'
                         f' суши-поваров — окунут вас в мир японской кухни.'
                         f' У нас большой ассортимент и доступные цены.')

    await message.answer_photo(photo=photo,
                               caption='Наша зона доставки')
