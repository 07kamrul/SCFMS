"""Conversions between GeoJSON (over the API) and PostGIS geometry (in the DB).

First spatial code in the repo — geoalchemy2/shapely are pinned in
requirements.txt but unused until this module.
"""
from __future__ import annotations

from typing import Any

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point, mapping, shape
from shapely.geometry.polygon import Polygon


def to_geojson_polygon(geom: WKBElement | None) -> dict[str, Any] | None:
    """Convert a stored PostGIS geometry to a GeoJSON Polygon dict."""
    if geom is None:
        return None
    return mapping(to_shape(geom))


def geojson_polygon_to_wkb(geojson: dict[str, Any]) -> WKBElement:
    """Convert a GeoJSON Polygon dict to a PostGIS geometry for storage.

    Raises ValueError if the ring is degenerate or self-intersecting.
    """
    polygon: Polygon = shape(geojson)
    if not isinstance(polygon, Polygon):
        raise ValueError("Boundary must be a GeoJSON Polygon.")
    if not polygon.is_valid:
        raise ValueError("Boundary polygon is invalid (self-intersecting or degenerate).")
    return from_shape(polygon, srid=4326)


def latlng_to_point_wkb(lat: float, lng: float) -> WKBElement:
    """GeoJSON/GIS convention is (lng, lat) — shapely Point takes (x, y)."""
    return from_shape(Point(lng, lat), srid=4326)


def point_to_latlng(geom: WKBElement | None) -> tuple[float, float] | None:
    if geom is None:
        return None
    point: Point = to_shape(geom)
    return (point.y, point.x)
