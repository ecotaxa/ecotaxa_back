# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import Optional, List

from helpers.pydantic import BaseModel, Field, root_validator

# noinspection PyPackageRequirements
# from urllib3.util import Url
Url = str


class EMODNetMeta(BaseModel):
    """
    The dataset metadata. Not to be confused with DwC metadata, which describes
    how data is organized.
    """

    provider: str = Field(title="Person providing the metadata: name, institute, email")
    title: str = Field(title="Dataset title in English")
    orig_title: Optional[str] = Field(
        title="Dataset title in original language (and language)"
    )
    contact: str = Field(title="Contact person for the dataset: name, institute, email")
    creator: List[str] = Field(title="Data creator(s): (name), institute", min_items=1)
    other_persons: List[str] = Field(
        title="Other person(s) associated with the dataset - Highly recommended"
    )
    citation: str = Field(title="Dataset citation")
    license: str = Field(title="License or terms of use")
    abstract: str = Field(title="Abstract")
    extended_description: Optional[str] = Field(
        title="Extended description-Highly recommended"
    )
    geo_coverage: str = Field(title="Geographical coverage")
    temporal_coverage: str = Field(title="Temporal coverage")
    taxonomic_coverage: str = Field(title="Taxonomic coverage")
    themes: List[str] = Field(title="Themes", min_items=1)
    keywords: List[str] = Field(title="Keywords")
    websites: List[Url] = Field(title="Websites")
    related_publications: List[str] = Field(
        title="Publications related to the dataset - Highly recommended"
    )


# Some values from https://www.dublincore.org/specifications/dublin-core/dcmi-type-vocabulary/2010-10-11/


class RecordTypeEnum(str, Enum):
    Collection = "Collection"
    Dataset = "Dataset"
    Event = "Event"
    StillImage = "StillImage"
    Text = "Text"
    MovingImage = "MovingImage"
    PhysicalObject = "PhysicalObject"
    # These 2 are not 'official'
    cruise = "cruise"
    sample = "sample"


# https://dwc.tdwg.org/ Darwin Core for terms below


class DwcEvent(BaseModel):
    # Unicity
    eventID: str = Field(
        term="http://rs.tdwg.org/dwc/terms/eventID", is_id=True, dup_id=True
    )
    # Record DwC field
    type: RecordTypeEnum = Field(term="http://purl.org/dc/terms/type")
    parentEventID: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/parentEventID"
    )

    institutionCode: str = Field(term="http://rs.tdwg.org/dwc/terms/institutionCode")
    """ The name (or acronym) in use by the institution having custody of the object(s) or 
    information referred to in the record. Examples `MVZ`, `FMNH`, `CLO`, `UCMP`"""

    datasetName: str = Field(term="http://rs.tdwg.org/dwc/terms/datasetName")
    # Can be date, date+time or date range using "/"
    eventDate: str = Field(term="http://rs.tdwg.org/dwc/terms/eventDate")

    # Location DwC fields
    decimalLatitude: str = Field(term="http://rs.tdwg.org/dwc/terms/decimalLatitude")
    decimalLongitude: str = Field(term="http://rs.tdwg.org/dwc/terms/decimalLongitude")
    geodeticDatum: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/geodeticDatum"
    )

    coordinateUncertaintyInMeters: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/coordinateUncertaintyInMeters"
    )
    minimumDepthInMeters: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/minimumDepthInMeters"
    )
    maximumDepthInMeters: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/maximumDepthInMeters"
    )
    footprintWKT: Optional[str] = Field(term="http://purl.org/dc/terms/type")

    # Record DwC field
    modified: Optional[str] = Field(term="http://purl.org/dc/terms/modified")


# An alias I find clearer
DwC_Event = DwcEvent


class BasisOfRecordEnum(str, Enum):
    materialSample = "MaterialSample"
    preservedSpecimen = "PreservedSpecimen"
    humanObservation = "HumanObservation"
    machineObservation = "MachineObservation"
    livingSpecimen = "LivingSpecimen"


class IdentificationVerificationEnum(str, Enum):
    # for identifications generated by an algorithm and not validated by human.
    predictedByMachine = "PredictedByMachine"
    # for identifications generated by an algorithm and verified to be correct by a
    # human, this is also referred as validated data
    validatedByHuman = "ValidatedByHuman"


class OccurrenceStatusEnum(str, Enum):
    present = "present"
    absent = "absent"


