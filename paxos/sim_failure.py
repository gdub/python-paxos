"""
Extensions to the Mailbox and System classes for simulating message and/or
node failures.
"""

from collections import namedtuple
import random

from paxos import SystemConfig
from paxos.messages import ClientRequestMsg, AdjustWeightsMsg
from paxos.sim import Mailbox
from paxos.test import DebugMailbox


class FailTestMailbox(Mailbox):
    """
    A Mailbox class that drops messages destined to each process with a
    probability specified  in the system config.
    """

    def send(self, to, msg):
        """
        Test a random number between [0,1) against the fail rate to determine
        whether or not to deliver/drop the message.
        """
        try:
            fail_rate = self.config.fail_rates[to]
        except (AttributeError, IndexError):
            fail_rate = 0
        if msg == "quit" or isinstance(msg, SystemConfig) or isinstance(msg, ClientRequestMsg) or \
                isinstance(msg, AdjustWeightsMsg) or fail_rate == 0 or fail_rate <= random.random():
            super(FailTestMailbox, self).send(to, msg)
        else:
            self.message_failed()
            #print("****** Message to {} failed: {} ******".format(to, msg))

    def message_failed(self):
        """Hook for accounting of failed messages."""
        pass


class FailTestSystemConfig(SystemConfig):

    def __init__(self, *args, fail_rate=None, fail_rates=None, **kwargs):
        """
        If given, fail_rate should be a number between 0 and 1, inclusive, that
        will be set as a global message failure rate for all processes.
        If fail_rates is given, it should be a list of fail rates with length
        equal to the number of processes in the system.
        """
        super(FailTestSystemConfig, self).__init__(*args, **kwargs)
        if fail_rates:
            self.fail_rates = fail_rates
        else:
            if fail_rate is None:
                fail_rate = 0
            self.fail_rates = [fail_rate for _ in range(self.num_processes)]


class DebugFailTestMailbox(FailTestMailbox, DebugMailbox):

    def __init__(self, *args, **kwargs):
        super(DebugFailTestMailbox, self).__init__(*args, **kwargs)
        self.num_failed = 0

    def get_counts(self):
        #Counts = namedtuple('Counts', ['sent', 'recv', 'fail', 'total'])
        return (self.num_sent, self.num_recv, self.num_failed,
                self.num_sent + self.num_failed)

    def message_failed(self):
        self.num_failed += 1


def run_test(config):
    """

    """
    from test import DebugSystem
    system = DebugSystem(config, mailbox=DebugFailTestMailbox)
    system.start()

    for x in range(config.num_test_requests):
        # Always send to the same proposer, effective using that proposer as
        # the leader.
        to = 0
        #system.mailbox.send(to, ClientRequestMsg(None, "Query {}".format(x+1)))
        system.mailbox.send(to, ClientRequestMsg(None, x+1))
        #time.sleep(random.random()/10)

    system.shutdown_agents()
    system.logger.print_results()
    system.print_summary(log=True)
    system.quit()


def run_failrate_tests():
    for num_agents in (3, 5, 7, 9, 11):
        for fail_rate in [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
            config = FailTestSystemConfig(num_agents, num_agents, num_agents,
                                          num_test_requests=1000, fail_rate=fail_rate)
            run_test(config)


def run_reliability_example():
    fail_rates = [0, 0, 0, 0, 0,  0, 0.2, 0.2, 0.4, 0.4,   0, 0, 0, 0, 0]
    requests = 1000
    config = FailTestSystemConfig(5, 5, 5, num_test_requests=requests,
        fail_rates=fail_rates)
    run_test(config)
    config = FailTestSystemConfig(5, 5, 5, num_test_requests=requests,
        fail_rates=fail_rates, weights=[3,2,2,1,1])
    run_test(config)


def demo1():
    fail_rates = [0, 0, 0, 0, 0,  0, 0.2, 0.2, 0.4, 0.4,   0, 0, 0, 0, 0]
    requests = 100
    config = FailTestSystemConfig(5, 5, 5,
        num_test_requests=requests,
        fail_rates=fail_rates)
    run_test(config)

def demo2():
    fail_rates = [0, 0, 0, 0, 0,  0, 0.2, 0.2, 0.4, 0.4,   0, 0, 0, 0, 0]
    requests = 100
    config = FailTestSystemConfig(5, 5, 5,
        num_test_requests=requests,
        fail_rates=fail_rates, weights=[3,2,2,1,1])
    run_test(config)



if __name__ == "__main__":
    #run_failrate_tests()
    run_reliability_example()

    # Global fail rate for simulating unreliable messaging.
    #config = FailTestSystemConfig(3, 3, 3, fail_rate=0.1, num_test_requests=3)
    # Individual fail rates of 0/1 to simulate some machines down.
    #config = FailTestSystemConfig(3, 3, 3, num_test_requests=30, fail_rates=[0, 1, 1,   1, 0, 0,   0, 0, 1])

    # Failed acceptors.  With equal weights nothing is learned.  If we adjust
    # the rates to give the only alive acceptor a majority weight, then values
    # are accepted and it learns all values.
    #config = FailTestSystemConfig(3, 3, 3, num_test_requests=100, fail_rates=[0, 0, 0,   1, 1, 0,   0, 0, 0], weights=[1,1,3])
    #config = FailTestSystemConfig(3, 3, 3, num_test_requests=4000, fail_rates=[.2, .2, .2,   .8, .2, .1,   .2, .2, .2], weights=[1,2,4])
    #config = FailTestSystemConfig(6, 6, 6, num_test_requests=400, fail_rates=[.2, .2, .2, .2, .2, .2,   .8, .2, .1, .8, .2, .1,   .2, .2, .2, .2, .2, .2], weights=[1,2,4,1,2,4])
    #config = FailTestSystemConfig(3, 3, 3, num_test_requests=1000, fail_rate=0)


