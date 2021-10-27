"""``Conductor`` class definition.
"""


class Conductor:
    def __init__(self, scheduler: "Scheduler", executor: "Executor"):
        self.scheduler = scheduler
        self.executor = executor


