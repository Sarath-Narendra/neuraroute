from datetime import datetime


class ExecutionLogger:

    def __init__(self):
        self.logs = []

    def log(self, entry):
        self.logs.append(entry)

    def get_logs(self):
        return self.logs

    def clear(self):
        self.logs.clear()


logger = ExecutionLogger()