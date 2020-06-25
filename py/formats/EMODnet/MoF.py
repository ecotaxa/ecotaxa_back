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


from formats.EMODnet.models import DwC_ExtendedMeasurementOrFact


class Count(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, occurrence_id: str, value: str):
        super().__init__(
            eventID=event_id,
            occurrenceID=occurrence_id,
            measurementType="Count (in assayed sample) of biological entity specified elsewhere",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/",
            measurementValue=value
        )


class AbundancePerUnitAreaOfTheBed(DwC_ExtendedMeasurementOrFact):
    # Also:
    # Abundance of biological entity specified elsewhere per unit of sampling time in the water body
    # http://vocab.nerc.ac.uk/collection/P01/current/ADBIOL02/
    def __init__(self, event_id: str, occurrence_id: str, value: str):
        super().__init__(
            eventID=event_id,
            occurrenceID=occurrence_id,
            measurementType="Abundance of biological entity specified elsewhere per unit area of the bed",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL02/",
            measurementValue=value,
            measurementUnit="N/km2",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/NPKM/"
        )


class BioMass(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, occurrence_id: str, value: str):
        super().__init__(
            eventID=event_id,
            occurrenceID=occurrence_id,
            measurementType="Wet weight biomass of biological entity specified elsewhere per unit area of the bed",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL05/",
            measurementValue=value,
            measurementUnit="kg/km2",
            measurementUnitID=""
        )


class SamplingInstrumentName(DwC_ExtendedMeasurementOrFact):
    # One of: http://vocab.nerc.ac.uk/collection/L22/current/
    # e.g. http://vocab.nerc.ac.uk/collection/L22/current/TOOL1252/
    def __init__(self, event_id: str, value: str, value_id: str):
        super().__init__(
            eventID=event_id,
            measurementType="Sampling instrument name",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/Q01/current/Q0100002/",
            measurementValue=value,  # e.g."Otter-Trawl Maireta System (OTMS)",
            measurementValueID=value_id
        )


class SamplingSpeed(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Speed of measurement platform relative to ground surface {speed over ground}",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/P01/current/APSAZZ01/",
            measurementValue=value,
            measurementUnit="knots",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/UKNT/"
        )


class SampleDeviceAperture(DwC_ExtendedMeasurementOrFact):
    # also width in http://vocab.nerc.ac.uk/collection/Q01/current/Q0100013/
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Sampling device aperture length",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/Q01/current/Q0100014/",
            measurementValue=value,
            measurementUnit="m",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/ULAA/"
        )


class SampleDeviceDiameter(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Sampling device aperture diameter",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/Q01/current/Q0100012/",
            measurementValue=value,
            measurementUnit="m",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/ULAA/"
        )


class SamplingNetMeshSize(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Sampling net mesh size",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/Q01/current/Q0100015/",
            measurementValue=value,
            measurementUnit="mm",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/UXMM/"
        )
