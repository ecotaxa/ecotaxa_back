# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List

# noinspection PyPackageRequirements
from sqlalchemy import Index, Column, Sequence, func
# noinspection PyPackageRequirements
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER, CHAR, TIMESTAMP
# noinspection PyPackageRequirements,PyProtectedMember
from sqlalchemy.engine import ResultProxy
# noinspection PyPackageRequirements
from sqlalchemy.orm import Session

from db.Model import Model


class Taxonomy(Model):
    __tablename__ = 'taxonomy'
    id = Column(INTEGER, Sequence('seq_taxonomy'), primary_key=True)
    parent_id = Column(INTEGER)
    name = Column(VARCHAR(100), nullable=False)
    id_source = Column(VARCHAR(20))
    taxotype = Column(CHAR(1), nullable=False, server_default='P')  # P = Phylo , M = Morpho
    display_name = Column(VARCHAR(200))
    lastupdate_datetime = Column(TIMESTAMP(precision=0))
    id_instance = Column(INTEGER)
    taxostatus = Column(CHAR(1), nullable=False, server_default='A')
    rename_to = Column(INTEGER)
    source_url = Column(VARCHAR(200))
    source_desc = Column(VARCHAR(1000))
    creator_email = Column(VARCHAR(255))
    creation_datetime = Column(TIMESTAMP(precision=0))
    nbrobj = Column(INTEGER)
    nbrobjcum = Column(INTEGER)

    def __str__(self):
        return "{0} ({1})".format(self.name, self.id)

    @staticmethod
    def find_ids(session: Session, classif_id_seen: List):
        """
            Return input IDs for the existing ones.
        """
        res: ResultProxy = session.execute(
            "SELECT id "
            "  FROM taxonomy "
            " WHERE id = ANY (:een)",
            {"een": list(classif_id_seen)})
        return {int(r['id']) for r in res}

    @staticmethod
    def resolve_taxa(session: Session, taxo_found, taxon_lower_list):
        """
            Match taxa in taxon_lower_list and return the matched ones in taxo_found.
        """
        res: ResultProxy = session.execute(
            """SELECT t.id, lower(t.name) AS name, lower(t.display_name) AS display_name, 
                      lower(t.name)||'<'||lower(p.name) AS computedchevronname 
                FROM taxonomy t
                LEFT JOIN taxonomy p on t.parent_id = p.id
                WHERE lower(t.name) = ANY(:nms) OR lower(t.display_name) = ANY(:dms) 
                    OR lower(t.name)||'<'||lower(p.name) = ANY(:chv) """,
            {"nms": taxon_lower_list, "dms": taxon_lower_list, "chv": taxon_lower_list})
        for rec_taxon in res:
            for found_k, found_v in taxo_found.items():
                if ((found_k == rec_taxon['name'])
                        or (found_k == rec_taxon['display_name'])
                        or (found_k == rec_taxon['computedchevronname'])
                        or (('alterdisplayname' in found_v) and (
                                found_v['alterdisplayname'] == rec_taxon['display_name']))):
                    taxo_found[found_k]['nbr'] += 1
                taxo_found[found_k]['id'] = rec_taxon['id']


Index('IS_TaxonomyParent', Taxonomy.parent_id)
Index('IS_TaxonomySource', Taxonomy.id_source)
Index('IS_TaxonomyNameLow', func.lower(Taxonomy.name))
Index('IS_TaxonomyDispNameLow',
      func.lower(Taxonomy.display_name))  # create index IS_TaxonomyDispNameLow on taxonomy(lower(display_name));
