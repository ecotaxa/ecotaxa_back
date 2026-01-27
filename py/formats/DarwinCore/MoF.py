# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Other vocabulary found here and there:
#   not applicable
#   http://vocab.nerc.ac.uk/collection/P06/current/XXXX/
#   female
#   http://vocab.nerc.ac.uk/collection/S10/current/S102/
#   larvea
#   http://vocab.nerc.ac.uk/collection/S11/current/S1128/
#   Temperature of the water body (for ESD)
#   http://vocab.nerc.ac.uk/collection/P01/current/TEMPPR01/


from formats.DarwinCore.models import DwC_ExtendedMeasurementOrFact


class CountOfBiologicalEntity(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, occurrence_id: str, value: str):
        super().__init__(
            eventID=event_id,
            occurrenceID=occurrence_id,
            measurementType="Count (in assayed sample) of biological entity specified elsewhere",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/",
            measurementValue=value,
        )


class AbundancePerUnitAreaOfTheBed(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, occurrence_id: str, value: str):
        assert occurrence_id is not None
        super().__init__(
            eventID=event_id,
            occurrenceID=occurrence_id,
            measurementType="Abundance of biological entity specified elsewhere per unit area of the bed",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL02/",
            measurementValue=value,
            measurementUnit="N/km2",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/NPKM/",
        )


class AbundancePerUnitVolumeOfTheWaterBody(DwC_ExtendedMeasurementOrFact):
    # TODO: Duplicated in Vocabulary.py
    def __init__(self, event_id: str, occurrence_id: str, value: str):
        assert occurrence_id is not None
        super().__init__(
            eventID=event_id,
            occurrenceID=occurrence_id,
            measurementType="Abundance of biological entity specified elsewhere per unit volume of the water body",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL01/",
            measurementValue=value,
            measurementUnit="Number per cubic metre",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/UPMM/",
        )


class BiovolumeOfBiologicalEntity(DwC_ExtendedMeasurementOrFact):
    # TODO: Duplicated in Vocabulary.py
    def __init__(self, event_id: str, occurrence_id: str, value: str):
        assert occurrence_id is not None
        super().__init__(
            eventID=event_id,
            occurrenceID=occurrence_id,
            measurementType="Biovolume of biological entity specified elsewhere per unit volume of the water body",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/CVOLUKNB/",
            measurementValue=value,
            measurementUnit="Cubic millimetres per cubic metre",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/CMCM/",
        )


# class BioMass(DwC_ExtendedMeasurementOrFact):
#     def __init__(self, event_id: str, occurrence_id: str, value: str):
#         assert occurrence_id is not None
#         super().__init__(
#             eventID=event_id,
#             occurrenceID=occurrence_id,
#             measurementType="Wet weight biomass of biological entity specified elsewhere per unit area of the bed",
#             measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL05/",
#             measurementValue=value,
#             measurementUnit="kg/km2",
#             measurementUnitID=""
#         )


class SamplingInstrumentName(DwC_ExtendedMeasurementOrFact):
    # One of: http://vocab.nerc.ac.uk/collection/L22/current/
    # e.g. http://vocab.nerc.ac.uk/collection/L22/current/TOOL1252/
    def __init__(self, event_id: str, value: str, value_id: str):
        super().__init__(
            eventID=event_id,
            measurementType="Name of sampling instrument",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/NMSPINST/",
            measurementValue=value,  # e.g."Otter-Trawl Maireta System (OTMS)",
            measurementValueID=value_id,
        )


# class SamplingSpeed(DwC_ExtendedMeasurementOrFact):
#     def __init__(self, event_id: str, value: str):
#         super().__init__(
#             eventID=event_id,
#             measurementType="Speed of measurement platform relative to ground surface {speed over ground}",
#             measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/APSAZZ01/",
#             measurementValue=value,
#             measurementUnit="knots",
#             measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/UKNT/"
#         )


class SampleDeviceApertureAreaInSquareMeters(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Area of sample collector (aperture) {mouth area}",
            # The 2-dimensional size of the opening of a sampling device (e.g. a grab or a trawl);
            # the type of device is specified elsewhere.
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/MTHAREA1/",
            measurementValue=value,
            measurementUnit="Square metres",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/UMSQ/",
        )


class SampleDeviceApertureLength(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Height of sample collector (aperture) {mouth height}",
            # The larger dimension of the sampling area of a device with a rectangular aperture (e.g. a grab);
            # the type of device is specified elsewhere.
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/MTHHGHT1/",
            measurementValue=value,
            measurementUnit="Metres",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/ULAA/",
        )


class SampleDeviceDiameterInMeters(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Diameter of sample collector (aperture)",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/DSAMPA01/",
            measurementValue=value,
            measurementUnit="Metres",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/ULAA/",
        )


class SamplingNetMeshSizeInMillimeters(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Mesh size of sample collector",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/MSHSIZE1/",
            measurementValue=value,
            measurementUnit="Millimetres",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/UXMM/",
        )


class SamplingNetMeshSizeInMicrons(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Mesh size of sample collector",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/MSHSIZE1/",
            measurementValue=value,
            measurementUnit="Micrometres (microns)",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/UMIC/",
        )


class SampleVolumeInCubicMeters(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Volume sampled of the water body",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/",
            measurementValue=value,
            measurementUnit="Cubic metres",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/MCUB/",
        )


class ImagingInstrumentName(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Imaging instrument name",
            # Requested: https://github.com/nvs-vocabs/Q01/issues/1
            # Aug 22nd, 2024: Above issue is still open. Below field is NOK.
            # measurementTypeID="http://vocab.nerc.ac.uk/collection/P06/current/XXXX/",
            measurementTypeID="",
            measurementValue=value,
            measurementValueID=value_id,
            measurementUnit="Not applicable",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/XXXX/",
        )


class AnalyticalInstrumentName(DwC_ExtendedMeasurementOrFact):
    def __init__(self,event_id:str,value_id: str,value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Analytical instrument name",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/NMANINST/",
            measurementValue=value,
            measurementValueID=value_id,
            measurementUnit="Not applicable",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/XXXX/",
        )