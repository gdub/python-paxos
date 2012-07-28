import time

from paxos.sim_failure import *
from paxos.test import DebugSystem


def run_test(config, delay=0):
    system = DebugSystem(config, mailbox=DebugFailTestMailbox)
    system.start()

    for x in range(config.num_test_requests):
        to = 0
        system.mailbox.send(to, ClientRequestMsg(None, x+1))
        time.sleep(delay)

    system.shutdown_agents()
    system.logger.print_results()
    system.print_summary(log=True)
    system.quit()

if __name__ == '__main__':
    p_fail = [0]
    a_fail = [0.0,0.0,0.2,0.3,0.4]
    l_fail = [0,0]
    f_rates = p_fail + a_fail + l_fail
    config = FailTestSystemConfig(1, 5, 2, \
                                  num_test_requests=100, \
                                  fail_rates=f_rates, \
                                  dynamic_weights=True)
    run_test(config, 1)
