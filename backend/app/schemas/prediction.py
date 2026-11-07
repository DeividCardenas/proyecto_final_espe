"""Esquemas Pydantic v2 de entrada/salida para la inferencia de riesgo vial."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import CHICAGO_BBOX

WeatherInput = Literal["CLEAR", "RAIN", "SNOW", "FOG", "OTHER", "UNKNOWN"]
LightingInput = Literal["DAY", "DARK_LIGHTED", "DARK", "DARKNESS", "DUSK_DAWN", "UNKNOWN"]

# Categorías exactas que vio el modelo en el entrenamiento (OneHotEncoder del artefacto).
# Un valor fuera de lista (p. ej. "REAR-END") antes caía en silencio en la categoría
# "infrecuente" y cambiaba la predicción; ahora se rechaza con 422.
TrafficwayInput = Literal[
    "ALLEY", "CENTER TURN LANE", "DIVIDED - W/MEDIAN (NOT RAISED)", "DIVIDED - W/MEDIAN BARRIER", "DRIVEWAY",
    "FIVE POINT, OR MORE", "FOUR WAY", "L-INTERSECTION", "NOT DIVIDED", "NOT REPORTED", "ONE-WAY", "OTHER",
    "PARKING LOT", "RAMP", "ROUNDABOUT", "T-INTERSECTION", "TRAFFIC ROUTE", "UNKNOWN", "UNKNOWN INTERSECTION TYPE",
    "Y-INTERSECTION",
]
ControlDeviceInput = Literal[
    "BICYCLE CROSSING SIGN", "DELINEATORS", "FLASHING CONTROL SIGNAL", "NO CONTROLS", "NO PASSING", "OTHER",
    "OTHER RAILROAD CROSSING", "OTHER REG. SIGN", "OTHER WARNING SIGN", "PEDESTRIAN CROSSING SIGN", "POLICE/FLAGMAN",
    "RAILROAD CROSSING GATE", "RR CROSSING SIGN", "SCHOOL ZONE", "STOP SIGN/FLASHER", "TRAFFIC SIGNAL", "UNKNOWN",
    "YIELD",
]
CrashTypeInput = Literal[
    "ANGLE", "ANIMAL", "FIXED OBJECT", "HEAD ON", "OTHER NONCOLLISION", "OTHER OBJECT", "OVERTURNED",
    "PARKED MOTOR VEHICLE", "PEDALCYCLIST", "PEDESTRIAN", "REAR END", "REAR TO FRONT", "REAR TO REAR", "REAR TO SIDE",
    "SIDESWIPE OPPOSITE DIRECTION", "SIDESWIPE SAME DIRECTION", "TRAIN", "TURNING",
]


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
    trafficway_type: TrafficwayInput | None = Field(None, examples=["NOT DIVIDED", "DIVIDED - W/MEDIAN (NOT RAISED)"])
    traffic_control_device: ControlDeviceInput | None = Field(None, examples=["NO CONTROLS", "TRAFFIC SIGNAL"])
    intersection_related: bool | None = None
    first_crash_type: CrashTypeInput | None = Field(
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

    @field_validator("trafficway_type", "traffic_control_device", "first_crash_type", "roadway_surface_cond",
                     mode="before")
    @classmethod
    def blank_is_none(cls, v):
        """El formulario envía "" para "sin especificar": equivale a omitir el campo."""
        if isinstance(v, str):
            v = v.strip().upper()
            return v or None
        return v

    @field_validator("lighting_condition")
    @classmethod
    def normalize_lighting(cls, v: str) -> str:
        return "DARK" if v == "DARKNESS" else v


class RiskFactor(BaseModel):
    feature: str
    contribution: float
    direction: Literal["aumenta", "reduce"]


class PredictionContext(BaseModel):
    evaluated_at: str = Field(..., description="Momento evaluado (ISO 8601, hora de Chicago si no se indicó zona)")
    aadt_volume: int | float | None = Field(
        None, description="AADT usado: estación cercana (<= 500 m) o media de la ciudad")
    aadt_station_distance_m: float | None = None
    aadt_imputed: bool
    cell_crashes_per_year: float = Field(..., description="Siniestros por año en la celda de 500 m")
    history_years: float = Field(..., description="Años de historia usados para anualizar la densidad")
    roadway_surface_cond: str


class ModelInfo(BaseModel):
    mode: Literal["ml", "heuristic_fallback"]
    algorithm: str | None = None
    trained_at: str | None = None


class SegmentRiskResponse(BaseModel):
    risk_level: Literal["Bajo", "Moderado", "Crítico"]
    risk_class: int
    probabilities: dict[str, float]
    critical_score: float = Field(..., description="Probabilidad de la clase Crítica")
    critical_alert: bool = Field(..., description="Probabilidad crítica >= umbral óptimo F1 del modelo")
    top_factors: list[RiskFactor]
    context: PredictionContext
    model: ModelInfo
    inference_ms: float
