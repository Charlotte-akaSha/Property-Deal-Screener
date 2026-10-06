"""Look up walk-to-station and train-to-city-center via Google Maps (not the listing)."""

from __future__ import annotations

import json
import math
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import certifi

from utils import load_env

MAPS_MAX_RETRIES = 4
MAPS_RETRY_BASE_DELAY_SEC = 2.0
TRANSIENT_MAPS_HTTP_CODES = {429, 500, 502, 503, 504}
TRANSIENT_MAPS_API_STATUSES = frozenset({"OVER_QUERY_LIMIT", "UNKNOWN_ERROR"})

DEFAULT_CITY_CENTERS = {
    "New York": "Grand Central Terminal, New York, NY",
    "Chicago": "Millennium Station, Chicago, IL",
    "Columbus": "Downtown Columbus, OH",
}

DEFAULT_OSU_DESTINATION = "Ohio State University, Columbus, OH"

REGION_TIMEZONES = {
    "New York": "America/New_York",
    "Chicago": "America/Chicago",
    "Columbus": "America/New_York",
}

COLUMBUS_REGION = "Columbus"
BUS_STOP_TYPES = ("bus_stop", "transit_station")

COMMUTE_WEEKDAY = 0  # Monday
COMMUTE_HOUR = 8
COMMUTE_MINUTE = 0

# Bus stops also appear as transit_station — use rail types only.
RAIL_STATION_TYPES = ("train_station", "subway_station")


def _maps_key() -> str:
    load_env()
    key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GOOGLE_MAPS_API_KEY is missing. Enable Maps APIs in Google Cloud and add the key to .env."
        )
    return key


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _is_transient_maps_http_error(exc: urllib.error.HTTPError) -> bool:
    return exc.code in TRANSIENT_MAPS_HTTP_CODES


