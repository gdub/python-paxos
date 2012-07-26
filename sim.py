from collections import defaultdict
from multiprocessing import Process, Queue, JoinableQueue
import queue
from threading import Thread
import time

from paxos import Proposer, Acceptor, Learner, BaseSystem


class Mailbox:
    """
    Provides messaging functionality for a paxos system instance.
    """

    def __init__(self, config):
        self.config = config
        self.funnel = Queue()
        self.inbox = [Queue() for i in range(config.num_processes)]
        self.message_count = 0

        # Two flags, active to signal when we haven't received any messages
        # for timeout_interval seconds, and terminate to signal when we have
        # been asked to shutdown by the System.
        self.active = True
        self.terminate = False
        # If don't receive any messages in this amount of time, then shutdown.
        self.timeout_interval = 3 * self.config.message_timeout
        # Time stamp of the last seen message, used together with
        # timeout_interval to determine when the mailbox should shutdown.
        self.last_seen = None

    def run(self):
        print("Mailbox started")
        while True:
            if not self.active and self.terminate:
                break
            if self.active and self.last_seen and (time.time() - self.last_seen) > self.timeout_interval:
                self.active = False
            # Take messages off the funnel and deliver them to the appropriate
            # process.
            try:
                dest, msg = self.funnel.get(timeout=0.5)
                self.last_seen = time.time()
            except queue.Empty:
                pass
            else:
                self.inbox[dest].put(msg)
        print("Mailbox shutting down")

    def send(self, to, msg):
        """
        Send msg to process id ``to``.
        """
        # Funnel all messages through a primary queue so that we can keep track
        # of when we are done (i.e. all messages are processed).
        self.message_count += 1
        self.funnel.put((to, msg))

    def recv(self, from_):
        """
        Receive (blocking) msg destined for process id ``from_``.
        """
        return self.inbox[from_].get()

    def task_done(self, pid):
        """
        Inform pid's queue that it has processed a task.
        Called by agents when they are done processing a message, and used by
        the queue instance to know when all messages have been processed.
        """
        self.funnel.task_done()

    def join(self):
        """
        Block until all messages have finished processing and we haven't had
        any messages for a while (i.e. active set to False).
        """
        while self.active:
            time.sleep(0.5)
        # Don't join funnel queue because there's a good chance that it will
        # never be fully exhausted due to heart beat messages.
        #self.funnel.join()

    def shutdown(self):
        """
        Perform any shutdown actions prior to quitting.  In this base Mailbox
        class this is just a hook that isn't used.
        """
        pass

    def quit(self):
        self.terminate = True


class ResultLogger:
    """
    Class to hold log of results from each learner process.
    """

    def __init__(self, config):
        self.config = config
        self.queue = Queue()
        self.active = True
        # Results, PID mapped to list of decided values.
        self.results = defaultdict(dict)

    def run(self):
        print("Logger started")
        while True:
            if not self.active and self.queue.empty():
                break
            try:
                source, instance, value = self.queue.get(timeout=0.5)
            except queue.Empty:
                pass
            else:
                if source == "quit":
                    self.active = False
                else:
                    self.results[source][instance] = value
        print("Logger shutting down")

    def log_result(self, source, instance, value):
        self.queue.put((source, instance, value))

    def print_results(self):
        print("Process Result Log:")
        processes = sorted(self.results.keys())
        for pid in processes:
            instances = range(1, self.config.num_test_requests + 1)
            results = [(instance, self.results[pid].get(instance))
                       for instance in instances]
            print("  {}: {}".format(pid, results))

    def check_results(self):
        """
        Check that each learner process got the same results in the same order.
        Return False if there is a result list that is not the same.  If all
        results are the same, then return the list of results.
        """
        results = list(self.results.values())
        compare_list = results[0]
        result = True
        for result_list in results[1:]:
            if result_list != compare_list:
                result =  False
        print("Logger results consistent:", result)
        return result

    def get_summary_data(self):
        return ResultSummary(self)

    def print_summary(self):
        summary = self.get_summary_data()
        summary.print_summary()


