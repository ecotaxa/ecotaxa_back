from typing import Optional, Any

from pydantic import model_validator
from typing_extensions import TypedDict

from API_models.helpers.TypedDictToModel import typed_dict_to_model
from helpers.pydantic import Field, DescriptiveModel


class ProjectFiltersDict(TypedDict, total=False):
    taxo: Optional[str]
    """ Coma-separated list of numeric taxonomy/category ids. Only include objects classified with one of them """
    taxochild: Optional[str]
    """ If 'Y' and taxo is set, also include children of each member of 'taxo' list in taxonomy tree """
    statusfilter: Optional[str]
    """ Include objects with given status:
          'NV': Not validated 
          'PV': Predicted or Validated 
          'PVD': Predicted or Validated or Dubious
          'NVM': Validated, but not by me 
          'VM': Validated by me 
          'U': Not classified
          'UP': Updatable by prediction 
           other: direct equality comparison with DB value, i.e. P V or D """
    MapN: Optional[str]
    MapW: Optional[str]
    MapE: Optional[str]
    MapS: Optional[str]
    """ If all 4 are set, include objects inside the defined bounding rectangle. """
    depthmin: Optional[str]
    depthmax: Optional[str]
    """ If both are set, include objects for which both depths (min and max) are inside the range """
    samples: Optional[str]
    """ Coma-separated list of sample IDs, include only objects for these samples """
    instrum: Optional[str]
    """ Instrument name, include objects for which sampling was done using this instrument """
    daytime: Optional[str]
    """ Coma-separated list of sun position values: 
         D for Day, U for Dusk, N for Night, A for Dawn (Aube in French) """
    month: Optional[str]
    """ Coma-separated list of month numbers, 1=Jan and so on """
    fromdate: Optional[str]
    """ Format is 'YYYY-MM-DD', include objects collected after this date """
    todate: Optional[str]
    """ Format is 'YYYY-MM-DD', include objects collected before this date """
    fromtime: Optional[str]
    """ Format is 'HH24:MM:SS', include objects collected after this time of day """
    totime: Optional[str]
    """ Format is 'HH24:MM:SS', include objects collected before this time of day """
    inverttime: Optional[str]
    """ If '1', include objects outside fromtime an totime range """
    validfromdate: Optional[str]
    """ Format is 'YYYY-MM-DD HH24:MI', include objects validated/set to dubious after this date+time """
    validtodate: Optional[str]
    """ Format is 'YYYY-MM-DD HH24:MI', include objects validated/set to dubious before this date+time """
    freenum: Optional[str]
    """ Numerical DB column in Object, as basis for the 2 following criteria. e.g. on04. Use oscore for classification score. """
    freenumst: Optional[str]
    """ Start of included range for the column defined by freenum, in which objects are included """
    freenumend: Optional[str]
    """ End of included range for the column defined by freenum, in which objects are included """
    freetxt: Optional[str]
    """ Textual DB column number as basis for following criteria 
            If starts with 's' then it's a text column in Sample
            If starts with 'a' then it's a text column in Acquisition 
            If starts with 'p' then it's a text column in Process 
            If starts with 'o' then it's a text column in Object 
        """
    freetxtval: Optional[str]
    """ Text to match in the column defined by freetxt, for an object to be included """
    filt_annot: Optional[str]
    """ Coma-separated list of annotator, i.e. person who validated the classification
        at any point in time. """
    filt_last_annot: Optional[str]
    """ Coma-separated list of annotator, i.e. person who validated the classification
        in last. """


