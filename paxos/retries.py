"""
Agents that retry client requests that don't get accepted or that aren't
learned by one or more learners.
"""

import time
from threading import Thread

from paxos import Proposer, Learner
from paxos.messages import RetryMsg


class RetryProposer(Proposer):
    """
    A Proposer subclass that handles retry messages from learners to re-propose
    in a particular instance.

    TODO: Proposer should also try re-proposing if it determines that an
    instance has not successfully come to an agreement yet.
    """

    def __init__(self, *args, **kwargs):
        super(RetryProposer, self).__init__(*args, **kwargs)
        # Default leader to PID 0.
        self.leader = 0

    def handle_message(self, msg):
        super(Proposer, self).handle_message(msg)
        if isinstance(msg, RetryMsg):
            self.handle_retry(msg)

    def handle_retry(self, msg):
        """
        Handle another process wanting to retry a run of the protocol in the
        specified instance, typically invoked by another process when it needs
        to learn the value for an instance that it doesn't know about.
        """
        self.handle_client_request(msg, msg.instance)


class RetryLearner(Learner):
    """
    A Learner subclass that will ask a proposer to re-propose in an instance
    that the Learner is missing a value for (i.e. never learned the message
    from a majority of Acceptors).
    """

    class LoggerThread(Thread):
        """
        Helper thread to order and log results.
        """
        def __init__(self, agent):
            Thread.__init__(self, name="LoggerThread-{}".format(agent.pid))
            self.agent = agent
        def run(self):
            counter = 1
            # Even if agent is not active, we need to continue until we've
            # logged all results we've seen.
            while self.agent.active or (counter <= self.agent.highest_instance):
                # Wait until agent has received its configuration before starting.
                if not self.agent.config:
                    time.sleep(0.5)
                    continue
                # If the counter has reached an instance beyond what we've seen
                # yet, then wait for more results.  We can't go on, otherwise
                # we'd end up retrying instances that haven't occurred yet.
                if counter > self.agent.highest_instance:
                    time.sleep(0.5)
                    continue
                try:
                    result = self.agent.results[counter]
                except KeyError:
                    # Wait five message delays.
                    time.sleep(5 * self.agent.config.message_timeout)
                    # If result still not there, tell the proposer to rerun the
                    # protocol in that instance.
                    if counter not in self.agent.results:
                        msg = RetryMsg(self.agent.pid, counter)
                        self.agent.send_message(msg, [self.agent.leader])
                else:
                    self.agent.log_result_to_logger(counter, result)
                    del self.agent.results[counter]
                    counter += 1

    def __init__(self, *args, **kwargs):
        super(RetryLearner, self).__init__(*args, **kwargs)
        self.active = True
        # The highest instance we've seen a result for.  This lets us know when
        # we have caught up to logging results that have come in.
        self.highest_instance = 0

    def run(self):
        self.loggerthread = self.LoggerThread(self)
        self.loggerthread.start()
        super(RetryLearner, self).run()

    def handle_quit(self):
        self.active = False
        self.loggerthread.join()
        super(RetryLearner, self).handle_quit()

    def record_result(self, instance, value):
        super(RetryLearner, self).record_result(instance, value)
        print("*** {} recording result for instance {}: {}"
              .format(self.pid, instance, value))
        if instance > self.highest_instance:
            self.highest_instance = instance

    def log_result(self, msg):
        """
        Don't actually log the result yet, just record it and let the
        LoggerThread handle the ordering and logging of the results to the
        result logger object.
        """
        instance = msg.proposal.instance
        value = msg.proposal.value
        self.record_result(instance, value)

    def log_result_to_logger(self, instance, value):
        print("*** {} logging result for instance {}: {}"
              .format(self.pid, instance, value))
        self.logger.log_result(self.pid, value)