class ResultSummary:
    """
    Given a logger object, summarize its results.
    """

    def __init__(self, logger):
        self.logger = logger
        self.instances = range(1, self.logger.config.num_test_requests + 1)
        self.pids = self.logger.config.learner_ids
        self.calculate()

    def calculate(self):
        self.calculate_missing()
        self.calculate_consistency()

    def calculate_missing(self):
        self.learned_values = 0
        self.missing_values = 0
        self.total_values = 0
        for i in self.instances:
            for pid in self.pids:
                value = self.logger.results[pid].get(i)
                self.total_values += 1
                if value is None:
                    self.missing_values += 1
                else:
                    self.learned_values += 1
        self.learned_values_percent = float(100) * self.learned_values / self.total_values
        self.missing_values_percent = float(100) * self.missing_values / self.total_values

    def calculate_consistency(self):
        """
        Count the number of consistent and inconsistent instance results,
        excluding unlearned or missing values.
        """
        # Disjoint set: good and bad (consistent and inconsistent) instances.
        self.good_instances = 0
        self.bad_instances = 0
        # Disjoint set: empty, incomplete, and complete instances representing
        # no, some, or all learners learned the value.
        self.empty_instances = 0
        self.incomplete_instances = 0
        self.complete_instances = 0
        for i in self.instances:
            values = set()
            num_none = 0
            for pid in self.pids:
                value = self.logger.results[pid].get(i)
                if value is None:
                    num_none += 1
                else:
                    values.add(value)
            length = len(values)
            if length == 0:
                self.good_instances += 1
                self.empty_instances += 1
            elif length == 1:
                if num_none == 0:
                    self.complete_instances += 1
                else:
                    self.incomplete_instances += 1
                self.good_instances += 1
            else:
                self.bad_instances += 1
        self.good_instances_percent = float(100) * self.good_instances / len(self.instances)
        self.bad_instances_percent = float(100) * self.bad_instances / len(self.instances)
        self.empty_instances_percent = float(100) * self.empty_instances / len(self.instances)
        self.incomplete_instances_percent = float(100) * self.incomplete_instances / len(self.instances)
        self.complete_instances_percent = float(100) * self.complete_instances / len(self.instances)

    def get_summary_headings(self):
        return [
            "learned values", "learned values percent",
            "missing values", "missing_values_percent",
            "total_values",
            "good_instances", "good_instances_percent",
            "bad_instances", "bad_instances_percent",
            "empty_instances", "empty_instances_percent",
            "incomplete_instances", "incomplete_instances_percent",
            "complete_instances", "complete_instances_percent",
            "total instances",
        ]

    def get_summary_data(self):
        return [
            self.learned_values, self.learned_values_percent,
            self.missing_values, self.missing_values_percent,
            self.total_values,
            self.good_instances, self.good_instances_percent,
            self.bad_instances, self.bad_instances_percent,
            self.empty_instances, self.empty_instances_percent,
            self.incomplete_instances, self.incomplete_instances_percent,
            self.complete_instances, self.complete_instances_percent,
            len(self.instances),
        ]

    def print_summary(self):
        print(self.get_summary_data())
        print("""\
Values:
    Learned: {:>6} {:>6.1f}%
    Missing: {:>6} {:>6.1f}%
    =======================
      Total: {:>6}

Instances:
    Consistent: {:>6} {:>6.1f}%
  Inconsistent: {:>6} {:>6.1f}%
    --------------------------
         Empty: {:>6} {:>6.1f}%
    Incomplete: {:>6} {:>6.1f}%
      Complete: {:>6} {:>6.1f}%
    ==========================
         Total: {:>6}
""".format(*self.get_summary_data()))

    def log_summary(self):
        import os
        filename = 'log.txt'
        print_headings = not os.path.exists(filename)
        with open(filename, 'a') as f:
            if print_headings:
                f.write('\t'.join(self.get_summary_headings()))
            f.write('\t'.join(self.get_summary_data()))


class System(BaseSystem):
    """
    Class for simulating a network of paxos agents.
    """

    def __init__(self, config, mailbox=None):
        """
        ``mailbox`` should be a mailbox class; if None, then use default
        Mailbox class.
        """
        print("System starting...")
        self.config = config
        # Set up mailbox and logger before launching agent processes so that
        # the agent processes will have access to them.
        if mailbox:
            mailbox_class = mailbox
        else:
            mailbox_class = Mailbox
        self.mailbox = mailbox_class(config)
        self.mailbox_process = Thread(target=self.mailbox.run, name="System Mailbox")
        self.mailbox_process.start()
        # Start the logger thread.
        self.logger = ResultLogger(config)
        self.logger_process = Thread(target=self.logger.run, name="System Logger")
        self.logger_process.start()

        self.processes = self.launch_processes()

    def launch_processes(self):
        """
        Launch ``number`` number of processes of the given ``agent_class``,
        using the given Mailbox instance and with process id starting with the
        given ``pid`` and incrementing for each process spawned.

        Return the incremented pid value when done, which is meant to be used
        in subsequent calls to this method for a starting pid.
        """
        processes = []
        for pid, agent_class in self.config.process_list():
            agent = agent_class(pid, self.mailbox, self.logger)
            p = Process(target=agent.run)
            p.start()
            processes.append(p)
        return processes

    def join(self):
        """
        Join with all processes that have been launched.
        """
        for process in self.processes:
            process.join()

    def start(self):
        """
        Start the system by sending a message to each process containing
        this system object.
        """
        for x in range(len(self.processes)):
            self.mailbox.send(x, self.config)

    def shutdown_agents(self):
        """
        Wait for all mailbox messages to be processed, then send quit messages
        to all processes and join with all processes.  This will block until
        all agents have terminated.
        """
        print("System waiting for mailbox to go inactive...")
        # Sleep a bit to allow any actions based on timeouts to fire.
        #time.sleep(10)
        self.mailbox.join()
        print("System shutting down agents...")
        for x in range(len(self.processes)):
            self.mailbox.send(x, "quit")
        self.join()

    def quit(self):
        self.logger.log_result("quit", None, None)
        self.logger_process.join()
        self.mailbox.quit()
        self.mailbox_process.join()
        print("System terminated.")
