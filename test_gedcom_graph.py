import unittest
from gedcom_graph import build_graph, distance_and_path

class TestGedcomGraph(unittest.TestCase):

    def setUp(self):
        # Create a dummy GEDCOM file for testing
        with open("test.ged", "w") as f:
            f.write("0 @I1@ INDI\n")
            f.write("1 NAME John /Doe/\n")
            f.write("0 @I2@ INDI\n")
            f.write("1 NAME Jane /Doe/\n")
            f.write("0 @I3@ INDI\n")
            f.write("1 NAME Peter /Doe/\n")
            f.write("0 @I4@ INDI\n")
            f.write("1 NAME Mary /Doe/\n")
            f.write("0 @F1@ FAM\n")
            f.write("1 HUSB @I1@\n")
            f.write("1 WIFE @I2@\n")
            f.write("1 CHIL @I3@\n")
            f.write("0 @F2@ FAM\n")
            f.write("1 HUSB @I3@\n")
            f.write("1 WIFE @I4@\n")

        self.graph, self.indi = build_graph("test.ged")

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
        # Add a new person to the graph without any connections
        self.graph.add_node("@I5@", name="Disconnected Person")
        dist, path = distance_and_path(self.graph, "@I1@", "@I5@")
        self.assertIsNone(dist)
        self.assertEqual(path, [])

    def test_distance_and_path_node_not_found(self):
        # Test path with a non-existent person
        dist, path = distance_and_path(self.graph, "@I1@", "@I6@")
        self.assertIsNone(dist)
        self.assertEqual(path, [])

if __name__ == '__main__':
    unittest.main()
