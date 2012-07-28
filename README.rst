=====
Paxos
=====

This is a demo implementation of the Paxos algorithm implemented in Python.


Requirements
============
* Python 3


Install
=======
::

    pip install paxos


Implementation Notes
====================

* The proposer, acceptor, and learner roles of the Paxos algorithm are
  implemented in with classes that subclass from a common ``Agent`` class.
* Each role/agent is run in a separate process.
* Communication between processes occurs using ``Queue`` objects, so all
  processes are run on the same machine.
* Paxos Made Simple states that "we require that different proposals have
  different numbers."  To achieve this, we start each proposer process's
  proposal number sequence equal to its own PID, and then increment the number
  for each new proposal by the number of proposer processes in the system.
  This also seems to be the method used in the "Paxos Made Live" paper by
  Google employees.
* It is assumed that all processes in the system be considered members of the
  system from the beginning, without needing to explicitly join the system by
  getting a decree passed.

References
==========
* Lamport's first paper on the subject: `The Part-Time Parliament`_
* Lamport's later paper on Paxos, a simplified version of the first without any
  Greek references: `Paxos Made Simple`_
* Google employees' experience in building a Paxos implementation for Chubby:
  `Paxos Made Live - An Engineering Perspective`_

.. _The Part-Time Parliament: http://research.microsoft.com/en-us/um/people/lamport/pubs/pubs.html#lamport-paxos
.. _Paxos Made Simple: http://research.microsoft.com/en-us/um/people/lamport/pubs/pubs.html#paxos-simple
.. _Paxos Made Live - An Engineering Perspective:


TODO
====
* Add a collapsed version of the roles so that each process plays all of the
  roles.

  * Once we have a collapsed version, leaders should retry a client's request
    if they determine that the instance hasn't been decided after some timeout
    amount of time.  This should fix a couple issues:

    1. Learners are not able to determine whether or not there are more values
       to learn (when it is the last value they are missing).

    2. Since leaders are currently remembering the original value of each
       client request they propose, if a Proposer is asked to retry an
       instance (e.g. from a Learner that is missing a value) then it is
       possible that the value learned will be None in the situation where no
       Acceptor has yet accepted a value in that instance (which means the
       Proposer should specify the value, but since it is not remembering the
       original values it just proposes None).

* When a learner asks a proposer to retry, the proposer shouldn't retry if it
  has already retried that proposal within a certain time period because
  otherwise, by re-upping the proposal number it would be guaranteed to not
  have a successful agreement in that instance it is retrying.

* With a consistent leader, only perform phase one once.
