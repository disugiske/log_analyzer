## Log Analyzer

Скрипт для парсинга и аналитики логов nginx и загрузки их в отчёт.

### Обычный запуск: 
```python
python log_analyzer.py --config config.txt
```

где config.txt - файл с нужным пользователю конфигом

### Запуск тестов: 
```python
python -m unittest tests/test.py
```
В результате выдаёт отчет в HTML со статистикой по запросам

Тесты добавлены GitHub Actions, запускаются автоматически при push