class DwcOccurrence(BaseModel):
    # Unicity
    eventID: str = Field(
        term="http://rs.tdwg.org/dwc/terms/eventID", is_id=True, dup_id=True
    )
    occurrenceID: str = Field(term="http://rs.tdwg.org/dwc/terms/occurrenceID")

    # Record-level fields
    basisOfRecord: BasisOfRecordEnum = Field(
        term="http://rs.tdwg.org/dwc/terms/basisOfRecord"
    )

    # identified By # TODO

    identificationVerificationStatus: Optional[IdentificationVerificationEnum] = Field(
        term="http://rs.tdwg.org/dwc/terms/identificationVerificationStatus"
    )

    # https://github.com/ecotaxa/ecotaxa_front/issues/764#issuecomment-1508165516
    # We don't do see comment above
    # identificationReferences
    # We don't do see comment above
    # associatedMedia

    # Identification fields
    scientificName: str = Field(term="http://rs.tdwg.org/dwc/terms/scientificName")
    # LSID from WoRMS for EMODnet
    scientificNameID: str = Field(term="http://rs.tdwg.org/dwc/terms/scientificNameID")

    # Count field
    individualCount: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/individualCount"
    )

    # Taxon fields
    # Even if the LSID is not ambiguous from marinespecies.org, the GBIF backbone mixes several
    # sources of taxonomy so setting the below helps in solving ambiguities.
    kingdom: Optional[str] = Field(term="http://rs.tdwg.org/dwc/terms/kingdom")
    taxonRank: Optional[str] = Field(term="http://rs.tdwg.org/dwc/terms/taxonRank")
    scientificNameAuthorship: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/scientificNameAuthorship"
    )

    # Occurrence fields
    occurrenceStatus: OccurrenceStatusEnum = Field(
        term="http://rs.tdwg.org/dwc/terms/occurrenceStatus"
    )

    # For museum
    collectionCode: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/collectionCode"
    )
    catalogNumber: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/catalogNumber"
    )

    # Identification fields, eg. "cf."
    identificationQualifier: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/identificationQualifier"
    )

    # Record DwC fields
    modified: Optional[str] = Field(term="http://purl.org/dc/terms/modified")


DwC_Occurrence = DwcOccurrence


class DwcExtendedMeasurementOrFact(BaseModel):
    """
    In case of doubt, eMoF table is better as more precise.
    E.g. prefer eMoF for samplingProtocol rather than DwC field.
    """

    # Unicity is determined by the eventID alone if the EMOF is related to
    # the whole event, or by the pair (eventID, occurrenceID) if related to an occurence, so...
    eventID: str = Field(
        term="http://rs.tdwg.org/dwc/terms/eventID", is_id=True, dup_id=False
    )
    # ...if related to the whole event, occurrenceID must not be present
    occurrenceID: Optional[str] = Field(
        term="http://rs.tdwg.org/dwc/terms/occurrenceID"
    )

    # Note: although measurementType, measurementValue and measurementUnit are free text fields,
    # it is recommended to fill them in with the "preferred label" given by the BODC parameter.
    measurementValue: str = Field(
        title="measurement value, free text",
        term="http://rs.tdwg.org/dwc/terms/measurementValue",
    )
    # https://www.bodc.ac.uk/resources/vocabularies/vocabulary_search/L22/
    measurementType: str = Field(
        title="measurement type, free text",
        term="http://rs.tdwg.org/dwc/terms/measurementType",
    )
    measurementUnit: Optional[str] = Field(
        title="measurement unit, free text",
        term="http://rs.tdwg.org/dwc/terms/measurementUnit",
    )
    # Controlled vocabulary
    # https://www.bodc.ac.uk/resources/vocabularies/vocabulary_search/P01/
    # examples:
    #   Temperature of the water body: search for "temperature%water%body"
    #   Salinity of the water body with CTD: search for "salinity%CTD"
    #   Measurements related to lithology (sediment characteristics): "lithology"
    # http://seadatanet.maris2.nl/bandit/browse_step.php for just P01
    measurementValueID: Optional[str] = Field(
        title="controlled vocabulary value ID",
        term="http://rs.iobis.org/obis/terms/measurementValueID",
    )

    measurementTypeID: str = Field(
        title="controlled vocabulary type ID",
        term="http://rs.iobis.org/obis/terms/measurementTypeID",
    )
    # http://vocab.nerc.ac.uk/collection/P06/current/
    measurementUnitID: Optional[str] = Field(
        title="controlled vocabulary unit ID",
        term="http://rs.iobis.org/obis/terms/measurementUnitID",
    )

    measurementRemarks: Optional[str] = Field(
        title="free text", term="http://rs.iobis.org/obis/terms/measurementRemarks"
    )


