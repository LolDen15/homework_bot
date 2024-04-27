import logging
import os
import sys
import time
from contextlib import suppress
from http import HTTPStatus

import requests
import telebot
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
    all_tokens = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_tokens = [
        name for name in all_tokens if not globals().get(name)
    ]
    if missing_tokens:
        log_message = (
            f'Отсутствует переменная окружения{", ".join(missing_tokens)}'
        )
        logging.critical(log_message)
        raise TokenNotFound(log_message)
    logging.info('Токены проверены')


def send_message(bot, message):
    """Отправка сообщения в чат."""
    logging.info('Начало отправки сообщения в чат')
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Проверка запроса к API."""
    logging.debug('Получение ответа от API')
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        raise APIError(f'Ошибка: {error}')
    if response.status_code != HTTPStatus.OK:
        raise APIError(f'Статус запроса к API: {response.status_code}')
    logging.info('Запрос к API прошёл успешно!')

    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    logging.info('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является "dict". '
                        f'Ответ API является {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('Ответ API не содержит список проектов "homeworks"')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Список проектов не является "list". '
                        'Список проектов является '
                        f'{type(response.get("homeworks"))}')
    logging.info('Проверка ответа API прошла успешно!')


def parse_status(homework):
    """Проверяется статус домашней работы."""
    logging.info('Начало проверки статуса проекта')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework_status:
        raise KeyError('Не найден статус проекта в ответе API')
    if not homework_name:
        raise KeyError('Не найдено имя проекта в ответе API')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('Не найден статус последнего проекта:'
                         f' {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    logging.info('Проверка статуса проекта успешна!')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info('Бот запущен.')

    check_tokens()

    bot = telebot.TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            last_work = response['homeworks']
            if last_work:
                message = parse_status(last_work[0])
                if last_message != message:
                    send_message(bot, message)
                    last_message = message
            else:
                logging.info('Cтатус проекта не обновился')
            timestamp = int(response.get('current_date', time.time()))
        except telebot.apihelper.ApiTelegramException as error:
            logging.error(f'Ошибка отправки сообщения: {error}')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
            if last_message != message:
                with suppress(Exception):
                    send_message(bot, message)
                    last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        handlers=[logging.StreamHandler(sys.stdout)],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )
    main()
