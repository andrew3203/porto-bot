"""
    Celery tasks. Some of them will be launched periodically from admin panel via django-celery-beat
"""
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from portobello.settings import REDIS_URL, SOCHI_TURNOVER_LINK
import requests
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
    logger.info(f"Going to send message to {len(user_ids)} users")

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
    broadcast_id: str,
    sleep_between: float = 0.4,
) -> None:
    """ It's used to broadcast message to big amount of users """
    logger.info(f"Going to send message to {len(users)} users")

    broad_info = []
    for user_id, persone_code  in users:
        next_state, prev_message_id = models.User.get_broadcast_next_states(user_id, message_id, persone_code)
        prev_msg_id = utils.send_broadcast_message(
            next_state=next_state,
            user_id=user_id,
            prev_message_id=prev_message_id
        )
        broad_info.append(
            (user_id, prev_msg_id, next_state)
        )
        User.set_message_id(user_id, prev_msg_id)
        logger.info(f"Sent message ({prev_msg_id}) to {user_id}!")
        time.sleep(max(sleep_between, 0.1))

    models.Broadcast.save_data(broadcast_id, broad_info)
    logger.info("Broadcast finished!")

@app.task(ignore_result=True)
def revoke_prev_message(users: List[Union[str, int]], sleep_between: float = 0.4) -> None:
     logger.info(f"Going to send del {len(users)} messages")
     for user_id in users:
        message_id = User.unset_prew_message_id(user_id)
        if message_id and message_id != '':
            utils._revoke_message(user_id=user_id, message_id=message_id)
        logger.info(f"Message deleted for {user_id} {message_id}!")
        time.sleep(max(sleep_between, 0.1))

     logger.info("Deleting finished!")

@app.task(ignore_result=True)
def update_photo(queue):
    r = redis.from_url(REDIS_URL)
    cash = models.Message.make_cashes()
    r.mset(cash)


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


@app.task(ignore_result=True)
def sochi_turnover_update(): 
    logger.info(f" - - - START updating Sochi Turnover - - - ")
    resp = requests.get(SOCHI_TURNOVER_LINK)
    data = resp.json()
    persons = data['winners'] + data['other']
    logger.info(f'{len(persons)} - - - - - - - - - - - - ')
    for person in persons:
        usr = User.objects.filter(deep_link=person['code_person'] ).first()
        if usr:
            usr.turnover = person['sum']
            usr.save()
    logger.info(f" - - - FINISH updating Sochi Turnover - - - ")
    


@app.task(ignore_result=True)
def sochi_turnover_send():
    sochi_turnover_update()
    logger.info(f" - - - START sending Sochi Turnover - - - ")
    user_list = User.objects.filter(turnover__lte=3000000, is_blocked_bot=False)
    user_ids = list(user_list.values_list('user_id', flat=True))
    deep_links = list(user_list.values_list('deep_link', flat=True))
    users = list(zip(user_ids, deep_links))
    msg = models.Message.objects.get(name='sochi_turnover_send')
    broadcast_message2.delay(users=users, message_id=msg.pk, text=None)
    logger.info(f" - - - FINISH sending Sochi Turnover - - - ")


@app.task(ignore_result=True)
def edit_broadcast_task(broadcast_data):
    logger.info(f" - - - START editing broadcast - - - ")
    utils.edit_broadcast(broadcast_data)
    logger.info(f" - - - FINISH editing broadcast - - - ")



every_7_days, _ = IntervalSchedule.objects.get_or_create(
    every=7, period=IntervalSchedule.DAYS,
)

PeriodicTask.objects.update_or_create(
    task="bot.tasks.sochi_turnover_send",
    name="sochi_turnover_send",
    defaults=dict(
        interval=every_7_days,
        expire_seconds=100, 
    ),
)

PeriodicTask.objects.update_or_create(
    task="bot.tasks.sochi_turnover_update",
    name="sochi_turnover_update",
    defaults=dict(
        interval=every_7_days,
        expire_seconds=100, 
    ),
)
