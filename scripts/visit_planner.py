"""Cluster selected listings into visit days and suggest a timed itinerary.

Uses neighbourhood first, then geographic proximity (haversine). Days hold 5–8
stops when enough properties share an area; leftover stops spill to extra days.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

# Rough urban driving speed for straight-line distance between stops.
_KMH = 28.0
_MINUTES_PER_STOP = 35
_BUFFER_MIN = 12
_MAX_PER_DAY = 8
_MIN_PER_DAY = 5
_CLUSTER_KM = 8.0


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def drive_minutes(a: tuple[float, float], b: tuple[float, float]) -> int:
    km = haversine_km(a, b)
    minutes = (km / _KMH) * 60.0 + _BUFFER_MIN
    return max(8, int(round(minutes)))


@dataclass
class VisitStop:
    property_id: str
    label: str
    neighbourhood: str
    lat: float | None
    lon: float | None
    address: str = ""
    link: str = ""
    phone: str = ""
    agent_name: str = ""
    arrive: datetime | None = None
    depart: datetime | None = None
    travel_from_prev_min: int | None = None

    def coord(self) -> tuple[float, float] | None:
        if self.lat is None or self.lon is None:
            return None
        if math.isnan(self.lat) or math.isnan(self.lon):
            return None
        return (float(self.lat), float(self.lon))


@dataclass
class VisitDay:
    day_index: int
    title: str
    stops: list[VisitStop] = field(default_factory=list)

    @property
    def neighbourhoods(self) -> list[str]:
        seen: list[str] = []
        for stop in self.stops:
            name = stop.neighbourhood or "Unknown area"
            if name not in seen:
                seen.append(name)
        return seen


def _hood_key(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none", "—", "-"}:
        return ""
    return text


def stops_from_rows(
    rows: pd.DataFrame,
    coords: dict[str, tuple[float, float]],
    contacts: dict[str, dict[str, str]],
    *,
    label_for,
    address_for,
) -> list[VisitStop]:
    stops: list[VisitStop] = []
    for _, row in rows.iterrows():
        pid = str(row["Property ID"])
        latlon = coords.get(pid)
        contact = contacts.get(pid) or {}
        stops.append(
            VisitStop(
                property_id=pid,
                label=label_for(pid),
                neighbourhood=_hood_key(row.get("Neighbourhood display") or row.get("Neighbourhood")),
                lat=latlon[0] if latlon else None,
                lon=latlon[1] if latlon else None,
                address=address_for(pid),
                link=str(row.get("Link") or ""),
                phone=str(contact.get("phone") or ""),
                agent_name=str(contact.get("agent_name") or ""),
            )
        )
    return stops


def _greedy_order(stops: list[VisitStop]) -> list[VisitStop]:
    """Nearest-neighbour tour starting at the westernmost geocoded stop."""
    remaining = list(stops)
    located = [s for s in remaining if s.coord()]
    if len(located) < 2:
        return remaining
    start = min(located, key=lambda s: s.coord()[1])  # type: ignore[index]
    ordered = [start]
    remaining.remove(start)
    while remaining:
        last = ordered[-1].coord()
        if last is None:
            ordered.extend(remaining)
            break

        def dist(stop: VisitStop) -> float:
            c = stop.coord()
            if c is None:
                return 1e9
            return haversine_km(last, c)

        nxt = min(remaining, key=dist)
        ordered.append(nxt)
        remaining.remove(nxt)
    return ordered


def _split_chunks(stops: list[VisitStop], max_per: int = _MAX_PER_DAY) -> list[list[VisitStop]]:
    if not stops:
        return []
    return [stops[i : i + max_per] for i in range(0, len(stops), max_per)]


def _cluster_by_proximity(stops: list[VisitStop], radius_km: float = _CLUSTER_KM) -> list[list[VisitStop]]:
    """Single-linkage buckets: a stop joins the nearest existing cluster within radius."""
    clusters: list[list[VisitStop]] = []
    for stop in stops:
        placed = False
        coord = stop.coord()
        if coord is not None and clusters:
            best_i = None
            best_d = radius_km
            for i, group in enumerate(clusters):
                dists = [
                    haversine_km(coord, other.coord())  # type: ignore[arg-type]
                    for other in group
                    if other.coord()
                ]
                if not dists:
                    continue
                d = min(dists)
                if d <= best_d:
                    best_d = d
                    best_i = i
            if best_i is not None:
                clusters[best_i].append(stop)
                placed = True
        if not placed:
            clusters.append([stop])
    return clusters


def group_into_days(stops: list[VisitStop]) -> list[VisitDay]:
    """Group by neighbourhood, then proximity; cap each day at 8 stops."""
    by_hood: dict[str, list[VisitStop]] = {}
    for stop in stops:
        key = stop.neighbourhood or "Other"
        by_hood.setdefault(key, []).append(stop)

    raw_groups: list[list[VisitStop]] = []
    # Largest neighbourhoods first so full days form before leftovers.
    for key in sorted(by_hood, key=lambda k: (-len(by_hood[k]), k)):
        group = by_hood[key]
        if key == "Other" or len(group) < 2:
            raw_groups.extend(_cluster_by_proximity(group))
        else:
            raw_groups.append(group)

    # Merge tiny geographic leftovers into the nearest day that still has room.
    days_stops: list[list[VisitStop]] = []
    leftovers: list[VisitStop] = []
    for group in raw_groups:
        ordered = _greedy_order(group)
        if len(ordered) >= _MIN_PER_DAY or (len(ordered) >= 3 and group and group[0].neighbourhood):
            days_stops.extend(_split_chunks(ordered))
        else:
            leftovers.extend(ordered)

    if leftovers:
        for cluster in _cluster_by_proximity(leftovers, radius_km=_CLUSTER_KM * 1.5):
            days_stops.extend(_split_chunks(_greedy_order(cluster)))

    days: list[VisitDay] = []
    for i, group in enumerate(days_stops, start=1):
        hoods = []
        for stop in group:
            name = stop.neighbourhood or "Nearby"
            if name not in hoods:
                hoods.append(name)
        title = " · ".join(hoods[:3]) if hoods else f"Day {i}"
        if len(group) < _MIN_PER_DAY:
            noun = "stop" if len(group) == 1 else "stops"
            title = f"{title} (light day — {len(group)} {noun})"
        days.append(VisitDay(day_index=i, title=title, stops=group))
    return days


def schedule_day(
    day: VisitDay,
    *,
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
    minutes_per_stop: int = _MINUTES_PER_STOP,
    on_date: datetime | None = None,
) -> tuple[VisitDay, list[str]]:
    """Assign arrival/departure times. Returns warnings if the window is too short."""
    base = on_date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cursor = base.replace(hour=start_hour, minute=start_minute)
    window_end = base.replace(hour=end_hour, minute=end_minute)
    warnings: list[str] = []
    prev: VisitStop | None = None
    for stop in day.stops:
        travel = 0
        if prev is not None and prev.coord() and stop.coord():
            travel = drive_minutes(prev.coord(), stop.coord())  # type: ignore[arg-type]
            cursor = cursor + timedelta(minutes=travel)
        elif prev is not None:
            travel = 20
            cursor = cursor + timedelta(minutes=travel)
        stop.travel_from_prev_min = travel if prev is not None else None
        stop.arrive = cursor
        stop.depart = cursor + timedelta(minutes=minutes_per_stop)
        cursor = stop.depart
        prev = stop
    if day.stops and day.stops[-1].depart and day.stops[-1].depart > window_end:
        over = int((day.stops[-1].depart - window_end).total_seconds() // 60)
        warnings.append(
            f"Day {day.day_index} runs about {over} min past your end time. "
            "Shorten visits, start earlier, or split this day."
        )
    if len(day.stops) > _MAX_PER_DAY:
        warnings.append(f"Day {day.day_index} has more than {_MAX_PER_DAY} stops.")
    if 0 < len(day.stops) < _MIN_PER_DAY:
        warnings.append(
            f"Day {day.day_index} has only {len(day.stops)} stops "
            f"(aim for {_MIN_PER_DAY}–{_MAX_PER_DAY} when properties are close)."
        )
    return day, warnings


def default_message(stop: VisitStop, when: str) -> str:
    who = f" {stop.agent_name}" if stop.agent_name else ""
    addr = stop.address or stop.label
    return (
        f"Hi{who}, I'm interested in {addr} and would like to schedule a visit"
        f"{(' around ' + when) if when else ''}. "
        "Would that time work? Thank you!"
    )


def plan_summary(days: list[VisitDay]) -> dict[str, Any]:
    return {
        "days": len(days),
        "stops": sum(len(d.stops) for d in days),
    }
