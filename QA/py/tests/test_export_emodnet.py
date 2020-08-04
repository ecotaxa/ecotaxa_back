# noinspection PyUnresolvedReferences
# noinspection PyPackageRequirements
import logging

from api.exports import *
from formats.EMODnet.models import *
# noinspection PyPackageRequirements
from tasks.export.EMODnet import EMODNetExport
# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database


def no_test_emodnet_export(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_ids = [757]
    person1 = EMLPerson(organizationName="IMEV",
                        givenName="Jean-Olivier",
                        surName="Irisson",
                        country="FR",
                        positionName='professor'
                        )
    person2 = EMLAssociatedPerson(organizationName="IMEV",
                                  givenName="Laurent",
                                  surName="Salinas",
                                  country="FR",
                                  role='developer',
                                  positionName='engineer'
                                  )
    title = EMLTitle(title="Point B, Juday-Bogorov net series, 2018")
    abstract = """
This series is part of the long term planktonic monitoring of
Villefranche-sur-mer, which is one of the oldest and richest in the world.
The data collection and processing has been funded by several projects
over its lifetime. It is currently supported directly by the Institut de la Mer
de Villefranche (IMEV), as part of its long term monitoring effort.
    """
    keywords = EMLKeywordSet(keywords=["Zooplankton",
                                       "Mediterranean Sea",
                                       "Ligurian sea"],
                             keywordThesaurus="GBIF Dataset Type Vocabulary: http://rs.gbif.org/vocabulary/gbif/dataset_type.xml")
    additional_info = """
marine, harvested by iOBIS.
The OOV supported the financial effort of the survey. 
We are grateful to the crew of the research boat at OOV that collected plankton during the temporal survey."""
    geo_cov = EMLGeoCoverage(geographicDescription="Entrance of Villefranche-sur-Mer Bay",
                             westBoundingCoordinate="7.092",
                             eastBoundingCoordinate="7.674",
                             northBoundingCoordinate="43.823",
                             southBoundingCoordinate="43.437")
    time_cov = EMLTemporalCoverage(beginDate="1966-11-14",
                                   endDate="1999-09-10")
    taxo_cov = [EMLTaxonomicClassification(taxonRankName="phylum",
                                           taxonRankValue="Arthropoda"),
                EMLTaxonomicClassification(taxonRankName="phylum",
                                           taxonRankValue="Chaetognatha"),
                ]
    licence = "This work is licensed under a <ulink url=\"http://creativecommons.org/licenses/by/4.0/legalcode\"> " \
              "<citetitle>Creative Commons Attribution (CC-BY) 4.0 License</citetitle></ulink>."
    project = EMLProject(title="EcoTaxa",
                         personnel=[person2])
    meta_plus = EMLAdditionalMeta(dateStamp="2021-06-24")
    meta = EMLMeta(titles=[title],
                   creators=[person1],
                   contacts=[person1],
                   metadataProviders=[person1],
                   associatedParties=[person1],
                   pubDate="2020-06-23",
                   abstract=[abstract],
                   keywordSet=keywords,
                   additionalInfo=additional_info,
                   geographicCoverage=geo_cov,
                   temporalCoverage=time_cov,
                   taxonomicCoverage=taxo_cov,
                   intellectualRights=licence,
                   project=project,
                   maintenance="periodic review of origin data",
                   maintenanceUpdateFrequency="1M",
                   additionalMetadata=meta_plus)
    req = EMODNetExportReq(meta=meta, project_ids=prj_ids)
    rsp = EMODNetExport(req).run()
    print("\n".join(caplog.messages))
