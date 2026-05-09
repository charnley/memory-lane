"""
Artistic elevation map using contour lines.
No country borders — pure terrain art.

Data: OpenTopoData SRTM 90m API (https://www.opentopodata.org/)
"""

from __future__ import annotations

import math
import time
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.figure import Figure

OPENTOPODATA_URL = "https://api.opentopodata.org/v1/srtm90m"
API_BATCH_SIZE = 100  # max locations per request
API_RATE_LIMIT = 1.1  # seconds between requests (free tier: 1 req/s)


def _zoom_to_degrees(zoom: int) -> float:
    """Convert zoom level (1-20) to approximate half-span in degrees.

    zoom=1  → ~45 deg (continent)
    zoom=10 → ~0.09 deg (city)
    zoom=15 → ~0.003 deg (street)
    """
    return 45.0 / (2 ** (zoom - 1))


def _fetch_elevations(locations: list[tuple[float, float]]) -> list[Optional[float]]:
    """Fetch elevation for list of (lat, lon) from OpenTopoData API.
    Batches requests to respect 100-location limit.
    Returns list of elevations (None on failure).
    """
    results: list[Optional[float]] = []

    for i in range(0, len(locations), API_BATCH_SIZE):
        batch = locations[i : i + API_BATCH_SIZE]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        resp = requests.get(
            OPENTOPODATA_URL,
            params={"locations": loc_str},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for result in data["results"]:
            results.append(result.get("elevation"))

        if i + API_BATCH_SIZE < len(locations):
            time.sleep(API_RATE_LIMIT)

    return results


def draw_map(
    center: tuple[float, float],
    zoom: int,
    points: Optional[list[tuple[float, float]]] = None,
    output: str = "map.png",
    grid_size: int = 50,
    figsize: tuple[float, float] = (10, 10),
    dpi: int = 150,
    style: str = "sepia",
) -> Figure:
    """Draw an artistic contour-line elevation map.

    Parameters
    ----------
    center : (lat, lon) center of map
    zoom : zoom level 1-18 (higher = closer)
    points : optional list of (lat, lon) to mark on map
    output : output PNG path
    grid_size : NxN elevation sample grid (more = finer contours, more API calls)
    figsize : matplotlib figure size in inches
    dpi : output resolution
    style : 'sepia', 'ink', or 'blueprint'

    Returns
    -------
    matplotlib Figure
    """
    if points is None:
        points = []

    lat0, lon0 = center
    half = _zoom_to_degrees(zoom)
    lat_min, lat_max = lat0 - half, lat0 + half
    lon_min, lon_max = lon0 - half, lon0 + half

    # Build grid of sample points
    lats = np.linspace(lat_min, lat_max, grid_size)
    lons = np.linspace(lon_min, lon_max, grid_size)
    grid_lons, grid_lats = np.meshgrid(lons, lats)

    locations = [
        (grid_lats[r, c], grid_lons[r, c]) for r in range(grid_size) for c in range(grid_size)
    ]

    print(
        f"Fetching {len(locations)} elevation points "
        f"({math.ceil(len(locations) / API_BATCH_SIZE)} API requests)..."
    )
    elevations_flat = _fetch_elevations(locations)

    elev_grid = np.array(
        [e if e is not None else 0.0 for e in elevations_flat],
        dtype=float,
    ).reshape(grid_size, grid_size)

    # Style palette
    styles = {
        "sepia": dict(
            bg="#f5f0e8",
            line_color="#5c4a2a",
            point_color="#8b2020",
            title_color="#3a2a10",
        ),
        "ink": dict(
            bg="#ffffff",
            line_color="#1a1a1a",
            point_color="#cc0000",
            title_color="#000000",
        ),
        "blueprint": dict(
            bg="#1a2a4a",
            line_color="#a8c8f0",
            point_color="#ffcc00",
            title_color="#d0e8ff",
        ),
    }
    palette = styles.get(style, styles["sepia"])

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor(palette["bg"])
    ax.set_facecolor(palette["bg"])

    elev_min = np.nanmin(elev_grid)
    elev_max = np.nanmax(elev_grid)
    elev_range = elev_max - elev_min if elev_max > elev_min else 1.0

    # Number of contour levels scales with terrain relief
    n_levels = max(8, min(40, int(elev_range / 20)))
    levels = np.linspace(elev_min, elev_max, n_levels)

    # Major/minor contours — thicker lines every 5th level
    major_levels = levels[::5]
    cs_major = ax.contour(
        grid_lons,
        grid_lats,
        elev_grid,
        levels=major_levels,
        colors=palette["line_color"],
        linewidths=1.0,
        alpha=0.85,
    )

    # Label major contours
    ax.clabel(
        cs_major,
        fmt="%dm",
        fontsize=6,
        colors=palette["line_color"],
        inline=True,
        inline_spacing=2,
    )

    # GPS points
    if points:
        pt_lats = [p[0] for p in points]
        pt_lons = [p[1] for p in points]
        ax.scatter(
            pt_lons,
            pt_lats,
            color=palette["point_color"],
            s=40,
            zorder=5,
            linewidths=0.8,
            edgecolors=palette["bg"],
        )

    # Clean up axes — artistic, no tick clutter
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect("equal")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    # Subtle border frame
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(palette["line_color"])
        spine.set_linewidth(0.8)
        spine.set_alpha(0.4)

    fig.tight_layout(pad=0.5)
    fig.savefig(output, dpi=dpi, bbox_inches="tight", facecolor=palette["bg"])
    print(f"Saved: {output}")

    return fig