DwC_ExtendedMeasurementOrFact = DwcExtendedMeasurementOrFact


# Check tool http://rshiny.lifewatch.be/BioCheck/

# Specs: https://eml.ecoinformatics.org/schema/index.html


class EMLIdentifier(BaseModel):
    """
    EML unique identifier for the document
    """

    packageId: str = Field(title="Unique ID for this dataset in the system.")
    system: str = Field(title="The system providing unicity, e.g. https://doi.org")
    scope: Optional[str] = Field(
        title="The scope of the ID inside the system", default="system"
    )


class EMLTitle(BaseModel):
    """
    EML title with optional lang.
    """

    title: str = Field(title="Descriptive title(s) - not too short")
    """ A good title allows a user to a first assessment whether the dataset is useful for the intended purpose. 
    EMODnet Biology recommends including the region and time period of sampling."""
    lang: str = Field(title="Title language, ISO-639.2", default="eng")


class EMLPerson(BaseModel):
    """
    A person for EML metadata. Can be, in fact, simply an organization.
    """

    givenName: Optional[str]
    surName: Optional[str]

    organizationName: str
    positionName: Optional[str]
    """ To be used as alternative to persons names (leave individualName blank and use positionName 
    instead e.g. data manager). """

    # address
    deliveryPoint: Optional[str]
    city: Optional[str]
    administrativeArea: Optional[str]
    postalCode: Optional[str]
    country: Optional[str]
    """ Looks like an alpha_2 ISO 3166 for country """

    phone: Optional[str]
    electronicMailAddress: Optional[str]

    onlineUrl: Optional[str]
    userID: Optional[str]


class EMLAssociatedPerson(EMLPerson):
    # A person with a role.
    # role can be, e.g. ‘originator’, ‘content provider’, ‘principle investigator’, 'technician', 'reviewer'
    # 'developer' :)
    role: str


class EMLKeywordSet(BaseModel):
    """
    EML keyword set
    Relevant keywords facilitate the discovery of a dataset. An indication of the represented functional groups
    can help in a general search (e.g. plankton, benthos, zooplankton, phytoplankton, macrobenthos, meiobenthos …).
    Assigned keywords can be related to taxonomy, habitat, geography or relevant keywords extracted from thesauri
    such as the ASFA thesaurus, the CAB thesaurus or GCMD keywords.
    """

    keywords: List[str]
    keywordThesaurus: str


class EMLGeoCoverage(BaseModel):
    """
    EML metadata coverage - geographic
    """

    geographicDescription: str
    """ Better use http://www.marineregions.org/ """
    westBoundingCoordinate: str
    eastBoundingCoordinate: str
    northBoundingCoordinate: str
    southBoundingCoordinate: str


class EMLTemporalCoverage(BaseModel):
    """
    EML metadata coverage - temporal
     Use ISO 8601
    """

    singleDateTime: Optional[str]
    beginDate: Optional[str]
    endDate: Optional[str]

    # noinspection PyMethodParameters
    @root_validator(pre=True)
    def check_at_least_a_date(cls, values):
        assert "singleDateTime" in values or (
            "beginDate" in values and "endDate" in values
        ), "singleDateTime or beginDate+endDate should be specified"
        return values


class EMLTaxonomicClassification(BaseModel):
    """
    EML metadata coverage - taxonomic
    https://eml.ecoinformatics.org/schema/eml-coverage_xsd.html
    """

    taxonRankName: str
    """ e.g. phylum """
    taxonRankValue: str
    """ e.g. Copepoda  """
    commonName: Optional[str]


class EMLMethod(BaseModel):
    """
    EML method - unused
    """

    methodStep: str
    """ Descriptions of procedures, relevant literature, software, instrumentation, source data and 
    any quality control measures taken."""
    sampling: str
    """ Description of sampling procedures including the geographic, temporal and taxonomic coverage of the study."""
    studyExtent: str
    """ Description of the specific sampling area, the sampling frequency (temporal boundaries, frequency of occurrence)
    , and groups of living organisms sampled (taxonomic coverage)."""
    samplingDescription: str
    """ Description of sampling procedures, similar to the one found in the methods section of a journal article."""


