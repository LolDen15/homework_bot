class TokenNotFound(Exception):
    """Исключение возникает, если не найдены токены в виртуальном окружении"""


class APIError(Exception):
    """Исключение возникает, если есть ошибка API"""
