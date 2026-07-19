"""IoT device simulators for the three facility domains.

Each simulator emits unified-schema telemetry at a fixed interval over a
simulated time span. Devices can be healthy, degrading (gradual drift toward
failure), or faulty (already exhibiting failure signatures). Degradation
profiles are the ground truth used to label ML training data.

Simulated physics, deliberately simple but realistic in shape:

- HVAC: compressor efficiency decays as refrigerant leaks / bearings wear;
  supply-return temperature differential shrinks with efficiency; vibration
  amplitude grows with bearing wear; filter differential pressure rises as
  filters clog. Daily ambient cycle superimposed.
- Energy: power draw follows an occupancy-shaped daily curve; developing
  electrical faults show up as voltage sags, rising total harmonic distortion
  and load spikes.
- Occupancy: weekday office curve (morning ramp, lunch dip, evening decline),
  weekend near-zero, meeting rooms booked-but-empty a configurable fraction of
  the time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

import numpy as np

from ..ingestion.schema import TelemetryMessage


@dataclass
class DeviceProfile:
    device_id: str
    zone: str
    # 'healthy' | 'degrading' | 'faulty'
    condition: str = "healthy"
    # Fraction of the simulated span at which failure occurs (degrading only).
    # Degradation signatures ramp up as t approaches this point.
    failure_at: float = 1.0
    seed: int = 0


class BaseSimulator:
    domain = "base"
    interval_minutes = 15

    def __init__(self, profile: DeviceProfile):
        self.profile = profile
        self.rng = np.random.default_rng(profile.seed)

    def stream(self, start: datetime, days: float) -> Iterator[dict]:
        """Yield telemetry dicts covering `days` from `start`."""
        steps = int(days * 24 * 60 / self.interval_minutes)
        for i in range(steps):
            ts = start + timedelta(minutes=i * self.interval_minutes)
            t = i / max(steps - 1, 1)  # 0..1 through the span
            yield self._emit(ts, t)

    def _emit(self, ts: datetime, t: float) -> dict:
        raise NotImplementedError

    def _degradation(self, t: float) -> float:
        """0..1 severity of degradation at normalized time t.

        Healthy: 0. Faulty: high from the start. Degrading: accelerating ramp
        that reaches ~1 at the configured failure point.
        """
        p = self.profile
        if p.condition == "healthy":
            return 0.0
        if p.condition == "faulty":
            return 0.85 + 0.15 * t
        frac = min(t / max(p.failure_at, 1e-6), 1.0)
        return frac**2  # slow start, accelerating toward failure

    @staticmethod
    def _daily(ts: datetime) -> float:
        """0..1 daily cycle peaking mid-afternoon."""
        hour = ts.hour + ts.minute / 60
        return 0.5 * (1 + math.sin((hour - 9) / 24 * 2 * math.pi))

    @staticmethod
    def _is_workhours(ts: datetime) -> bool:
        return ts.weekday() < 5 and 8 <= ts.hour < 19


class HVACSimulator(BaseSimulator):
    domain = "hvac"

    def _emit(self, ts: datetime, t: float) -> dict:
        d = self._degradation(t)
        daily = self._daily(ts)
        noise = self.rng.normal

        efficiency = max(0.98 - 0.45 * d + noise(0, 0.015), 0.05)
        # Healthy differential ~8-10C, collapses as efficiency drops
        differential = (8.5 + 1.5 * daily) * (0.35 + 0.65 * efficiency)
        return_temp = 24 + 3 * daily + noise(0, 0.4)
        supply_temp = return_temp - differential + noise(0, 0.3)
        vibration = 1.2 + 9.0 * d**1.5 + noise(0, 0.15 + 0.6 * d)
        filter_dp = 120 + 380 * d + 20 * daily + noise(0, 8)
        motor_temp = 45 + 8 * daily + 30 * d + noise(0, 1.5)

        return TelemetryMessage(
            device_id=self.profile.device_id,
            domain=self.domain,
            zone=self.profile.zone,
            timestamp=ts.isoformat(),
            metrics={
                "supply_temp_c": round(supply_temp, 2),
                "return_temp_c": round(return_temp, 2),
                "humidity_pct": round(min(max(48 + 10 * daily + noise(0, 2), 0), 100), 2),
                "compressor_efficiency": round(efficiency, 4),
                "vibration_mm_s": round(max(vibration, 0), 3),
                "filter_dp_pa": round(max(filter_dp, 0), 1),
                "motor_temp_c": round(min(motor_temp, 149.0), 2),
            },
        ).to_dict()


class EnergySimulator(BaseSimulator):
    domain = "energy"

    def _emit(self, ts: datetime, t: float) -> dict:
        d = self._degradation(t)
        noise = self.rng.normal
        base_load = 40.0
        occ_load = 120.0 * self._daily(ts) if self._is_workhours(ts) else 10.0

        # Fault development: intermittent load spikes and voltage sags
        spike = 0.0
        sag = 0.0
        if d > 0.15 and self.rng.random() < 0.12 * d:
            spike = self.rng.uniform(30, 90) * d
        if d > 0.15 and self.rng.random() < 0.10 * d:
            sag = self.rng.uniform(8, 25) * d

        power = base_load + occ_load + spike + noise(0, 3)
        voltage = 230 - sag + noise(0, 1.2)
        pf = min(max(0.95 - 0.25 * d + noise(0, 0.01), 0.3), 1.0)
        current = power * 1000 / max(voltage * pf * math.sqrt(3), 1)
        thd = 2.5 + 14 * d + (3 if spike else 0) + abs(noise(0, 0.4))

        return TelemetryMessage(
            device_id=self.profile.device_id,
            domain=self.domain,
            zone=self.profile.zone,
            timestamp=ts.isoformat(),
            metrics={
                "power_kw": round(max(power, 0), 2),
                "voltage_v": round(max(voltage, 0), 2),
                "current_a": round(max(current, 0), 2),
                "power_factor": round(pf, 3),
                "thd_pct": round(min(thd, 100), 2),
            },
        ).to_dict()


class OccupancySimulator(BaseSimulator):
    domain = "occupancy"
    interval_minutes = 30

    def __init__(self, profile: DeviceProfile, desk_total: int = 40,
                 ghost_booking_rate: float = 0.25):
        super().__init__(profile)
        self.desk_total = desk_total
        self.ghost_booking_rate = ghost_booking_rate

    def _emit(self, ts: datetime, t: float) -> dict:
        noise = self.rng.normal
        if self._is_workhours(ts):
            hour = ts.hour + ts.minute / 60
            # morning ramp, lunch dip, evening decline
            shape = math.exp(-((hour - 11) ** 2) / 18) + 0.8 * math.exp(
                -((hour - 15.5) ** 2) / 10
            )
            occ_frac = min(shape * 0.75 + noise(0, 0.05), 1.0)
        else:
            occ_frac = max(noise(0.01, 0.01), 0)

        desks = int(max(min(occ_frac * self.desk_total, self.desk_total), 0))
        booked = 1.0 if (self._is_workhours(ts) and self.rng.random() < 0.55) else 0.0
        occupied = booked
        if booked and self.rng.random() < self.ghost_booking_rate:
            occupied = 0.0  # booked but empty — utilization discrepancy signal

        return TelemetryMessage(
            device_id=self.profile.device_id,
            domain=self.domain,
            zone=self.profile.zone,
            timestamp=ts.isoformat(),
            metrics={
                "occupancy_count": float(desks + self.rng.integers(0, 3)),
                "motion_events": float(max(int(desks * 2.5 + noise(0, 3)), 0)),
                "desk_occupied": float(desks),
                "desk_total": float(self.desk_total),
                "room_booked": booked,
                "room_occupied": occupied,
            },
        ).to_dict()


SIMULATORS = {
    "hvac": HVACSimulator,
    "energy": EnergySimulator,
    "occupancy": OccupancySimulator,
}


def default_fleet() -> list[tuple[str, DeviceProfile]]:
    """The POC device fleet: mix of healthy, degrading and faulty assets."""
    fleet: list[tuple[str, DeviceProfile]] = []
    hvac = [
        DeviceProfile("hvac-ahu-01", "floor1", "healthy", seed=11),
        DeviceProfile("hvac-ahu-02", "floor2", "degrading", failure_at=0.9, seed=12),
        DeviceProfile("hvac-chiller-01", "roof", "healthy", seed=13),
        DeviceProfile("hvac-chiller-02", "roof", "degrading", failure_at=0.75, seed=14),
        DeviceProfile("hvac-pump-01", "basement", "faulty", seed=15),
    ]
    energy = [
        DeviceProfile("meter-main-01", "building", "healthy", seed=21),
        DeviceProfile("meter-floor1-01", "floor1", "degrading", failure_at=0.8, seed=22),
        DeviceProfile("meter-floor2-01", "floor2", "healthy", seed=23),
        DeviceProfile("meter-server-01", "serverroom", "faulty", seed=24),
    ]
    occupancy = [
        DeviceProfile("occ-floor1-01", "floor1", "healthy", seed=31),
        DeviceProfile("occ-floor2-01", "floor2", "healthy", seed=32),
        DeviceProfile("occ-meeting-a", "meetingA", "healthy", seed=33),
        DeviceProfile("occ-meeting-b", "meetingB", "healthy", seed=34),
    ]
    fleet += [("hvac", p) for p in hvac]
    fleet += [("energy", p) for p in energy]
    fleet += [("occupancy", p) for p in occupancy]
    return fleet


def simulate_fleet(days: float = 14.0, start: datetime | None = None):
    """Yield telemetry dicts for the whole default fleet."""
    start = start or (datetime.now(timezone.utc) - timedelta(days=days))
    for domain, profile in default_fleet():
        sim = SIMULATORS[domain](profile)
        yield from sim.stream(start, days)
