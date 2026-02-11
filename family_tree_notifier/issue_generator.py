from datetime import timedelta
from gedcom.parser import Parser
from .localization import get_translation

def get_relationship(p1_id, p2_id, parser: Parser, lang="he"):
    """
    Determines the direct relationship between two individuals in the family tree.

    This function checks for parent-child, child-parent, and spousal relationships
    by examining the family (`FAM`) records associated with each individual.

    Args:
        p1_id (str): The GEDCOM pointer ID of the first person.
        p2_id (str): The GEDCOM pointer ID of the second person.
        parser (Parser): The initialized GEDCOM parser instance containing the
                         parsed family tree.

    Returns:
        str: A string describing the relationship (e.g., "husband (of)",
             "father (of)", "son (of)", "relative"). Returns
             "unknown/non-individual" if one of the IDs is not a valid
             individual.
    """
    # Helper to find a specific sub-element (like FAMC) by tag
    def find_sub_element(element, tag):
        for child in element.get_child_elements():
            if child.get_tag() == tag:
                return child
        return None

    def get_husband_and_wife_ids(family):
        husband_id = None
        wife_id = None
        for child in family.get_child_elements():
            if child.get_tag() == 'HUSB':
                husband_id = child.get_value()
            elif child.get_tag() == 'WIFE':
                wife_id = child.get_value()
        return husband_id, wife_id

    # Get the individual elements
    try:
        p1 = parser.get_element_dictionary()[p1_id]
        p2 = parser.get_element_dictionary()[p2_id]
    except KeyError:
        return "unknown/non-individual"

    # --- Check 1: Spouses ---
    p1_families_as_spouse = parser.get_families(p1)
    for family in p1_families_as_spouse:
        husband_id, wife_id = get_husband_and_wife_ids(family)
        if husband_id and wife_id:
            if (p1.get_pointer() == husband_id and p2.get_pointer() == wife_id) or \
               (p1.get_pointer() == wife_id and p2.get_pointer() == husband_id):
                if p1.get_gender() == "M":
                    return get_translation(lang, "husband_of")
                else:
                    return get_translation(lang, "wife_of")

    # --- Check 2: p1 is Parent of p2 (Look up p2's FAMC) ---
    p2_famc_element = find_sub_element(p2, 'FAMC')
    if p2_famc_element:
        famc_id = p2_famc_element.get_value()
        p2_child_family = parser.get_element_dictionary().get(famc_id)

        if p2_child_family:
            husband_id, wife_id = get_husband_and_wife_ids(p2_child_family)

            if husband_id and p1.get_pointer() == husband_id:
                return get_translation(lang, "father_of")
            if wife_id and p1.get_pointer() == wife_id:
                return get_translation(lang, "mother_of")

    # --- Check 3: p2 is Parent of p1 (Look up p1's FAMC) ---
    p1_famc_element = find_sub_element(p1, 'FAMC')
    if p1_famc_element:
        famc_id = p1_famc_element.get_value()
        p1_child_family = parser.get_element_dictionary().get(famc_id)

        if p1_child_family:
            husband_id, wife_id = get_husband_and_wife_ids(p1_child_family)

            if (husband_id and p2.get_pointer() == husband_id) or \
               (wife_id and p2.get_pointer() == wife_id):
                if p1.get_gender() == "M":
                    return get_translation(lang, "son_of")
                else:
                    return get_translation(lang, "daughter_of")

    return get_translation(lang, "relative")

