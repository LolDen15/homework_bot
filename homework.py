import logging
import os
import sys
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
    all_tokens = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_tokens = [
        name for name in all_tokens if globals().get(name) in [None, '']
    ]
    if any(missing_tokens):
        logging.critical(f'Отсутсвует переменная окружения {missing_tokens}')
        raise TokenNotFound(
            f'Отсутсвует переменная окружения {missing_tokens}'
        )
    logging.info('Токены проверены')


def send_message(bot, message):
    """Отправка сообщения в чат."""
    logging.info('Начало отправки сообщения в чат')
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Проверка запроса к API."""
    logging.info('Получение ответа от API')
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise APIError('Не удалось выполнить запрос к API.')
    if response.status_code != HTTPStatus.OK:
        raise APIError(f'Статус запроса к API: {response.status_code}')
    logging.info('Запрос к API прошёл успешно!')

    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    logging.info('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API не является "dict".'
                        f'Ответ API является {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('Ответ API не содержит список проектов')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Список проектов не является "list"')
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
        raise ValueError('Не найден статус последнего проекта')
    verdict = HOMEWORK_VERDICTS[homework_status]
    logging.info('Проверка статуса проекта успешна!')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info('Бот запущен.')

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    status = '1qwe'

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = int(time.time())
            check_response(response)
            last_work = response['homeworks'][0]
            message = parse_status(last_work)
            send_message(bot, message)

        except IndexError:
            message = 'Статус не поменялся'
            if str(status) != str(message):
                send_message(bot, message)
            logging.info(message)
            status = message

        except telegram.error.TelegramError as error:
            message = f'Ошибка отправки сообщения: {error}'
            logging.error(message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if str(status) != str(message):
                send_message(bot, message)
            logging.error(message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    main()
