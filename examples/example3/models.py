from typing import List, Optional
from diffsync import DiffSyncModel


class Region(DiffSyncModel):
    """Example model of a geographic region."""

    _modelname = "region"
    _identifiers = ("slug",)
    _attributes = ("name",)

    # By listing country as a child to Region
    # DiffSync will be able to recursively compare all regions including all their children
    _children = {"country": "countries"}

    slug: str
    name: str
    countries: List[str] = list()


class Country(DiffSyncModel):
    """Example model of a Country.

    A must be part of a region and can be also associated with a subregion.
    """

    _modelname = "country"
    _identifiers = ("slug",)
    _attributes = ("name", "region", "subregion")

    slug: str
    name: str
    region: str
    subregion: Optional[str]