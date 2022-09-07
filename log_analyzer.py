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
import os
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
    encoding="UTF-8",
    filemode="w",
    format="[%(asctime)s] %(levelname).1s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname).1s %(message)s"))
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
            with open(options.log_dir, "r") as file:
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


def find_path(config):
    data = {}
    files = []
    directory = Path(config["LOG_DIR"])

    try:
        for i in directory.iterdir():
            patch_file = re.search(r".*\.gz|.*\.txt", i.as_posix())
            if patch_file != None:
                files.append(patch_file.group(0))
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
        quit()


def open_file(path):
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt") as data_log:
                for logs in data_log:
                    yield logs
        elif path.endswith(".txt"):
            with open(path, "rt") as data_log:
                for logs in data_log:
                    yield logs
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


def parser(config, logs):
    urls = []
    all_requests, count_str, all_times = 0, 0, 0
    count = {}
    try:
        for i in logs:
            first_parse = re.findall(r"(GET /\S*|POST /\S*)+ +.+ +(\d\.\d{3})", i)
            # first_parse = re.search(r"(GET /\S*|POST /\S*)", i)
            # times = re.search(r"\s\d\.\d{3}", i)

            if len(first_parse):
                parse = re.sub(r"GET |POST ", "", first_parse[0][0])
                urls.append(parse)
                count.setdefault(parse, [])
                count[parse].append(float(first_parse[0][1]))
                all_requests += 1
                all_times += float(first_parse[0][1])
            count_str += 1
        logger.info("Логи распаршены")
        if all_requests != count_str:
            err_count = 100 - (all_requests / count_str) * 100
            logger.error(
                f"Не удалось распарсить {float_cut(err_count)}% логов, проверьте синтаксис"
            )
            if err_count > 50:
                logger.info(
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
            result = {
                "url": i,
                "count": urls_count,
                "count_perc": float_cut(sum_time),
                "time_sum": float_cut(sum(count[i])),
                "time_perc": float_cut((sum_time / all_times) * 100),
                "time_avg": float_cut(mean(count[i])),
                "time_max": float_cut(max(count[i])),
                "time_med": float_cut(median(count[i])),
            }
            yield result
        logger.info("Данные из лог файла преобразованны в json")

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
    list_dict = []
    try:
        with open("report.html", "r") as template_report:
            report = template_report.read()
        template = Template(report)
        for i in result:
            list_dict.append(i)
        template_with_data = template.safe_substitute(table_json=list_dict)
        logger.info("Открыт шаблон отчёта, данные json переданы")
    except FileNotFoundError:
        logger.error("Не найден файл шаблона report.html")
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()

    try:
        os.mkdir(config["REPORT_DIR"])
        logger.info(f"Создана папка {config['REPORT_DIR']}")
    except:
        logger.info(f"Папка {config['REPORT_DIR']} уже существует")

    try:
        with open(f'{config["REPORT_DIR"]}/report-{data_file}.html', "w") as report_out:
            report_out.write(template_with_data)
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
        path, data_file = find_path(config)
        logs = open_file(path)
        result = parser(config, logs)
        write_report(result, data_file, config)
    except KeyboardInterrupt:
        logger.error("Операция прервана пользователем")
        quit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error(f"Ошибка: {e}, в строке {exc_tb.tb_lineno}")
        quit()
