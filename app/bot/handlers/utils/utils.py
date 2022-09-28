from bot.models import MessageType
from portobello.settings import TELEGRAM_LOGS_CHAT_ID

from flashtext import KeywordProcessor
from django.utils import timezone
from bot.handlers.broadcast_message.utils import _send_message, _send_media_group, _revoke_message
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
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


def send_poll(user_id, poll_id, text, markup, context):
    questions = [m[0][0] for m in markup]
    message = context.bot.send_poll(
        user_id,
        text,
        questions,
        is_anonymous=False,
        allows_multiple_answers=False,
    )
    payload = {
        message.poll.id: {
            'poll_id': poll_id,
            "questions": questions,
            "message_id": message.message_id,
            "chat_id": user_id,
            #"answers": 0,
        }
    }
    context.bot_data.update(payload)


def send_message(prev_state, next_state, context, user_id, prev_message_id):
    prev_msg_type = prev_state["message_type"] if prev_state else None
    next_msg_type = next_state["message_type"]

    markup = next_state["markup"]
    message_text = get_message_text(
        next_state["text"], 
        next_state['user_keywords']
    )

    photos = next_state.get("photos", [])

    if len(photos) > 1:
        _send_media_group(photos, user_id=user_id)
        photo = None
    elif len(photos) == 1:
        photo = photos.pop(0)
    else:
        photo = None
    

    if prev_message_id and prev_message_id != '' and prev_message_id != MessageType.POLL:
        #_revoke_message(
        #    user_id=user_id,
        #    message_id=prev_message_id
        #)
        pass
    
    if next_msg_type == MessageType.POLL:
        send_poll(
            user_id, 
            poll_id=next_state['poll_id'], 
            text=message_text, 
            markup=markup, 
            context=context
        )
        message_id = ''

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


def send_broadcast_message(next_state, user_id, prev_message_id):
    next_msg_type = next_state["message_type"]

    markup = next_state["markup"]
    message_text = get_message_text(next_state["text"], next_state['user_keywords'])

    if prev_message_id and prev_message_id != '' and prev_message_id != MessageType.POLL:
        _revoke_message(
            user_id=user_id,
            message_id=prev_message_id
        )

    if next_msg_type == MessageType.POLL:
        send_poll(text='Опрос', markup=markup)
        reply_markup = None
    elif next_msg_type == MessageType.KEYBOORD_BTN:
        reply_markup = get_keyboard_marckup(markup)
    elif next_msg_type == MessageType.FLY_BTN:
        reply_markup = get_inline_marckup(markup)
    else:
        reply_markup = None

    photos = next_state.get("photos", [])
    photo = photos.pop(0) if len(photos) > 0 else None

    prev_msg_id = _send_message(
        user_id=user_id,
        text=message_text,
        photo=photo,
        reply_markup=reply_markup
    )
    return prev_msg_id


def send_logs_message(msg_text, user_keywords, prev_state):
    markup = prev_state.get('markup', []) if prev_state else []
    try:
        decoder = dict([(k[0][0].replace(' ', '').lower(), k[0][0]) for k in markup])
        msg_text = decoder.get(msg_text, msg_text)
    except Exception as e:
        msg_text = msg_text

    text = f'{msg_text}' + \
        '\n\n' \
        '<b>first_name last_name</b> (user_id)\n' \
        'company\n' \
        'phone'
    try:
        message_text = get_message_text(text, user_keywords)
    except:
        message_text = f'{msg_text}' + \
        '\n\n' \
        f'<b>{user_keywords.get("first_name", "Noname")} {user_keywords.get("last_name", "Noname")}</b> ({user_keywords.get("user_id", "Noname")})\n' \


    _send_message(
        user_id=TELEGRAM_LOGS_CHAT_ID,
        text=message_text
    )