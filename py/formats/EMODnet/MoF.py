# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
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


class Abundance(DwC_ExtendedMeasurementOrFact):
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


class SampleAperture(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Sampling device aperture length",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/Q01/current/Q0100014/",
            measurementValue=value,
            measurementUnit="m",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/ULAA/"
        )


class SamplingInstrumentName(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Sampling instrument name",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/Q01/current/Q0100002/",
            measurementValue=value,  # e.g."Otter-Trawl Maireta System (OTMS)",
        )


class SamplingMeshSize(DwC_ExtendedMeasurementOrFact):
    def __init__(self, event_id: str, value: str):
        super().__init__(
            eventID=event_id,
            measurementType="Sampling net mesh size",
            measurementTypeID="http://vocab.nerc.ac.uk/collection/Q01/current/Q0100015/",
            measurementValue=value,
            measurementUnit="mm",
            measurementUnitID="http://vocab.nerc.ac.uk/collection/P06/current/UXMM/"
        )
