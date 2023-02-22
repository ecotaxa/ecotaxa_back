_eml = r"""
<?xml version="1.0" encoding="UTF-8"?>
<eml:eml xmlns:eml="eml://ecoinformatics.org/eml-2.1.1"
         xmlns:dc="http://purl.org/dc/terms/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="eml://ecoinformatics.org/eml-2.1.1 http://rs.gbif.org/schema/eml-gbif-profile/1.1/eml.xsd"
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
  <pubDate>2021-07-10</pubDate>
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
  <intellectualRights>
    <para>This work is licensed under a <ulink url="https://creativecommons.org/licenses/by/4.0/legalcode">
        <citetitle>Creative Commons Attribution (CC-BY) 4.0 License</citetitle>
      </ulink>.</para>
  </intellectualRights>
  <distribution>
    <online>
      <url function="information">https://ecotaxa.obs-vlfr.fr/api/collections/by_title?q=EMODNET+test+collection</url>
    </online>
  </distribution>
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
        <taxonRankName>Class</taxonRankName>
        <taxonRankValue>Actinopterygii</taxonRankValue>
      </taxonomicClassification>
      <taxonomicClassification>
        <taxonRankName>Family</taxonRankName>
        <taxonRankValue>Oncaeidae</taxonRankValue>
      </taxonomicClassification>
      <taxonomicClassification>
        <taxonRankName>Order</taxonRankName>
        <taxonRankValue>Cyclopoida</taxonRankValue>
      </taxonomicClassification>
    </taxonomicCoverage>
  </coverage>
  <maintenance>
    <description>
      <para>periodic review of origin data</para>
    </description>
    <maintenanceUpdateFrequency>unknown</maintenanceUpdateFrequency>
  </maintenance>
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
</dataset>
<additionalMetadata>
  <metadata>
    <gbif>
      <dateStamp>2021-07-10T11:22:33</dateStamp>
    </gbif>
  </metadata>
</additionalMetadata>

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
    <field index="1" term="http://rs.tdwg.org/dwc/terms/eventID"/>
    <field index="2" term="http://purl.org/dc/terms/type"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/institutionCode"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/datasetName"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/eventDate"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/decimalLatitude"/>
    <field index="7" term="http://rs.tdwg.org/dwc/terms/decimalLongitude"/>
    <field index="8" term="http://rs.tdwg.org/dwc/terms/minimumDepthInMeters"/>
    <field index="9" term="http://rs.tdwg.org/dwc/terms/maximumDepthInMeters"/>
  </core>

  <extension encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" 
        ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
    <files>
      <location>occurrence.txt</location>
    </files> 
    <coreid index="0"/>
    <field index="1" term="http://rs.tdwg.org/dwc/terms/eventID"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/occurrenceID"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
    <field index="4" term="https://dwc.tdwg.org/list/#dwc_identificationVerificationStatus"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/scientificNameID"/>
    <field index="7" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
    <field index="8" term="http://rs.tdwg.org/dwc/terms/occurrenceStatus"/>
  </extension>
"""
_meta_emofs_with_computations = r"""
  <extension encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" 
        ignoreHeaderLines="1" rowType="http://rs.iobis.org/obis/terms/ExtendedMeasurementOrFact">
    <files>
      <location>extendedmeasurementorfact.txt</location>
    </files> 
    <coreid index="0"/>
    <field index="1" term="http://rs.tdwg.org/dwc/terms/occurrenceID"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/measurementValue"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/measurementType"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/measurementUnit"/>
    <field index="5" term="http://rs.iobis.org/obis/terms/measurementTypeID"/>
    <field index="6" term="http://rs.iobis.org/obis/terms/measurementUnitID"/>
  </extension>
</archive>

"""
# No occurence emof -> 2 columns less
_meta_emofs_without_computations = r"""
  <extension encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" 
        ignoreHeaderLines="1" rowType="http://rs.iobis.org/obis/terms/ExtendedMeasurementOrFact">
    <files>
      <location>extendedmeasurementorfact.txt</location>
    </files> 
    <coreid index="0"/>
    <field index="1" term="http://rs.tdwg.org/dwc/terms/occurrenceID"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/measurementValue"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/measurementType"/>
    <field index="4" term="http://rs.iobis.org/obis/terms/measurementTypeID"/>
  </extension>
</archive>

"""
_event = r"""
id	eventID	type	institutionCode	datasetName	eventDate	decimalLatitude	decimalLongitude	minimumDepthInMeters	maximumDepthInMeters
m106_mn01_n1_sml	m106_mn01_n1_sml	sample	IMEV	EMODNET test collection	2014-04-20T04:20:00Z	18.000000	-24.416667	600.0	1000.0
m106_mn01_n2_sml	m106_mn01_n2_sml	sample	IMEV	EMODNET test collection	2014-04-20T04:20:00Z	18.000000	-24.416667	300.0	600.0
m106_mn01_n3_sml	m106_mn01_n3_sml	sample	IMEV	EMODNET test collection	2014-04-20T04:20:00Z/2014-04-21T04:20:00Z	18.000000	-24.416667	300.0	600.0
m106_mn04_n4_sml	m106_mn04_n4_sml	sample	IMEV	EMODNET test collection	2014-04-20T04:20:00Z	18.000000	-24.416667	600.0	1000.0
m106_mn04_n5_sml	m106_mn04_n5_sml	sample	IMEV	EMODNET test collection	2014-04-20T04:20:00Z	18.000000	-24.416667	600.0	1000.0
m106_mn04_n6_sml	m106_mn04_n6_sml	sample	IMEV	EMODNET test collection	2014-04-20T04:20:00Z	18.000000	-24.416667	600.0	1000.0
"""
_occurence = r"""
id	eventID	occurrenceID	basisOfRecord	identificationVerificationStatus	scientificName	scientificNameID	kingdom	occurrenceStatus
m106_mn01_n1_sml	m106_mn01_n1_sml	m106_mn01_n1_sml_78418	MachineObservation	ValidatedByHuman	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586	Animalia	present
m106_mn01_n1_sml	m106_mn01_n1_sml	m106_mn01_n1_sml_45072	MachineObservation	ValidatedByHuman	Cyclopoida	urn:lsid:marinespecies.org:taxname:1101	Animalia	present
m106_mn01_n3_sml	m106_mn01_n3_sml	m106_mn01_n3_sml_56693	MachineObservation	ValidatedByHuman	Actinopterygii	urn:lsid:marinespecies.org:taxname:10194	Animalia	present
m106_mn01_n3_sml	m106_mn01_n3_sml	m106_mn01_n3_sml_P_56693	MachineObservation	PredictedByMachine	Actinopterygii	urn:lsid:marinespecies.org:taxname:10194	Animalia	present
m106_mn04_n4_sml	m106_mn04_n4_sml	m106_mn04_n4_sml_78418	MachineObservation	ValidatedByHuman	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586	Animalia	present
m106_mn04_n5_sml	m106_mn04_n5_sml	m106_mn04_n5_sml_78418	MachineObservation	ValidatedByHuman	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586	Animalia	present
m106_mn04_n6_sml	m106_mn04_n6_sml	m106_mn04_n6_sml_45072	MachineObservation	ValidatedByHuman	Cyclopoida	urn:lsid:marinespecies.org:taxname:1101	Animalia	present
m106_mn04_n6_sml	m106_mn04_n6_sml	m106_mn04_n6_sml_78418	MachineObservation	ValidatedByHuman	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586	Animalia	present
"""
# _occurence_with_absent = r"""m106_mn01_n2_sml	m106_mn01_n2_sml	m106_mn01_n2_sml_45072	MachineObservation	Cyclopoida	urn:lsid:marinespecies.org:taxname:1101	0	Animalia	absent
# m106_mn01_n2_sml	m106_mn01_n2_sml	m106_mn01_n2_sml_78418	MachineObservation	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586	0	Animalia	absent
# m106_mn01_n3_sml	m106_mn01_n3_sml	m106_mn01_n3_sml_45072	MachineObservation	Cyclopoida	urn:lsid:marinespecies.org:taxname:1101	0	Animalia	absent
# m106_mn01_n3_sml	m106_mn01_n3_sml	m106_mn01_n3_sml_78418	MachineObservation	Oncaeidae	urn:lsid:marinespecies.org:taxname:128586	0	Animalia	absent
# """
_occurence_with_absent = ""
_emofs = r"""
id	occurrenceID	measurementValue	measurementType	measurementUnit	measurementTypeID	measurementUnitID
m106_mn01_n1_sml	m106_mn01_n1_sml_78418	2	Count (in assayed sample) of biological entity specified elsewhere		http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/	
m106_mn01_n1_sml	m106_mn01_n1_sml_78418	0.04	Abundance of biological entity specified elsewhere per unit volume of the water body	Number per cubic metre	http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL01/	http://vocab.nerc.ac.uk/collection/P06/current/UPMM/
m106_mn01_n1_sml	m106_mn01_n1_sml_78418	1992121.390848	Biovolume of biological entity specified elsewhere per unit volume of the water body	Cubic millimetres per cubic metre	http://vocab.nerc.ac.uk/collection/P01/current/CVOLUKNB/	http://vocab.nerc.ac.uk/collection/P06/current/CMCM/
m106_mn01_n1_sml	m106_mn01_n1_sml_45072	1	Count (in assayed sample) of biological entity specified elsewhere		http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/	
m106_mn01_n1_sml	m106_mn01_n1_sml_45072	0.02	Abundance of biological entity specified elsewhere per unit volume of the water body	Number per cubic metre	http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL01/	http://vocab.nerc.ac.uk/collection/P06/current/UPMM/
m106_mn01_n1_sml	m106_mn01_n1_sml_45072	355604.586438	Biovolume of biological entity specified elsewhere per unit volume of the water body	Cubic millimetres per cubic metre	http://vocab.nerc.ac.uk/collection/P01/current/CVOLUKNB/	http://vocab.nerc.ac.uk/collection/P06/current/CMCM/
m106_mn01_n1_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name		https://vocab.nerc.ac.uk/collection/P06/current/XXXX/	
m106_mn01_n2_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name		https://vocab.nerc.ac.uk/collection/P06/current/XXXX/	
m106_mn01_n3_sml	m106_mn01_n3_sml_56693	1	Count (in assayed sample) of biological entity specified elsewhere		http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/	
m106_mn01_n3_sml	m106_mn01_n3_sml_56693	0.02	Abundance of biological entity specified elsewhere per unit volume of the water body	Number per cubic metre	http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL01/	http://vocab.nerc.ac.uk/collection/P06/current/UPMM/
m106_mn01_n3_sml	m106_mn01_n3_sml_56693	200279.314771	Biovolume of biological entity specified elsewhere per unit volume of the water body	Cubic millimetres per cubic metre	http://vocab.nerc.ac.uk/collection/P01/current/CVOLUKNB/	http://vocab.nerc.ac.uk/collection/P06/current/CMCM/
m106_mn01_n3_sml	m106_mn01_n3_sml_P_56693	1	Count (in assayed sample) of biological entity specified elsewhere		http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/	
m106_mn01_n3_sml	m106_mn01_n3_sml_P_56693	0.02	Abundance of biological entity specified elsewhere per unit volume of the water body	Number per cubic metre	http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL01/	http://vocab.nerc.ac.uk/collection/P06/current/UPMM/
m106_mn01_n3_sml	m106_mn01_n3_sml_P_56693	194359.383023	Biovolume of biological entity specified elsewhere per unit volume of the water body	Cubic millimetres per cubic metre	http://vocab.nerc.ac.uk/collection/P01/current/CVOLUKNB/	http://vocab.nerc.ac.uk/collection/P06/current/CMCM/
m106_mn01_n3_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name		https://vocab.nerc.ac.uk/collection/P06/current/XXXX/	
m106_mn04_n4_sml	m106_mn04_n4_sml_78418	1	Count (in assayed sample) of biological entity specified elsewhere		http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/	
m106_mn04_n4_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name		https://vocab.nerc.ac.uk/collection/P06/current/XXXX/	
m106_mn04_n5_sml	m106_mn04_n5_sml_78418	1	Count (in assayed sample) of biological entity specified elsewhere		http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/	
m106_mn04_n5_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name		https://vocab.nerc.ac.uk/collection/P06/current/XXXX/	
m106_mn04_n6_sml	m106_mn04_n6_sml_45072	1	Count (in assayed sample) of biological entity specified elsewhere		http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/	
m106_mn04_n6_sml	m106_mn04_n6_sml_78418	1	Count (in assayed sample) of biological entity specified elsewhere		http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/	
m106_mn04_n6_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name		https://vocab.nerc.ac.uk/collection/P06/current/XXXX/	
"""
# _emofs_no_comp = r"""
# id	measurementValue	measurementType	measurementUnit	measurementTypeID	measurementUnitID
# m106_mn01_n1_sml	100.0	Volume sampled of the water body	Cubic metres	http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/	http://vocab.nerc.ac.uk/collection/P06/current/MCUB/
# m106_mn01_n2_sml	100.0	Volume sampled of the water body	Cubic metres	http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/	http://vocab.nerc.ac.uk/collection/P06/current/MCUB/
# m106_mn01_n3_sml	100.0	Volume sampled of the water body	Cubic metres	http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/	http://vocab.nerc.ac.uk/collection/P06/current/MCUB/
# """
_emofs_no_comp = r"""
id	occurrenceID	measurementValue	measurementType	measurementTypeID
m106_mn01_n1_sml	m106_mn01_n1_sml_78418	2	Count (in assayed sample) of biological entity specified elsewhere	http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/
m106_mn01_n1_sml	m106_mn01_n1_sml_45072	1	Count (in assayed sample) of biological entity specified elsewhere	http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/
m106_mn01_n1_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name	https://vocab.nerc.ac.uk/collection/P06/current/XXXX/
m106_mn01_n2_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name	https://vocab.nerc.ac.uk/collection/P06/current/XXXX/
m106_mn01_n3_sml	m106_mn01_n3_sml_56693	1	Count (in assayed sample) of biological entity specified elsewhere	http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/
m106_mn01_n3_sml	m106_mn01_n3_sml_P_56693	1	Count (in assayed sample) of biological entity specified elsewhere	http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/
m106_mn01_n3_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name	https://vocab.nerc.ac.uk/collection/P06/current/XXXX/
m106_mn04_n4_sml	m106_mn04_n4_sml_78418	1	Count (in assayed sample) of biological entity specified elsewhere	http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/
m106_mn04_n4_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name	https://vocab.nerc.ac.uk/collection/P06/current/XXXX/
m106_mn04_n5_sml	m106_mn04_n5_sml_78418	1	Count (in assayed sample) of biological entity specified elsewhere	http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/
m106_mn04_n5_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name	https://vocab.nerc.ac.uk/collection/P06/current/XXXX/
m106_mn04_n6_sml	m106_mn04_n6_sml_45072	1	Count (in assayed sample) of biological entity specified elsewhere	http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/
m106_mn04_n6_sml	m106_mn04_n6_sml_78418	1	Count (in assayed sample) of biological entity specified elsewhere	http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/
m106_mn04_n6_sml		http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/	Imaging instrument name	https://vocab.nerc.ac.uk/collection/P06/current/XXXX/
"""
ref_zip = {"event.txt": _event,
           "eml.xml": _eml,
           "extendedmeasurementorfact.txt": _emofs,
           "meta.xml": _meta + _meta_emofs_with_computations,
           "occurrence.txt": _occurence}
with_zeroes_zip = {"event.txt": _event,
                   "eml.xml": _eml,
                   "extendedmeasurementorfact.txt": _emofs,
                   "meta.xml": _meta + _meta_emofs_with_computations,
                   "occurrence.txt": _occurence + _occurence_with_absent}
no_computations_zip = {"event.txt": _event,
                       "eml.xml": _eml,
                       "extendedmeasurementorfact.txt": _emofs_no_comp,
                       "meta.xml": _meta + _meta_emofs_without_computations,
                       "occurrence.txt": _occurence}
