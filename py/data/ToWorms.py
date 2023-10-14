# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Matching of present, as of March 2021, UNIEUK-based taxonomy system, to Worms one
#
# Rules:
#     If deprecate then the proposed alternative is final_aphia_id
#
# We cannot eliminate an ecotaxa subtree if there are objects attached to the root, as the semantic in this case is
# "could be anything in the subtree". -> we cannot eliminate anything...
#
# When deprecated, the 'advised' destination is final_aphia_id
#
# TODO: Any child of a deprecated taxon, having an homonym in the deprecation target taxon,
#       becomes deprecated itself.
#
from os.path import dirname, realpath, join
from typing import Tuple, Iterable, Dict, List, Optional, Any, Union

import openpyxl
from openpyxl import Workbook
from openpyxl.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet
from typing_extensions import ParamSpec

from API_operations.TaxonomyService import TaxonomyService
from BO.Classification import ClassifIDT, ClassifIDListT
from BO.Taxonomy import TaxonBO, StrictWoRMSSetFromTaxaSet
from data.structs.TaxaTree import TaxaTree

P = ParamSpec("P")

XLSX = "Correspondance WoRMS.xlsx"
TABS = [
    "Cas 1a",
    "Cas 2a",
    "Cas 3a",
    "Cas 4a",
    "Cas 1b",
    "Cas 2b",
    "Cas 3b",
    "Cas 4b",
    "Cas 1c",
    "Cas 2c",
    "Cas 3c",
    "Cas 4c",
    "Cas 1d",
    "Cas 1e",
    "Cas 2e",
    "Cas 3e",
    "Cas 4e",
    "Cas 1f",
    "Cas 1g",
]
HERE = dirname(realpath(__file__))
ECOTAXOSERVER_URL = "http://ecotaxoserver.obs-vlfr.fr/browsetaxo/"
WORMS_URL = "http://www.marinespecies.org/aphia.php?p=taxdetails"


class Action(object):  # class action :)
    """
    The actions to do on an EcoTaxa category, from XLSX file.
    """

    def __init__(self, eco_id: int, cell_coords: str):
        # The impacted category id
        self.eco_id = eco_id
        # Where the cell is referenced
        self.coords = cell_coords
        # Present state actions
        self.deprecated: bool = False
        self.make_morpho: bool = False
        self.eco_parent: Optional[str] = None
        self.new_name: Optional[str] = None
        # WoRMS actions
        self.link_with_aphia_id: Optional[int] = None
        self.text: Optional[str] = None
        # Anything...
        self.worms_parent_id: Optional[int] = None

    def add_cell(self, cell_str: str) -> None:
        self.coords += cell_str

    def worms_parent_is(self, parent_aphia_id: int) -> None:
        assert self.worms_parent_id is None
        self.worms_parent_id = parent_aphia_id

    # def exotaxa_parent_is(self, ecotaxa_parent_name):
    #     assert len(ecotaxa_parent_name) > 0
    #     self.eco_parent = ecotaxa_parent_name

    def turn_to_morpho(self) -> None:
        assert not self.make_morpho
        self.make_morpho = True

    def deprecate(self) -> None:
        self.deprecated = True

    def dont_deprecate(self) -> None:
        if self.deprecated:
            print("%s deprecated or not?" % self.coords)

    def rename_to(self, new_val: str) -> None:
        assert self.new_name is None
        self.new_name = new_val

    def dont_rename(self) -> None:
        assert self.new_name is None

    def set_free_action(self, action: str) -> None:
        assert not self.text
        self.text = action

    def set_target_worms(self, aphia_id: ClassifIDT) -> None:
        if self.link_with_aphia_id is not None and self.link_with_aphia_id != aphia_id:
            print(
                "In %s: %d -> %d or %d -> %d ?"
                % (
                    self.coords,
                    self.eco_id,
                    self.link_with_aphia_id,
                    self.eco_id,
                    aphia_id,
                )
            )
        self.link_with_aphia_id = aphia_id

    def something_to_do(self) -> bool:
        return (
            self.link_with_aphia_id is not None
            or self.eco_parent is not None
            or self.worms_parent_id is not None
            or self.make_morpho
            or self.deprecated
            or self.new_name is not None
            or self.text is not None
        )

    def manual_action(self) -> bool:
        """ """
        return (
            self.link_with_aphia_id is None
            and self.eco_parent is None
            and self.worms_parent_id is None
            and not self.make_morpho
            and not self.deprecated
            and self.new_name is None
            and self.text is not None
        )

    def __str__(self) -> str:
        ret = ""
        if self.make_morpho:
            ret += "->'M'"
        if self.deprecated:
            ret += "->Dep"
        if self.link_with_aphia_id is not None:
            # noinspection PyStringFormat
            ret += " ->%d" % self.link_with_aphia_id
        if self.worms_parent_id is not None:
            # noinspection PyStringFormat
            ret += " -P>%d" % self.worms_parent_id
        if self.eco_parent is not None:
            ret += " -P>%s" % self.eco_parent
        if self.text is not None:
            ret += " TODO:%s" % self.text
        return ret

    def something_to_do_on_present(self) -> bool:
        return self.make_morpho or self.deprecated or self.eco_parent is not None

    def to_do_on_present(self) -> str:
        ret = []
        if self.make_morpho:
            ret.append("make morpho")
        if self.deprecated:
            ret.append("deprecate")
        if self.eco_parent:
            ret.append("set parent to '%s'" % self.eco_parent)
        if self.new_name:
            ret.append("rename to '%s'" % self.new_name)
        return ", ".join(ret)

    def invalid_reason(self) -> Optional[str]:
        if self.deprecated and self.link_with_aphia_id is None:
            # Deprecated OK but in favor of something else
            return "deprecated with no replacement"
        if self.deprecated and self.make_morpho:
            # We only deprecate Phylo in favor of something in WoRMS
            return "deprecated but Morpho"
        if self.make_morpho and self.link_with_aphia_id is not None:
            # Morpho type do not map to worms
            return "morpho with final_aphia_id"
        if self.worms_parent_id is not None and self.link_with_aphia_id is not None:
            # Cannot change both self and parent
            return "two branchings"
        return None

    def not_mapped_to_worms(self) -> bool:
        return self.link_with_aphia_id is None and self.worms_parent_id is None

    def possible_aphia_ids(self) -> List[int]:
        return [
            an_id
            for an_id in (self.link_with_aphia_id, self.worms_parent_id)
            if an_id is not None
        ]


