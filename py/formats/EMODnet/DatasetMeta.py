# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from lxml import etree

from formats.EMODnet.models import EMLPerson, EMLMeta, EMLAssociatedPerson, EMLAdditionalMeta

etree_sub_element = etree.SubElement


class DatasetMetadata(object):
    """
        Dataset metadata, general information about the dataset.
            Format is Ecological Metadata Language (EML)
            https://obis.org/manual/eml/
    """

    def __init__(self, meta: EMLMeta):
        self.name = "eml.xml"
        self.meta: EMLMeta = meta
        # metadataProvider;
        # associatedParty;
        # contact

    EML_HEADER = """
<eml:eml xmlns:eml="eml://ecoinformatics.org/eml-2.1.1"
         xmlns:dc="http://purl.org/dc/terms/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="eml://ecoinformatics.org/eml-2.1.1 http://rs.gbif.org/schema/eml-gbif-profile/1.1/eml.xsd"
         packageId="758c44fb-18f7-4f21-a9d7-a0fe8519f633/v1.1" system="http://gbif.org" scope="system"
         xml:lang="eng">
"""
    EML_FOOTER = """
</eml:eml>
"""

    def content(self) -> str:
        dataset: etree.Element = etree.Element("dataset")
        meta = self.meta
        for a_title in meta.titles:
            xml_title = etree_sub_element(dataset, "title")
            xml_title.set("lang", a_title.lang)
            xml_title.text = a_title.title
        for a_person in meta.creators:
            xml_person = etree_sub_element(dataset, "creator")
            self.person_to_xml(xml_person, a_person)
        for a_person in meta.contacts:
            xml_person = etree_sub_element(dataset, "contact")
            self.person_to_xml(xml_person, a_person)
        for a_person in meta.associatedParties:
            xml_person = etree_sub_element(dataset, "associatedParty")
            self.party_to_xml(xml_person, a_person)
        for a_person in meta.metadataProviders:
            xml_person = etree_sub_element(dataset, "metadataProvider")
            self.person_to_xml(xml_person, a_person)
        etree_sub_element(dataset, "pubDate").text = meta.pubDate
        etree_sub_element(dataset, "language").text = meta.language
        # Abstract
        xml_abstract = etree_sub_element(dataset, "abstract")
        for a_para in meta.abstract:
            etree_sub_element(xml_abstract, "para").text = a_para
        # KeywordSet
        xml_keywordset = etree_sub_element(dataset, "keywordSet")
        for a_keyword in meta.keywordSet.keywords:
            etree_sub_element(xml_keywordset, "keyword").text = a_keyword
        if meta.keywordSet.keywordThesaurus:
            etree_sub_element(xml_keywordset, "keywordThesaurus").text = meta.keywordSet.keywordThesaurus
        if meta.additionalInfo:
            etree_sub_element(etree_sub_element(dataset, "additionalInfo"), "para").text = meta.additionalInfo
        self.coverage_to_xml(etree_sub_element(dataset, "coverage"))
        # Licence
        ir_xml = etree.HTML("<para>" + meta.intellectualRights + "</para>")
        etree_sub_element(dataset, "intellectualRights").append(ir_xml[0][0])
        # Purpose
        if meta.purpose:
            etree_sub_element(etree_sub_element(dataset, "purpose"), "para").text = meta.purpose
        # Method
        if meta.methods:
            raise Exception("You should use eMoF table to describe the method")
        # Project
        if meta.project:
            # TODO: finish all fields
            xml_project = etree_sub_element(dataset, "project")
            etree_sub_element(xml_project, "title").text = meta.project.title
            if len(meta.project.personnel) > 0:
                xml_person = etree_sub_element(xml_project, "personnel")
                self.party_to_xml(xml_person, meta.project.personnel[0])
        # Maintenance
        if meta.maintenance and meta.maintenanceUpdateFrequency:
            xml_maint = etree_sub_element(dataset, "maintenance")
            etree_sub_element(etree_sub_element(xml_maint, "description"), "para").text = meta.maintenance
            etree_sub_element(xml_maint, "maintenanceUpdateFrequency").text = meta.maintenanceUpdateFrequency
        # Additional Metadata
        xml_additional_meta = etree_sub_element(etree_sub_element(dataset, "additionalMetadata"), "metadata")
        self.additional_meta_to_xml(xml_additional_meta, meta.additionalMetadata)
        # Format for output
        etree.indent(dataset, space="  ")
        as_string = etree.tostring(dataset, pretty_print=True, encoding='unicode')
        ret = self.EML_HEADER + as_string.replace("lang=", "xml:lang=") + self.EML_FOOTER
        return ret

    @staticmethod
    def additional_meta_to_xml(xml_meta_plus, eml_meta_plus: EMLAdditionalMeta):
        etree_sub_element(xml_meta_plus, "dateStamp").text = eml_meta_plus.dateStamp

    @staticmethod
    def person_to_xml(xml_person, eml_person: EMLPerson):
        # Individual block
        if eml_person.givenName or eml_person.surName:
            indiv = etree_sub_element(xml_person, "individualName")
            if eml_person.givenName:
                etree_sub_element(indiv, "givenName").text = eml_person.givenName
            if eml_person.surName:
                etree_sub_element(indiv, "surName").text = eml_person.surName
        etree_sub_element(xml_person, "organizationName").text = eml_person.organizationName
        if eml_person.positionName:
            etree_sub_element(xml_person, "positionName").text = eml_person.positionName
        # Address block
        addr = etree_sub_element(xml_person, "address")
        if eml_person.deliveryPoint:
            etree_sub_element(addr, "deliveryPoint").text = eml_person.deliveryPoint
        if eml_person.city:
            etree_sub_element(addr, "city").text = eml_person.city
        if eml_person.administrativeArea:
            etree_sub_element(addr, "administrativeArea").text = eml_person.administrativeArea
        if eml_person.postalCode:
            etree_sub_element(addr, "postalCode").text = eml_person.postalCode
        etree_sub_element(addr, "country").text = eml_person.country
        # Rest of person fields
        if eml_person.phone:
            etree_sub_element(xml_person, "phone").text = eml_person.phone
        if eml_person.electronicMailAddress:
            etree_sub_element(xml_person, "electronicMailAddress").text = eml_person.electronicMailAddress
        if eml_person.onlineUrl:
            etree_sub_element(xml_person, "onlineUrl").text = eml_person.onlineUrl
        if eml_person.userID:
            etree_sub_element(xml_person, "userID").text = eml_person.userID

    def party_to_xml(self, xml_person, eml_person: EMLAssociatedPerson):
        self.person_to_xml(xml_person, eml_person)
        if eml_person.role:
            etree_sub_element(xml_person, "role").text = eml_person.role

    def coverage_to_xml(self, xml_coverage):
        meta = self.meta
        # Geographic
        xml_geo_cov = etree_sub_element(xml_coverage, "geographicCoverage")
        eml_geo_cov = meta.geographicCoverage
        etree_sub_element(xml_geo_cov, "geographicDescription").text = eml_geo_cov.geographicDescription
        xml_geo_cov_bounding = etree_sub_element(xml_geo_cov, "boundingCoordinates")
        etree_sub_element(xml_geo_cov_bounding, "westBoundingCoordinate").text = eml_geo_cov.westBoundingCoordinate
        etree_sub_element(xml_geo_cov_bounding, "eastBoundingCoordinate").text = eml_geo_cov.eastBoundingCoordinate
        etree_sub_element(xml_geo_cov_bounding, "northBoundingCoordinate").text = eml_geo_cov.northBoundingCoordinate
        etree_sub_element(xml_geo_cov_bounding, "southBoundingCoordinate").text = eml_geo_cov.southBoundingCoordinate
        # Temporal
        xml_temporal_cov = etree_sub_element(xml_coverage, "temporalCoverage")
        eml_temporal_cov = meta.temporalCoverage
        if eml_temporal_cov.singleDateTime:
            etree_sub_element(xml_temporal_cov, "singleDateTime").text = eml_temporal_cov.singleDateTime
        else:
            xml_range = etree_sub_element(xml_temporal_cov, "rangeOfDates")
            etree_sub_element(etree_sub_element(xml_range, "beginDate"),
                              "calendarDate").text = eml_temporal_cov.beginDate
            etree_sub_element(etree_sub_element(xml_range, "endDate"), "calendarDate").text = eml_temporal_cov.endDate
        # Taxonomic
        xml_taxo_cov = etree_sub_element(xml_coverage, "taxonomicCoverage")
        if meta.generalTaxonomicCoverage:
            etree_sub_element(xml_taxo_cov, "generalTaxonomicCoverage").text = meta.generalTaxonomicCoverage
        eml_taxo_cov = meta.taxonomicCoverage
        for an_eml_taxo in eml_taxo_cov:
            xml_classif = etree_sub_element(xml_taxo_cov, "taxonomicClassification")
            etree_sub_element(xml_classif, "taxonRankName").text = an_eml_taxo.taxonRankName
            etree_sub_element(xml_classif, "taxonRankValue").text = an_eml_taxo.taxonRankValue
            if an_eml_taxo.commonName:
                etree_sub_element(xml_classif, "commonName").text = an_eml_taxo.commonName
