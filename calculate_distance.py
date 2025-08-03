import os
import sys
from collections import deque
from gedcom.parser import Parser
from gedcom.element.individual import IndividualElement
from gedcom.element.family import FamilyElement

def build_family_graph(gedcom_file_path):
    parser = Parser()
    parser.parse_file(gedcom_file_path)
    root_elements = parser.get_root_child_elements()

    individuals = {}
    families = {}
    graph = {}

    # First pass: Collect individuals and families
    for element in root_elements:
        if element.get_tag() == 'INDI':
            indi_id = element.get_pointer()
            individuals[indi_id] = element
            graph[indi_id] = set()
        elif element.get_tag() == 'FAM':
            fam_id = element.get_pointer()
            families[fam_id] = element

    # Second pass: Build relationships
    for indi_id, individual_element in individuals.items():
        # Add family relationships (parents, children, spouses)
        for child in individual_element.get_child_elements():
            if child.get_tag() == 'FAMC':  # Family as Child
                fam_id = child.get_value()
                if fam_id in families:
                    family_element = families[fam_id]
                    # Link to parents
                    for fam_child in family_element.get_child_elements():
                        if fam_child.get_tag() == 'HUSB' and fam_child.get_value() in individuals:
                            graph[indi_id].add(fam_child.get_value())
                            graph[fam_child.get_value()].add(indi_id)
                        elif fam_child.get_tag() == 'WIFE' and fam_child.get_value() in individuals:
                            graph[indi_id].add(fam_child.get_value())
                            graph[fam_child.get_value()].add(indi_id)
            elif child.get_tag() == 'FAMS':  # Family as Spouse
                fam_id = child.get_value()
                if fam_id in families:
                    family_element = families[fam_id]
                    # Link to spouse
                    for fam_child in family_element.get_child_elements():
                        if fam_child.get_tag() == 'HUSB' and fam_child.get_value() != indi_id and fam_child.get_value() in individuals:
                            graph[indi_id].add(fam_child.get_value())
                            graph[fam_child.get_value()].add(indi_id)
                        elif fam_child.get_tag() == 'WIFE' and fam_child.get_value() != indi_id and fam_child.get_value() in individuals:
                            graph[indi_id].add(fam_child.get_value())
                            graph[fam_child.get_value()].add(indi_id)
    return graph, individuals

def get_person_name(individual_element):
    for child in individual_element.get_child_elements():
        if child.get_tag() == 'NAME':
            return child.get_value().replace('/', '').strip()
    return "Unknown Name"

def calculate_distances(graph, start_node):
    distances = {node: -1 for node in graph}
    distances[start_node] = 0
    queue = deque([start_node])

    while queue:
        current_node = queue.popleft()
        for neighbor in graph[current_node]:
            if distances[neighbor] == -1:
                distances[neighbor] = distances[current_node] + 1
                queue.append(neighbor)
    return distances

def find_path(graph, start_node, end_node):
    queue = deque([(start_node, [start_node])])
    visited = {start_node}

    while queue:
        current_node, path = queue.popleft()

        if current_node == end_node:
            return path

        for neighbor in graph[current_node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None

if __name__ == "__main__":
    gedcom_file = "fixed_tree.ged"  # Using the fixed GEDCOM file
    output_file = "distances.txt"
    person_id_env = os.getenv("PERSONID")

    if not person_id_env:
        print("Error: PERSONID environment variable not set.")
        sys.exit(1)

    graph, individuals = build_family_graph(gedcom_file)

    if person_id_env not in individuals:
        print(f"Error: PERSONID '{person_id_env}' not found in the GEDCOM file.")
        sys.exit(1)

    start_person_name = get_person_name(individuals[person_id_env])
    distances = calculate_distances(graph, person_id_env)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Distances from {start_person_name} ({person_id_env}):\n\n")
        for indi_id, dist in sorted(distances.items(), key=lambda item: item[1]):
            if dist != -1:
                person_name = get_person_name(individuals[indi_id])
                f.write(f"{person_name} ({indi_id}): {dist}\n")
    print(f"Distances calculated and saved to {output_file}")
