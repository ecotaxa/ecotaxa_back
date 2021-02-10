_eml = r"""

<eml:eml xmlns:eml="eml://ecoinformatics.org/eml-2.1.1"
         xmlns:dc="http://purl.org/dc/terms/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="eml://ecoinformatics.org/eml-2.1.1 http://rs.gbif.org/schema/eml-gbif-profile/1.1/eml.xsd"
         packageId="758c44fb-18f7-4f21-a9d7-a0fe8519f633/v1.1" system="http://gbif.org" scope="system"
         xml:lang="eng">
<dataset>
  <title xml:lang="eng">EMODNET test collection</title>
  <creator>
    <individualName>
      <givenName>Real</givenName>
      <surName>User</surName>
    </individualName>
    <organizationName>IMEV</organizationName>
    <address>
      <country>FR</country>
    </address>
    <electronicMailAddress>real@users.com</electronicMailAddress>
  </creator>
  <contact>
    <individualName>
      <givenName>Real</givenName>
      <surName>User</surName>
    </individualName>
    <organizationName>IMEV</organizationName>
    <address>
      <country>FR</country>
    </address>
    <electronicMailAddress>real@users.com</electronicMailAddress>
  </contact>
  <metadataProvider>
    <individualName>
      <givenName>Real</givenName>
      <surName>User</surName>
    </individualName>
    <organizationName>IMEV</organizationName>
    <address>
      <country>FR</country>
    </address>
    <electronicMailAddress>real@users.com</electronicMailAddress>
  </metadataProvider>
  <pubDate>2021-02-10</pubDate>
  <language>eng</language>
  <abstract>
    <para>
This series is part of the long term planktonic monitoring of
    # Villefranche-sur-mer, which is one of the oldest and richest in the world.
    # The data collection and processing has been funded by several projects
    # over its lifetime. It is currently supported directly by the Institut de la Mer
    # de Villefranche (IMEV), as part of its long term monitoring effort.
    </para>
  </abstract>
  <keywordSet>
    <keyword>Plankton</keyword>
    <keyword>Imaging</keyword>
    <keyword>EcoTaxa</keyword>
    <keywordThesaurus>GBIF Dataset Type Vocabulary: http://rs.gbif.org/vocabulary/gbif/dataset_type.xml</keywordThesaurus>
  </keywordSet>
  <coverage>
    <geographicCoverage>
      <geographicDescription>See coordinates</geographicDescription>
      <boundingCoordinates>
        <westBoundingCoordinate>-24.416667</westBoundingCoordinate>
        <eastBoundingCoordinate>-24.416667</eastBoundingCoordinate>
        <northBoundingCoordinate>18.000000</northBoundingCoordinate>
        <southBoundingCoordinate>18.000000</southBoundingCoordinate>
      </boundingCoordinates>
    </geographicCoverage>
    <temporalCoverage>
      <rangeOfDates>
        <beginDate>
          <calendarDate>2014-04-20</calendarDate>
        </beginDate>
        <endDate>
          <calendarDate>2014-04-21</calendarDate>
        </endDate>
      </rangeOfDates>
    </temporalCoverage>
    <taxonomicCoverage>
      <taxonomicClassification>
        <taxonRankName>Order</taxonRankName>
        <taxonRankValue>Cyclopoida</taxonRankValue>
      </taxonomicClassification>
      <taxonomicClassification>
        <taxonRankName>Family</taxonRankName>
        <taxonRankValue>Oncaeidae</taxonRankValue>
      </taxonomicClassification>
    </taxonomicCoverage>
  </coverage>
  <intellectualRights>
    <para>This work is licensed under a <ulink url="https://creativecommons.org/licenses/by/4.0/legalcode">
        <citetitle>Creative Commons Attribution (CC-BY) 4.0 License</citetitle>
      </ulink>.</para>
  </intellectualRights>
  <maintenance>
    <description>
      <para>periodic review of origin data</para>
    </description>
    <maintenanceUpdateFrequency>1M</maintenanceUpdateFrequency>
  </maintenance>
  <additionalMetadata>
    <metadata>
      <dateStamp>2021-02-10</dateStamp>
    </metadata>
  </additionalMetadata>
</dataset>

</eml:eml>

"""
_meta = r"""
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">

  <core encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" 
        ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Event">
    <files>
      <location>event.txt</location>
    </files> 
    <id index="0"/>
    <field index="0" term="http://rs.tdwg.org/dwc/terms/eventID"/>
    <field index="1" term="http://rs.tdwg.org/dwc/terms/datasetName"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/decimalLatitude"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/decimalLongitude"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/eventDate"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/institutionCode"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/maximumDepthInMeters"/>
    <field index="7" term="http://rs.tdwg.org/dwc/terms/minimumDepthInMeters"/>
    <field index="8" term="http://purl.org/dc/terms/type"/>
  </core>

  <extension encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" 
        ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
    <files>
      <location>occurrence.txt</location>
    </files> 
    <coreid index="0"/>
    <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/individualCount"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/occurrenceID"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/occurrenceStatus"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/scientificNameID"/>
  </extension>

  <extension encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" 
        ignoreHeaderLines="1" rowType="http://rs.iobis.org/obis/terms/ExtendedMeasurementOrFact">
    <files>
      <location>extendedmeasurementorfact.txt</location>
    </files> 
    <coreid index="0"/>
    <field index="1" term="http://rs.tdwg.org/dwc/terms/measurementType"/>
    <field index="2" term="http://rs.iobis.org/obis/terms/measurementTypeID"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/measurementUnit"/>
    <field index="4" term="http://rs.iobis.org/obis/terms/measurementUnitID"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/measurementValue"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/occurrenceID"/>
  </extension>
</archive>

"""
_event = r"""
eventID	datasetName	decimalLatitude	decimalLongitude	eventDate	institutionCode	maximumDepthInMeters	minimumDepthInMeters	type
m106_mn01_n1_sml	EMODNET test collection	18.000000	-24.416667	2014-04-20T04:20:00Z	IMEV	1000.0	600.0	sample
m106_mn01_n2_sml	EMODNET test collection	18.000000	-24.416667	2014-04-20T04:20:00Z	IMEV	600.0	300.0	sample
m106_mn01_n3_sml	EMODNET test collection	18.000000	-24.416667	2014-04-20T04:20:00Z/2014-04-21T04:20:00Z	IMEV	600.0	300.0	sample
"""
_occurence = r"""
eventID	basisOfRecord	individualCount	occurrenceID	occurrenceStatus	scientificName	scientificNameID
m106_mn01_n1_sml	machineObservation	2	m106_mn01_n1_sml_78418	present	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586
m106_mn01_n1_sml	machineObservation	1	m106_mn01_n1_sml_45072	present	Cyclopoida	urn:lsid:marinespecies.org:taxname:1101
"""
_occurence_with_absent = r"""m106_mn01_n2_sml	machineObservation	0	m106_mn01_n2_sml_45072	absent	Cyclopoida	urn:lsid:marinespecies.org:taxname:1101
m106_mn01_n2_sml	machineObservation	0	m106_mn01_n2_sml_78418	absent	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586
m106_mn01_n3_sml	machineObservation	0	m106_mn01_n3_sml_45072	absent	Cyclopoida	urn:lsid:marinespecies.org:taxname:1101
m106_mn01_n3_sml	machineObservation	0	m106_mn01_n3_sml_78418	absent	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586
"""
_emofs = r"""
eventID	measurementType	measurementTypeID	measurementUnit	measurementUnitID	measurementValue	occurrenceID
m106_mn01_n1_sml	Abundance of biological entity specified elsewhere per unit volume of the water body	http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL01/	Number per cubic metre	http://vocab.nerc.ac.uk/collection/P06/current/UPMM/	0.01	m106_mn01_n1_sml_78418
m106_mn01_n1_sml	Abundance of biological entity specified elsewhere per unit volume of the water body	http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL01/	Number per cubic metre	http://vocab.nerc.ac.uk/collection/P06/current/UPMM/	0.005	m106_mn01_n1_sml_45072
"""
ref_zip = {"event.txt": _event,
           "eml.xml": _eml,
           "extendedmeasurementorfact.txt": _emofs,
           "meta.xml": _meta,
           "occurrence.txt": _occurence}
with_zeroes_zip = {"event.txt": _event,
                   "eml.xml": _eml,
                   "extendedmeasurementorfact.txt": _emofs,
                   "meta.xml": _meta,
                   "occurrence.txt": _occurence + _occurence_with_absent}