class EMLProject(BaseModel):
    """
    EML project
    """

    title: str
    identifier: Optional[str]
    personnel: List[EMLAssociatedPerson]
    """ The personnel field is used to document people involved in a research project by providing contact information 
    and their role in the project. """
    description: Optional[str]
    funding: Optional[str]  # goes to para
    """ The funding field is used to provide information about funding sources for the project 
    such as: grant and contract numbers; names and addresses of funding sources. """
    studyAreaDescription: Optional[str]
    designDescription: Optional[str]
    """ The description of research design. """
    qualityControl: Optional[str]
    """Description of actions taken to either control or assess the quality of data resulting 
    from the associated method step."""


class EMLAdditionalMeta(BaseModel):
    """
    EML additional metadata
    """

    dateStamp: str
    """ The dateTime the metadata document was created or modified (ISO 8601)."""
    metadataLanguage: str = Field(title="Title language, ISO-639.2", default="eng")
    """ The language in which the metadata document (as opposed to the resource being described by the metadata) 
    is written. """

    citation: Optional[str]
    """ A single citation for use when citing the dataset. The IPT can also auto-generate 
    a citation based on the metadata (people, title, organization, onlineURL, DOI etc)."""
    bibliography: Optional[str]
    """ A list of citations that form a bibliography on literature related / used in the dataset """
    resourceLogoUrl: Optional[str]
    """ URL of the logo associated with a dataset."""
    parentCollectionIdentifier: Optional[str]
    collectionIdentifier: Optional[str]
    formationPeriod: Optional[str]
    """ Text description of the time period during which the collection was assembled. E.g., “Victorian”, 
    or “1922 - 1932”, or “c. 1750”. """
    livingTimePeriod: Optional[str]
    """ Time period during which biological material was alive (for palaeontological collections). """
    specimenPreservationMethod: Optional[str]
    """ Self-explaining. lol. """


class EMLMeta(BaseModel):
    """
    EML metadata
    """

    identifier: EMLIdentifier = Field(title="The unique identifier for the collection")
    titles: List[EMLTitle] = Field(title="Titles, at least 1", min_items=1)
    creators: List[EMLPerson] = Field(title="Creators, at least 1", min_items=1)
    metadataProviders: List[EMLPerson] = Field(
        title="Metadata providers, at least 1", min_items=1
    )
    associatedParties: List[EMLAssociatedPerson] = Field(
        title="Associated parties, at least 1", min_items=0
    )
    contacts: List[EMLPerson] = Field(title="Contacts, at least 1", min_items=1)
    pubDate: str
    """ The date that the resource was published. Use ISO 8601. """
    language: str = Field(title="Resource language, ISO-639.2", default="eng")
    """ The language in which the resource (not the metadata document) is written. Use ISO language code. """
    abstract: List[str] = Field(title="Paragraphs forming the abstract", min_items=1)
    """ The abstract or description of a dataset provides basic information on the content of the dataset. The 
    information in the abstract should improve understanding and interpretation of the data. It is recommended that 
    the description indicates whether the dataset is a subset of a larger dataset and – if so – provide a link to 
    the parent metadata and/or dataset.    
    If the data provider or OBIS node require bi- or multilingual entries for the description 
    (e.g. due to national obligations) then the following procedure can be followed:    
        Indicate English as metadata language
        Enter the English description first
        Type a slash (/)
        Enter the description in the second language
    Example
    The Louis-Marie herbarium grants a priority to the Arctic-alpine, subarctic and boreal species from the province of 
    Quebec and the northern hemisphere. This dataset is mainly populated with specimens from the province of Quebec. / 
    L’Herbier Louis-Marie accorde une priorité aux espèces arctiques-alpines, subarctiques et boréales du Québec, du 
    Canada et de l’hémisphère nord. Ce jeu présente principalement des spécimens provenant du Québec.
    """
    keywordSet: EMLKeywordSet
    additionalInfo: Optional[str]
    """ OBIS checks this EML field for harvesting. It should contain marine, harvested by iOBIS. 
    """
    geographicCoverage: EMLGeoCoverage
    temporalCoverage: EMLTemporalCoverage

    generalTaxonomicCoverage: Optional[str]
    taxonomicCoverage: List[EMLTaxonomicClassification]
    intellectualRights: str
    """ AKA licence """
    informationUrl: str
    """ A back-link to the dataset origin """
    purpose: Optional[str]
    """ A description of the purpose of this dataset. """
    methods: Optional[EMLMethod]
    """ Methods - sort of deprecated """
    project: Optional[EMLProject]  # TODO: is it project_s_ i.e. a list ?
    """ Project """
    maintenanceUpdateFrequency: Optional[str]
    maintenance: Optional[str]
    """ Meta of meta"""
    additionalMetadata: EMLAdditionalMeta
