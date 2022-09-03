#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import logging
import ast
import gzip
import itertools
import re
import sys
from string import Template
from optparse import OptionParser
from pathlib import Path, PurePath
from statistics import mean, median

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(filename='analyzer.log',
                    filemode='w',
                    format='[%(asctime)s] %(levelname).1s %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def float_cut(obj):
    return f"{obj:.{3}f}"


def options_parse():

    parser = OptionParser()
    parser.add_option('--config', '-c',
                      dest="log_dir",
                      help='Укажите путь к файлу с config. По умолчанию config:'
                           '{"REPORT_SIZE": 1000,'
                           '"REPORT_DIR": "./reports",'
                           '"LOG_DIR": "./log"}',
                      )
    (options, args) = parser.parse_args()
    if options.log_dir:
        logger.info(f'Передан путь к файлу config:{options.log_dir}')
        try:
            file = open(options.log_dir, "r")
            conf = file.read()
            config = ast.literal_eval(conf)
            logger.info('Файл config успешно прочитан')
            return config
        except PermissionError:
            logger.error('Не хватает прав доступа чтобы отрыть файл config')

            exit()
        except FileNotFoundError:
            logger.error('Файл не найден, неверный путь или имя файла config')

            exit()
        except Exception as e:
            logger.error(f'Ошибка: {e}')
            exit()


def parser(config):
    result, urls = [], []
    all_requests, all_times = 0, 0
    count = {}
    try:
        path = sorted(Path(config["LOG_DIR"]).glob('nginx-access-ui.log-*.gz'))
        path = (PurePath(path[0]))
        logger.info(f'Файл логов {path} найден')
    except FileNotFoundError:
        logger.error('Файл логов не найден')

        exit()
    except Exception as e:
        logger.error(f'Ошибка: {e}')

        exit()
    try:
        with gzip.open(path, 'rt') as data_log:
            logger.info('Открыт файл лог отчета')
            logs = data_log.read()
            count_str = logs.count('\n')
            logger.info(f'Файл {path} упешно открыт и прочитан')
    except UnicodeEncodeError:
        logger.error('Ошибка кодировки файла логов')

        exit()
    except EOFError:
        logger.error('Неожиданный конец файла логов')

        exit()
    except PermissionError:
        logger.error('Не хватает прав доступа чтобы отрыть файл логов')

        exit()
    except Exception as e:
        logger.error(f'Ошибка: {e}')

        exit()
    try:
        first_parse = re.findall(r"(GET /\S*|POST /\S*)+ +.+ +(\d\.\d{3})", logs)
        for i in first_parse:
            parse = re.sub(r"GET |POST ", "", i[0])
            urls.append(parse)
            count.setdefault(parse, [])
            count[parse].append(float(i[1]))
            all_requests += 1
            all_times += float(i[1])
        logger.info('Логи распаршены')
        if all_requests != count_str:
            err_count = 100-(all_requests/count_str)*100
            logger.error(f'Не удалось распарсить {float_cut(err_count)}% логов, проверьте синтаксис')
            if err_count > 50:
                logger.error('Не удалось рапарсить более 50% логов, проверьте синтаксис. Работа завершена')
                exit()
    except StopIteration:
        logger.error('В файле логов изменён синтаксис, не найдены $request или $request_time')

        exit()
    except Exception as e:
        logger.error(f'Ошибка: {e}')

        exit()
    sorted_count = dict(sorted(count.items(), key=lambda x: len(x[1]), reverse=True))
    try:
        for i in itertools.islice(sorted_count, 0, int(config["REPORT_SIZE"]) - 1):
            urls_count = len(count[i])
            sum_time = ((urls_count / all_requests) * 100)
            result.append({
                "url": i,
                "count": urls_count,
                "count_perc": float_cut(sum_time),
                "time_sum": float_cut(sum(count[i])),
                "time_perc": float_cut((sum_time / all_times) * 100),
                "time_avg": float_cut(mean(count[i])),
                "time_max": float_cut(max(count[i])),
                "time_med": float_cut(median(count[i]))
            })
        logger.info('Данные из лог файла преобразованны в json')
    except StopIteration:
        logger.error('Ошибка итерации, возможно REPORT_SIZE больше чем количество запросов')

        exit()
    except Exception as e:
        logger.error(f'Ошибка: {e}')

        exit()
    return result


def write_report(result):
    try:
        with open('report.html', 'r') as template_report:
            report = template_report.read()
            template = Template(report)
            a = template.safe_substitute(table_json=result)
            logger.info('Открыт шаблон отчёта, данные json переданы')
    except FileNotFoundError:
        logger.error('Не найден файл шаблона report.html')
        print('Не найден файл шаблона report.html')
        exit()
    except Exception as e:
        logger.error(f'Ошибка: {e}')
        print(f'Ошибка: {e}')
        exit()
    try:
        with open('report2.html', 'w') as report_out:
            report_out.write(a)
            logger.info('Отчёт сохранён')
    except FileExistsError:
        logger.error('Ошибка создания файла отчёта')
        print('Ошибка создания файла отчёта')
        exit()
    except Exception as e:
        logger.error(f'Ошибка: {e}')
        print(f'Ошибка: {e}')
        exit()

if __name__ == "__main__":
    try:
        a = parser(options_parse())
        write_report(a)
    except KeyboardInterrupt:
        logger.error('Операция прервана пользователем')
        print('Операция прервана пользователем')
        exit()
    except Exception as e:
        logger.error(f'Ошибка: {e}')
        print(f'Ошибка: {e}')
        exit()
