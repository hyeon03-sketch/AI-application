"""Online repetition / peak-trigger engine. The same class is used offline (calibration) and in the demo,
so the logic that produced the thresholds is exactly the logic that runs in real time."""
import numpy as np
import config as C


class RepEngine:
    REST, UP, DOWN = "REST", "UP", "DOWN"

    def __init__(self, exercise, threshold=None, params=None):
        self.ex = exercise
        self.spec = C.EXERCISES[exercise]
        self.p = dict(C.ENGINE, **(params or {}))
        self.thr = threshold
        self.d_start = self.spec.get("delta_start", 10.0)
        self.d_end = self.spec.get("delta_end", 6.0)
        self.t = -1
        self.y = None
        self.calib = []
        self.rest = None
        self.state = self.REST
        self.prev_s = 0.0
        self.reps = []
        self._cur = None
        self.s = 0.0

    # ------------------------------------------------------------------
    def _excursion(self, y):
        s = y - self.rest
        return abs(s) if self.spec["symmetric"] else s

    def update(self, value):
        """Feed one frame of the raw signal. Returns a list of events (dicts)."""
        self.t += 1
        ev = []
        if value is None or not np.isfinite(value):
            return ev
        a = self.p["ema_alpha"]
        self.y = value if self.y is None else a * value + (1 - a) * self.y
        if self.rest is None:
            self.calib.append(self.y)
            if len(self.calib) >= self.p["calib_frames"]:
                self.rest = float(np.median(self.calib))
            return ev
        s = self._excursion(self.y)
        vel = s - self.prev_s
        self.prev_s = s
        self.s = s

        if self.state == self.REST:
            if s < self.d_end:
                b = self.p["rest_beta"]
                self.rest = (1 - b) * self.rest + b * self.y
            if s > self.d_start:
                self.state = self.UP
                self._cur = dict(start=self.t, peak_t=self.t, peak=s, raw_peak=self.y, neg=0, still=0)
                ev.append(dict(type="start", t=self.t))
        elif self.state == self.UP:
            c = self._cur
            if s > c["peak"]:
                c.update(peak=s, peak_t=self.t, raw_peak=self.y, neg=0)
            elif vel < 0:
                c["neg"] += 1
            c["still"] = c["still"] + 1 if abs(vel) < self.p["plateau_vel"] else 0
            confirmed = (c["neg"] >= self.p["peak_confirm"] and c["peak"] - s > self.p["peak_drop"]) \
                or c["still"] >= self.p["plateau_frames"] or s < self.d_end
            if confirmed:
                ev.append(self._judge())
                self.state = self.DOWN
            elif self.t - c["start"] > self.p["max_rep_frames"]:
                self.state, self._cur = self.REST, None
        elif self.state == self.DOWN:
            c = self._cur
            if s < self.d_end or self.t - c["start"] > self.p["max_rep_frames"]:
                if self.t - c["start"] >= self.p["min_rep_frames"]:
                    rep = dict(start=c["start"], peak_t=c["peak_t"], end=self.t, peak=c["peak"],
                               raw_peak=c["raw_peak"], rest=self.rest, is_error=c.get("is_error"))
                    self.reps.append(rep)
                    ev.append(dict(type="end", t=self.t, rep=rep))
                self.state, self._cur = self.REST, None
        return ev

    def _judge(self):
        c = self._cur
        val = c["peak"] if self.spec.get("feature", "excursion") == "excursion" else \
            (abs(c["raw_peak"]) if self.spec["symmetric"] else c["raw_peak"])
        c["value"] = val
        c["is_error"] = None if self.thr is None else bool(val < self.thr)
        return dict(type="peak", t=self.t, peak_t=c["peak_t"], value=val, is_error=c["is_error"],
                    region=self.spec["region"])

    def flush(self):
        """Close an open repetition at the end of a recording."""
        if self._cur is not None and self.state in (self.UP, self.DOWN):
            c = self._cur
            if self.state == self.UP:
                self._judge()
            rep = dict(start=c["start"], peak_t=c["peak_t"], end=self.t, peak=c["peak"],
                       raw_peak=c["raw_peak"], rest=self.rest, is_error=c.get("is_error"))
            if self.t - c["start"] >= self.p["min_rep_frames"]:
                self.reps.append(rep)
            self._cur = None
        return self.reps


def feature_value(rep, exercise):
    spec = C.EXERCISES[exercise]
    if spec.get("feature", "excursion") == "excursion":
        return rep["peak"]
    return abs(rep["raw_peak"]) if spec["symmetric"] else rep["raw_peak"]
