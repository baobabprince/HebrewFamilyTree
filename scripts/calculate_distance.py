import os
import sys
from collections import deque
from gedcom.parser import Parser
from constants import LOG_ALL_PATHS_DISTANCE_THRESHOLD

def build_family_graph(gedcom_file_path):
    parser = Parser()
    parser.parse_file(gedcom_file_path)
    root_elements = parser.get_root_child_elements()

    individuals_data = {}
    families = {}
    graph = {}

    # First pass: Collect individuals and families
    for element in root_elements:
        if element.get_tag() == 'INDI':
            indi_id = element.get_pointer()

            birth_date = None
            death_date = None

            for child in element.get_child_elements():
                if child.get_tag() == 'BIRT':
                    for grand_child in child.get_child_elements():
                        if grand_child.get_tag() == 'DATE':
                            birth_date = grand_child.get_value()
                elif child.get_tag() == 'DEAT':
                    for grand_child in child.get_child_elements():
                        if grand_child.get_tag() == 'DATE':
                            death_date = grand_child.get_value()

            individuals_data[indi_id] = {
                "element": element,
                "birth_date": birth_date,
                "death_date": death_date
            }
            graph[indi_id] = set()
        elif element.get_tag() == 'FAM':
            fam_id = element.get_pointer()
            families[fam_id] = element

    # Second pass: Build relationships
    for indi_id, individual_data in individuals_data.items():
        individual_element = individual_data["element"]
        # Add family relationships (parents, children, spouses)
        for child in individual_element.get_child_elements():
            if child.get_tag() == 'FAMC':  # Family as Child
                fam_id = child.get_value()
                if fam_id in families:
                    family_element = families[fam_id]
                    # Link to parents
                    for fam_child in family_element.get_child_elements():
                        if fam_child.get_tag() == 'HUSB' and fam_child.get_value() in individuals_data:
                            graph[indi_id].add(fam_child.get_value())
                            graph[fam_child.get_value()].add(indi_id)
                        elif fam_child.get_tag() == 'WIFE' and fam_child.get_value() in individuals_data:
                            graph[indi_id].add(fam_child.get_value())
                            graph[fam_child.get_value()].add(indi_id)
            elif child.get_tag() == 'FAMS':  # Family as Spouse
                fam_id = child.get_value()
                if fam_id in families:
                    family_element = families[fam_id]
                    # Link to spouse
                    for fam_child in family_element.get_child_elements():
                        if fam_child.get_tag() == 'HUSB' and fam_child.get_value() != indi_id and fam_child.get_value() in individuals_data:
                            graph[indi_id].add(fam_child.get_value())
                            graph[fam_child.get_value()].add(indi_id)
                        elif fam_child.get_tag() == 'WIFE' and fam_child.get_value() != indi_id and fam_child.get_value() in individuals_data:
                            graph[indi_id].add(fam_child.get_value())
                            graph[fam_child.get_value()].add(indi_id)
    return graph, individuals_data

def get_person_name(individual_data):
    individual_element = individual_data["element"]
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

def find_path_with_details(graph, individuals_data, start_node, end_node):
    queue = deque([(start_node, [start_node])])
    visited = {start_node}

    while queue:
        current_node, path = queue.popleft()

        if current_node == end_node:
            detailed_path = []
            for node_id in path:
                person_data = individuals_data[node_id]
                name = get_person_name(person_data)
                birth_date = person_data.get("birth_date")
                death_date = person_data.get("death_date")
                detailed_path.append({
                    "id": node_id,
                    "name": name,
                    "birth_date": birth_date,
                    "death_date": death_date
                })
            return detailed_path

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

    graph, individuals_data = build_family_graph(gedcom_file)

    if person_id_env not in individuals_data:
        print(f"Error: PERSONID '{person_id_env}' not found in the GEDCOM file.")
        sys.exit(1)

    start_person_name = get_person_name(individuals_data[person_id_env])
    distances = calculate_distances(graph, person_id_env)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Distances from {start_person_name} ({person_id_env}):\n\n")
        for indi_id, dist in sorted(distances.items(), key=lambda item: item[1]):
            if dist != -1:
                person_name = get_person_name(individuals_data[indi_id])
                f.write(f"{person_name} ({indi_id}): {dist}\n")
                if dist > LOG_ALL_PATHS_DISTANCE_THRESHOLD:
                    path_details = find_path_with_details(graph, individuals_data, person_id_env, indi_id)
                    if path_details:
                        f.write("    Route:\n")
                        for i, person in enumerate(path_details):
                            date_info = ""
                            if person["birth_date"] or person["death_date"]:
                                date_info = f" (B: {person['birth_date'] if person['birth_date'] else 'N/A'}, D: {person['death_date'] if person['death_date'] else 'N/A'})"
                            f.write(f"        {i+1}. {person['name']} ({person['id']}){date_info}\n")
                    else:
                        f.write("    Route: Not found\n")
    print(f"Distances calculated and saved to {output_file}")
