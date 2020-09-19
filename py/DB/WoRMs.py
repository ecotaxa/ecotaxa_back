# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy import Column, Integer, String, Boolean, DateTime, SmallInteger

from DB.helpers.ORM import Model


class WoRMS(Model):
    __tablename__ = 'worms'
    # WoRMS record @see http://www.marinespecies.org/rest/
    aphia_id = Column(Integer, primary_key=True)
    """ Unique and persistent identifier within WoRMS. Primary key in the database -- """
    url = Column(String(255))
    """ HTTP URL to the AphiaRecord """
    scientificname = Column(String(128))
    """ the full scientific name without authorship """
    authority = Column(String(255))
    """ the authorship information for the scientificname formatted according to the conventions 
        of the applicable nomenclaturalCode """
    status = Column(String(24))
    """ the status of the use of the scientificname (usually a taxonomic opinion). 
        Additional technical statuses are (1) quarantined: hidden from public interface after decision from an editor 
        and (2) deleted: AphiaID should NOT be used anymore, please replace it by the valid_AphiaID
        Also seen: 'alternate representation' """
    unacceptreason = Column(String(512))
    """ the reason why a scientificname is unaccepted """
    taxon_rank_id = Column(SmallInteger)
    """ the taxonomic rank identifier of the most specific name in the scientificname """
    rank = Column(String(24))
    """ the taxonomic rank of the most specific name in the scientificname """
    valid_aphia_id = Column(Integer)
    """ the AphiaID (for the scientificname) of the currently accepted taxon. NULL if 
        there is no currently accepted taxon."""
    valid_name = Column(String(128))
    """ the scientificname of the currently accepted taxon """
    valid_authority = Column(String(128))
    """ the authorship information for the scientificname of the currently accepted taxon """
    parent_name_usage_id = Column(Integer)
    """ the AphiaID (for the scientificname) of the direct, most proximate higher-rank 
        parent taxon (in a classification) """
    kingdom = Column(String(128))
    """ the full scientific name of the kingdom in which the taxon is classified """
    phylum = Column(String(129))
    """ the full scientific name of the phylum or division in which the taxon is classified """
    class_ = Column(String(130))
    """ the full scientific name of the class in which the taxon is classified """
    order = Column(String(131))
    """ the full scientific name of the order in which the taxon is classified """
    family = Column(String(132))
    """ the full scientific name of the family in which the taxon is classified """
    genus = Column(String(133))
    """ the full scientific name of the genus in which the taxon is classified """
    citation = Column(String(1024))
    """ a bibliographic reference for the resource as a statement indicating how this record should 
        be cited (attributed) when used """
    lsid = Column(String(257))
    """ LifeScience Identifier. Persistent GUID for an AphiaID """
    is_marine = Column(Boolean)
    """ a boolean flag indicating whether the taxon is a marine organism, i.e. can be found in/above sea water. 
        Possible values: 0/1/NULL """
    is_brackish = Column(Boolean)
    """ a boolean flag indicating whether the taxon occurrs in brackish habitats. 
        Possible values: 0/1/NULL """
    is_freshwater = Column(Boolean)
    """ a boolean flag indicating whether the taxon occurrs in freshwater habitats, i.e. can be 
        found in/above rivers or lakes. Possible values: 0/1/NULL"""
    is_terrestrial = Column(Boolean)
    """ a boolean flag indicating the taxon is a terrestial organism, i.e. occurrs on land as opposed to the sea. 
        Possible values: 0/1/NULL"""
    is_extinct = Column(Boolean)
    """ a flag indicating an extinct organism. Possible values: 0/1/NULL """
    # In REST response
    match_type = Column(String(16), nullable=False)
    """ Type of match. Possible values: exact/like/phonetic/near_1/near_2"""
    modified = Column(DateTime)
    """ The most recent date-time in GMT on which the resource was changed """
    # Our management of taxon
    all_fetched = Column(Boolean)