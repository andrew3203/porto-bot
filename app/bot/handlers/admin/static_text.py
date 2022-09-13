command_start = '/stats'
broadcast_command = '/broadcast'
only_for_admins = 'К сожалению, эта функция доступна только для администраторов. Установить флаг «админ» в админ панели'
broadcast_wrong_format = f'Чтобы отправить сообщение всем вашим пользователям,' \
                         f' нажмите \n{broadcast_command} команда с текстом, разделенным пробелом.\n' \
                         f'Пример:\n' \
                         f'{broadcast_command} Привет, пользователи! Этот <b>выделенный жирным шрифтом</b> текст для вас,' \
                         f'а также этот <i>курсивный текст</i>.\n\n' \
                         f'Примеры использования стиля <code>HTML</code> вы можете найти <a href="https://core.telegram.org/bots/api#html-style">здесь</a>.'

secret_admin_commands = f"⚠️ Команды администратора\n" \
                        f"{command_start} - статистика\n" \
                        "/export_users - экспорт пользователей\n" \
                        f"/{broadcast_command} текст рассылки - запустить рассылку для всех пользователей\n" \

users_amount_stat = "<b>Пользователи</b>: {user_count}\n" \
                    "<b>активных за последние 24 часа</b>: {active_24}"