def _maps_request(service: str, params: dict[str, Any]) -> dict[str, Any]:
    params = {k: v for k, v in params.items() if v is not None}
    params["key"] = _maps_key()
    url = f"https://maps.googleapis.com/maps/api/{service}/json?{urllib.parse.urlencode(params)}"
    last_error: Exception | None = None
    for attempt in range(MAPS_MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=45, context=_ssl_context()) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            status = data.get("status")
            if status in ("OK", "ZERO_RESULTS"):
                return data
            if status in TRANSIENT_MAPS_API_STATUSES and attempt < MAPS_MAX_RETRIES - 1:
                time.sleep(MAPS_RETRY_BASE_DELAY_SEC * (2**attempt))
                continue
            message = data.get("error_message") or status
            raise RuntimeError(f"Google Maps API error ({service}): {message}")
        except urllib.error.HTTPError as exc:
            if _is_transient_maps_http_error(exc) and attempt < MAPS_MAX_RETRIES - 1:
                last_error = exc
                time.sleep(MAPS_RETRY_BASE_DELAY_SEC * (2**attempt))
                continue
            raise RuntimeError(
                f"Google Maps HTTP error ({service}): {exc.code} {exc.reason}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < MAPS_MAX_RETRIES - 1:
                last_error = exc
                time.sleep(MAPS_RETRY_BASE_DELAY_SEC * (2**attempt))
                continue
            raise RuntimeError(f"Google Maps request failed ({service}): {exc}") from exc
    raise RuntimeError(
        f"Google Maps API failed after {MAPS_MAX_RETRIES} retries ({service})"
    ) from last_error


def format_property_address(extracted: dict[str, Any]) -> str:
    parts = [
        extracted.get("address") or "",
        extracted.get("city") or "",
        extracted.get("state") or "",
        extracted.get("zip") or "",
    ]
    address = ", ".join(p.strip() for p in parts if p and str(p).strip())
    if not address:
        raise ValueError("Cannot look up transit: property address is missing after extraction.")
    return address


def city_center_for_region(sheet_tab: str | None) -> str:
    load_env()
    if sheet_tab:
        env_key = f"CITY_CENTER_{sheet_tab.upper().replace(' ', '_')}"
        override = os.getenv(env_key, "").strip()
        if override:
            return override
        if sheet_tab in DEFAULT_CITY_CENTERS:
            return DEFAULT_CITY_CENTERS[sheet_tab]
    default = os.getenv("CITY_CENTER_DEFAULT", "").strip()
    if default:
        return default
    if sheet_tab:
        raise ValueError(
            f"No city center configured for region '{sheet_tab}'. "
            f"Set CITY_CENTER_{sheet_tab.upper().replace(' ', '_')} in .env."
        )
    raise ValueError("Region (sheet tab) is required for train-to-city-center lookup.")


def _region_timezone(sheet_tab: str | None) -> ZoneInfo:
    tz_name = REGION_TIMEZONES.get(sheet_tab or "", "America/New_York")
    return ZoneInfo(tz_name)


def _next_commute_departure(sheet_tab: str | None) -> tuple[int, str]:
    """Next Monday 8:00 AM in the region timezone (typical rush-hour commute)."""
    tz = _region_timezone(sheet_tab)
    now = datetime.now(tz)
    days_ahead = (COMMUTE_WEEKDAY - now.weekday()) % 7
    departure = (now + timedelta(days=days_ahead)).replace(
        hour=COMMUTE_HOUR, minute=COMMUTE_MINUTE, second=0, microsecond=0
    )
    if departure <= now:
        departure += timedelta(days=7)
    label = departure.strftime("%a %-I:%M %p %Z").replace("  ", " ")
    return int(departure.timestamp()), label


def geocode_address(address: str) -> tuple[float, float]:
    data = _maps_request("geocode", {"address": address})
    if not data.get("results"):
        raise RuntimeError(f"Could not geocode address: {address}")
    loc = data["results"][0]["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _find_nearest_rail_station(lat: float, lng: float) -> dict[str, Any]:
    """Nearest commuter-rail or subway station (excludes bus stops)."""
    best: dict[str, Any] | None = None
    best_dist = float("inf")
    for place_type in RAIL_STATION_TYPES:
        data = _maps_request(
            "place/nearbysearch",
            {
                "location": f"{lat},{lng}",
                "rankby": "distance",
                "type": place_type,
            },
        )
        for place in data.get("results") or []:
            loc = place["geometry"]["location"]
            dist = _haversine_miles(lat, lng, float(loc["lat"]), float(loc["lng"]))
            if dist < best_dist:
                best_dist = dist
                best = {
                    "name": place.get("name", "Unknown station"),
                    "place_id": place.get("place_id"),
                    "lat": float(loc["lat"]),
                    "lng": float(loc["lng"]),
                    "distance_miles": round(dist, 2),
                    "station_type": place_type,
                }
    if not best:
        raise RuntimeError("No nearby train or subway station found for this address.")
    return best


def _format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} mins"
    hours, mins = divmod(minutes, 60)
    hour_label = "hour" if hours == 1 else "hours"
    if mins:
        return f"{hours} {hour_label} {mins} mins"
    return f"{hours} {hour_label}"


def _walking_to_station(property_address: str, station: dict[str, Any]) -> dict[str, Any]:
    dest = station["place_id"] or f"{station['lat']},{station['lng']}"
    data = _maps_request(
        "distancematrix",
        {
            "origins": property_address,
            "destinations": f"place_id:{dest}" if station.get("place_id") else dest,
            "mode": "walking",
        },
    )
    rows = data.get("rows") or []
    if not rows or not rows[0].get("elements"):
        raise RuntimeError("Walking distance lookup returned no results.")
    element = rows[0]["elements"][0]
    if element.get("status") != "OK":
        raise RuntimeError(f"Walking distance unavailable: {element.get('status')}")
    duration = element["duration"]
    distance = element["distance"]
    return {
        "text": f"{duration['text']} walk ({distance['text']})",
        "minutes": max(1, int(round(duration["value"] / 60))),
        "distance_text": distance["text"],
    }


def _transit_to_city_center(
    station: dict[str, Any],
    city_center: str,
    *,
    departure_time: int,
) -> dict[str, Any]:
    origin = f"{station['lat']},{station['lng']}"
    data = _maps_request(
        "directions",
        {
            "origin": origin,
            "destination": city_center,
            "mode": "transit",
            "departure_time": departure_time,
        },
    )
    routes = data.get("routes") or []
    if not routes:
        raise RuntimeError(f"No transit route found from {station['name']} to {city_center}.")
    leg = routes[0]["legs"][0]
    duration = leg["duration"]
    return {
        "text": duration["text"],
        "minutes": max(1, int(round(duration["value"] / 60))),
        "city_center": city_center,
    }


def osu_destination_for_region(sheet_tab: str | None) -> str:
    load_env()
    if sheet_tab == COLUMBUS_REGION:
        return os.getenv("CITY_CENTER_OSU_COLUMBUS", "").strip() or DEFAULT_OSU_DESTINATION
    return ""


def _find_nearest_bus_stop(lat: float, lng: float) -> dict[str, Any]:
    """Nearest COTA-relevant stop (bus_stop or transit_station)."""
    best: dict[str, Any] | None = None
    best_dist = float("inf")
    for place_type in BUS_STOP_TYPES:
        data = _maps_request(
            "place/nearbysearch",
            {
                "location": f"{lat},{lng}",
                "rankby": "distance",
                "type": place_type,
            },
        )
        for place in data.get("results") or []:
            loc = place["geometry"]["location"]
            dist = _haversine_miles(lat, lng, float(loc["lat"]), float(loc["lng"]))
            if dist < best_dist:
                best_dist = dist
                best = {
                    "name": place.get("name", "Unknown stop"),
                    "place_id": place.get("place_id"),
                    "lat": float(loc["lat"]),
                    "lng": float(loc["lng"]),
                    "distance_miles": round(dist, 2),
                    "stop_type": place_type,
                }
    if not best:
        raise RuntimeError("No nearby bus or transit stop found for this address.")
    return best


def _count_transit_legs(route: dict[str, Any]) -> int:
    legs = route.get("legs") or []
    if not legs:
        return 0
    steps = legs[0].get("steps") or []
    return sum(1 for step in steps if step.get("travel_mode") == "TRANSIT")


def _transit_from_address(
    origin_address: str,
    destination: str,
    *,
    departure_time: int,
) -> dict[str, Any]:
    data = _maps_request(
        "directions",
        {
            "origin": origin_address,
            "destination": destination,
            "mode": "transit",
            "departure_time": departure_time,
        },
    )
    routes = data.get("routes") or []
    if not routes:
        raise RuntimeError(f"No transit route found from property to {destination}.")
    route = routes[0]
    leg = route["legs"][0]
    duration = leg["duration"]
    transfers = max(0, _count_transit_legs(route) - 1)
    return {
        "text": duration["text"],
        "minutes": max(1, int(round(duration["value"] / 60))),
        "destination": destination,
        "transfers": transfers,
    }


def lookup_transit_columbus(extracted: dict[str, Any], *, sheet_tab: str | None) -> dict[str, Any]:
    """Walk to nearest bus stop; property → Downtown and property → OSU via Google Maps transit."""
    address = format_property_address(extracted)
    city_center = city_center_for_region(sheet_tab)
    osu = osu_destination_for_region(sheet_tab)
    lat, lng = geocode_address(address)
    stop = _find_nearest_bus_stop(lat, lng)
    walk = _walking_to_station(address, stop)
    departure_unix, departure_label = _next_commute_departure(sheet_tab)
    downtown = _transit_from_address(
        address, city_center, departure_time=departure_unix
    )
    osu_trip = _transit_from_address(address, osu, departure_time=departure_unix)
    total_minutes = downtown["minutes"]
    return {
        "nearest_station": stop["name"],
        "nearest_stop": stop["name"],
        "walk_to_station": walk["text"],
        "walk_to_station_minutes": walk["minutes"],
        "train_to_city_center": downtown["text"],
        "train_to_city_center_minutes": downtown["minutes"],
        "transit_to_osu": osu_trip["text"],
        "transit_to_osu_minutes": osu_trip["minutes"],
        "transfers_to_downtown": downtown["transfers"],
        "transfers_to_osu": osu_trip["transfers"],
        "total_to_city_center": downtown["text"],
        "total_to_city_center_minutes": downtown["minutes"],
        "train_departure_at": departure_label,
        "city_center": city_center,
        "osu_destination": osu,
        "transit_mode": "cota_bus",
        "source": "google_maps",
    }


def lookup_transit(extracted: dict[str, Any], *, sheet_tab: str | None) -> dict[str, Any]:
    """
    Compute walk time to nearest rail/transit station and train time to regional city center.
    Uses Google Maps APIs — independent of listing text.
    """
    if sheet_tab == COLUMBUS_REGION:
        return lookup_transit_columbus(extracted, sheet_tab=sheet_tab)
    address = format_property_address(extracted)
    city_center = city_center_for_region(sheet_tab)
    lat, lng = geocode_address(address)
    station = _find_nearest_rail_station(lat, lng)
    walk = _walking_to_station(address, station)
    departure_unix, departure_label = _next_commute_departure(sheet_tab)
    train = _transit_to_city_center(
        station, city_center, departure_time=departure_unix
    )
    total_minutes = walk["minutes"] + train["minutes"]
    return {
        "nearest_station": station["name"],
        "walk_to_station": walk["text"],
        "walk_to_station_minutes": walk["minutes"],
        "train_to_city_center": train["text"],
        "train_to_city_center_minutes": train["minutes"],
        "total_to_city_center": _format_duration(total_minutes),
        "total_to_city_center_minutes": total_minutes,
        "train_departure_at": departure_label,
        "city_center": city_center,
        "source": "google_maps",
    }
