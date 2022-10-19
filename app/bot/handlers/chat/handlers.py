import datetime
import re
from django.utils import timezone
import telegram
from django.utils import timezone
from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from bot.models import User, Poll
from bot.handlers.utils import utils
from bot.handlers.utils.info import extract_user_data_from_update
from bot.tasks import send_delay_message
from portobello.settings import TELEGRAM_SUPPORT_CHAT



def command_start(update: Update, context: CallbackContext) -> None:
    u, created = User.get_user_and_created(update, context)

    if u.deep_link:
        user_balance = utils.get_user_info(u.user_id, u.deep_link)
        u.update_info(user_balance)

    if created and u.deep_link:
            utils.send_registration(user_code=u.deep_link, user_id=u.user_id)
            update.message.reply_text(f'{u.first_name}, Вы успешно зарегистрированы в программе лояльности!')
            update.message.reply_photo(
                caption="👋 Привет! Давайте знакомиться!\n\n" \
                "Меня зовут Павел, и я отвечаю за нашу программу лояльности.\n" \
                "Сейчас вы находитесь в моем телеграм-боте, через который мы с вами можем общаться напрямую! " \
                "Мой бот будет присылать вам всю необходимую информацию в рамках программы, а иногда я лично " \
                "буду писать вам и рассказывать о наших новых возможностях, акциях и эксклюзивных предложениях! 😎\n\n" \
                "Если у вас возникнут вопросы по программе, пишите боту. Он передаст мне всю информацию, " \
                "и в ближайшее время я с вами свяжусь!",
                photo='https://bot.portobello.ru/media/messages/start__ues.png'
            )
            now = timezone.now()
            send_delay_message.apply_async(
                kwargs={'user_id': u.user_id, 'msg_name': 'start'}, 
                eta=now+datetime.timedelta(seconds=10)
            )
            utils.send_logs_message(
                msg_text='Новый пользователь!!', 
                user_keywords=u.get_keywords(), 
                prev_state=None
            )
            task1 = send_delay_message.apply_async(
                kwargs={'user_id': u.user_id, 'msg_name': 'Клуб лидеров'}, 
                eta=now+datetime.timedelta(days=1)
            )
            task2 = send_delay_message.apply_async(
                kwargs={'user_id': u.user_id, 'msg_name': 'Колесо Фортуны'},
                eta=now+datetime.timedelta(days=2)
            )
            
    else:
        recive_command(update, context)


def command_balance(update: Update, context: CallbackContext) -> None:
    u, _ = User.get_user_and_created(update, context)
    user_balance = utils.get_user_info(u.user_id, u.deep_link)
    u.update_info(user_balance)

    recive_command(update, context)

def command_support(update: Update, context: CallbackContext) -> None:
    context.user_data['ask_support'] = True
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
        prev_state=prev_state
    )


def _forward_to_support(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    li = f'<a href="http://bot.portobello.ru/admin/bot/user/{u.user_id}/change/">' \
        f'{u.first_name} {u.last_name} ({u.user_id})</a>\n' \
        f'{u.company}\n{u.phone}\n{u.owner}'

    text = f"{update.message.text}\n\n{li}"
    context.bot.send_message(
        chat_id=int(TELEGRAM_SUPPORT_CHAT),
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


def recive_message(update: Update, context: CallbackContext) -> None:

    if context.user_data.pop('ask_support', False):
        _forward_to_support(update, context)
        msg_text = 'Отправил вопрос в поддержку'
    else:
        msg_text = update.message.text


    user_id = extract_user_data_from_update(update)["user_id"]
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
        prev_state=prev_state
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
        prev_state=prev_state
    )


def receive_poll_answer(update: Update, context) -> None:
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]
    if len(answer.option_ids) > 0:
        answer_text = answered_poll['questions'][answer.option_ids[0]]
   
        context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])
        
        Poll.update_poll(answered_poll["poll_id"], answer=answer_text)

        
        user_id = answered_poll['chat_id']
        msg_text = answer_text.lower().replace(' ', '')

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
            prev_state=prev_state
        )


def forward_from_support(update: Update, context: CallbackContext) -> None:
    replay_msg = update.message.reply_to_message
    if replay_msg:
        text = replay_msg.text
        match = re.findall("\(\d{6,}\)", text)
    else:
        text = update.message.text
        match = re.findall("\d{6,}", text)
    
    try:
        chat_id = int(re.sub('\(|\)', '', match[0]))
        context.bot.send_message(
            chat_id=chat_id,
            text=f'<b>Сообщение от Павла:</b>\n\n{update.message.text}',
            parse_mode=ParseMode.HTML,
        )
        update.effective_chat.send_message(
            text=f'Сообщение для {chat_id} отправлено!'
        )
    except telegram.error.Unauthorized:
        update.effective_chat.send_message(
            text='ОШИБКА: Пользователь заблокировал бота.\nСообщение не отправлено!'
        )
    except Exception as e:
        update.effective_chat.send_message(
            text='ОШИБКА: Пользователь не найден.\nСообщение не отправлено!'
        )


