"""
    Celery tasks. Some of them will be launched periodically from admin panel via django-celery-beat
"""
from portobello.settings import REDIS_URL
import redis
import time
from typing import Union, List, Optional, Dict

import telegram
from bot.handlers.utils import utils
from bot import models
from portobello.celery import app
from celery.utils.log import get_task_logger
from bot.handlers.broadcast_message.utils import _send_message, _from_celery_entities_to_entities, \
    _from_celery_markup_to_markup
from bot.models import User

logger = get_task_logger(__name__)


@app.task(ignore_result=True)
def broadcast_message(
    user_ids: List[Union[str, int]],
    text: str,
    entities: Optional[List[Dict]] = None,
    reply_markup: Optional[List[List[Dict]]] = None,
    sleep_between: float = 0.4,
    parse_mode=telegram.ParseMode.HTML,
) -> None:
    """ It's used to broadcast message to big amount of users """
    logger.info(f"Going to send message: '{text}' to {len(user_ids)} users")

    entities_ = _from_celery_entities_to_entities(entities)
    reply_markup_ = _from_celery_markup_to_markup(reply_markup)
    for user_id in user_ids:
        try:
            _send_message(
                user_id=user_id,
                text=text,
                entities=entities_,
                reply_markup=reply_markup_,
            )
            logger.info(f"Broadcast message was sent to {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}, reason: {e}")
        time.sleep(max(sleep_between, 0.1))

    logger.info("Broadcast finished!")

@app.task(ignore_result=True)
def broadcast_message2(
    users: List[Union[str, int]],
    text: str,
    message_id: str,
    sleep_between: float = 0.4,
) -> None:
    """ It's used to broadcast message to big amount of users """
    logger.info(f"Going to send message: '{text}' to {len(users)} users")

    for user_id, persone_code  in users:
        next_state, prev_message_id = models.User.get_broadcast_next_states(user_id, message_id, persone_code)
        prev_msg_id = utils.send_broadcast_message(
            new_state=next_state,
            user_id=user_id,
            prev_message_id=prev_message_id
        )
        User.set_message_id(user_id, prev_msg_id)
        time.sleep(max(sleep_between, 0.1))

    logger.info("Broadcast finished!")

@app.task(ignore_result=True)
def update_photo(queue):
    r = redis.from_url(REDIS_URL)
    #for file_id, path in queue:
        #pass
        #File.objects.filter(file__path=path).update(tg_id=file_id)
    cash = models.Message.make_cashes()
    r.mset(cash)
    print('set_messages_states')


@app.task(ignore_result=True)
def send_delay_message(user_id, msg_name):
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_name)

    prev_msg_id = utils.send_message(
        prev_state=prev_state,
        next_state=next_state,
        user_id=user_id,
        context=None,
        prev_message_id=prev_message_id
    )
    User.set_message_id(user_id, prev_msg_id)


