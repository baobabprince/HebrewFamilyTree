"""
Build a directed graph from the GEDCOM and compute distances / paths.
"""
import networkx as nx
from gedcom.parser import Parser

def build_graph(file_path):
    """
    Constructs an undirected NetworkX graph from a GEDCOM file.

    This function parses a GEDCOM file to identify all individuals and families.
    It then builds a graph where:
    - Each individual (`INDI`) is a node, identified by their unique GEDCOM pointer.
    - An edge connects a husband and wife in a family (`FAM`).
    - Edges connect parents (husband and wife) to each of their children.

    Args:
        file_path (str): The path to the GEDCOM file to be processed.

    Returns:
        tuple: A tuple containing:
            - nx.Graph: The constructed graph representing the family tree.
            - dict: A dictionary mapping individual pointers (e.g., '@I1@') to
                    their formatted names.
    """
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
    """
    Calculates the shortest path and distance between two nodes in the graph.

    This function is a wrapper around NetworkX's shortest path algorithms.
    It gracefully handles cases where no path exists between the nodes or if
    one of the nodes is not found in the graph.

    Args:
        graph (nx.Graph): The NetworkX graph of the family tree.
        person_id (str): The starting node (GEDCOM pointer) for the path calculation.
        target_id (str): The ending node (GEDCOM pointer) for the path calculation.

    Returns:
        tuple: A tuple containing:
            - int or None: The shortest path distance (number of edges), or None
                           if no path exists.
            - list: A list of node pointers representing the shortest path, or an
                    empty list if no path exists.
    """
    try:
        d = nx.shortest_path_length(graph, person_id, target_id)
        p = nx.shortest_path(graph, person_id, target_id)
        return d, p
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, []
