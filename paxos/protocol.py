from collections import defaultdict

from paxos.messages import *


class BasicPaxosProtocol:

    def __init__(self, agent):
        self.agent = agent

    def have_acceptor_majority(self, acceptors):
        """
        Return True or False, depending on whether or not the passed collection
        of acceptors make up a majority.
        """
        config = self.agent.config
        majority_weight = config.total_weight / float(2)
        current_weight = sum([config.weights[i] for i in acceptors])
        return current_weight > majority_weight

    def tally_outbound_msgs(self):
        if self.agent.analyzer:
            for pid in self.agent.config.acceptor_ids:
                self.agent.analyzer.add_send(pid)

    def tally_inbound_msgs(self, pid):
        if self.agent.analyzer:
            self.agent.analyzer.add_recvd(pid)

    def adjust_weights(self):
        if self.agent.analyzer:
            self.agent.analyzer.check()
            if self.agent.analyzer.weight_changed:
                weights = self.agent.analyzer.weights
                source = self.agent.pid
                msg = AdjustWeightsMsg(source, weights)
                self.agent.send_message(msg, self.agent.config.learner_ids)
                print("--RATIOS--{}".format(self.agent.analyzer.msg_ratios))
                print("--WEIGHTS--{}".format(weights))
                self.agent.analyzer.weight_changed = False

class BasicPaxosProposerProtocol(BasicPaxosProtocol):

    def __init__(self, agent, proposal):
        super(BasicPaxosProposerProtocol, self).__init__(agent)
        # Request from a client.
        self.request = None
        # The current proposal for the instance started by this proposer.
        self.proposal = proposal

        self.prepare_responders = set()
        self.highest_proposal_from_promises = Proposal(-1, None)
        self.accept_responders = set()

        # States.
        self.state = None
        self.PREPARE_SENT = 0
        self.ACCEPT_SENT = 1

    def handle_client_request(self, proposal):
        next_msg = PrepareMsg(proposal.pid, proposal)
        self.agent.send_message(next_msg, self.agent.config.acceptor_ids)
        # if dynamic weights, tally messages
        self.tally_outbound_msgs()
        self.state = self.PREPARE_SENT

    def handle_prepare_response(self, msg):
        """
        Handle a response to a proposal.

        See if we've got a response from a majority of acceptors.  If so, send
        accept messages to acceptors.
        """
        self.prepare_responders.add(msg.source)
        self.tally_inbound_msgs(msg.source)
        if msg.highest_proposal.number > self.highest_proposal_from_promises.number:
            self.highest_proposal_from_promises = msg.highest_proposal
        # Check that we have sent prepare but not yet sent accept.
        if self.state == self.PREPARE_SENT:
            if self.have_acceptor_majority(self.prepare_responders):
                # If we have received any prepare responses with a higher
                # proposal number, we must use the value in that proposal.
                # If that value is None, then we get to choose (i.e. we'll use
                # the client's requested value.
                # Also set a flag here to note whether or not we used the
                # client's requested value (for retrying later).
                if self.highest_proposal_from_promises.value is not None:
                    self.proposal.value = self.highest_proposal_from_promises.value
                    self.client_request_handled = False
                else:
                    self.proposal.value = self.request
                    self.client_request_handled = True
                next_msg = AcceptMsg(self.agent.pid, self.proposal)
                # Can send to all acceptors or just the ones that responded.
                self.agent.send_message(next_msg, self.agent.config.acceptor_ids)
                #self.agent.send_message(next_msg, self.prepare_responders)
                self.tally_outbound_msgs()
                self.state = self.ACCEPT_SENT

    def handle_accept_response(self, msg):
        self.accept_responders.add(msg.source)
        self.tally_inbound_msgs(msg.source)
        if self.have_acceptor_majority(self.accept_responders):
            self.adjust_weights()

class BasicPaxosAcceptorProtocol(BasicPaxosProtocol):

    def __init__(self, agent):
        super(BasicPaxosAcceptorProtocol, self).__init__(agent)
        self.highest_proposal_promised = Proposal(-1, None)
        self.highest_proposal_accepted = Proposal(-1, None)

    def handle_prepare(self, msg):
        if msg.proposal.number > self.highest_proposal_promised.number:
            self.highest_proposal_promised = msg.proposal
            next_msg = PrepareResponseMsg(self.agent.pid, msg.proposal,
                                          self.highest_proposal_accepted)
            self.agent.send_message(next_msg, [msg.source])
        # Optimization: send proposer a reject message because another proposer
        # has already initiated a proposal with a higher number.
        #else:
        #    msg = RejectMsg()

    def handle_accept(self, msg):
        # Accept proposal unless we have already promised a higher proposal number.
        if msg.proposal.number >= self.highest_proposal_promised.number:
            # Set this accepted proposal number as the highest accepted.
            self.highest_proposal_accepted = msg.proposal
            next_msg = AcceptResponseMsg(self.agent.pid, msg.proposal)
            # Send "accepted" message to sender of the accept message
            # (the proposer), and to all learners.
            self.agent.send_message(next_msg,
                              [msg.source] + list(self.agent.config.learner_ids))


class BasicPaxosLearnerProtocol(BasicPaxosProtocol):

    def __init__(self, agent):
        super(BasicPaxosLearnerProtocol, self).__init__(agent)
        # Set of acceptors that have sent an accept response.
        self.accept_responders = defaultdict(set)

        self.state = None
        self.RESULT_SENT = 1

    def handle_accept_response(self, msg):
        self.accept_responders[msg.proposal.value].add(msg.source)
        # Don't do anything if we've already logged the result.
        if self.state == self.RESULT_SENT:
            return
        if self.have_acceptor_majority(self.accept_responders[msg.proposal.value]):
            self.agent.log_result(msg)
            self.state = self.RESULT_SENT
