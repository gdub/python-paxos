import copy

class Analyzer:
    def __init__(self, acceptor_ids, factor=0.05):
        self.weight_changed = False
        self.acceptor_ids = acceptor_ids
        self.factor=factor
        self.num_acceptors = len(acceptor_ids)
        self.nominal = 1 / self.num_acceptors
        #self.ceiling = (int(self.num_acceptors/3)+1) * self.nominal
        self.ceiling = 1/2

        self.weights = {}
        self.msgs_sent = {}
        self.msgs_recvd = {}
        self.msg_ratios = {}
        self.thresholds = {}
        for pid in acceptor_ids:
            self.weights[pid] = self.nominal
            self.msgs_sent[pid] = 0
            self.msgs_recvd[pid] = 0
            self.msg_ratios[pid] = 0
            self.thresholds[pid] = round(1-self.factor,2)

        # make copy of state to compare before/after run
        self._pre = copy.copy(self)

    def add_send(self, pid):
        self.msgs_sent[pid] += 1

    def add_recvd(self, pid):
        self.msgs_recvd[pid] += 1
        try:
            self.msg_ratios[pid] = round(self.msgs_recvd[pid]/self.msgs_sent[pid],2)
        except ZeroDivisionError:
            pass
        #self.check_threshold(pid)

    def check(self):
        for pid in self.acceptor_ids:
            self.check_threshold(pid)

    def check_threshold(self, pid):
        if self.msg_ratios[pid] <= self.thresholds[pid]:
            self.thresholds[pid] = round(self.thresholds[pid]-self.factor,2)
            self.lower_weight(pid)

    def lower_weight(self, pid):
        # lower the pid's weight
        tmp = round(self.weights[pid]-self.factor,2)
        if tmp > 0.0:
            self.weights[pid] = tmp
        else:
            self.weights[pid] = 0.0
        self.raise_weight()
        self.weight_changed = True

    def raise_weight(self):
        # increase another pid's weight
        if self.nominal != self.ceiling:
            adjusted = False
            while not adjusted:
                for i in range(self.num_acceptors):
                    pid = self.acceptor_ids[i]
                    diff = self.weights[pid] - self.nominal
                    if diff == 0.0:
                        self.weights[pid] = round(self.weights[pid]+self.factor,2)
                        adjusted = True
                        break
                if i is (self.num_acceptors-1):
                    self.nominal = round(self.nominal+self.factor,2)

    def log(self):
        print("Acceptor weights: {}".format(self.weights))
        print("Acceptor ratios: {}".format(self.msg_ratios))
        print("Acceptor thresholds: {}".format(self.thresholds))


if __name__ == '__main__':
    import random

    def test(acceptors, fail_rates, num_msgs):
        print("testing pids {}: ".format(acceptors))
        a=Analyzer(acceptors)
        print("\nBefore rounds...")
        a.log()
        for n in range(num_msgs):
            for pid in acceptors:
                a.add_send(pid)
                if fail_rates[pid] > random.random():
                    pass
                else:
                    a.add_recvd(pid)
        print("\nAfter rounds...")
        a.log()
        print('\n')

    test([0,1,2,3],[0,0,0.05,0],100)
    test([0,1,2,3,4],[0,0,0.05,0,0],100)
    test([0,1,2,3,4,5,6,7,8,9],[0,0,0.05,0,0,0,0,0,0.1,0],1000)