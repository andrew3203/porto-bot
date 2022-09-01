broadcast_command = '/broadcast'
support_command  = '/support'
broadcast_no_access = "К сожалению, у вас нет доступа к этой функции."
broadcast_wrong_format = f'Чтобы отправить сообщение всем вашим пользователям,' \
                         f' нажмите {broadcast_command} команда с текстом, разделенным пробелом.\n' \
                         f'Пример:\n' \
                         f'{broadcast_command} Привет, пользователи! Этот <b>выделенный жирным шрифтом</b> текст для вас,' \
                         f'а также этот <i>курсивный текст</i>.\n\n' \
                         f'Примеры использования стиля <code>HTML</code> вы можете найти <a href="https://core.telegram.org/bots/api#html-style">здесь</a>.'
confirm_broadcast = "Подтвердить ✅"
decline_broadcast = "Отмена ❌"
message_is_sent = "Сообщение отправлено ✅"
declined_message_broadcasting = "Рассылка сообщения отменена ❌"
error_with_html = "Не удается проанализировать ваш текст в стиле <code>HTML</code>. Причина: \n{reason}"
