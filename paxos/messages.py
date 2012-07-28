class Proposal:
    def __init__(self, number, instance, pid=None, value=None):
        self.number = number
        self.instance = instance
        # PID of the process that created this proposal.
        self.pid = pid
        self.value = value
    def __str__(self):
        return "Proposal[N-{}, I-{}, {}]".format(self.number, self.instance,
                                                 self.value)


class Message:
    def __init__(self, source):
        # PID of the sender of the message.
        self.source = source

class ClientRequestMsg(Message):
    def __init__(self, source, value):
        super(ClientRequestMsg, self).__init__(source)
        self.value = value
    def __str__(self):
        return "Client Request: {}".format(self.value)

class ProposalMsg(Message):
    """
    A base class for other message types that hold a proposal.
    """
    name = "Proposal"

    def __init__(self, source, proposal):
        super(ProposalMsg, self).__init__(source)
        self.proposal = proposal

    def __str__(self):
        return "{}: {}".format(self.name, self.proposal)

class PrepareMsg(ProposalMsg):
    name = "Prepare"

class PrepareResponseMsg(ProposalMsg):
    name = "Prepare Response"
    def __init__(self, source, proposal, highest_proposal):
        super(PrepareResponseMsg, self).__init__(source, proposal)
        self.highest_proposal = highest_proposal
    def __str__(self):
        return "{}: {}, {}".format(self.name, self.proposal,
                                   self.highest_proposal)

class AcceptMsg(ProposalMsg):
    name = "Accept"

class AcceptResponseMsg(ProposalMsg):
    name = "Accept Response"

class RetryMsg(Message):
    def __init__(self, source, instance):
        super(RetryMsg, self).__init__(source)
        self.instance = instance
        # Set a dummy value.
        self.value = None

    def __str__(self):
        return "RetryMsg: {}".format(self.instance)

class AdjustWeightsMsg(Message):
    def __init__(self, source, weights):
        super(AdjustWeightsMsg, self).__init__(source)
        self.weights = weights
    def __str__(self):
        return "Weights: {}".format(self.weights)
