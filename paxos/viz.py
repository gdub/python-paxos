"""
Visualize graph and messages with Ubigraph: http://ubietylab.net/ubigraph/
Based on routing.py example included with Ubigraph download.

To run demo:

1. Download and unpack Ubigraph:
   http://ubietylab.net/ubigraph/content/Downloads/index.php

2. Start the Ubigraph server, e.g.::

       ./bin/ubigraph_server &

3. Tweak the parameters to your liking in the __main__ block at the end of this
   module.

4. Run this module::

       python3 viz.py


Other graphing libraries
========================
NetworkX - http://networkx.lanl.gov/
igraph - http://igraph.sourceforge.net/
python-graph - http://code.google.com/p/python-graph/
graph-tool - http://projects.skewed.de/graph-tool/
tulip - http://tulip.labri.fr/
    Python docs - http://tulip.labri.fr/Documentation/3_6/pythonDoc/index.html
"""

import random
import time
from multiprocessing import Process
from xmlrpc.client import ServerProxy


def draw_nodes(graph, num_nodes):
    G = graph
    G.set_vertex_style_attribute(0, "shape", "sphere")
    G.set_vertex_style_attribute(0, "color", "#F4FF85")
    G.set_vertex_style_attribute(0, "size", "0.2")

    activeVertex = G.new_vertex_style(0)
    G.set_vertex_style_attribute(activeVertex, "color", "#FF4B30")

    for i in range(num_nodes):
        G.new_vertex_w_id(i)
        G.set_vertex_attribute(i, "label", str(i))


def draw_edges(graph, num_nodes):
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i != j:
                edge_id = i*num_nodes + j
                G.new_edge_w_id(edge_id, i, j)


def animateArrow(graph, e, steps=20, delay=0.005):
    G = graph
    pos = 0.0
    G.set_edge_attribute(e, "arrow_position", str(pos))
    G.set_edge_attribute(e, "arrow", "true")
    for i in range(steps):
        a = i / float(steps-1)
        G.set_edge_attribute(e, "arrow_position", str(a))
        time.sleep(delay)
    G.set_edge_attribute(e, "arrow", "false")


def demo(num_nodes, num_messages, delay=0.01):
    server_url = 'http://127.0.0.1:20738/RPC2'
    server = ServerProxy(server_url)
    G = server.ubigraph
    graph = G
    for _ in range(num_messages):
        to = random.randrange(0, num_nodes)
        from_ = random.randrange(0, num_nodes)
        if to == from_:
            continue
        edge_id = (from_*nodes + to)
        animateArrow(graph, edge_id)
        time.sleep(delay)


if __name__ == "__main__":
    nodes = 9
    messages = 100

    server_url = 'http://127.0.0.1:20738/RPC2'
    server = ServerProxy(server_url)
    G = server.ubigraph
    G.clear()
    draw_nodes(G, nodes)
    draw_edges(G, nodes)

    num_procs = 4
    procs = [Process(target=demo, args=(nodes, messages)) for _ in range(num_procs)]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join()
