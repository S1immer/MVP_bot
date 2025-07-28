from aiogram.filters.state import State, StatesGroup


class SubscriptionState(StatesGroup):

    waiting_for_action = State()
    waiting_for_payment = State()
    waiting_for_check_payment = State()

    """no_subscription"""
    no_sub_choose_tariff = State()
    no_sub_choose_devices = State()

    """expired"""
    expired_choose_tariff = State()
    expired_choose_devices = State()

    """active"""
    active_choose_tariff = State()
    active_choose_devices = State()
    active_choose_action = State()
