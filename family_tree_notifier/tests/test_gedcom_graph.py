import unittest
import os
from family_tree_notifier.gedcom_graph import build_graph, distance_and_path, get_path_category

class TestGedcomGraph(unittest.TestCase):

    def setUp(self):
        # Create a dummy GEDCOM file for testing
        # Structure:
        # I1 (H) + I2 (W) -> I3 (C)
        # I3 (H) + I4 (W) -> (No child)
        # I5 (Disconnected)
        with open("test.ged", "w") as f:
            f.write("0 @I1@ INDI\n")
            f.write("1 NAME John /Doe/\n")
            f.write("0 @I2@ INDI\n")
            f.write("1 NAME Jane /Doe/\n")
            f.write("0 @I3@ INDI\n")
            f.write("1 NAME Peter /Doe/\n")
            f.write("0 @I4@ INDI\n")
            f.write("1 NAME Mary /Doe/\n")
            f.write("0 @I5@ INDI\n")
            f.write("1 NAME Disconnected /Person/\n")
            f.write("0 @F1@ FAM\n")
            f.write("1 HUSB @I1@\n")
            f.write("1 WIFE @I2@\n")
            f.write("1 CHIL @I3@\n")
            f.write("0 @F2@ FAM\n")
            f.write("1 HUSB @I3@\n")
            f.write("1 WIFE @I4@\n")

        self.graph, self.di_graph, self.indi = build_graph("test.ged")

    def tearDown(self):
        if os.path.exists("test.ged"):
            os.remove("test.ged")

    def test_distance_and_path_direct_connection(self):
        # Test path between husband and wife
        dist, path = distance_and_path(self.graph, "@I1@", "@I2@")
        self.assertEqual(dist, 1)
        self.assertEqual(path, ["@I1@", "@I2@"])

    def test_distance_and_path_parent_child(self):
        # Test path between parent and child
        dist, path = distance_and_path(self.graph, "@I1@", "@I3@")
        self.assertEqual(dist, 1)
        self.assertEqual(path, ["@I1@", "@I3@"])

    def test_distance_and_path_indirect_connection(self):
        # Test path between father and son's wife
        dist, path = distance_and_path(self.graph, "@I1@", "@I4@")
        self.assertEqual(dist, 2)
        self.assertEqual(path, ["@I1@", "@I3@", "@I4@"])

    def test_distance_and_path_no_path(self):
        # Test path between two disconnected individuals
        dist, path = distance_and_path(self.graph, "@I1@", "@I5@")
        self.assertIsNone(dist)
        self.assertEqual(path, [])

    def test_get_path_category_direct(self):
        # I1 -> I3 is direct (parent to child)
        _, path = distance_and_path(self.graph, "@I1@", "@I3@")
        category = get_path_category(self.graph, self.di_graph, path)
        self.assertEqual(category, 'direct')

        # I3 -> I1 is direct (child to parent)
        _, path = distance_and_path(self.graph, "@I3@", "@I1@")
        category = get_path_category(self.graph, self.di_graph, path)
        self.assertEqual(category, 'direct')

    def test_get_path_category_marriage(self):
        # I1 -> I2 is marriage (husband and wife)
        _, path = distance_and_path(self.graph, "@I1@", "@I2@")
        category = get_path_category(self.graph, self.di_graph, path)
        self.assertEqual(category, 'marriage')

        # I1 -> I4 is marriage (father to son's wife)
        # Path: I1 -> I3 -> I4
        _, path = distance_and_path(self.graph, "@I1@", "@I4@")
        category = get_path_category(self.graph, self.di_graph, path)
        self.assertEqual(category, 'marriage')

    def test_get_path_category_blood(self):
        # Add a sibling for I3
        with open("test_blood.ged", "w") as f:
            f.write("0 @I1@ INDI\n")
            f.write("1 NAME John /Doe/\n")
            f.write("0 @I2@ INDI\n")
            f.write("1 NAME Jane /Doe/\n")
            f.write("0 @I3@ INDI\n")
            f.write("1 NAME Peter /Doe/\n")
            f.write("0 @I6@ INDI\n")
            f.write("1 NAME Sibling /Doe/\n")
            f.write("0 @F1@ FAM\n")
            f.write("1 HUSB @I1@\n")
            f.write("1 WIFE @I2@\n")
            f.write("1 CHIL @I3@\n")
            f.write("1 CHIL @I6@\n")

        g, dg, _ = build_graph("test_blood.ged")
        # I3 -> I1 -> I6 is blood (siblings)
        _, path = distance_and_path(g, "@I3@", "@I6@")
        category = get_path_category(g, dg, path)
        self.assertEqual(category, 'blood')
        if os.path.exists("test_blood.ged"):
            os.remove("test_blood.ged")

    def test_distance_and_path_node_not_found(self):
        # Test path with a non-existent person
        dist, path = distance_and_path(self.graph, "@I1@", "@I6@")
        self.assertIsNone(dist)
        self.assertEqual(path, [])

if __name__ == '__main__':
    unittest.main()
