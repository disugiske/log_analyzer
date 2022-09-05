import os
import unittest
from pathlib import Path
from typing import Union

import log_analyzer


class FunctionalTest(unittest.TestCase):

    def test_options_parse(self):
        out = log_analyzer.options_parse()
        data = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./log"
        }
        self.assertEqual(out, data)

    def test_open_file_gzip(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./log_test"
        }
        out = log_analyzer.open_file(config)
        data = ('log_test/nginx-access-ui.log-20170830.gz', '2017.08.30')
        self.assertEqual(out, data)

    def test_open_file_plain(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./log_plain"
        }
        out = log_analyzer.open_file(config)
        data = ('log_plain/nginx-access-ui.log-20170630.txt', '2017.06.30')
        self.assertEqual(out, data)

    def test_parser(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./log_plain"
        }
        path, date = log_analyzer.open_file(config)
        result = log_analyzer.parser(path, config)
        self.assertTrue(type(result) is list)
        self.assertTrue(type(result[0]) is dict)

    def test_parser_result(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./log_plain"
        }
        path, date = log_analyzer.open_file(config)
        result = log_analyzer.parser(path, config)
        test_result = {'url': '/export/appinstall_raw/2017-06-29/', 'count': 14929, 'count_perc': '8.381', 'time_sum': '49.980', 'time_perc': '0.012', 'time_avg': '0.003', 'time_max': '0.223', 'time_med': '0.003'}
        self.assertTrue(test_result in result[0])

    def test_write_report(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports_test",
            "LOG_DIR": "./log_plain"
        }
        path, date = log_analyzer.open_file(config)
        result = log_analyzer.parser(path, config)
        log_analyzer.write_report(result, date, config)
        path_test = "reports_test/report-2017.06.30.html"
        path = list((i.as_posix()) for i in Path("./reports_test").glob("*"))
        self.assertEqual(path_test, path[0])
        os.remove('./reports_test/report-2017.06.30.html')

if __name__ == '__main__':
    unittest.main()