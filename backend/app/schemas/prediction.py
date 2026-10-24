"""Esquemas Pydantic v2 de entrada/salida para la inferencia de riesgo vial."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import CHICAGO_BBOX

WeatherInput = Literal["CLEAR", "RAIN", "SNOW", "FOG", "OTHER", "UNKNOWN"]
LightingInput = Literal["DAY", "DARK_LIGHTED", "DARK", "DARKNESS", "DUSK_DAWN", "UNKNOWN"]


class SegmentRiskRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "coordinates": [-87.6298, 41.8781],
            "posted_speed_limit": 30,
            "weather_condition": "RAIN",
            "lighting_condition": "DARKNESS",
            "active_workzone": True,
        }
    })

    coordinates: tuple[float, float] = Field(..., description="[longitud, latitud] en WGS84 (EPSG:4326)")
    posted_speed_limit: int = Field(30, ge=0, le=70)
    weather_condition: WeatherInput = "CLEAR"
    lighting_condition: LightingInput = "DAY"
    active_workzone: bool = False
    roadway_surface_cond: Literal["DRY", "WET", "SNOW_ICE", "OTHER", "UNKNOWN"] | None = None
    trafficway_type: str | None = Field(None, examples=["NOT DIVIDED", "DIVIDED - W/MEDIAN (NOT RAISED)"])
    traffic_control_device: str | None = Field(None, examples=["NO CONTROLS", "TRAFFIC SIGNAL"])
    intersection_related: bool | None = None
    first_crash_type: str | None = Field(
        None, examples=["PEDESTRIAN", "REAR END", "ANGLE"],
        description="Tipo de colisión a evaluar; si se omite se promedian los mecanismos más frecuentes")
    when: datetime | None = Field(None, description="Momento a evaluar (por defecto: ahora, hora de Chicago)")

    @field_validator("coordinates")
    @classmethod
    def inside_chicago(cls, v: tuple[float, float]) -> tuple[float, float]:
        lon, lat = v
        b = CHICAGO_BBOX
        if not (b["min_lon"] <= lon <= b["max_lon"] and b["min_lat"] <= lat <= b["max_lat"]):
            raise ValueError(
                f"Coordenadas fuera del cuadrante municipal de Chicago "
                f"(lon {b['min_lon']}..{b['max_lon']}, lat {b['min_lat']}..{b['max_lat']})"
            )
        return v

    @field_validator("lighting_condition")
    @classmethod
    def normalize_lighting(cls, v: str) -> str:
        return "DARK" if v == "DARKNESS" else v


class RiskFactor(BaseModel):
    feature: str
    contribution: float
    direction: Literal["aumenta", "reduce"]


class SegmentRiskResponse(BaseModel):
    risk_level: Literal["Bajo", "Moderado", "Crítico"]
    risk_class: int
    probabilities: dict[str, float]
    critical_score: float = Field(..., description="Probabilidad de la clase Crítica")
    critical_alert: bool = Field(..., description="Probabilidad crítica >= umbral óptimo F1 del modelo")
    top_factors: list[RiskFactor]
    context: dict
    model: dict
    inference_ms: float
