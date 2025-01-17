"""Diffsync adapter class for Nautobot."""
# pylint: disable=import-error,no-name-in-module
import os
import requests
from models import RegionModel, SiteModel
from diffsync import DiffSync


NAUTOBOT_URL = os.getenv("NAUTOBOT_URL", "https://demo.nautobot.com")
NAUTOBOT_TOKEN = os.getenv("NAUTOBOT_TOKEN", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")


class RegionNautobotModel(RegionModel):
    """Implementation of Region create/update/delete methods for updating remote Nautobot data."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a new Region record in remote Nautobot.

        Args:
            diffsync (NautobotRemote): DiffSync adapter owning this Region
            ids (dict): Initial values for this model's _identifiers
            attrs (dict): Initial values for this model's _attributes
        """
        data = {
            "name": ids["name"],
            "slug": attrs["slug"],
        }
        if attrs["description"]:
            data["description"] = attrs["description"]
        if attrs["parent_name"]:
            data["parent"] = str(diffsync.get(diffsync.region, attrs["parent_name"]).pk)
        diffsync.post("/api/dcim/regions/", data)
        return super().create(diffsync, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update an existing Region record in remote Nautobot.

        Args:
            attrs (dict): Updated values for this record's _attributes
        """
        data = {}
        if "slug" in attrs:
            data["slug"] = attrs["slug"]
        if "description" in attrs:
            data["description"] = attrs["description"]
        if "parent_name" in attrs:
            if attrs["parent_name"]:
                data["parent"] = str(self.diffsync.get(self.diffsync.region, attrs["parent_name"]).pk)
            else:
                data["parent"] = None
        self.diffsync.patch(f"/api/dcim/regions/{self.pk}/", data)
        return super().update(attrs)

    def delete(self):  # pylint: disable= useless-super-delegation
        """Delete an existing Region record from remote Nautobot."""
        # self.diffsync.delete(f"/api/dcim/regions/{self.pk}/")
        return super().delete()


class SiteNautobotModel(SiteModel):
    """Implementation of Site create/update/delete methods for updating remote Nautobot data."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a new Site in remote Nautobot.

        Args:
            diffsync (NautobotRemote): DiffSync adapter owning this Site
            ids (dict): Initial values for this model's _identifiers
            attrs (dict): Initial values for this model's _attributes
        """
        diffsync.post(
            "/api/dcim/sites/",
            {
                "name": ids["name"],
                "slug": attrs["slug"],
                "description": attrs["description"],
                "status": attrs["status_slug"],
                "region": {"name": attrs["region_name"]} if attrs["region_name"] else None,
                "latitude": attrs["latitude"],
                "longitude": attrs["longitude"],
            },
        )
        return super().create(diffsync, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update an existing Site record in remote Nautobot.

        Args:
            attrs (dict): Updated values for this record's _attributes
        """
        data = {}
        if "slug" in attrs:
            data["slug"] = attrs["slug"]
        if "description" in attrs:
            data["description"] = attrs["description"]
        if "status_slug" in attrs:
            data["status"] = attrs["status_slug"]
        if "region_name" in attrs:
            if attrs["region_name"]:
                data["region"] = {"name": attrs["region_name"]}
            else:
                data["region"] = None
        if "latitude" in attrs:
            data["latitude"] = attrs["latitude"]
        if "longitude" in attrs:
            data["longitude"] = attrs["longitude"]
        self.diffsync.patch(f"/api/dcim/sites/{self.pk}/", data)
        return super().update(attrs)

    def delete(self):  # pylint: disable= useless-super-delegation
        """Delete an existing Site record from remote Nautobot."""
        # self.diffsync.delete(f"/api/dcim/sites/{self.pk}/")
        return super().delete()


class NautobotRemote(DiffSync):
    """DiffSync adapter class for loading data from a remote Nautobot instance using Python requests."""

    # Model classes used by this adapter class
    region = RegionNautobotModel
    site = SiteNautobotModel

    # Top-level class labels, i.e. those classes that are handled directly rather than as children of other models
    top_level = ("region", "site")

    def __init__(self, *args, url=NAUTOBOT_URL, token=NAUTOBOT_TOKEN, **kwargs):
        """Instantiate this class, but do not load data immediately from the remote system.

        Args:
            url (str): URL of the remote Nautobot system
            token (str): REST API authentication token
            job (Job): The running Job instance that owns this DiffSync adapter instance
        """
        super().__init__(*args, **kwargs)
        if not url or not token:
            raise ValueError("Both url and token must be specified!")
        self.url = url
        self.token = token
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Token {self.token}",
        }

    def load(self):
        """Load Region and Site data from the remote Nautobot instance."""
        region_data = requests.get(f"{self.url}/api/dcim/regions/", headers=self.headers, params={"limit": 0}).json()
        regions = region_data["results"]
        while region_data["next"]:
            region_data = requests.get(region_data["next"], headers=self.headers, params={"limit": 0}).json()
            regions.extend(region_data["results"])

        for region_entry in regions:
            region = self.region(
                name=region_entry["name"],
                slug=region_entry["slug"],
                description=region_entry["description"] or None,
                parent_name=region_entry["parent"]["name"] if region_entry["parent"] else None,
                pk=region_entry["id"],
            )
            self.add(region)

        site_data = requests.get(f"{self.url}/api/dcim/sites/", headers=self.headers, params={"limit": 0}).json()
        sites = site_data["results"]
        while site_data["next"]:
            site_data = requests.get(site_data["next"], headers=self.headers, params={"limit": 0}).json()
            sites.extend(site_data["results"])

        for site_entry in sites:
            site = self.site(
                name=site_entry["name"],
                slug=site_entry["slug"],
                status_slug=site_entry["status"]["value"] if site_entry["status"] else "active",
                region_name=site_entry["region"]["name"] if site_entry["region"] else None,
                description=site_entry["description"],
                longitude=site_entry["longitude"],
                latitude=site_entry["latitude"],
                pk=site_entry["id"],
            )
            self.add(site)

    def post(self, path, data):
        """Send an appropriately constructed HTTP POST request."""
        response = requests.post(f"{self.url}{path}", headers=self.headers, json=data)
        response.raise_for_status()
        return response

    def patch(self, path, data):
        """Send an appropriately constructed HTTP PATCH request."""
        response = requests.patch(f"{self.url}{path}", headers=self.headers, json=data)
        response.raise_for_status()
        return response

    def delete(self, path):
        """Send an appropriately constructed HTTP DELETE request."""
        response = requests.delete(f"{self.url}{path}", headers=self.headers)
        response.raise_for_status()
        return response
