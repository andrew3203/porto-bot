import imp
import asyncio
from re import M
import redis
from bot.models import MessageType
from bot.tasks import update_photo

import datetime
import logging
import telegram

from portobello.settings import TELEGRAM_TOKEN, TELEGRAM_LOGS_CHAT_ID

from flashtext import KeywordProcessor
from django.utils import timezone
from bot.handlers.broadcast_message.utils import _send_message, _send_photo, _revoke_message
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Poll, ParseMode,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
import requests


def get_inline_marckup(markup):
    keyboard = []
    for row in markup:
        keyboard.append([])
        for col in row:
            if len(col) == 2 and col[1]:
                btn = InlineKeyboardButton(text=col[0], url=col[1])
            else:
                btn = InlineKeyboardButton(
                    text=col[0], callback_data=col[0].lower().replace(' ', ''))
            keyboard[-1].append(btn)

    return InlineKeyboardMarkup(keyboard)


def get_keyboard_marckup(markup):
    keyboard = []
    for row in markup:
        keyboard.append([])
        for col in row:
            btn = KeyboardButton(text=col[0])
            keyboard[-1].append(btn)

    return ReplyKeyboardMarkup(keyboard)


def get_message_text(text, user_keywords):
    keyword_processor = KeywordProcessor()
    keyword_processor.add_keywords_from_dict(user_keywords)
    text = keyword_processor.replace_keywords(text)
    return text


def send_poll(context, update, text, markup):
    questions = ["Good", "Really good", "Fantastic", "Great"]
    message = context.bot.send_poll(
        update.effective_chat.id,
        "How are you?",
        questions,
        is_anonymous=False,
        allows_multiple_answers=False,
    )
    # Save some info about the poll the bot_data for later use in receive_poll_answer
    payload = {
        message.poll.id: {
            "questions": questions,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)


def send_message(prev_state, next_state, user_id, prev_message_id):
    prev_msg_type = prev_state["message_type"] if prev_state else None
    next_msg_type = next_state["message_type"]

    markup = next_state["markup"]
    message_text = get_message_text(
        next_state["text"], 
        next_state['user_keywords']
    )

    photos = next_state.get("photos", [])
    photo = photos.pop(0) if len(photos) > 0 else None

    for file in photos:
        _send_photo(file,  user_id=user_id)

    if prev_msg_type != MessageType.POLL and prev_message_id and prev_message_id != '':
        _revoke_message(
            user_id=user_id,
            message_id=prev_message_id
        )
    
    if next_msg_type == MessageType.POLL:
        send_poll(text=message_text, markup=markup)
        message_id = None

    else:
        if next_msg_type == MessageType.KEYBOORD_BTN:
            reply_markup = get_keyboard_marckup(markup)

        elif next_msg_type == MessageType.FLY_BTN:
            reply_markup = get_inline_marckup(markup)

        else:
            reply_markup = None

        message_id = _send_message(
            user_id=user_id,
            text=message_text,
            photo=photo,
            reply_markup=reply_markup
        )

    return message_id


def send_registration(user_id, user_code):
    requests.post(
        url='https://crm.portobello.ru/api/telegram/sign-up', 
        data = {'tg_user_id': user_id, 'bd_user_id': user_code }
    )


def get_user_info(user_id, user_code):
    resp = requests.get(
        url=f'https://crm.portobello.ru/api/telegram/get-user-info?id={user_id}'
    )
    return resp.json()


def send_broadcast_message(next_state, user_id):
    next_msg_type = next_state["message_type"]

    markup = next_state["markup"]
    message_text = get_message_text(next_state["text"], next_state['user_keywords'])

    if next_msg_type == MessageType.POLL:
        send_poll(text='Опрос', markup=markup)
        reply_markup = None
    elif next_msg_type == MessageType.KEYBOORD_BTN:
        reply_markup = get_keyboard_marckup(markup)
    elif next_msg_type == MessageType.FLY_BTN:
        reply_markup = get_inline_marckup(markup)
    else:
        reply_markup = None

    prev_msg_id = _send_message(
        user_id=user_id,
        text=message_text,
        reply_markup=reply_markup
    )
    return prev_msg_id


def send_logs_message(msg_text, user_keywords):
    text = f'{msg_text}' + \
        '\n\n<b>first_name last_name</b>\n' \
        'company, phone'
    
    message_text = get_message_text(text, user_keywords)
    _send_message(
        user_id=TELEGRAM_LOGS_CHAT_ID,
        text=message_text
    )