class ToWorms(object):
    """
    Read the XLSX data source and map IDs.
    """

    def __init__(self) -> None:
        # Taxo data source
        self.ignored_cells: List[str] = []
        # The actions, per eco_id
        self.actions: Dict[int, Action] = {}
        xlsx_path = join(HERE, XLSX)
        workbook: Workbook = openpyxl.load_workbook(xlsx_path, read_only=True)
        for a_tab in TABS:
            self.analyze(workbook[a_tab])
        # The source (present) taxa
        self.unieuk: Dict[int, TaxonBO] = {}  # TODO: Should be in the TaxaTree
        self.unieuk_tree: TaxaTree = TaxaTree(0, "root")
        # The target worms taxa
        self.worms: Dict[int, TaxonBO] = {}  # TODO: Should be in the TaxaTree
        self.worms_tree: TaxaTree = TaxaTree(0, "worms")
        # The link b/w the two trees
        self.done_remaps: Dict[ClassifIDT, Optional[ClassifIDT]] = {}

    def pre_validate(self) -> List[str]:
        """
        Validate the actions, regardless of any context.
        """
        # Local validation
        ret: List[str] = []
        for an_id, an_action in self.actions.items():
            invalid_reason = an_action.invalid_reason()
            if invalid_reason:
                ret.append(
                    "Invalid action in %s: (%s) %s"
                    % (an_action.coords, invalid_reason, str(an_action))
                )
        return ret

    def prepare(self) -> None:
        """
        Scan the actions and prepare the application. Build in-memory trees (origin, destination).
        """
        with TaxonomyService() as taxo_sce:
            all_eco_ids = list(self.actions.keys())
            # for an_eco_id in all_eco_ids:
            #     orig = sce.query(an_eco_id)
            #     assert orig is not None, "%d doesn't exist?" % an_eco_id
            #     print(orig.lineage)
            self.add_to_unieuk(all_eco_ids, taxo_sce)
            # # Commented out for tests
            # assert len(self.unieuk_tree.children) <= 3

            # Gather all potential targets, as node aphia_id or parent aphia_id
            target_or_parents = [
                an_action.link_with_aphia_id
                for an_action in self.actions.values()
                if an_action.link_with_aphia_id is not None
            ]
            target_or_parents.extend(
                [
                    an_action.worms_parent_id
                    for an_action in self.actions.values()
                    if an_action.worms_parent_id is not None
                ]
            )
            target_or_parents = list(set(target_or_parents))
            worms_taxo_infos: List[TaxonBO] = taxo_sce.query_worms_set(
                target_or_parents
            )
            worms_aphia_ids = set([a_taxon.id for a_taxon in worms_taxo_infos])
            # # Commented out for tests
            # assert len(worms_taxo_infos) == len(target_or_parents), "%s missing or extra" % str(
            #     set(target_or_parents).difference(worms_aphia_ids))
            for an_info in worms_taxo_infos:
                # print("W: %d -> %s %s" % (an_info.id, an_info.lineage, len(an_info.children) == 0))
                self.worms[an_info.id] = an_info
                self.worms_tree.add_path(list(zip(an_info.id_lineage, an_info.lineage)))

    def add_to_unieuk(self, eco_ids: ClassifIDListT, taxo_sce: TaxonomyService) -> None:
        # Add taxo from IDs, if they are not there already
        missing_eco_ids = [an_id for an_id in eco_ids if an_id not in self.unieuk]
        ecotaxa_taxo_infos: List[TaxonBO] = taxo_sce.query_set(missing_eco_ids)
        # assert len(ecotaxa_taxo_infos) == len(all_eco_ids), "Some categories don't resolve"
        for an_info in ecotaxa_taxo_infos:
            self.unieuk[an_info.id] = an_info
            self.unieuk_tree.add_path(list(zip(an_info.id_lineage, an_info.lineage)))
            self.unieuk_tree.find_node(an_info.id).add_to_node(an_info.nb_objects)
            # print("E: %d -> %s %s" % (an_info.id, an_info.lineage, len(an_info.children) == 0))

    def add_to_unieuk_with_lineage(
        self, eco_ids: ClassifIDListT, taxo_sce: TaxonomyService
    ) -> None:
        """Add taxo from IDs, if not there, with their lineage"""
        self.add_to_unieuk(eco_ids, taxo_sce)
        needed_parents = []
        for an_id in eco_ids:
            for a_parent_id in self.unieuk[an_id].id_lineage:
                if a_parent_id not in self.unieuk:
                    needed_parents.append(a_parent_id)
        self.add_to_unieuk(needed_parents, taxo_sce)

    def validate_with_trees(self) -> None:
        # It's dubious if a terminal (leaf) maps to a non-terminal
        for an_id, an_action in self.actions.items():
            if an_id not in self.unieuk:
                # TODO
                continue
            ecotaxa_taxo_info = self.unieuk[an_id]
            if an_action.link_with_aphia_id is not None:
                if an_action.link_with_aphia_id not in self.worms:
                    # TODO
                    continue
                worms_taxo_info = self.worms[an_action.link_with_aphia_id]
                if len(ecotaxa_taxo_info.children) != len(worms_taxo_info.children):
                    # TODO: review here
                    pass
                    # print("Problem: for %d -> %d EcoTaxa: %d WoRMS: %d" % (an_id, an_action.link_with_aphia_id,
                    #                                                        len(ecotaxa_taxo_info.children),
                    #                                                        len(worms_taxo_info.children)))

        # No rename to same name as final aphia
        for an_id, an_action in self.actions.items():
            if (
                an_action.new_name is not None
                and an_action.link_with_aphia_id is not None
            ):
                if an_action.link_with_aphia_id not in self.worms:
                    # TODO
                    continue
                worms_taxo_info = self.worms[an_action.link_with_aphia_id]
                if worms_taxo_info.name.lower() == an_action.new_name.lower():
                    print("Redundant rename in %s", an_action.coords)

    def show_stats(self) -> None:
        print("Ignored cells: %s", str(self.ignored_cells))
        # morpho_ids = ",".join([str(an_action.eco_id)
        #                        for an_action in self.actions.values()
        #                        if an_action.make_morpho]
        #                       )
        # morhpo_sql = "update taxonomy set taxotype='M' where id in (" + morpho_ids + ")"
        # print("To morpho:%s" % morhpo_sql)
        to_do = [
            an_action
            for an_action in self.actions.values()
            if an_action.something_to_do()
        ]
        print("%d actions to do on existing entries" % len(to_do))
        text_actions = [
            "On %d, '%s'" % (an_action.eco_id, an_action.text)
            for an_action in self.actions.values()
            if an_action.manual_action()
        ]
        print("To do manually\n" + "\n".join(text_actions))
        print("Source tree size: %d" % self.unieuk_tree.size())
        print("WoRMS tree size: %d" % self.worms_tree.size())

    def print_trees(self) -> None:
        self.worms_tree.print()
        # self.eco_tree.print()

    def apply(self) -> None:
        """
        Apply the actions onto present tree.
        We go through the tree top-down, i.e. highest-level taxa first.
        """
        for a_node in self.unieuk_tree.top_to_bottom_ite():
            try:
                an_info = self.unieuk[a_node.id]
            except KeyError:
                continue
            eco_id = an_info.id
            action = self.actions[eco_id]
            # print(action.coords, eco_id, an_info.top_down_lineage())
            # Actions on present state
            if action.something_to_do_on_present():
                # TODO. Lol
                pass
                # print("    ", action.to_do_on_present())
            target_info = None
            # Actions related to WoRMS
            if action.link_with_aphia_id is not None:
                try:
                    target_info = self.worms[action.link_with_aphia_id]
                except KeyError:  # For tests
                    continue
                # print("    -W>", target_info.top_down_lineage(":"))
                # if action.worms_parent_id is not None:
                #     target_info = self.worms[action.worms_parent_id]
                #     print("    -P>", target_info.top_down_lineage(":"))
            if action.worms_parent_id is not None:
                try:
                    target_info = self.worms[action.worms_parent_id]
                except KeyError:  # For tests
                    continue
                if an_info.id != 11226:  # Holodinophyta
                    assert (
                        an_info.type == "M" or action.make_morpho
                    ), "Not Morpho: %d %s" % (an_info.id, str(an_info.lineage))
                # print("    -W>", target_info.top_down_lineage(":"))
                # if action.worms_parent_id is not None:
                #     target_info = self.worms[action.worms_parent_id]
                #     print("    -P>", target_info.top_down_lineage(":"))

            self.done_remaps[an_info.id] = None
            if target_info:
                target = self.worms_tree.find_node(target_info.id)
                target.add_to_node(an_info.nb_objects)
                self.done_remaps[an_info.id] = target_info.id

    def check_ancestors(self) -> None:
        # The first non-morpho parent should have the same corresponding WoRMS
        for an_unieuk_id, a_worms_id in self.done_remaps.items():
            if a_worms_id is None:
                continue
            an_info = self.unieuk[an_unieuk_id]
            target_info = self.worms[a_worms_id]
            node = self.unieuk_tree.find_node(an_info.id)
            for a_parent in node.parents_ite():
                # Climb the tree
                parent_id = a_parent.id
                if parent_id not in self.unieuk:
                    # Intermediate node from fetched lineage
                    continue
                if self.unieuk[parent_id].type == "M":
                    pass
                else:
                    if parent_id not in self.actions:
                        continue
                    # There can be a full Morpho chain, e.g. starting from temporary at the root,
                    # the code below is not reached then
                    parent_action = self.actions[parent_id]
                    possible_aphia_ids = parent_action.possible_aphia_ids()
                    possible_aphia_names = [
                        self.worms[aphia_id].name for aphia_id in possible_aphia_ids
                    ]
                    if an_info.id not in (
                        85234,  # Branch change
                        85213,  # Branch change
                    ):
                        if target_info.id not in possible_aphia_ids:
                            print(
                                "for eco %s(%d), target %s(%d) not in %s %s"
                                % (
                                    an_info.name,
                                    an_info.id,
                                    target_info.name,
                                    target_info.id,
                                    possible_aphia_ids,
                                    possible_aphia_names,
                                )
                            )
                    break

    def check_closure(self) -> None:
        # Check that we do not damage the origin hierarchy,
        # i.e. A -> B in present situation and B' -> A' in target
        closure = set(self.worms_tree.closure())
        missing_parents = set()
        for an_eco_id, a_worms_id in self.done_remaps.items():
            if a_worms_id is None:
                continue
            for a_parent in self.unieuk_tree.find_node(an_eco_id).parents_ite():
                if a_parent.id == 0:
                    break
                if a_parent.nb_objects == 0:
                    continue
                if a_parent.id not in self.done_remaps:
                    # print("Parent %d not remapped yet" % a_parent.id)
                    missing_parents.add(a_parent.id)
                    continue
                remap_id_for_parent = self.done_remaps[a_parent.id]
                if remap_id_for_parent is None:
                    continue
                edge = (remap_id_for_parent, a_worms_id)
                if edge not in closure:
                    if remap_id_for_parent != a_worms_id:
                        pass
                        # print("For %d, %s not in closure" % (an_eco_id, str(edge)))
                else:
                    pass
                    # print("*", end="")
                reverse_edge = (a_worms_id, remap_id_for_parent)
                if reverse_edge in closure:
                    print("For %d, %s REVERSE in closure" % (an_eco_id, str(edge)))

        if len(missing_parents) > 0:
            print("Missing parents: %s" % str(missing_parents))

    @staticmethod
    def find_in_header(
        cell_iterable: Iterable[Cell], optional: bool = False, *args: Any
    ) -> Tuple[Optional[int], ...]:
        """
        Return 0-based indices of the requested columns in the Cell list.
        """
        ret: List[Optional[int]] = []
        for a_col in args:
            for ndx, a_cell in enumerate(cell_iterable):
                if a_cell.value == a_col:
                    ret.append(ndx)
                    break
            else:
                if not optional:
                    assert False, "%s is not in cell list" % a_col
                else:
                    ret.append(None)
        return tuple(ret)

    def analyze(self, a_tab: Worksheet) -> None:
        """
        Go thru the spreadsheet and scan identifiers.
        """
        with TaxonomyService() as taxo_sce:
            tab_name = a_tab.title
            assert isinstance(tab_name, str)
            tab_iter = iter(a_tab)
            header = next(tab_iter)
            # print(tab_name)
            eco_id_col, aphia_id_col = self.find_in_header(
                header, False, "eco_id", "final_aphia_id"
            )
            assert eco_id_col is not None and aphia_id_col is not None
            (
                make_morpho_id_col,
                deprecate_col,
                rename_col,
                parent_aphia_id_col,
                parent_worms_col,
                action_col,
            ) = self.find_in_header(
                header,
                True,
                "make_morpho",
                "deprecate",
                "rename_as",
                "final_parent_aphia_id",
                "parent_aphia_name",
                "action",
            )
            a_line: List[Cell]
            for a_line in tab_iter:
                a_line = list(a_line)  # tuples are slow in random access
                line_length = len(a_line)

                if eco_id_col >= line_length:
                    continue
                eco_id_cell = a_line[eco_id_col]
                # If cell was strike-d out, ignore.
                if eco_id_cell.font is not None and eco_id_cell.font.strike is not None:
                    self.ignored_cells.append(str(eco_id_cell))
                    continue
                eco_str_id = eco_id_cell.value
                if eco_str_id is None:
                    continue
                assert isinstance(eco_str_id, str)
                # We have e.g. =HYPERLINK("http://ecotaxoserver.obs-vlfr.fr/browsetaxo/?id=93066","93066")
                assert (
                    ECOTAXOSERVER_URL in eco_str_id
                ), "Unexpected eco_id value '%s' in tab '%r'" % (eco_str_id, tab_name)
                eco_id = int(eco_str_id.split('"')[3])
                cell_str = str(eco_id_cell).replace("ReadOnlyCell ", "")

                action_for_eco_id = self.actions.get(eco_id)
                if action_for_eco_id is None:
                    action_for_eco_id = Action(eco_id, cell_str)
                    self.actions[eco_id] = action_for_eco_id
                else:
                    action_for_eco_id.add_cell(cell_str)

                if action_col is not None:
                    if a_line[action_col] is not None:
                        action_cell = a_line[action_col]
                        if action_cell is not None:
                            if action_cell.fill.bgColor.rgb != "00000000":
                                info = taxo_sce.query(eco_id)
                                assert info is not None
                                print(
                                    "Ignored actions for '%s' in %s line due to color: '%s', %d obj %d children"
                                    % (
                                        info.name,
                                        cell_str,
                                        action_cell.value,
                                        info.nb_objects,
                                        info.nb_children_objects,
                                    )
                                )
                                continue
                            else:
                                call_val = action_cell.value
                                assert call_val is None or isinstance(call_val, str)
                                action_for_eco_id.set_free_action(call_val)

                if make_morpho_id_col is not None:
                    # Switch to morpho action
                    make_morpho_opt = a_line[make_morpho_id_col]
                    if make_morpho_opt.value:
                        action_for_eco_id.turn_to_morpho()

                if deprecate_col is not None:
                    # Deprecate action
                    deprecate_opt = a_line[deprecate_col]
                    deprecate_val = deprecate_opt.value
                    assert deprecate_val in (None, "", "x"), (
                        "Unexpected deprecate %s" % deprecate_val
                    )
                    if deprecate_opt.value == "x":
                        action_for_eco_id.deprecate()
                    else:
                        action_for_eco_id.dont_deprecate()

                if rename_col is not None:
                    # Rename action
                    rename_cell = a_line[rename_col]
                    rename_val = rename_cell.value
                    if rename_val is not None:
                        assert isinstance(rename_val, str)
                        action_for_eco_id.rename_to(rename_val)
                    else:
                        action_for_eco_id.dont_rename()

                if parent_aphia_id_col is not None:
                    # Constraint to parent aphia_id
                    parent_aphia_id_str = a_line[parent_aphia_id_col].value
                    if parent_aphia_id_str is not None:
                        assert isinstance(parent_aphia_id_str, (str, int))
                        try:
                            parent_aphia_id = int(parent_aphia_id_str)
                            action_for_eco_id.worms_parent_is(parent_aphia_id)
                        except ValueError:
                            # In fact it's a parent_name
                            print("Cannot convert %s", parent_aphia_id_str)
                            # action_for_eco_id.exotaxa_parent_is(parent_aphia_id_str)

                if aphia_id_col >= line_length:
                    continue
                aphia_str_id = a_line[aphia_id_col].value
                if aphia_str_id is None:
                    continue
                assert isinstance(aphia_str_id, (str, int))
                aphia_id = self.read_aphia_id_value(aphia_str_id, tab_name)
                if aphia_id is None:
                    continue

                action_for_eco_id.set_target_worms(aphia_id)

    @staticmethod
    def read_aphia_id_value(
        aphia_str_id: Union[str, int], tab_name: str
    ) -> Optional[int]:
        if isinstance(aphia_str_id, str):
            if WORMS_URL in aphia_str_id:
                aphia_id = int(aphia_str_id.split('"')[3])
            else:
                try:
                    aphia_id = int(aphia_str_id)
                except ValueError:
                    print("Not a number in %s: %s" % (tab_name, aphia_str_id))
                    aphia_id = None
        else:
            aphia_id = int(aphia_str_id)
        return aphia_id

    def check_sums(self) -> None:
        """
        Check if the trees/ignored contain the same number of objects.
        """
        nothing_to_do = set(
            [
                an_action.eco_id
                for an_action in self.actions.values()
                if an_action.not_mapped_to_worms()
            ]
        )
        not_worms_how_many: List[Tuple[int, int, str]] = [
            (a_present.id, a_present.nb_objects, a_present.name)
            for a_present in self.unieuk.values()
            if a_present.id in nothing_to_do
        ]
        not_worms_how_many.sort(key=lambda elem: -elem[1])
        not_worms_objs = sum([not_worms[1] for not_worms in not_worms_how_many])
        print("Not to WoRMS: %s" % str(not_worms_how_many))
        eco_sum = self.unieuk_tree.nb_objects
        worms_sum = self.worms_tree.nb_objects
        print(
            "From %d validated objects in %d categories, to WoRMS: %d, not to WoRMS: %s"
            % (eco_sum, len(self.unieuk), worms_sum, not_worms_objs)
        )
        # Fails. TODO
        # assert worms_sum + not_worms_objs == eco_sum

    def old_way(self) -> None:
        """
        Mapping the old way, for stats.
        """
        with TaxonomyService() as taxo_sce:
            eco_tree = TaxaTree(0, "root")
            all_eco_ids = list(self.unieuk.keys())
            ecotaxa_taxo_infos: List[TaxonBO] = taxo_sce.query_set(all_eco_ids)
            assert len(ecotaxa_taxo_infos) == len(
                all_eco_ids
            ), "In old_way, some categories don't resolve"
            for an_info in ecotaxa_taxo_infos:
                eco_tree.add_path(list(zip(an_info.id_lineage, an_info.lineage)))
                # Juste copy the number of objects, no cumulate
                eco_tree.find_node(an_info.id).nb_objects = an_info.nb_objects

            mapping = StrictWoRMSSetFromTaxaSet(taxo_sce.session, all_eco_ids).res

        worms_tree = TaxaTree(0, "worms")
        all_worms_ids = [a_worms_info.aphia_id for a_worms_info in mapping.values()]
        worms_taxo_infos: List[TaxonBO] = taxo_sce.query_worms_set(all_worms_ids)
        for an_info in worms_taxo_infos:
            worms_tree.add_path(list(zip(an_info.id_lineage, an_info.lineage)))

        for an_eco_id, a_worms in mapping.items():
            worms_tree.find_node(a_worms.aphia_id).add_to_node(
                eco_tree.find_node(an_eco_id).nb_objects
            )

        worms_sum = worms_tree.nb_objects
        print("Old-way comparison: %d" % worms_sum)
