"""
Build a directed graph from the GEDCOM and compute distances / paths.
"""
import networkx as nx
from gedcom.parser import Parser

def build_graph(file_path):
    """Return an undirected NetworkX graph of the GEDCOM family tree."""
    G = nx.Graph()

    gedcom_parser = Parser()
    gedcom_parser.parse_file(file_path)
    root = gedcom_parser.get_root_child_elements()

    indi = {}
    for elem in root:
        if elem.get_tag() == "INDI":
            pid = elem.get_pointer()
            name = "Unknown"
            for ch in elem.get_child_elements():
                if ch.get_tag() == "NAME":
                    name = ch.get_value().replace("/", "").strip()
                    break
            indi[pid] = name
            G.add_node(pid, name=name)

    for elem in root:
        if elem.get_tag() == "FAM":
            husb = wife = None
            children = []
            for ch in elem.get_child_elements():
                tag = ch.get_tag()
                val = ch.get_value()
                if tag == "HUSB":
                    husb = val
                elif tag == "WIFE":
                    wife = val
                elif tag == "CHIL":
                    children.append(val)
            # spouse link
            if husb and wife:
                G.add_edge(husb, wife)
            # parent-child links
            for parent in [husb, wife]:
                if parent:
                    for child in children:
                        G.add_edge(parent, child)
    return G, indi


def distance_and_path(graph, person_id, target_id):
    """Return (distance, path) or (None, []) if not reachable."""
    try:
        d = nx.shortest_path_length(graph, person_id, target_id)
        p = nx.shortest_path(graph, person_id, target_id)
        return d, p
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, []