def build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, family_details, lang="he"):
    """
    Constructs the Markdown body for the GitHub issue.

    This function formats a list of upcoming events into a human-readable
    Markdown string. It includes emojis, age calculations, and the genealogical
    path from the `PERSONID` if the distance exceeds the threshold.

    Args:
        enriched_list (list): A list of tuples, where each tuple contains event
                              details: (distance, path, gregorian_date,
                              heb_date_str, name, event_type).
        id2name (dict): A dictionary mapping GEDCOM pointers to display names.
        today_gregorian (date): The current date, for the issue header.
        distance_threshold (int): The distance beyond which the genealogical path
                                  should be displayed.
        person_id (str): The GEDCOM pointer ID of the person from whom distances
                         are calculated.
        parser (Parser): The initialized GEDCOM parser instance.
        individual_details (dict): A dictionary with birth/death years for age calculation.
        family_details (dict): A dictionary with marriage years for anniversary calculation.

    Returns:
        str: The formatted Markdown string for the GitHub issue body.
    """
    issue_body = (
        f"## {get_translation(lang, 'upcoming_hebrew_dates')} "
        f"({today_gregorian.strftime('%Y-%m-%d')} - "
        f"{(today_gregorian + timedelta(days=7)).strftime('%Y-%m-%d')})\n\n"
    )

    # sort by date (closest first), then by distance
    enriched_list.sort(key=lambda t: (t[2], t[0]))

    for dist, path, gregorian_date, original_date_str_parsed, name, event_type in enriched_list:
        hebrew_weekday = get_translation(lang, gregorian_date.strftime('%A').lower())
        event_name = get_translation(lang, event_type.lower())

        # --- Emojis and Age ---
        emoji = ""
        age_str = ""
        if event_type == "BIRT":
            details = individual_details.get(name, {})
            birth_year = details.get("birth_year")
            death_year = details.get("death_year")
            gender = details.get("gender", "M")

            if death_year and birth_year:
                # Deceased person's birthday
                emoji = "🕯️"
                age_at_death = death_year - birth_year
                years_since_birth = gregorian_date.year - birth_year
                key = "deceased_birthday_age_details_female" if gender == "F" else "deceased_birthday_age_details_male"
                age_str = get_translation(lang, key, age_at_death=age_at_death, years_since_birth=years_since_birth)
            elif birth_year:
                # Living person's birthday
                emoji = "🎂"
                age = gregorian_date.year - birth_year
                age_str = get_translation(lang, "birthday_age", age=age)
            else:
                # Birthday event, but no birth year data
                emoji = "🎂"

        elif event_type == "DEAT":
            emoji = "🪦"
            details = individual_details.get(name, {})
            birth_year = details.get("birth_year")
            death_year = details.get("death_year")
            gender = details.get("gender", "M")

            if death_year:
                years_since_death = gregorian_date.year - death_year
                if birth_year:
                    age_at_death = death_year - birth_year
                    key = "yahrzeit_age_details_female" if gender == "F" else "yahrzeit_age_details_male"
                    age_str = get_translation(lang, key, age_at_death=age_at_death, years_since_death=years_since_death)
                else:
                    key = "yahrzeit_years_only_female" if gender == "F" else "yahrzeit_years_only_male"
                    age_str = get_translation(lang, key, years_since_death=years_since_death)
        elif event_type == "MARR":
            emoji = "💑"
            family_info = family_details.get(name, {})
            marriage_year = family_info.get("marriage_year")
            divorce_year = family_info.get("divorce_year")
            husband_death_year = family_info.get("husband_death_year")
            wife_death_year = family_info.get("wife_death_year")

            if marriage_year:
                if divorce_year:
                    age_str = get_translation(lang, "anniversary_divorced", marriage_year=marriage_year)
                elif husband_death_year or wife_death_year:
                    first_death_year = min(filter(None, [husband_death_year, wife_death_year]))
                    if first_death_year >= marriage_year:
                        marriage_duration = first_death_year - marriage_year
                        age_str = get_translation(lang, "anniversary_deceased", marriage_duration=marriage_duration)
                else:
                    years_married = gregorian_date.year - marriage_year
                    age_str = get_translation(lang, "anniversary_married", years_married=years_married)

        issue_body += get_translation(lang, "event_header", emoji=emoji, hebrew_weekday=hebrew_weekday, original_date_str_parsed=original_date_str_parsed)
        issue_body += get_translation(lang, "event_type_label", event_name=event_name)
        issue_body += get_translation(lang, "person_family_label", name=name, age_str=age_str)

        if person_id and dist is not None and dist > distance_threshold and path:
            path_parts = []
            reversed_path = list(reversed(path))
            for i in range(len(reversed_path) - 1):
                p1_id = reversed_path[i]
                p2_id = reversed_path[i+1]
                p1_name = id2name.get(p1_id, p1_id)
                relationship = get_relationship(p1_id, p2_id, parser, lang)
                path_parts.append(f"{p1_name} ({relationship})")

            path_parts.append(id2name.get(reversed_path[-1], reversed_path[-1]))
            readable_path = " ".join(path_parts)
            issue_body += get_translation(lang, "distance_label", dist=dist)
            issue_body += get_translation(lang, "path_label", readable_path=readable_path)
        issue_body += "\n"

    return issue_body
