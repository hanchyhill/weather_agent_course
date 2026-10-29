def pytest_addoption(parser):
    parser.addoption("--run-exercises", action="store_true", default=False,
                     help="运行学员练习的测试（练习未完成时会失败）")
