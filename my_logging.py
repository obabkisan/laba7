import sys
import functools
import io
import logging
import requests
from typing import Any, Callable, Optional, Union, List

# тип для аргумента handle: либо Logger, либо объект с write()
LoggerOrStream = Union[logging.Logger, io.TextIOBase]


def logger(func: Optional[Callable] = None, *, handle: LoggerOrStream = sys.stdout):
    """Параметризуемый декоратор для логирования вызовов функций

    Поддерживает три режима логирования в зависимости от типа `handle`:
        - Если `handle` — экземпляр `logging.Logger`, используются методы
          `info()` и `error()`
        - Иначе предполагается, что `handle` имеет метод `write()` (например,
          `sys.stdout` или `io.StringIO`)

    Логирует:
        - INFO: старт вызова с аргументами
        - INFO: успешное завершение с возвращаемым значением
        - ERROR: исключение (тип и сообщение), после чего исключение
          пробрасывается дальше

    Args:
        func: Декорируемая функция (может быть None при использовании с аргументами)
        handle: Объект для записи логов (по умолчанию — sys.stdout)

    Returns:
        Декорированную функцию с добавленным логированием
    """

    def _decorate(fn: Callable) -> Callable:
        # определяем, как именно писать логи
        if isinstance(handle, logging.Logger):
            info = handle.info
            error = handle.error
        else:
            def info(msg: str):
                handle.write(f"INFO: {msg}\n")

            def error(msg: str):
                handle.write(f"ERROR: {msg}\n")

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # логируем вход
            info(f"Calling {fn.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = fn(*args, **kwargs)
                # логируем выход
                info(f"{fn.__name__} returned {result!r}")
                return result
            except Exception as e:
                # логируем ошибку
                error(f"Function {fn.__name__} raised {type(e).__name__}: {e}")
                raise  # Пробрасываем исключение без изменений

        return wrapper

    # поддержка синтаксиса @logger и @logger(handle=...)
    if func is None:
        return _decorate
    return _decorate(func)


def get_currencies(currency_codes: List[str],
                   url: str = "https://www.cbr-xml-daily.ru/daily_json.js") -> dict:
    """Получает курсы валют по кодам с API ЦБ РФ

    Эта функция содержит только бизнес-логику и не выполняет логирование

    Args:
        currency_codes: Список символьных кодов валют (например, ["USD", "EUR"])
        url: URL API для получения курсов (по умолчанию — JSON от ЦБ РФ)

    Returns:
        dict: Словарь вида {"USD": 93.25, "EUR": 101.7}

    Raises:
        ConnectionError: Если не удалось подключиться к API
        ValueError: Если ответ не является корректным JSON
        KeyError: Если отсутствует ключ "Valute" или запрашиваемая валюта
        TypeError: Если курс валюты не является числом
    """
    try:
        response = requests.get(url, timeout=5.0)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Ошибка при запросе к API: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise ValueError("Некорректный JSON в ответе API") from e

    if "Valute" not in data:
        raise KeyError('В ответе JSON отсутствует ключ "Valute"')

    valute = data["Valute"]
    result = {}

    for code in currency_codes:
        if code not in valute:
            raise KeyError(f"Валюта '{code}' отсутствует в данных API")

        value = valute[code].get("Value")
        if not isinstance(value, (int, float)):
            raise TypeError(f"Валюта '{code}' имеет нечисловой тип: {repr(value)}")

        result[code] = float(value)

    return result


# примеры использования

# логирование в stdout
@logger
def get_currencies_stdout(currency_codes: List[str]) -> dict:
    return get_currencies(currency_codes)


# логирование в StringIO
stream = io.StringIO()


@logger(handle=stream)
def get_currencies_stringio(currency_codes: List[str]) -> dict:
    return get_currencies(currency_codes)


# логирование через logging.Logger в файл
currency_file_logger = logging.getLogger("currency_file")
currency_file_logger.setLevel(logging.INFO)

# настройка файлового хендлера
if not currency_file_logger.handlers:
    file_handler = logging.FileHandler("currency.log", encoding="utf-8")
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    file_handler.setFormatter(formatter)
    currency_file_logger.addHandler(file_handler)


@logger(handle=currency_file_logger)
def get_currencies_file(currency_codes: List[str]) -> dict:
    return get_currencies(currency_codes)


# функция для демонстрации: квадратное уравнение
quadratic_logger = logging.getLogger("quadratic")
quadratic_logger.setLevel(logging.DEBUG)

if not quadratic_logger.handlers:
    quad_handler = logging.FileHandler("quadratic.log", encoding="utf-8")
    quad_formatter = logging.Formatter("%(levelname)s: %(message)s")
    quad_handler.setFormatter(quad_formatter)
    quadratic_logger.addHandler(quad_handler)


@logger(handle=quadratic_logger)
def solve_quadratic(a: float, b: float, c: float) -> Optional[tuple]:
    """Решает квадратное уравнение a*x^2 + b*x + c = 0.

    Логирование входа/выхода и ошибок выполняется декоратором.
    Дополнительные уровни (WARNING/CRITICAL) не используются, чтобы
    не нарушать принцип «декоратор — единственное место логирования».

    Args:
        a: Коэффициент при x^2.
        b: Коэффициент при x.
        c: Свободный член.

    Returns:
        tuple: Один или два корня, либо None, если корней нет.

    Raises:
        TypeError: Если любой из коэффициентов не является числом.
        ValueError: Если a == 0 (уравнение не квадратное).
    """
    for name, val in [("a", a), ("b", b), ("c", c)]:
        if not isinstance(val, (int, float)):
            raise TypeError(f"Параметр '{name}' должен быть числом")

    if a == 0:
        raise ValueError("Коэффициент 'a' не может быть нулем")

    d = b * b - 4 * a * c
    if d < 0:
        return None
    elif d == 0:
        return (-b / (2 * a),)
    else:
        sqrt_d = d ** 0.5
        return ((-b + sqrt_d) / (2 * a), (-b - sqrt_d) / (2 * a))


# демонстрация при запуске напрямую
if __name__ == "__main__":
    print("Демонстрация логирования в stdout")
    try:
        print(get_currencies_stdout(["USD", "EUR"]))
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\nДемонстрация логирования в StringIO")
    try:
        get_currencies_stringio(["USD"])
        print("Лог из StringIO:")
        print(stream.getvalue())
    except Exception as e:
        print(f"Ошибка: {e}")

    print("Демонстрация логирования в файл currency.log")
    try:
        get_currencies_file(["USD"])
        print("См. файл currency.log")
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\nДемонстрация solve_quadratic")
    try:
        print("solve_quadratic(1, -3, 2):", solve_quadratic(1, -3, 2))
        print("solve_quadratic(1, 0, 1):", solve_quadratic(1, 0, 1))
        print("solve_quadratic('a', 1, 2):", solve_quadratic("a", 1, 2))
    except Exception as e:
        print(f"Исключение: {e}")
    print("См. файл quadratic.log")
