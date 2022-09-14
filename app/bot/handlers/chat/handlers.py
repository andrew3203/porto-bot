import datetime
from email import message
import logging
import re
from django.utils import timezone

from django.utils import timezone
from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from bot.models import User, Poll
from bot.handlers.utils import utils
from bot.handlers.utils.info import extract_user_data_from_update
from bot.tasks import send_delay_message


def command_start(update: Update, context: CallbackContext) -> None:
    u, created = User.get_user_and_created(update, context)

    if u.deep_link:
        user_balance = utils.get_user_info(u.user_id, u.deep_link)
        u.update_info(user_balance)

    if created and u.deep_link:
            utils.send_registration(user_code=u.deep_link, user_id=u.user_id)
            update.message.reply_text(f'{u.first_name}, Вы успешно зарегистрированы в программе лояльности!')
            update.message.reply_text(
                text="👋 Привет! Давайте знакомиться!\n\n" \
                "Меня зовут Павел, и я отвечаю за нашу программу лояльности.\n" \
                "Сейчас вы находитесь в моем телеграм-боте, через который мы с вами можем общаться напрямую! " \
                "Мой бот будет присылать вам всю необходимую информацию в рамках программы, а иногда я лично " \
                "буду писать вам и рассказывать о наших новых возможностях, акциях и эксклюзивных предложениях! 😎\n\n" \
                "Если у вас возникнут вопросы по программе, пишите боту. Он передаст мне всю информацию, " \
                "и в ближайшее время я с вами свяжусь!",
            )
            now = timezone.now()
            send_delay_message.apply_async(
                  kwargs={'user_id': u.user_id, 'msg_name': 'start'}, 
                eta=now+datetime.timedelta(seconds=10)
            )
            utils.send_logs_message(
                msg_text='start', 
                user_keywords=u.get_keywords(), 
                markup=[]
            )
            task1 = send_delay_message.apply_async(
                kwargs={'user_id': u.user_id, 'msg_name': 'Клуб лидеров'}, 
                eta=now+datetime.timedelta(seconds=60)#days=1)
            )
            task2 = send_delay_message.apply_async(
                kwargs={'user_id': u.user_id, 'msg_name': 'Колесо Фортуны'},
                 eta=now+datetime.timedelta(seconds=200)#days=2)
            )
            
    else:
        recive_command(update, context)


def command_balance(update: Update, context: CallbackContext) -> None:
    u, _ = User.get_user_and_created(update, context)
    user_balance = utils.get_user_info(u.user_id, u.deep_link)
    u.update_info(user_balance)

    recive_command(update, context)


def recive_command(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.message.text.replace('/', '') 
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)

    prev_msg_id = utils.send_message(
        prev_state=prev_state,
        next_state=next_state,
        context=context,
        user_id=user_id,
        prev_message_id=prev_message_id
    )
    User.set_message_id(user_id, prev_msg_id)
    utils.send_logs_message(
        msg_text=msg_text, 
        user_keywords=next_state['user_keywords'], 
        markup=prev_state.get("markup", [])
    )


def recive_message(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.message.text

    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)

    prev_msg_id = utils.send_message(
        prev_state=prev_state,
        next_state=next_state,
        context=context,
        user_id=user_id,
        prev_message_id=prev_message_id
    )
    User.set_message_id(user_id, prev_msg_id)
    utils.send_logs_message(
        msg_text=msg_text, 
        user_keywords=next_state['user_keywords'], 
        markup=prev_state.get("markup", [])
    )


def recive_calback(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.callback_query.data

    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)

    prev_msg_id = utils.send_message(
        prev_state=prev_state,
        next_state=next_state,
        context=context,
        user_id=user_id,
        prev_message_id=prev_message_id
    )
    User.set_message_id(user_id, prev_msg_id)
    utils.send_logs_message(
        msg_text=msg_text, 
        user_keywords=next_state['user_keywords'], 
        markup=prev_state.get("markup", [])
    )


def receive_poll_answer(update: Update, context) -> None:
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]

    context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])
    
    Poll.update_poll(answered_poll["poll_id"], answer=answer)

    
    user_id = answered_poll['chat_id']
    msg_text = answer.lower().replace(' ', '')

    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)

    prev_msg_id = utils.send_message(
        prev_state=prev_state,
        next_state=next_state,
        context=context,
        user_id=user_id,
        prev_message_id=prev_message_id
    )
    User.set_message_id(user_id, prev_msg_id)
    utils.send_logs_message(
        msg_text=msg_text, 
        user_keywords=next_state['user_keywords'], 
        markup=prev_state.get("markup", [])
    )


def forward_from_support(update: Update, context: CallbackContext) -> None:
    replay_msg = update.message.reply_to_message
    text = replay_msg.text

    regex = "\(\d+\)"
    match = re.findall(regex, text)
    chat_id = int(re.sub('\(|\)', '', match[0]))

    context.bot.send_message(
        chat_id=int(chat_id),
        text=f'Ответ от Павла:\n\n{update.message.text}',
        parse_mode=ParseMode.HTML,
    )
    update.effective_chat.send_message(
        text='Cообщение отправлено',
    )



def forward_to_support(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.message.text.lower()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)

    prev_msg_id = utils.send_message(
        prev_state=prev_state,
        next_state=next_state,
        context=context,
        user_id=user_id,
        prev_message_id=prev_message_id
    )
    User.set_message_id(user_id, prev_msg_id)
    utils.send_logs_message(
        msg_text=msg_text, 
        user_keywords=next_state['user_keywords'], 
        markup=prev_state.get("markup", [])
    )

