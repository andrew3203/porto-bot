from typing import Union, Optional, Dict, List

import telegram
from telegram import MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup

from portobello.settings import TELEGRAM_TOKEN
from bot.models import User


def _from_celery_markup_to_markup(celery_markup: Optional[List[List[Dict]]]) -> Optional[InlineKeyboardMarkup]:
    markup = None
    if celery_markup:
        markup = []
        for row_of_buttons in celery_markup:
            row = []
            for button in row_of_buttons:
                row.append(
                    InlineKeyboardButton(
                        text=button['text'],
                        callback_data=button.get('callback_data'),
                        url=button.get('url'),
                    )
                )
            markup.append(row)
        markup = InlineKeyboardMarkup(markup)
    return markup


def _from_celery_entities_to_entities(celery_entities: Optional[List[Dict]] = None) -> Optional[List[MessageEntity]]:
    entities = None
    if celery_entities:
        entities = [
            MessageEntity(
                type=entity['type'],
                offset=entity['offset'],
                length=entity['length'],
                url=entity.get('url'),
                language=entity.get('language'),
            )
            for entity in celery_entities
        ]
    return entities


def _send_message(
    user_id: Union[str, int],
    text: str,
    photo: str = None,
    parse_mode: Optional[str] = telegram.ParseMode.HTML,
    reply_markup: Optional[List[List[Dict]]] = None,
    reply_to_message_id: Optional[int] = None,
    disable_web_page_preview: Optional[bool] = None,
    entities: Optional[List[MessageEntity]] = None,
    tg_token: str = TELEGRAM_TOKEN,
) -> bool:
    bot = telegram.Bot(tg_token)
    try:
        if photo:
            m = bot.send_photo(
                chat_id=user_id,
                caption=text,
                photo=open(photo, 'rb'),
                parse_mode=parse_mode, 
                reply_markup=reply_markup,
            )
        else:
            m = bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=parse_mode, 
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
                disable_web_page_preview=disable_web_page_preview,
                entities=entities,
            )
        
    except telegram.error.Unauthorized:
        print(f"Can't send message to {user_id}. Reason: Bot was stopped.")
        User.objects.filter(user_id=user_id).update(is_blocked_bot=True)
        return None
    except Exception as e:
        print(e)
        User.objects.filter(user_id=user_id).update(is_blocked_bot=True)
        return None

    else:
        User.objects.filter(user_id=user_id).update(is_blocked_bot=False)
        return m.message_id
   

def _send_media_group(
    photos: list,
    user_id: Union[str, int],
    tg_token: str = TELEGRAM_TOKEN
) -> bool:
    bot = telegram.Bot(tg_token)
    media = [telegram.InputMediaPhoto(open(photo, 'rb'))  for photo in photos]
    bot.send_media_group(user_id, media=media)



def _revoke_message(
    message_id: str,
    user_id: Union[str, int],
    tg_token: str = TELEGRAM_TOKEN
) -> bool:
    bot = telegram.Bot(tg_token)
    try:
        bot.delete_message(
            chat_id=user_id,
            message_id=message_id
        )
    except Exception as e:
        print(e)



    
