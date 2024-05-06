from django.core.management.base import BaseCommand
from store.models import *
from telebot.types import ReplyKeyboardRemove
from store.keyboards import *
from django.conf import settings
from django.core.cache import cache
from pprint import pprint
# from apscheduler.schedulers.background import BackgroundScheduler
import subprocess
import datetime
import os
import re
from telebot import TeleBot, types
import random
import string

import logging
import time

from telebot.types import Message

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

integer_regex = re.compile(r'^[0-9]+$')


class BotState:
    def __init__(self):
        self.state = None


fsm = BotState()
USER_STATE = {}


def log_errors(f):
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_message = f'Error: {e}'
            logger.error(error_message, exc_info=True)  # Log the error with stack trace
            raise e

    return inner


def generate_product_details(product, quantity, color):
    return (
        f"Title: {product.title}\n"
        f"Price: {product.price} $\n"
        f"Size: {product.size}\n"
        f"Color: {color}\n"  # Dynamic color display
        f"Quantity available: {product.quantity} (Selected: {quantity})\n"
        f"Description: {product.description}\n"
    )


def generate_markup(product, quantity, has_multiple_images, current_index=0):
    """Generate dynamic markup for product interactions."""
    markup = types.InlineKeyboardMarkup(row_width=2)

    # Quantity adjustment buttons, respecting product quantity limits
    cart_buttons = [
        types.InlineKeyboardButton(text='-', callback_data=f'decr_{product.id}_{quantity}' if quantity > 1 else '022'),
        types.InlineKeyboardButton(text=str(quantity), callback_data='noop'),  # Display only
        types.InlineKeyboardButton(text='+',
                                   callback_data=f'incr_{product.id}_{quantity}' if quantity < product.quantity else '023'),
    ]
    markup.row(*cart_buttons)

    # Navigation buttons for images, conditionally enabled
    if has_multiple_images:
        left_button = types.InlineKeyboardButton(
            text='⬅️',
            callback_data=f'left_{product.id}_{current_index}' if current_index > 0 else '020'
        )
        right_button = types.InlineKeyboardButton(
            text='➡️',
            callback_data=f'right_{product.id}_{current_index}' if current_index < product.images.count() - 1 else '020'
        )
        markup.row(left_button, right_button)

    # Back and Add to Cart buttons
    markup.add(
        types.InlineKeyboardButton(text='🏠 Главное меню', callback_data=f'main'),
        types.InlineKeyboardButton(text='Add to Cart 🛒', callback_data=f'cart_{product.id}_{quantity}'),
        types.InlineKeyboardButton(text='♥ Add to Favorites', callback_data=f'favorites_{product.id}')
    )

    return markup


def generate_navigation_markup(product_id, current_index, total_images, quantity):
    """Generate dynamic markup for navigation and purchasing."""
    markup = types.InlineKeyboardMarkup(row_width=2)

    # Quantity adjustment buttons, always active but limits respected
    markup.row(
        types.InlineKeyboardButton(text='-', callback_data=f'decr_{product_id}_{quantity}' if quantity > 1 else '022'),
        types.InlineKeyboardButton(text=str(quantity), callback_data='noop'),
        types.InlineKeyboardButton(text='+',
                                   callback_data=f'incr_{product_id}_{quantity}' if quantity < total_images else '023'),
    )

    # Conditional navigation buttons
    left_button = types.InlineKeyboardButton(
        text='⬅️',
        callback_data=f'left_{product_id}_{current_index}' if current_index > 0 else '020'
    )
    right_button = types.InlineKeyboardButton(
        text='➡️',
        callback_data=f'right_{product_id}_{current_index}' if current_index < total_images - 1 else '020'
    )
    markup.row(left_button, right_button)

    # Back and Add to Cart buttons
    markup.add(
        types.InlineKeyboardButton(text='🏠 Главное меню', callback_data=f'main'),
        types.InlineKeyboardButton(text='Add to Cart 🛒', callback_data=f'cart_{product_id}_{quantity}'),
        types.InlineKeyboardButton(text='♥ Add to Favorites', callback_data=f'favorites_{product_id}')
    )

    return markup


