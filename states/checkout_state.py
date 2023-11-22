from aiogram.dispatcher.filters.state import StatesGroup, State


class CheckoutState(StatesGroup):
    check_cart = State()
    name = State()
    delivery_choice = State()
    number_phone = State()
    address = State()
    confirm = State()
