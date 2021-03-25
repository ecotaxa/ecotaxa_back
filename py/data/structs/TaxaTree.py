# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A taxa tree.
#
from typing import Dict, Optional, Tuple, List

from BO.Classification import ClassifIDT


class TaxaTree(object):
    """
        A tree of taxa.
    """

    def __init__(self, taxo_id: ClassifIDT, name: str,
                 all_nodes: Dict[ClassifIDT, 'TaxaTree'] = None,
                 parent: Optional['TaxaTree'] = None):
        # Node identity
        self.id = taxo_id
        self.name = name
        # Tree machinery
        self.parent: Optional[TaxaTree] = parent
        self.children: Dict[ClassifIDT, TaxaTree] = {}
        self.all_nodes: Dict[ClassifIDT, TaxaTree]
        if all_nodes is None:
            self.all_nodes = {}
        else:
            self.all_nodes = all_nodes
        assert taxo_id not in self.all_nodes, "%d is already in" % taxo_id
        self.all_nodes[taxo_id] = self
        # Workload
        self.nb_objects = 0

    def add_path(self, path: List[Tuple[ClassifIDT, str]]):
        """
            Add a path into the tree. Paths are root-last.
        """
        if len(path) == 0:
            return
        child_id, child_name = path[-1]
        child = self.children.get(child_id)
        if child is None:
            child = TaxaTree(child_id, child_name, self.all_nodes, self)
            self.children[child_id] = child
        child.add_path(path[:-1])

    def size(self):
        ret = 1
        for a_child in self.children.values():
            ret += a_child.size()
        return ret

    def print(self, indent=0, with_children=True):
        print(("|  " * indent) + self.name + "(%d): %d objs" % (self.id, self.nb_objects))
        if not with_children:
            return
        for a_child in self.children.values():
            a_child.print(indent + 1)

    def __str__(self):
        return self.name + ">"

    def find_node(self, taxo_id: ClassifIDT) -> 'TaxaTree':
        return self.all_nodes[taxo_id]

    def add_to_node(self, nb_objects: int):
        self.nb_objects += nb_objects
        if self.parent is not None:
            self.parent.add_to_node(nb_objects)

    def newick(self):
        """
            https://en.wikipedia.org/wiki/Newick_format
        """
        ret = "(" + self.name
        ret += ",".join([a_child.newick() for a_child in self.children.values()])
        ret += ")"
        return ret

    def parents_ite(self):
        """
            An iterator for climbing the tree.
        """
        parent = self.parent
        while parent is not None:
            yield parent
            parent = parent.parent

    def top_to_bottom_ite(self):
        if self.parent is not None:
            yield self
        for a_child in self.children.values():
            for a_subtree in a_child.top_to_bottom_ite():
                yield a_subtree

    def closure(self):
        """
            List of edges with transitive closure.
        """
        ret = []
        if self.parent is None:
            for a_child in self.children.values():
                ret.extend(a_child.closure())
        else:
            ret.append((self.parent.id, self.id))
            for a_child in self.children.values():
                for a_closure in a_child.closure():
                    ret.append(a_closure)
                    if a_closure[0] == self.id:
                        ret.append((self.parent.id, a_closure[1]))
        return ret


def do_test_closure():
    t = TaxaTree(0, 'root')
    pathes = [[(1, 'A'), (2, 'B'), (3, 'C'), (4, 'D')],
              [(1, 'A'), (2, 'B'), (3, 'C'), (5, 'E')]]
    for a_pth in pathes:
        t.add_path(list(reversed(a_pth)))
    t.find_node(1).nb_objects = 6
    t.find_node(3).nb_objects = 6
    t.find_node(5).nb_objects = 6
    closure = t.closure()
    t.print(with_children=True)
    print(list(t.top_to_bottom_ite()))
    print(sorted(closure))


if __name__ == '__main__':
    do_test_closure()