def safe_polling(bot):
    while True:
        try:
            bot.infinity_polling()
            break  # If infinity_polling returns normally, exit the loop
        except Exception as e:
            logger.error("Unexpected error: %s. Restarting bot.", str(e), exc_info=True)
            time.sleep(10)  # Wait before restarting


def list_categories(chat_id):
    categories = Category.objects.all()[1:]  # Assuming the first category is excluded
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)

    # Assume each category has an 'emoji' attribute for simplicity
    # If not, you can define a dictionary to map categories to emojis
    temp_row = []
    for category in categories:
        button_text = f"'{category.emojis}' {category.title}"  # Concatenate emoji and title
        temp_row.append(button_text)
        if len(temp_row) == 2:
            markup.row(*temp_row)
            temp_row = []
    if temp_row:  # Add the last row if there's an odd number of categories
        markup.row(*temp_row)

    USER_STATE[chat_id] = 'choosing_category'
    return markup


class Command(BaseCommand):
    help = 'Telegram bot'

    def handle(self, *args, **options):
        bot = TeleBot(settings.TOKEN)
        logger = logging.getLogger(__name__)
        logger.info("Bot started")

        @bot.message_handler(commands=['start'])
        def command_start(message):
            chat_id = message.chat.id
            existing_profiles = ProfileTelegram.objects.filter(external_id=chat_id)
            user_full_name = message.from_user.full_name
            if existing_profiles.exists():
                for profile in existing_profiles:
                    fullname = profile.fullname
                    bot.send_message(chat_id, 'Добро пожаловать!', reply_markup=ReplyKeyboardRemove())
                    bot.send_message(chat_id, f'🤗 Здравствуйте, {fullname}.', reply_markup=gen_main_menu())

            else:
                fsm.state = 'awaiting_fullname'
                bot.send_message(chat_id, f'🤗 Здравствуйте, {message.from_user.full_name}',
                                 reply_markup=ReplyKeyboardRemove())

                bot.send_message(chat_id, '📝 Пожалуйста, введите свое полное имя',
                                 reply_markup=my_name_button(user_full_name))

        @bot.message_handler(func=lambda message: fsm.state == 'awaiting_fullname')
        def fullname_handler(message: Message):
            chat_id = message.chat.id
            cache.set(chat_id, {'fullname': message.text})
            fsm.state = 'awaiting_contact'
            bot.send_message(chat_id, '☎️ Пожалуйста, поделитесь своим контактом',
                             reply_markup=contact_keyboard())

        @bot.message_handler(regexp='(❌ Отменить|❌ Bekor qilish)',
                             func=lambda message: fsm.state == 'awaiting_contact')
        def cancel_handler(message: Message):
            chat_id = message.from_user.id

            bot.send_message(chat_id, '❌ Отменено', reply_markup=ReplyKeyboardRemove())

        @bot.message_handler(content_types=['contact'], func=lambda message: fsm.state == 'awaiting_contact')
        def contact(message: Message):
            chat_id = message.chat.id
            user_data = cache.get(chat_id)
            if user_data and 'fullname' in user_data:
                fullname = user_data['fullname']
                phone_number = message.contact.phone_number
                fullname = fullname.replace('👤', '')
            profile, created = ProfileTelegram.objects.get_or_create(
                contacts=phone_number,
                defaults={
                    'external_id': chat_id,
                    'fullname': fullname,
                    'username': message.from_user.username
                }
            )
            msg = f'🤗 Здравствуйте, {fullname}.'
            bot.send_message(chat_id, ' Добро пожаловать!', reply_markup=ReplyKeyboardRemove())
            bot.send_message(chat_id, msg, reply_markup=gen_main_menu())
            if not created:
                bot.send_message(chat_id, 'Вы уже зарегистрированы.', reply_markup=gen_main_menu())

        @bot.callback_query_handler(func=lambda call: 'category' in call.data)
        def category(call):
            chat_id = call.message.chat.id
            bot.send_message(chat_id, '📗 Выберите категорию', reply_markup=list_categories(chat_id))

        @bot.callback_query_handler(func=lambda call: 'main' in call.data)
        def main(call):
            chat_id = call.message.chat.id
            bot.send_message(chat_id, '🏠 Главное меню', reply_markup=gen_main_menu())

        @bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id) == 'choosing_category')
        def handle_category_selection(message):
            chat_id = message.chat.id
            category_title = message.text.split("'")[2].strip()
            category = Category.objects.filter(title=category_title).first()
            if category:
                products = ProductTelegram.objects.filter(category=category.id).all()
                if products:
                    bot.send_message(chat_id, "Выберите продукт:", reply_markup=list_products(products))
                else:
                    bot.send_message(chat_id, "В этой категории пока нет продуктов.",
                                     reply_markup=back_to_main())  # No products found

                fsm.state = None
            else:
                bot.send_message(chat_id, "Категория не найдена, пожалуйста, выберите заново.")
                list_categories(chat_id)

        @bot.callback_query_handler(func=lambda call: call.data.startswith('prod_'))
        def show_product(call):
            product_id = int(call.data.split('_')[1])
            product = ProductTelegram.objects.get(id=product_id)
            images = product.images.all()
            print(images)
            if images.exists():
                initial_image = images.first()
                photo_path = os.path.join(settings.MEDIA_ROOT, str(initial_image.image))
                initial_quantity = 1  # Start with a default purchasing quantity of 1
                initial_color = initial_image.color  # Get the color of the initial image
                product_details = generate_product_details(product, initial_quantity,
                                                           initial_color)  # Include color in details

                markup = generate_markup(product, initial_quantity, len(images) > 1, 0)  # Start at the first image
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(chat_id=call.message.chat.id, photo=photo, caption=product_details,
                                   reply_markup=markup)
            else:
                bot.answer_callback_query(call.id, "No images available for this product.")

        @bot.callback_query_handler(func=lambda call: call.data == '020')
        def noop(call):
            bot.answer_callback_query(call.id, "No more images in this direction.")

        @bot.callback_query_handler(func=lambda call: call.data == '023')
        def noop(call):
            bot.answer_callback_query(call.id, "Cannot order more than available")

        @bot.callback_query_handler(func=lambda call: call.data == '022')
        def noop(call):
            bot.answer_callback_query(call.id, "Cannot order less than one")

        @bot.callback_query_handler(func=lambda call: call.data.startswith(('left_', 'right_')))
        def navigate_images(call):
            direction, product_id, index = call.data.split('_')
            product_id = int(product_id)
            index = int(index)
            product = ProductTelegram.objects.get(id=product_id)
            images = product.images.all()
            current_quantity = 1  # This could be dynamic based on user interactions if implemented

            if len(images) > 1:
                new_index = (index - 1 if direction == 'left' and index > 0 else
                             (index + 1 if direction == 'right' and index < len(images) - 1 else index))
                new_image = images[new_index]
                new_image_path = os.path.join(settings.MEDIA_ROOT, str(new_image.image))
                current_color = new_image.color  # Fetch color of the new image
                product_details = generate_product_details(product, current_quantity, current_color)

                with open(new_image_path, 'rb') as photo:
                    markup = generate_navigation_markup(product_id, new_index, len(images), current_quantity)
                    try:
                        bot.edit_message_media(
                            media=types.InputMediaPhoto(photo, caption=product_details),
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            reply_markup=markup
                        )
                    except Exception as e:
                        print(f"Failed to update image due to: {str(e)}")
                        bot.answer_callback_query(call.id, "Failed to update image.")
            else:
                bot.answer_callback_query(call.id, "No additional images to navigate.")

        @bot.callback_query_handler(func=lambda call: call.data.startswith(('incr_', 'decr_')))
        def adjust_quantity(call):
            action, product_id, current_quantity = call.data.split('_')
            product_id = int(product_id)
            current_quantity = int(current_quantity)
            product = ProductTelegram.objects.get(id=product_id)
            images = product.images.all()  # Assuming images are available
            if images.exists():
                current_image = images.first()  # This should ideally be the currently displayed image
                current_color = current_image.color

                if 'incr' in action:
                    new_quantity = min(product.quantity, current_quantity + 1)
                else:
                    new_quantity = max(1, current_quantity - 1)

                product_details = generate_product_details(product, new_quantity, current_color)
                markup = generate_markup(product, new_quantity, len(images) > 1)
                bot.edit_message_caption(
                    caption=product_details,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=markup
                )

        bot.infinity_polling()

        logger.info("Bot stopped")
