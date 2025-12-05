import io
import unittest
from unittest.mock import patch, Mock
from requests.exceptions import RequestException
from my_logging import get_currencies, logger


class TestGetCurrencies(unittest.TestCase):
    """Тесты бизнес-логики: проверка корректности возврата и всех требуемых исключений"""

    @patch("my_logging.requests.get")
    def test_returns_correct_data(self, mock_get):
        """Успешный сценарий: API возвращает корректные курсы → функция возвращает словарь"""
        mock_get.return_value.json.return_value = {
            "Valute": {"USD": {"Value": 80.0}}
        }
        result = get_currencies(["USD"])
        self.assertEqual(result, {"USD": 80.0})

    @patch("my_logging.requests.get")
    def test_missing_currency_raises_key_error(self, mock_get):
        """Запрос валюты, отсутствующей в ответе API → KeyError"""
        mock_get.return_value.json.return_value = {"Valute": {}}
        with self.assertRaises(KeyError):
            get_currencies(["XYZ"])

    @patch("my_logging.requests.get")
    def test_no_valute_key_raises_key_error(self, mock_get):
        """Ответ API не содержит ключ 'Valute' → KeyError"""
        mock_get.return_value.json.return_value = {"Date": "2025-01-01"}
        with self.assertRaises(KeyError):
            get_currencies(["USD"])

    @patch("my_logging.requests.get")
    def test_invalid_json_raises_value_error(self, mock_get):
        """API возвращает некорректный JSON → ValueError"""
        mock_get.return_value.json.side_effect = ValueError()
        with self.assertRaises(ValueError):
            get_currencies(["USD"])

    @patch("my_logging.requests.get")
    def test_non_numeric_rate_raises_type_error(self, mock_get):
        """Курс валюты не является числом (например, строка) → TypeError"""
        mock_get.return_value.json.return_value = {
            "Valute": {"USD": {"Value": "abc"}}
        }
        with self.assertRaises(TypeError):
            get_currencies(["USD"])

    @patch("my_logging.requests.get")
    def test_network_error_raises_connection_error(self, mock_get):
        """Сетевая ошибка → ConnectionError"""
        mock_get.side_effect = RequestException()
        with self.assertRaises(ConnectionError):
            get_currencies(["USD"])


class TestLoggerDecorator(unittest.TestCase):
    """Тесты декоратора logger: проверка логирования при успехе и ошибке"""

    def test_logs_success_in_stringio(self):
        """При успешном вызове функции в StringIO записываются INFO-сообщения о входе и результате"""
        stream = io.StringIO()
        @logger(handle=stream)
        def f(x): return x
        f(42)
        log = stream.getvalue()
        self.assertIn("Calling f", log)
        self.assertIn("returned 42", log)

    def test_logs_error_and_re_raises(self):
        """При исключении в StringIO записывается ERROR, а исключение пробрасывается дальше"""
        stream = io.StringIO()
        @logger(handle=stream)
        def bad(): raise ValueError("test")
        with self.assertRaises(ValueError):
            bad()
        log = stream.getvalue()
        self.assertIn("ERROR", log)
        self.assertIn("ValueError", log)


class TestStreamWriteExample(unittest.TestCase):
    """Проверяет, что ошибка подключения корректно логируется и исключение пробрасывается"""

    def setUp(self):
        self.stream = io.StringIO()
        @logger(handle=self.stream)
        def call_api():
            return get_currencies(["USD"])
        self.func = call_api

    @patch("my_logging.requests.get")
    def test_logs_connection_error(self, mock_get):
        """Имитация сетевой ошибки → проверка записи ERROR и проброса ConnectionError"""
        mock_get.side_effect = RequestException()
        with self.assertRaises(ConnectionError):
            self.func()
        log = self.stream.getvalue()
        self.assertIn("ERROR", log)
        self.assertIn("ConnectionError", log)


if __name__ == "__main__":
    unittest.main()