import sys
import time
from threading import Thread
from multiprocessing import Queue
from queue import Empty

from paxos.messages import *
from paxos.protocol import *
from paxos.analyzer import *


class BaseSystem:
    """
    Base class that simulation system classes should inherit.
    Included here so that this module can check for a system instance's type
    without creating circular import by importing the actual implementation
    class that lives someplace else.
    """


class Agent:
    """
    A Paxos agent, meant to be subclassed for implementing the paxos roles.
    """

    def __init__(self, pid, mailbox, logger):
        self.config = None
        self.pid = pid
        self.mailbox = mailbox
        self.logger = logger
        # Flag that will shutdown process.
        self.active = True
        # Flag for any process threads to shutdown.
        self.stopping = False

    def run(self):
        """
        Loop forever, listening for and handling any messages sent to us.
        """
        print("{}-{} started".format(self.pid, self.__class__.__name__))
        while self.active:
            msg = self.recv()
            self.handle_message(msg)
            #self.message_done()
        print("Process {} shutting down".format(self.pid))

    def send_message(self, msg, pids):
        for pid in pids:
            print("Process {}-{} sending message to {}: {}".format(
                  self.pid, self.__class__.__name__, pid, msg))
            self.mailbox.send(pid, msg)

    def recv(self):
        """
        Blocking receive of a message destined to this agent process.
        """
        msg = self.mailbox.recv(self.pid)
        source = getattr(msg, 'source', None)
        print("  Process {}-{} received message from {}: {}".format(
              self.pid, self.__class__.__name__, source, msg))
        return msg

    def message_done(self):
        """
        Signal to the mailbox that we've finished processing of the message.
        This gives the mailbox to take care of any needed accounting.
        """
        self.mailbox.task_done(self.pid)

    def handle_message(self, msg):
        """
        Handle a received message.  Meant to be overridden in subclasses for
        customizing agent's behavior.
        """
        if isinstance(msg, SystemConfig):
            self.set_config(msg)
        if msg == 'quit':
            self.handle_quit()

    def set_config(self, config):
        self.config = config

    def stop(self):
        """Stop any helper threads."""
        self.stopping = True

    def handle_quit(self):
        self.stop()
        self.mailbox.shutdown()
        self.active = False


class Proposer(Agent):
    def __init__(self, *args, **kwargs):
        super(Proposer, self).__init__(*args, **kwargs)

        # Paxos Made Simple suggests that proposers in a system use a disjoint
        # set of proposal numbers.  So, we start each Proposer's sequence
        # number at its pid value (which is unique) and we increment by the
        # number of proposers.
        self.sequence = self.pid
        # Step gets set when the process receives the system configuration
        # message on startup.
        self.sequence_step = None

        # States for various instances of the algorithm, i.e. sequence numbers.
        # This will itself contain dictionaries of states for the rounds of
        # each proposal tried during an instance.
        self.instances = {}
        self.instance_sequence = 1

    def set_config(self, config):
        """
        Set this process's sequence step to the number of proposers.
        """
        super(Proposer, self).set_config(config)
        if config.proposer_sequence_start:
            self.sequence = config.proposer_sequence_start
        if config.proposer_sequence_step:
            self.sequence_step = config.proposer_sequence_step
        else:
            self.sequence_step = len(config.proposer_ids)

        # instantiate analyzer if dynamic weights enabled after configuration
        self.analyzer = None
        if config.dynamic_weights:
            self.analyzer = Analyzer(config.acceptor_ids)

    def handle_message(self, msg):
        super(Proposer, self).handle_message(msg)
        if isinstance(msg, ClientRequestMsg):
            self.handle_client_request(msg)
        elif isinstance(msg, PrepareResponseMsg):
            self.handle_prepare_response(msg)
        elif isinstance(msg, AcceptResponseMsg):
            self.handle_accept_response(msg)

    def create_proposal(self, instance=None):
        """
        Create a new proposal using this process's current proposal number
        sequence and instance number sequence.  If instance is given, then
        use it as the instance number instead of using this process's current
        instance sequence number.
        """
        if instance:
            instance_sequence = instance
        else:
            instance_sequence = self.instance_sequence
        print("*** Process {} creating proposal with Number {}, Instance {}"
              .format(self.pid, self.sequence, instance_sequence))
        proposal = Proposal(self.sequence, instance_sequence, self.pid)
        self.sequence += self.sequence_step
        # Only increment the instance sequence if we weren't given one.
        if instance is None:
            self.instance_sequence += 1
        return proposal

    def handle_client_request(self, msg, instance=None):
        """
        Start a Paxos instance.
        """
        proposal = self.create_proposal(instance)
        if proposal.instance not in self.instances:
            self.instances[proposal.instance] = {}
        if proposal.number not in self.instances[proposal.instance]:
            self.instances[proposal.instance][proposal.number] = \
                    BasicPaxosProposerProtocol(self, proposal)
        self.instances[proposal.instance][proposal.number].request = msg.value
        self.instances[proposal.instance][proposal.number].handle_client_request(proposal)

    def handle_prepare_response(self, msg):
        self.instances[msg.proposal.instance][msg.proposal.number].handle_prepare_response(msg)

    def handle_accept_response(self, msg):
        self.instances[msg.proposal.instance][msg.proposal.number].handle_accept_response(msg)


