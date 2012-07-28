from collections import namedtuple
from multiprocessing import Queue
import random
import time

from paxos import SystemConfig
from paxos.messages import *
from paxos.sim import System, Mailbox


class DebugMailbox(Mailbox):
    """
    A Mailbox subclass that keeps track of the messages send and received, so
    that they can be later verified.
    """

    def __init__(self, *args, **kwargs):
        super(DebugMailbox, self).__init__(*args, **kwargs)
        self.num_sent = 0
        self.num_recv = 0
        if self.config.debug_messages:
            self.messages_sent = []
            self.messages_recv = []
        self.debug_queue = Queue()

    def is_protocol_message(self, msg):
        return isinstance(msg, (PrepareMsg, PrepareResponseMsg, AcceptMsg,
                                AcceptResponseMsg))

    def send(self, to, msg):
        super(DebugMailbox, self).send(to, msg)
        self.num_sent += 1
        if self.config.debug_messages:
            source = getattr(msg, 'source', None)
            self.messages_sent.append((source, to))

    def recv(self, from_):
        msg = super(DebugMailbox, self).recv(from_)
        source = getattr(msg, 'source', None)
        if source is not None:
            self.num_recv += 1
            if self.config.debug_messages:
                self.messages_recv.append((source, from_))
        return msg

    def get_counts(self):
        #Counts = namedtuple('Counts', ['sent', 'recv', 'total'])
        return (self.num_sent, self.num_recv, self.num_sent)

    def shutdown(self):
        """
        Shutdown an agent's locally referenced mailbox object by sending the
        debug data to the debug queue.
        """
        self.debug_queue.put(self.get_counts())
        super(DebugMailbox, self).shutdown()


class DebugSystem(System):
    """
    A system instance that is instrumented with debugging features.
    """

    def __init__(self, *args, **kwargs):
        if not kwargs.get('mailbox', None):
            kwargs['mailbox'] = DebugMailbox
        super(DebugSystem, self).__init__(*args, **kwargs)
        self.message_counts = {}
        self.sent_messages = {}
        self.recv_messages = {}

    def shutdown_agents(self, *args, **kwargs):
        super(DebugSystem, self).shutdown_agents(*args, **kwargs)
        # We aren't getting these an any sort of pid order, we just store them
        # with index keys in a dictionary.
        for x in range(len(self.processes)):
            self.message_counts[x] = self.mailbox.debug_queue.get()

    def print_summary(self, log=False):
        result_summary = self.logger.get_summary_data()
        result_summary.print_summary()
        self.message_count_summary()

        if log:
            import os
            import csv
            filename = 'log.txt'
            print_headings = not os.path.exists(filename)
            with open(filename, 'a') as f:
                writer = csv.writer(f)
                if print_headings:
                    writer.writerow(["agents", "fail rates"] + result_summary.get_summary_headings() + self.message_headings())
                writer.writerow([self.config.agent_config, self.config.fail_rates] + result_summary.get_summary_data() + self.message_data())

    def message_headings(self):
        headings = [
            "messages sent",
            "messages sent percent",
        ]
        if len(self.message_counts[0]) > 3:
            headings += [
                "failed messages",
                "failed messages percent",
            ]
        headings += [
            "total messages",
            "received messages",
        ]
        return headings

    def message_data(self):
        sent = sum([c[0] for c in self.message_counts.values()])
        recv = sum([c[1] for c in self.message_counts.values()])
        total = sum([c[-1] for c in self.message_counts.values()])
        sent_percent = float(100) * sent/total
        insert_fails = len(self.message_counts[0]) > 3
        if insert_fails:
            fail = sum([c[2] for c in self.message_counts.values()])
            fail_percent = float(100)*fail/total
        else:
            fail = None
            fail_percent = None
        return [sent, sent_percent, fail, fail_percent, total, recv]

    def message_count_summary(self):
        print("""\
Messages::
    Sent: {:>6} {:>6.1f}%
    Fail: {:>6} {:>6.1f}%
   =============
   Total: {:>6}
   -------------
    Recv: {:>6}
""".format(*self.message_data()))

    def print_sent_messages(self):
        text = "Messages sent were:"
        for p, msg_list in self.sent_messages.items():
            text += "\n{}: {}".format(p, msg_list)
        return text

    def print_recv_messages(self):
        text = "Messages received were:"
        for p, msg_list in self.recv_messages.items():
            text += "\n{}: {}".format(p, msg_list)
        return text


def test_paxos(sytem):
    for x in range(2):
        system.mailbox.send(random.randint(0, len(system.config.proposer_ids)-1),
                            ClientRequestMsg(None, "Query {}".format(x)))
        time.sleep(0.5)

def test_paxos2():
    system.mailbox.send(0,ClientRequestMsg(None, "Query {}".format(0)))
    time.sleep(0.5)
    system.mailbox.send(1,ClientRequestMsg(None, "Query {}".format(1)))
    time.sleep(0.5)
    system.mailbox.send(0,ClientRequestMsg(None, "Query {}".format(2)))

def test_multi_paxos():
    config = SystemConfig(3, 3, 3)
    system = DebugSystem(config)
    system.start()

    for x in range(20):
        # Always send to the same proposer, effective using that proposer as
        # the leader.
        to = 0
        system.mailbox.send(to, ClientRequestMsg(None, "Query {}".format(x)))
        time.sleep(random.random()/10)

    system.shutdown_agents()
    system.logger.print_results()
    #print(system.print_sent_messages())
    system.quit()
    import sys
    sys.exit()

if __name__ == "__main__":
    test_multi_paxos()
    system = System(SystemConfig(1, 1, 1))
    #system = DebugSystem(SystemConfig(2, 3, 2, proposer_sequence_start=1,
    #                             proposer_sequence_step=1))
    #system = DebugSystem(SystemConfig(1, 3, 1))
    system.start()
    #test_paxos(system)
    test_paxos2()
    system.shutdown_agents()
    system.logger.print_results()
    #print(system.print_sent_messages())
    system.quit()
