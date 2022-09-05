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
from operator import itemgetter
from string import Template
from optparse import OptionParser
from pathlib import Path
from statistics import mean, median


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(
    filename="analyzer.log",
    filemode="w",
    format="[%(asctime)s] %(levelname).1s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def float_cut(obj):
    return f"{obj:.{3}f}"


def options_parse():
    parser = OptionParser()
    parser.add_option(
        "--config",
        "-c",
        dest="log_dir",
        help="Укажите путь к файлу с config. По умолчанию config:"
        '{"REPORT_SIZE": 1000,'
        '"REPORT_DIR": "./reports",'
        '"LOG_DIR": "./log"}',
    )
    (options, args) = parser.parse_args()
    logger.info("Старт скрипта")
    try:
        config = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}
        if options.log_dir:
            logger.info(f"Передан путь к файлу config:{options.log_dir}")
            file = open(options.log_dir, "r")
            conf = file.read()
            parse_config = ast.literal_eval(conf)
            if parse_config.values() != config.values():
                for i in parse_config:
                    config[i] = parse_config[i]
            logger.info("Файл config успешно прочитан")
            return config
        else:
            logger.info("Config по умолчнию")
            return config
    except PermissionError:
        logger.error("Не хватает прав доступа чтобы отрыть файл config")
        quit()
    except FileNotFoundError:
        logger.error("Файл не найден, неверный путь или имя файла config")
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()


def open_file(config):
    data = {}
    files = []
    directory = Path(config["LOG_DIR"])

    try:
        for i in directory.iterdir():
            patch_file = re.search(".*\.gz|.*\.txt", i.as_posix())
            if patch_file != None:
                print(patch_file.group(0))
                files.append(patch_file.group(0))
        print(files)
        for logs_file in files:
            data_name = re.search(r"\d\d\d\d\d\d\d\d", logs_file)
            data[logs_file] = data_name.group(0)
        file_data = sorted(data.items(), key=itemgetter(1), reverse=True)[0]
        path_file = file_data[0]
        data_file_raw = file_data[1]
        data_file = f"{data_file_raw[:4]}.{data_file_raw[4:6]}.{data_file_raw[6:]}"

        for reports in Path(config["REPORT_DIR"]).glob("report-*.html"):
            data_report = re.search(r"\d\d\d\d.\d\d.\d\d", reports.as_posix())
            if data_report.group(0) == data_file:
                logger.error("Отчёт на сегодня уже готов! Скрипт завершён")
                quit(0)
        return path_file, data_file

    except FileNotFoundError:
        logger.error("Файл логов не найден")
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        print(data)
        quit()


def parser(path, config):
    result, urls = [], []
    all_requests, all_times = 0, 0
    count = {}
    try:
        if path[-2:] == "gz":
            with gzip.open(path, "rt") as data_log:
                logs = data_log.read()
                count_str = logs.count("\n")
        elif path[-3:] == "txt":
            with open(path, "rt") as data_log:
                logs = data_log.read()
                count_str = logs.count("\n")
        if logs == "":
            logger.info("Файл логов пустой")
            quit()
        logger.info(f"Файл {path} упешно открыт и прочитан")
    except UnicodeEncodeError:
        logger.error("Ошибка кодировки файла логов")
        quit()
    except EOFError:
        logger.error("Неожиданный конец файла логов")
        quit()
    except PermissionError:
        logger.error("Не хватает прав доступа чтобы отрыть файл логов")
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()
    try:
        first_parse = re.findall(r"(GET /\S*|POST /\S*)+ +.+ +(\d\.\d{3})", logs)
        for i in first_parse:
            parse = re.sub(r"GET |POST ", "", i[0])
            urls.append(parse)
            count.setdefault(parse, [])
            count[parse].append(float(i[1]))
            all_requests += 1
            all_times += float(i[1])
        logger.info("Логи распаршены")
        if all_requests != count_str:
            err_count = 100 - (all_requests / count_str) * 100
            logger.error(
                f"Не удалось распарсить {float_cut(err_count)}% логов, проверьте синтаксис"
            )
            if err_count > 50:
                logger.error(
                    "Не удалось рапарсить более 50% логов, проверьте синтаксис. Работа завершена"
                )
                quit()
    except StopIteration:
        logger.error(
            "В файле логов изменён синтаксис, не найдены $request или $request_time"
        )
        quit()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()

    try:
        sorted_count = dict(
            sorted(count.items(), key=lambda x: len(x[1]), reverse=True)
        )
        for i in itertools.islice(sorted_count, 0, int(config["REPORT_SIZE"]) - 1):
            urls_count = len(count[i])
            sum_time = (urls_count / all_requests) * 100
            result.append(
                {
                    "url": i,
                    "count": urls_count,
                    "count_perc": float_cut(sum_time),
                    "time_sum": float_cut(sum(count[i])),
                    "time_perc": float_cut((sum_time / all_times) * 100),
                    "time_avg": float_cut(mean(count[i])),
                    "time_max": float_cut(max(count[i])),
                    "time_med": float_cut(median(count[i])),
                }
            )
        logger.info("Данные из лог файла преобразованны в json")
        return result
    except StopIteration:
        logger.error(
            "Ошибка итерации, возможно REPORT_SIZE больше чем количество запросов"
        )
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()


def write_report(result, data_file, config):
    try:
        with open("report.html", "r") as template_report:
            report = template_report.read()
            template = Template(report)
            a = template.safe_substitute(table_json=result)
            logger.info("Открыт шаблон отчёта, данные json переданы")
    except FileNotFoundError:
        logger.error("Не найден файл шаблона report.html")
        print("Не найден файл шаблона report.html")
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()
    try:
        with open(f'{config["REPORT_DIR"]}/report-{data_file}.html', "w") as report_out:
            report_out.write(a)
            logger.info("Отчёт сохранён")
    except FileExistsError:
        logger.error("Ошибка создания файла отчёта")
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()


if __name__ == "__main__":
    try:
        config = options_parse()
        path, data_file = open_file(config)
        result = parser(path, config)
        write_report(result, data_file, config)
    except KeyboardInterrupt:
        logger.error("Операция прервана пользователем")
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()
