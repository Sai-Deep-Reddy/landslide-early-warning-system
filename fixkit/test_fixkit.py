"""
test_fixkit.py  —  run:  pytest -q test_fixkit.py
All tests are offline (network calls are mocked), so they run anywhere.
"""
import datetime as dt
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import physics_engine as pe
import weather_fix as wf
from cap_alert import CAP_NS, approve, build_alert, validate
from fusion_inference import FusionModel


# ---------- I-D thresholds match the published equations ----------
def test_sikkim_thresholds_match_paper():
    assert pe.threshold_intensity(1) == pytest.approx(43.26, rel=1e-6)              # mm/day at D=1 day
    assert pe.threshold_intensity(2) * 2 == pytest.approx(50.4, abs=0.2)             # 48 h cumulative
    assert pe.threshold_intensity(1, "gangtok_local") == pytest.approx(100.0)


def test_caine_is_not_a_floor_for_sikkim():
    caine_24h = pe.threshold_intensity(24, "caine_global") * 24
    assert caine_24h > 2 * pe.threshold_intensity(1)                                # ~103 mm vs ~43 mm


def test_id_exceedance_picks_worst_window():
    r = pe.id_exceedance_daily([0, 0, 0, 0, 0, 0, 43.26])
    assert r["ratio"] == pytest.approx(1.0, abs=1e-3) and r["duration_days"] == 1


# ---------- slope stability behaves physically ----------
def test_fos_dry_stable_wet_unstable():
    fos_dry = pe.factor_of_safety(35, 5, 32, 2, 19, 0.0)
    fos_wet = pe.factor_of_safety(35, 5, 32, 2, 19, 1.0)
    assert fos_dry > 1.0 > fos_wet


def test_failure_probability_monotone_in_rain_and_slope():
    storm = [10, 20, 30, 40, 60, 90, 150]
    assert pe.failure_probability(35, [0] * 7)["p_failure"] < pe.failure_probability(35, storm)["p_failure"]
    ps = [pe.failure_probability(s, storm)["p_failure"] for s in (15, 25, 35, 45)]
    assert all(b >= a for a, b in zip(ps, ps[1:]))
    assert pe.failure_probability(3, storm)["p_failure"] == 0.0


# ---------- weather: no silent fallback, no post-event leakage ----------
def _fake_archive(n_hours=24 * 9, soil=True, storm_after_cutoff=True):
    start = dt.datetime(2024, 6, 4, 0, 0)
    times = [(start + dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(n_hours)]
    precip = [1.0] * n_hours
    if storm_after_cutoff:
        for i in range(n_hours - 24, n_hours):      # huge rain ON the event day
            precip[i] = 50.0
    h = {"time": times, "precipitation": precip}
    if soil:
        h["soil_moisture_0_to_7cm"] = [0.35] * n_hours
        h["soil_moisture_7_to_28cm"] = [0.33] * n_hours
    return {"hourly": h}


def test_features_use_only_data_before_cutoff(monkeypatch):
    monkeypatch.setattr(wf, "fetch_archive", lambda *a, **k: _fake_archive())
    f = wf.features_at(27.5, 88.5, dt.datetime(2024, 6, 12, 0, 0))
    assert f["rain_24h"] == pytest.approx(24.0)      # event-day storm (50 mm/h) must NOT leak in
    assert f["soil_0_28cm"] == pytest.approx((0.35 * 7 + 0.33 * 21) / 28, abs=1e-4)


def test_missing_soil_returns_none_not_a_month_constant(monkeypatch):
    monkeypatch.setattr(wf, "fetch_archive", lambda *a, **k: _fake_archive(soil=False))
    assert wf.features_at(27.5, 88.5, dt.datetime(2024, 6, 12, 0, 0)) is None


# ---------- fusion: explanation == computation ----------
def test_fusion_explanation_reproduces_score(tmp_path):
    from train_fusion import run, smoke_data
    run(smoke_data(), test_from=2019, out=str(tmp_path))
    fm = FusionModel(str(tmp_path))
    w = {"daily_rain_7d": [5, 5, 10, 10, 20, 30, 40], "soil_0_28cm": 0.33, "rain_6h": 12, "rain_24h": 40,
         "rain_48h": 70, "rain_72h": 80, "rain_7d": 120, "max_1h_24h": 8}
    r = fm.assess(30, 1200, w)
    e = r["explanation"]
    logodds = e["b0"] + sum(e["log_odds_contribution"].values())
    if not r["published_threshold_override"]:
        assert r["risk"] == pytest.approx(1 / (1 + np.exp(-logodds)), abs=2e-3)
    # and it matches sklearn's own prediction
    z = np.array([[np.log(max(e["inputs"]["ML_prob"], 1e-4) / max(1 - e["inputs"]["ML_prob"], 1e-4)),
                   np.log(max(e["inputs"]["Physics_P_fail"], 1e-4) / max(1 - e["inputs"]["Physics_P_fail"], 1e-4)),
                   np.log1p(e["inputs"]["ID_ratio"])]])
    assert fm.meta.predict_proba(z)[0, 1] == pytest.approx(r["risk"], abs=5e-3) or r["published_threshold_override"]


def test_flat_ground_not_flagged():
    fm = FusionModel(None)
    w = {"daily_rain_7d": [30, 40, 60, 80, 100, 150, 200], "soil_0_28cm": 0.42}
    assert fm.assess(3, 300, w)["level"] == "LOW"


# ---------- CAP ----------
def test_cap_valid_and_human_in_loop():
    xml = build_alert("HIGH", 27.5, 88.5, "Mangan", 0.78, status="Draft")
    ok, errs = validate(xml)
    assert ok, errs
    assert ET.fromstring(approve(xml, "DDMA-01")).find(f"{{{CAP_NS}}}status").text == "Actual"
    with pytest.raises(ValueError):
        approve(build_alert("LOW", 27.5, 88.5, "x", 0.1, status="Exercise"), "DDMA-01")


# ---------- replay computes lead time from data, never typed in ----------
def test_replay_timeline_offline(monkeypatch):
    import replay_real_event as rp
    start = dt.datetime(2024, 6, 2, 0, 0)
    n = 24 * 13
    times = [(start + dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(n)]
    precip = [0.5] * n
    for i in range(24 * 10, 24 * 11):          # heavy rain the day before the event
        precip[i] = 8.0
    fake = {"hourly": {"time": times, "precipitation": precip,
                       "soil_moisture_0_to_7cm": [0.40] * n, "soil_moisture_7_to_28cm": [0.38] * n}}
    monkeypatch.setattr(rp, "fetch_archive", lambda *a, **k: fake)
    steps, first, lead, ref = rp.timeline(27.5, 88.5, dt.date(2024, 6, 13), None, 38, 1300, FusionModel(None))
    assert steps and all(s["rel_hour"] <= 0 for s in steps)
    assert lead is not None and lead > 0
