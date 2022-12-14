import gzip
import os
import runpy
import sys
import unittest

import log_analyzer

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "tests/reports_test",
    "LOG_DIR": "tests/log_test",
    "ERR_LIMIT": 50,
}


class FunctionalTest(unittest.TestCase):
    def test_main(self):
        sys.argv[1:] = ["-cconfig_test.txt"]
        runpy.run_module("log_analyzer", run_name="__main__", alter_sys=True)
        self.assertEqual(os.listdir("tests/reports_test")[0], "report-2017.08.30.html")
        os.remove("tests/reports_test/report-2017.08.30.html")

    def test_main_logs(self):
        sys.argv[1:] = ["-cconfig_test.txt"]
        with self.assertLogs("logs_analyse", level="INFO"):
            runpy.run_module("log_analyzer", run_name="__main__", alter_sys=True)

    def test_find_patch(self):
        path_file = log_analyzer.find_latest_log(config["LOG_DIR"])
        out = ("tests/log_test/nginx-access-ui.log-20170830.gz", "2017.08.30")
        self.assertEqual(out, path_file)

    def test_open_file(self):
        res_logs = []
        logs = []
        path_file = log_analyzer.find_latest_log(config["LOG_DIR"])
        result = log_analyzer.open_file(path_file[0])
        for i in result:
            res_logs.append(i)
        f = gzip.open(
            "tests/log_test/nginx-access-ui.log-20170830.gz", "rt", encoding="utf-8"
        )
        for i in f:
            logs.append(i)
        self.assertTrue(res_logs[0] in logs)
        f.close()

    def test_parse_file(self):
        path_file = log_analyzer.find_latest_log(config["LOG_DIR"])
        result = log_analyzer.open_file(path_file[0])
        all_requests = log_analyzer.parse_file(result)
        self.assertTrue(all_requests[0] == 23)
        self.assertTrue(all_requests[1] == 23)
        self.assertTrue(f"{all_requests[2]:.{3}f}" == "6.732")
        self.assertTrue(all_requests[3]["/api/v2/group/1769230/banners"] == [0.628])


if __name__ == "__main__":
    unittest.main()
