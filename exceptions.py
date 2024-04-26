class TokenNotFound(Exception):
    """Исключение возникает, если не найдены токены в виртуальном окружении"""
    pass


class APIError(Exception):
    """Исключение возникает, если есть ошибка API"""
    pass
