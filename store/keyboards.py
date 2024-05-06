from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from .models import *


def contact_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    buttons = [
        [KeyboardButton(text='Поделиться контактами 📲', request_contact=True)],
        [KeyboardButton(text='❌ Отменить ')]
    ]
    keyboard.add(*[button for row in buttons for button in row])
    return keyboard


def my_name_button(my_name):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn = KeyboardButton(text=f'👤 {my_name}')
    markup.add(btn)
    return markup


def gen_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    button = [
        InlineKeyboardButton("📗 Категории", callback_data="category"),
        InlineKeyboardButton("🖤 Избранное", callback_data="favourites"),
        InlineKeyboardButton("🛒 Корзина", callback_data="cart"),
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
    ]
    keyboard.add(*button)
    keyboard.row(
        InlineKeyboardButton("📞 Call-center", callback_data="callcenter"),
    )
    keyboard.row(
        InlineKeyboardButton("📬 Жалобы и предложения", callback_data="complaints"),
    )
    return keyboard


# def list_categories():
#     products = Category.objects.all()[1:]
#     emojis = ['']
#     markup = InlineKeyboardMarkup()
#     for product in products:
#         button = InlineKeyboardButton(text=product.title, callback_data=f'cat_{product.id}')
#         markup.add(button)
#     return markup

def back_to_main():
    keyboard = InlineKeyboardMarkup(row_width=2)
    button = [
        InlineKeyboardButton("🏠 Главное меню", callback_data="main"),
    ]
    keyboard.add(*button)
    return keyboard


def list_products(products):
    markup = InlineKeyboardMarkup()
    for product in products:
        button = InlineKeyboardButton(text=product.title, callback_data=f'prod_{product.id}')
        markup.add(button)
    return markup
