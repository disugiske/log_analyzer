import itertools
import os
import unittest
from pathlib import Path
from typing import Union

import log_analyzer


class FunctionalTest(unittest.TestCase):
    def test_options_parse(self):
        out = log_analyzer.options_parse()
        data = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}
        self.assertEqual(out, data)

    def test_find_path_gzip(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./tests/log_test",
        }

        out = log_analyzer.find_path(config)
        data = ("tests/log_test/nginx-access-ui.log-20170830.gz", "2017.08.30")
        self.assertEqual(out, data)

    def test_find_path_plain(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./tests/log_plain",
        }
        out = log_analyzer.find_path(config)
        data = ("tests/log_plain/nginx-access-ui.log-20170630.txt", "2017.06.30")
        self.assertEqual(out, data)

    def test_open_file(self):
        test_logs = []
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./tests/log_plain",
        }
        path, data_file = log_analyzer.find_path(config)
        logs = log_analyzer.open_file(path)
        test_str = '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390'
        self.assertTrue(test_str in next(logs))

    def test_parser(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./tests/log_plain",
        }
        path, data_file = log_analyzer.find_path(config)
        logs = log_analyzer.open_file(path)
        result = log_analyzer.parser(config, logs)
        for i in result:
            self.assertTrue(type(i) is dict)

    def test_parser_result(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./tests/log_plain",
        }
        path, data_file = log_analyzer.find_path(config)
        logs = log_analyzer.open_file(path)
        result = log_analyzer.parser(config, logs)
        test_result = {
            "url": "/api/v2/banner/25019354",
            "count": 1,
            "count_perc": "4.762",
            "time_sum": "0.390",
            "time_perc": "73.091",
            "time_avg": "0.390",
            "time_max": "0.390",
            "time_med": "0.390",
        }
        res = []
        for i in result:
            res.append(i)
        self.assertTrue(test_result in res)

    def test_write_report(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./tests/reports_test",
            "LOG_DIR": "./tests/log_plain",
        }
        path, data_file = log_analyzer.find_path(config)
        logs = log_analyzer.open_file(path)
        result = log_analyzer.parser(config, logs)
        log_analyzer.write_report(result, data_file, config)
        path_test = "tests/reports_test/report-2017.06.30.html"
        path = list((i.as_posix()) for i in Path("tests/reports_test").glob("*"))
        self.assertEqual(path_test, path[0])
        os.remove("tests/reports_test/report-2017.06.30.html")


if __name__ == "__main__":
    unittest.main()
