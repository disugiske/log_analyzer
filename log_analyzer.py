#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
import argparse
import json
import logging
import gzip
import itertools
import os
import re
import sys
from operator import itemgetter
from string import Template
from pathlib import Path
from statistics import mean, median


config = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}


def float_cut(obj):
    return f"{obj:.{3}f}"


def open_config(config_path):
    if config_path is None:
        return config
    with open(config_path, "r", encoding="utf8") as conf_file:
        parse_config = json.load(conf_file)
    return parse_config


def check_config(parse_config, conf):
    if parse_config.values() == conf.values():
        return conf
    else:
        for i in parse_config:
            conf[i] = parse_config[i]
        return conf


def find_patch(path_log_dir):
    data = {}
    if not os.path.isdir(path_log_dir):
        return None
    for i in os.listdir(path_log_dir):
        patch_file = re.search(r".*\.gz|.*\.txt", i)
        if patch_file != None:
            data_name = re.search(r"\d\d\d\d\d\d\d\d", patch_file.group(0))
            data[patch_file.group(0)] = data_name.group(0)
    file_data = sorted(data.items(), key=itemgetter(1), reverse=True)[0]
    path_file = f"{path_log_dir}/{file_data[0]}"
    data_file_raw = file_data[1]
    data_file = f"{data_file_raw[:4]}.{data_file_raw[4:6]}.{data_file_raw[6:]}"
    return path_file, data_file


def check_today_report(report_dir_patch, data_file):
    for reports in report_dir_patch.glob("report-*.html"):
        data_report = re.search(r"\d\d\d\d.\d\d.\d\d", reports.as_posix())
        if data_report.group(0) == data_file:
            return True


def open_file(path):
    if path.endswith(".gz"):
        with gzip.open(path, "rt") as data_log:
            for logs in data_log:
                yield logs
    elif path.endswith(".txt"):
        with open(path, "rt") as data_log:
            for logs in data_log:
                yield logs


def parse_file(logs):
    urls = []
    all_requests, count_str, all_times = 0, 0, 0
    count = {}
    for i in logs:
        first_parse = re.findall(r"(GET /\S*|POST /\S*)+ +.+ +(\d\.\d{3})", i)
        if len(first_parse):
            parse = re.sub(r"GET |POST ", "", first_parse[0][0])
            urls.append(parse)
            count.setdefault(parse, [])
            count[parse].append(float(first_parse[0][1]))
            all_requests += 1
            all_times += float(first_parse[0][1])
        count_str += 1
    return all_requests, count_str, all_times, count


def check_parse(all_requests, count_str):
    err_count = 100 - (all_requests / count_str) * 100
    return err_count


def make_json(all_requests, all_times, count, path_size):
    sorted_count = dict(sorted(count.items(), key=lambda x: len(x[1]), reverse=True))
    for i in itertools.islice(sorted_count, 0, int(path_size) - 1):
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


def make_report_dir(report_dir):
    if not os.path.isdir(report_dir):
        os.mkdir(report_dir)
        return report_dir


def open_report_template():
    with open("report.html", "r") as template_report:
        report = template_report.read()
    return report


def make_report(result, report):
    list_dict = []
    template = Template(report)
    for i in result:
        list_dict.append(i)
    template_with_data = template.safe_substitute(table_json=list_dict)
    return template_with_data


def write_report(template_with_data, data_file):
    with open(f'{config["REPORT_DIR"]}/report-{data_file}.html', "w") as report_out:
        report_out.write(template_with_data)


def main(config):

    path_file = find_patch(config["LOG_DIR"])
    if path_file == None:
        logger.error("не найдена папка с логами")
        quit(0)
    check_result = check_today_report(Path(config["REPORT_DIR"]), path_file[1])
    if check_result == True:
        logger.error("Отчёт на сегодня уже готов! Скрипт завершён")
        return
    logs = open_file(path_file[0])
    if logs == "":
        logger.info("Файл логов пустой")
        return
    logger.info(f"Файл {path_file[0]} упешно открыт и прочитан")
    all_requests, count_str, all_times, count = parse_file(logs)
    err_count = check_parse(all_requests, count_str)
    if err_count > 50:
        logger.error(
            "Не удалось рапарсить более 50% логов, проверьте синтаксис. Работа завершена"
        )
        quit()
    elif err_count > 0:
        logger.info(
            f"Не удалось распарсить {float_cut(err_count)}% логов, проверьте синтаксис"
        )
    else:
        logger.info("Логи распаршены")
    report_dir = make_report_dir(config["REPORT_DIR"])
    if report_dir:
        logger.info(f"Создана папка {report_dir}")
    report = open_report_template()
    result = make_json(all_requests, all_times, count, config_result["REPORT_SIZE"])
    template_with_data = make_report(result, report)
    write_report(template_with_data, path_file[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        "-c",
        help="Укажите путь к файлу с config. По умолчанию config:"
        '{"REPORT_SIZE": 1000,'
        '"REPORT_DIR": "./reports",'
        '"LOG_DIR": "./log_test"}',
    )
    args = parser.parse_args()

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
    logger.info("Старт скрипта")
    if args.config:
        logger.info(f"Передан путь к файлу config:{args.config}")
    parse_config = open_config(args.config)
    config_result = check_config(parse_config, config)
    if config_result:
        logger.info("Файл config успешно прочитан")
    try:
        main(config_result)
        logger.info("Отчёт сохранен")
    except KeyboardInterrupt:
        logger.exception("Операция прервана пользователем", exc_info=False)
        quit()
    except Exception:
        logger.exception(f"Ошибка:")
        quit()
