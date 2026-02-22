"""
Build a directed graph from the GEDCOM and compute distances / paths.
"""
import networkx as nx
from gedcom.parser import Parser

def build_graph(file_path):
    """
    Constructs an undirected and a directed NetworkX graph from a GEDCOM file.

    This function parses a GEDCOM file to identify all individuals and families.
    It builds:
    - An undirected graph (G_undirected) where edges represent relationships
      (blood or marriage). Edges are tagged with 'type'.
    - A directed graph (G_directed) where edges represent parent-to-child
      relationships.

    Args:
        file_path (str): The path to the GEDCOM file to be processed.

    Returns:
        tuple: A tuple containing:
            - nx.Graph: The undirected graph.
            - nx.DiGraph: The directed graph (parent -> child).
            - dict: A dictionary mapping individual pointers to names.
    """
    G_undirected = nx.Graph()
    G_directed = nx.DiGraph()

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
            G_undirected.add_node(pid, name=name)
            G_directed.add_node(pid, name=name)

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
                G_undirected.add_edge(husb, wife, type='marriage')
            # parent-child links
            for parent in [husb, wife]:
                if parent:
                    for child in children:
                        G_undirected.add_edge(parent, child, type='blood')
                        G_directed.add_edge(parent, child)
    return G_undirected, G_directed, indi


def get_path_category(G_undirected, G_directed, path):
    """
    Categorizes the relationship represented by a path.

    - 'direct': All edges are parent-child and the path is monotonic (all up or all down).
    - 'blood': All edges in the path are 'blood' type.
    - 'marriage': At least one edge in the path is 'marriage' type.

    Args:
        G_undirected (nx.Graph): The undirected graph with tagged edges.
        G_directed (nx.DiGraph): The directed graph (parent -> child).
        path (list): A list of node pointers representing a path.

    Returns:
        str: 'direct', 'blood', or 'marriage'.
    """
    if not path or len(path) < 2:
        return 'direct' # Self is direct

    # Check for marriage edges
    for i in range(len(path) - 1):
        edge_data = G_undirected.get_edge_data(path[i], path[i+1])
        if edge_data and edge_data.get('type') == 'marriage':
            return 'marriage'

    # If no marriage edges, it's either blood or direct.
    # Check if direct (exists as a path in the directed graph)
    start_node = path[0]
    end_node = path[-1]

    if nx.has_path(G_directed, start_node, end_node):
        return 'direct'
    if nx.has_path(G_directed, end_node, start_node):
        return 'direct'

    return 'blood'


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
