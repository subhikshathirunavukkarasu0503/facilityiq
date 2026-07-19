"""Unit tests: IoT device simulators produce valid, physically plausible
telemetry and encode the intended degradation signatures."""

from datetime import datetime, timezone

import numpy as np

from facilityiq.ingestion.schema import validate_message
from facilityiq.simulators.devices import (
    DeviceProfile, EnergySimulator, HVACSimulator, OccupancySimulator,
    default_fleet, simulate_fleet,
)

START = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_all_simulator_output_passes_schema():
    for msg in simulate_fleet(days=1.0):
        validate_message(msg)  # raises on violation


def test_fleet_covers_three_domains():
    domains = {d for d, _ in default_fleet()}
    assert domains == {"hvac", "energy", "occupancy"}


def test_message_volume():
    msgs = list(simulate_fleet(days=1.0))
    # 9 devices at 15-min cadence + 4 at 30-min over 24h
    assert len(msgs) == 9 * 96 + 4 * 48


def test_degrading_hvac_efficiency_declines():
    sim = HVACSimulator(DeviceProfile("d", "z", "degrading", failure_at=0.9, seed=1))
    effs = [m["metrics"]["compressor_efficiency"]
            for m in sim.stream(START, days=14)]
    first, last = np.mean(effs[:50]), np.mean(effs[-50:])
    assert last < first - 0.2, "efficiency must visibly degrade"


def test_degrading_hvac_vibration_rises():
    sim = HVACSimulator(DeviceProfile("d", "z", "degrading", failure_at=0.9, seed=2))
    vib = [m["metrics"]["vibration_mm_s"] for m in sim.stream(START, days=14)]
    assert np.mean(vib[-50:]) > np.mean(vib[:50]) + 2.0


def test_healthy_hvac_stays_stable():
    sim = HVACSimulator(DeviceProfile("d", "z", "healthy", seed=3))
    effs = [m["metrics"]["compressor_efficiency"]
            for m in sim.stream(START, days=14)]
    assert abs(np.mean(effs[-50:]) - np.mean(effs[:50])) < 0.05


def test_faulty_energy_has_higher_thd():
    healthy = EnergySimulator(DeviceProfile("h", "z", "healthy", seed=4))
    faulty = EnergySimulator(DeviceProfile("f", "z", "faulty", seed=4))
    thd_h = np.mean([m["metrics"]["thd_pct"] for m in healthy.stream(START, 7)])
    thd_f = np.mean([m["metrics"]["thd_pct"] for m in faulty.stream(START, 7)])
    assert thd_f > thd_h + 5


def test_occupancy_weekend_near_zero():
    sim = OccupancySimulator(DeviceProfile("o", "z", seed=5))
    msgs = list(sim.stream(datetime(2026, 6, 6, tzinfo=timezone.utc), days=1))  # Saturday
    counts = [m["metrics"]["desk_occupied"] for m in msgs]
    assert np.mean(counts) < 2


def test_occupancy_weekday_shows_usage():
    sim = OccupancySimulator(DeviceProfile("o", "z", seed=6))
    msgs = list(sim.stream(datetime(2026, 6, 1, tzinfo=timezone.utc), days=1))  # Monday
    counts = [m["metrics"]["desk_occupied"] for m in msgs]
    assert max(counts) > 10


def test_simulation_is_deterministic_per_seed():
    a = HVACSimulator(DeviceProfile("d", "z", "healthy", seed=7))
    b = HVACSimulator(DeviceProfile("d", "z", "healthy", seed=7))
    assert list(a.stream(START, 1)) == list(b.stream(START, 1))
