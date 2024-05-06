# @bot.callback_query_handler(func=lambda call: call.data.startswith('prod_'))
# def show_product(call):
#     product_id = int(call.data.split('_')[1])
#     product = Product.objects.get(id=product_id)
#     images = product.images.all()
#     if images.exists():
#         photo = open(os.path.join(settings.MEDIA_ROOT, str(images[0].image)), 'rb')
#         markup = types.InlineKeyboardMarkup()
#         if len(images) > 1:
#             markup.add(
#                 types.InlineKeyboardButton(text='⬅️', callback_data=f'left_{product_id}_0'),
#                 types.InlineKeyboardButton(text='➡️', callback_data=f'right_{product_id}_0')
#             )
#         bot.send_photo(chat_id=call.message.chat.id, photo=photo, reply_markup=markup)
#         photo.close()
#     else:
#         bot.answer_callback_query(call.id, "No images available for this product.")
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith(('left_', 'right_')))
# def navigate_images(call):
#     direction, product_id, index = call.data.split('_')
#     product_id = int(product_id)
#     index = int(index)
#     images = Product.objects.get(id=product_id).images.all()
#     if len(images) > 1:
#         if direction == 'left':
#             new_index = index - 1 if index > 0 else len(images) - 1
#         elif direction == 'right':
#             new_index = index + 1 if index < len(images) - 1 else 0
#
#         new_image = images[new_index].image.path
#         markup = types.InlineKeyboardMarkup()
#         markup.add(
#             types.InlineKeyboardButton(text='⬅️', callback_data=f'left_{product_id}_{new_index}'),
#             types.InlineKeyboardButton(text='➡️', callback_data=f'right_{product_id}_{new_index}')
#         )
#         with open(new_image, 'rb') as photo:
#             bot.edit_message_media(media=types.InputMediaPhoto(photo),
#                                    chat_id=call.message.chat.id,
#                                    message_id=call.message.message_id,
#                                    reply_markup=markup)
#     else:
#         bot.answer_callback_query(call.id, "Only one image available, no navigation needed.")
#
# def list_products(bot, chat_id):
#     products = Product.objects.all()
#     markup = types.InlineKeyboardMarkup()
#     for product in products:
#         button = types.InlineKeyboardButton(text=product.title, callback_data=f'prod_{product.id}')
#         markup.add(button)
#     bot.send_message(chat_id, "Select a product:", reply_markup=markup)

# Use safe_polling() to handle exceptions and automatically restart polling