class Acceptor(Agent):

    def __init__(self, *args, **kwargs):
        super(Acceptor, self).__init__(*args, **kwargs)
        self.instances = {}

    def create_instance(self, instance_id):
        """
        Create a protocol instances for the given instance_id if one doesn't
        already exist.  Return the protocol instance.
        """
        if instance_id not in self.instances:
            self.instances[instance_id] = BasicPaxosAcceptorProtocol(self)
        return self.instances[instance_id]

    def handle_message(self, msg):
        super(Acceptor, self).handle_message(msg)
        if isinstance(msg, PrepareMsg):
            self.handle_prepare(msg)
        if isinstance(msg, AcceptMsg):
            self.handle_accept(msg)

    def handle_prepare(self, msg):
        self.create_instance(msg.proposal.instance).handle_prepare(msg)

    def handle_accept(self, msg):
        self.create_instance(msg.proposal.instance).handle_accept(msg)


class Learner(Agent):

    def __init__(self, *args, **kwargs):
        super(Learner, self).__init__(*args, **kwargs)
        self.instances = {}
        # Results stored by instance number.
        self.results = {}

    def handle_message(self, msg):
        super(Learner, self).handle_message(msg)
        if isinstance(msg, AcceptResponseMsg):
            self.handle_accept_response(msg)
        elif isinstance(msg, AdjustWeightsMsg):
            self.handle_adjust_weights(msg)

    def handle_accept_response(self, msg):
        number = msg.proposal.number
        instance_id = msg.proposal.instance
        if instance_id not in self.instances:
            self.instances[instance_id] = {}
        if number not in self.instances[instance_id]:
            self.instances[instance_id][number] = BasicPaxosLearnerProtocol(self)
        self.instances[instance_id][number].handle_accept_response(msg)

    def handle_adjust_weights(self, msg):
        self.config.weights = msg.weights

    def record_result(self, instance, value):
        self.results[instance] = value

    def log_result(self, msg):
        instance = msg.proposal.instance
        value = msg.proposal.value
        self.record_result(instance, value)
        print("*** {} logging result for instance {}: {}".format(self.pid, instance, value))
        self.logger.log_result(self.pid, instance, value)

class SystemConfig:
    """
    Encapsulates the configuration of a system, i.e. the processes IDs of all
    the proposer, acceptor, and learner processes.
    """
    def __init__(self, num_proposers, num_acceptors, num_learners,
                 proposer_class=Proposer,
                 acceptor_class=Acceptor,
                 learner_class=Learner,
                 proposer_sequence_start=None,
                 proposer_sequence_step=None,
                 message_timeout=0.5,
                 num_test_requests=0,
                 weights=None,
                 dynamic_weights=False,
                 debug_messages=False,
                 ):
        self.agent_config = (num_proposers, num_acceptors, num_learners)
        self.num_processes = sum([num_proposers, num_acceptors, num_learners])
        self.proposer_class = proposer_class
        self.acceptor_class = acceptor_class
        self.learner_class = learner_class

        counter = 0
        self.proposer_ids = list(range(0, counter + num_proposers))
        counter += num_proposers
        self.acceptor_ids = list(range(counter, counter + num_acceptors))
        counter += num_acceptors
        self.learner_ids = list(range(counter, counter + num_learners))

        self.proposer_sequence_start = proposer_sequence_start
        self.proposer_sequence_step = proposer_sequence_step
        self.message_timeout = message_timeout
        self.num_test_requests = num_test_requests

        # configure weights based on static/dynamic setting
        if not dynamic_weights:
            self.config_static_weights(weights, num_acceptors)
        else:
            self.config_dynamic_weights(num_acceptors)
        self.dynamic_weights = dynamic_weights

        # The following used by DebugMailbox.
        # If True, each process will record who they sent messages to.
        self.debug_messages = debug_messages

    def __str__(self):
        return "System Configuration: {}-{}-{}".format(self.proposer_ids,
                                                       self.acceptor_ids,
                                                       self.learner_ids)

    def process_list(self):
        """
        Return a list of (pid, agent class) two-tuples that get used by
        System.launch_processes.
        """
        pid = 0
        for pid in self.proposer_ids:
            yield (pid, self.proposer_class)
        for pid in self.acceptor_ids:
            yield (pid, self.acceptor_class)
        for pid in self.learner_ids:
            yield (pid, self.learner_class)

    def config_static_weights(self, weights, num_acceptors):
        if weights:
            assert len(weights) == num_acceptors
        else:
            weights = [1] * num_acceptors
        # Convert weights list into dict mapping pid to weight.
        self.weights = {}
        for pid, weight in zip(self.acceptor_ids, weights):
            self.weights[pid] = weight
        self.total_weight = sum(weights)

    def config_dynamic_weights(self, num_acceptors):
        weight = round(1/num_acceptors,2)
        self.weights = {}
        for pid in self.acceptor_ids:
            self.weights[pid] = weight
        self.total_weight = 1.0