class _ProjectFilters2Model(DescriptiveModel):
    taxo: Optional[str] = Field(
        title="Taxo",
        description="Coma-separated list of numeric taxonomy/category ids. Only include objects classified with one of them.",
        examples=["12,7654,5409"],
    )
    taxochild: Optional[str] = Field(
        title="Taxo child",
        description="If 'Y' and taxo is set, also include children of each member of 'taxo' list in taxonomy tree.",
        examples=["Y"],
    )
    statusfilter: Optional[str] = Field(
        title="",
        description="""Include objects with given status:
            'NV': Not validated 
            'PV': Predicted or Validated 
            'PVD': Predicted or Validated or Dubious
            'NVM': Validated, but not by me 
            'VM': Validated by me 
            'U': Not classified
            other: direct equality comparison with DB value 
        """,
        examples=["NV"],
        max_length=3,
    )
    MapN: Optional[str] = Field(
        title="Map North",
        description="If all 4 are set (MapN, MapW, MapE, MapS), include objects inside the defined bounding rectangle.",
        examples=[44.34],
    )
    MapW: Optional[str] = Field(
        title="Map West",
        description="If all 4 are set (MapN, MapW, MapE, MapS), include objects inside the defined bounding rectangle.",
        examples=[3.88],
    )
    MapE: Optional[str] = Field(
        title="Map East",
        description="If all 4 are set (MapN, MapW, MapE, MapS), include objects inside the defined bounding rectangle.",
        examples=[7.94],
    )
    MapS: Optional[str] = Field(
        title="Map South",
        description="If all 4 are set (MapN, MapW, MapE, MapS), include objects inside the defined bounding rectangle.",
        examples=[42.42],
    )
    depthmin: Optional[str] = Field(
        title="Depthmin",
        description="Positive values. If both are set (depthmin, depthmax), include objects for which both depths (min and max) are inside the range.",
        examples=["10"],
    )
    depthmax: Optional[str] = Field(
        title="Depthmax",
        description="Positive values. If both are set (depthmin, depthmax), include objects for which both depths (min and max) are inside the range.",
        examples=["110"],
    )
    samples: Optional[str] = Field(
        title="Samples",
        description="Coma-separated list of sample IDs, include only objects for these samples.",
        examples=["10987,3456,987,38"],
    )
    instrum: Optional[str] = Field(
        title="Instrument",
        description="Instrument name, include objects for which sampling was done using this instrument.",
        examples=["uvp5"],
    )
    daytime: Optional[str] = Field(
        title="Day time",
        description="Coma-separated list of sun position values: D for Day, U for Dusk, N for Night, A for Dawn (Aube in French).",
        examples=["N,A"],
    )
    month: Optional[str] = Field(
        title="Month",
        description="Coma-separated list of month numbers, 1=Jan and so on.",
        examples=["11,12"],
    )
    fromdate: Optional[str] = Field(
        title="From date",
        description="Format is 'YYYY-MM-DD', include objects collected after this date.",
        examples=["2020-10-09"],
    )
    todate: Optional[str] = Field(
        title="To date",
        description="Format is 'YYYY-MM-DD', include objects collected before this date.",
        examples=["2021-10-09"],
    )
    fromtime: Optional[str] = Field(
        title="From time",
        description="Format is 'HH24:MM:SS', include objects collected after this time of day.",
        examples=["1:17:00"],
    )
    totime: Optional[str] = Field(
        title="To time",
        description="Format is 'HH24:MM:SS', include objects collected before this time of day.",
        examples=["23:32:00"],
    )
    inverttime: Optional[str] = Field(
        title="Invert time",
        description="If '1', include objects outside fromtime and totime range.",
        examples=["0"],
    )
    validfromdate: Optional[str] = Field(
        title="Valid from date",
        description="Format is 'YYYY-MM-DD HH24:MI', include objects validated/set to dubious after this date+time.",
        examples=["2020-10-09 10:00:00"],
    )
    validtodate: Optional[str] = Field(
        title="Valid to date",
        description="Format is 'YYYY-MM-DD HH24:MI', include objects validated/set to dubious before this date+time.",
        examples=["2021-10-09 10:00:00"],
    )
    freenum: Optional[str] = Field(
        title="Free num",
        description="Numerical DB column number in Object as basis for the 2 following criteria (freenumst, freenumend).",
        examples=["n01"],
    )
    freenumst: Optional[str] = Field(
        title="Freenum start",
        description="Start of included range for the column defined by freenum, in which objects are included.",
        examples=["0"],
    )
    freenumend: Optional[str] = Field(
        title="Free num end",
        description="End of included range for the column defined by freenum, in which objects are included.",
        examples=["999999"],
    )
    freetxt: Optional[str] = Field(
        title="Free text",
        description=""" Textual DB column number as basis for following criteria (freetxtval)
            If starts with 's' then it's a text column in Sample
            If starts with 'a' then it's a text column in Acquisition 
            If starts with 'p' then it's a text column in Process 
            If starts with 'o' then it's a text column in Object .
        """,
        examples=["p01"],
    )
    freetxtval: Optional[str] = Field(
        title="Free text val",
        description="Text to match in the column defined by freetxt, for an object to be include.",
        examples=["zooprocess"],
    )
    filt_annot: Optional[str] = Field(
        title="Filter annotator",
        description="Coma-separated list of annotators, i.e. persons who validated the classification at any point in time.",
        examples=[["34,67,67"]],
    )
    filt_last_annot: Optional[str] = Field(
        title="Filter last annotator",
        description="Coma-separated list of annotators, i.e. persons who validated the classification in last.",
        examples=["34,67"],
    )

    class Config:
        json_schema_extra = {
            "title": "Project filters Model",
            "description": "How to reduce project data.",
        }


ProjectFiltersModel = typed_dict_to_model(ProjectFiltersDict, _ProjectFilters2Model)


class ProjectFilters(ProjectFiltersModel):
    def base(self) -> ProjectFiltersDict:
        return self.model_dump()  # type: ignore

    def min_base(self) -> ProjectFiltersDict:
        return {k: v for k, v in self.model_dump().items() if v}  # type: ignore


class LaxProjectFilters(ProjectFilters):
    @model_validator(mode="before")
    @classmethod
    def allow_empty_list_or_none(cls, v: Any) -> Any:
        if v == [] or v is None:
            return {}
        return v
