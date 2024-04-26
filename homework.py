import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import APIError, TokenNotFound

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    logging.info('Начало проверки токенов')
    all_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(all_tokens):
        logging.critical('Токен не найден в переменных окружения')
        raise TokenNotFound('Токен не найден в переменных окружения')
    logging.info('Токены проверены')
    return True


def send_message(bot, message):
    """Отправка сообщения в чат."""
    logging.info('Начало отправки сообщения в чат')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение отправлено')
    except Exception as error:
        raise Exception(f'Ошибка отправки сообщения: {error}')
    else:
        logging.info('Сообщение отправлено')


def get_api_answer(timestamp):
    """Проверка запроса к API."""
    logging.info('Получение ответа от API')
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise APIError('Запрос к API некорректный')
    if response.status_code != HTTPStatus.OK:
        raise APIError('Запрос к API некорректный')
    logging.info('Запрос к API корректный!')
    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    logging.info('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является "dict"')
    if 'homeworks' not in response:
        raise TypeError('Ответ API не содержит список проектов')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Список проектов не является "list"')
    for index in range(len(response.get('homeworks'))):
        if 'homework_name' not in response['homeworks'][index]:
            raise TypeError('Ответ API не содержит ключ "homework_name"!')
        if 'status' not in response.get('homeworks')[index]:
            raise TypeError('Ответ API не содержит ключ "status"!')
    logging.info('Проверка ответа API прошла успешно!')
    return response


def parse_status(homework):
    """Проверяется статус домашней работы."""
    logging.info('Начало проверки статуса проекта')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework_status or not homework_name:
        raise KeyError('Не найдено имя или статус проекта в ответе API')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Не найден статус последнего проекта')
    verdict = HOMEWORK_VERDICTS[homework_status]
    logging.info('Проверка статуса проекта успешна!')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info('Бот запущен.')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    if not check_tokens():
        err_msg = 'Отсутствуют обязательныя переменные окружения!'
        logging.critical(err_msg)
        raise SystemExit(err_msg)

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)['homeworks']
            last_work = homeworks[0]
            message = parse_status(last_work)
            try:
                send_message(bot, message)
            except Exception as error:
                logging.error(f'Ошибка отправки сообщения{error}')
        except IndexError:
            message = 'Статус не поменялся'
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            raise Exception(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    main()
