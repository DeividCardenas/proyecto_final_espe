"""Validación del simulador: categorías del entrenamiento y valores vacíos."""
from __future__ import annotations

import os
import typing

import joblib
import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.prediction import ControlDeviceInput, CrashTypeInput, SegmentRiskRequest, TrafficwayInput

BASE = {"coordinates": [-87.6298, 41.8781]}


def test_blank_strings_mean_not_specified():
    r = SegmentRiskRequest(**BASE, first_crash_type="", trafficway_type="  ", traffic_control_device=None)
    assert r.first_crash_type is None and r.trafficway_type is None


def test_categories_are_normalized_to_upper_case():
    assert SegmentRiskRequest(**BASE, first_crash_type="rear end").first_crash_type == "REAR END"


@pytest.mark.parametrize("field,value", [
    ("first_crash_type", "REAR-END"),
    ("trafficway_type", "AUTOPISTA"),
    ("traffic_control_device", "SEMAFORO"),
])
def test_unknown_categories_rejected(field, value):
    with pytest.raises(ValidationError):
        SegmentRiskRequest(**BASE, **{field: value})


def test_darkness_alias_and_bbox():
    assert SegmentRiskRequest(**BASE, lighting_condition="DARKNESS").lighting_condition == "DARK"
    with pytest.raises(ValidationError):
        SegmentRiskRequest(coordinates=[-74.0, 40.7])


@pytest.mark.skipif(not os.path.exists(settings.MODEL_PATH), reason="modelo no entrenado")
def test_enums_match_model_categories():
    """Si se reentrena con categorías nuevas, este test avisa que hay que actualizar los enums."""
    prep = joblib.load(settings.MODEL_PATH)["pipeline"].named_steps["prep"]
    cats = {}
    for _, transformer, cols in prep.transformers_:
        if hasattr(transformer, "named_steps") and "onehot" in transformer.named_steps:
            cats.update(zip(cols, transformer.named_steps["onehot"].categories_))
    for col, literal in (("trafficway_type", TrafficwayInput), ("traffic_control_device", ControlDeviceInput),
                         ("first_crash_type", CrashTypeInput)):
        assert set(typing.get_args(literal)) == {str(c) for c in cats[col]}, col
