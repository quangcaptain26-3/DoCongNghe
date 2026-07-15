# -*- coding: utf-8 -*-
"""Tổng hợp chất lượng AGV từ danh sách DayResult.

Tỷ lệ bất thường (%) của một kỳ:
    Sum(giờ bất thường của các ngày) / (denom_hours * tổng số xe-ngày) * 100
trong đó "xe-ngày" = tổng số xe hoạt động cộng dồn qua từng ngày (car_count mỗi ngày).
Cách này nhất quán với tỷ lệ từng ngày (denom_hours * số_xe) trong bản gốc.

Ngoài các tổng hợp theo kỳ (thứ 7 / tuần / tháng), module còn cung cấp các phân tích
phục vụ báo cáo cho cấp quản lý:
  - aggregate_points : xếp hạng ĐIỂM hay kẹt.
  - aggregate_cars   : xếp hạng XE bất thường.
  - overall_summary  : KPI tổng thể (ngày/xe/tỷ lệ/điểm-xe tệ nhất...).
  - weekday_pattern  : mẫu bất thường theo thứ trong tuần.
  - daynight_split   : so sánh ca ngày và ca đêm.
  - severity_buckets : phân nhóm mức độ nặng theo thời gian dừng.
  - trend_series     : chuỗi tỷ lệ theo ngày (để vẽ biểu đồ).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from .abnormal import DayResult, DEFAULT_DENOM_HOURS

WEEKDAY_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def weekday_name(d: date) -> str:
    return WEEKDAY_VI[d.weekday()]


# --- Thống kê theo xe ----------------------------------------------------------

@dataclass
class CarStat:
    car_id: str
    abnormal_count: int = 0
    abnormal_hours: float = 0.0

    @property
    def abnormal_min(self) -> float:
        return round(self.abnormal_hours * 60.0, 2)

    @property
    def avg_min(self) -> float:
        if self.abnormal_count <= 0:
            return 0.0
        return round(self.abnormal_hours * 60.0 / self.abnormal_count, 2)


def aggregate_cars(days: List[DayResult]) -> List[CarStat]:
    """Cộng dồn số lần/giờ bất thường theo từng xe qua nhiều ngày."""
    stats: Dict[str, CarStat] = {}
    for d in days:
        for shift in (d.day, d.night):
            for rec in shift.records:
                cs = stats.get(rec.car_id)
                if cs is None:
                    cs = CarStat(car_id=rec.car_id)
                    stats[rec.car_id] = cs
                cs.abnormal_count += 1
                cs.abnormal_hours += rec.stay_sec / 3600.0
    result = list(stats.values())
    for cs in result:
        cs.abnormal_hours = round(cs.abnormal_hours, 4)
    result.sort(key=lambda x: (-x.abnormal_count, -x.abnormal_hours, x.car_id))
    return result


# --- Thống kê theo điểm --------------------------------------------------------

@dataclass
class PointStat:
    point_id: str
    abnormal_count: int = 0
    abnormal_hours: float = 0.0
    cars: Set[str] = field(default_factory=set)

    @property
    def abnormal_min(self) -> float:
        return round(self.abnormal_hours * 60.0, 2)

    @property
    def avg_min(self) -> float:
        if self.abnormal_count <= 0:
            return 0.0
        return round(self.abnormal_hours * 60.0 / self.abnormal_count, 2)

    @property
    def car_count(self) -> int:
        return len(self.cars)


def aggregate_points(days: List[DayResult]) -> List[PointStat]:
    """Cộng dồn bất thường theo từng ĐIỂM (điểm nào hay kẹt nhất)."""
    stats: Dict[str, PointStat] = {}
    for d in days:
        for shift in (d.day, d.night):
            for rec in shift.records:
                ps = stats.get(rec.point_id)
                if ps is None:
                    ps = PointStat(point_id=rec.point_id)
                    stats[rec.point_id] = ps
                ps.abnormal_count += 1
                ps.abnormal_hours += rec.stay_sec / 3600.0
                ps.cars.add(rec.car_id)
    result = list(stats.values())
    for ps in result:
        ps.abnormal_hours = round(ps.abnormal_hours, 4)
    result.sort(key=lambda x: (-x.abnormal_count, -x.abnormal_hours, x.point_id))
    return result


# --- Tổng hợp theo kỳ ----------------------------------------------------------

@dataclass
class PeriodSummary:
    """Tóm tắt một kỳ (tuần / tháng / ngày thứ 7)."""

    kind: str                       # 'week' | 'month' | 'saturday'
    label: str                      # nhãn hiển thị, vd '2026-W28' hoặc '2026-07'
    days: List[DayResult] = field(default_factory=list)
    denom_hours: float = DEFAULT_DENOM_HOURS

    @property
    def num_days(self) -> int:
        return len(self.days)

    @property
    def date_start(self):
        return min(d.base_date for d in self.days) if self.days else None

    @property
    def date_end(self):
        return max(d.base_date for d in self.days) if self.days else None

    @property
    def abnormal_count(self) -> int:
        return sum(d.abnormal_count for d in self.days)

    @property
    def abnormal_hours(self) -> float:
        return sum(d.abnormal_hours for d in self.days)

    @property
    def car_days(self) -> int:
        """Tổng số xe-ngày (mẫu số quy đổi)."""
        return sum(d.car_count for d in self.days)

    @property
    def distinct_car_count(self) -> int:
        cars = set()
        for d in self.days:
            cars.update(d.all_cars)
        return len(cars)

    @property
    def abnormal_rate(self) -> float:
        if self.car_days <= 0 or self.denom_hours <= 0:
            return 0.0
        return round(self.abnormal_hours / (self.denom_hours * self.car_days) * 100.0, 2)

    def car_stats(self) -> List[CarStat]:
        return aggregate_cars(self.days)

    def point_stats(self) -> List[PointStat]:
        return aggregate_points(self.days)

    def sorted_days(self) -> List[DayResult]:
        return sorted(self.days, key=lambda d: d.base_date)


def saturday_summaries(day_results: List[DayResult],
                       denom_hours: float = DEFAULT_DENOM_HOURS) -> List[PeriodSummary]:
    """Mỗi ngày thứ 7 là một PeriodSummary riêng (tổng hợp ngày AGV chạy cuối tuần)."""
    saturdays = [d for d in day_results if d.is_saturday]
    saturdays.sort(key=lambda d: d.base_date)
    summaries: List[PeriodSummary] = []
    for d in saturdays:
        summaries.append(PeriodSummary(
            kind="saturday",
            label="%s (Thứ Bảy)" % d.base_date.isoformat(),
            days=[d],
            denom_hours=denom_hours,
        ))
    return summaries


def weekly_summaries(day_results: List[DayResult],
                     denom_hours: float = DEFAULT_DENOM_HOURS) -> List[PeriodSummary]:
    """Gom theo tuần ISO (Thứ Hai - Chủ Nhật)."""
    groups: Dict[Tuple[int, int], List[DayResult]] = defaultdict(list)
    for d in day_results:
        groups[d.iso_week].append(d)

    summaries: List[PeriodSummary] = []
    for (iso_year, iso_week) in sorted(groups.keys()):
        days = sorted(groups[(iso_year, iso_week)], key=lambda d: d.base_date)
        summaries.append(PeriodSummary(
            kind="week",
            label="%d-W%02d" % (iso_year, iso_week),
            days=days,
            denom_hours=denom_hours,
        ))
    return summaries


def monthly_summaries(day_results: List[DayResult],
                      denom_hours: float = DEFAULT_DENOM_HOURS) -> List[PeriodSummary]:
    """Gom theo tháng dương lịch."""
    groups: Dict[Tuple[int, int], List[DayResult]] = defaultdict(list)
    for d in day_results:
        groups[d.year_month].append(d)

    summaries: List[PeriodSummary] = []
    for (year, month) in sorted(groups.keys()):
        days = sorted(groups[(year, month)], key=lambda d: d.base_date)
        summaries.append(PeriodSummary(
            kind="month",
            label="%04d-%02d" % (year, month),
            days=days,
            denom_hours=denom_hours,
        ))
    return summaries


# --- KPI tổng thể --------------------------------------------------------------

@dataclass
class OverallSummary:
    """KPI tổng thể của toàn bộ dữ liệu đã nạp - phục vụ dashboard cho sếp."""

    num_days: int = 0
    distinct_cars: int = 0
    car_days: int = 0
    abnormal_count: int = 0
    abnormal_hours: float = 0.0
    denom_hours: float = DEFAULT_DENOM_HOURS
    day_abnormal_hours: float = 0.0
    night_abnormal_hours: float = 0.0
    num_saturdays: int = 0
    worst_day: Optional[DayResult] = None
    best_day: Optional[DayResult] = None
    top_car: Optional[CarStat] = None
    top_point: Optional[PointStat] = None

    @property
    def abnormal_rate(self) -> float:
        if self.car_days <= 0 or self.denom_hours <= 0:
            return 0.0
        return round(self.abnormal_hours / (self.denom_hours * self.car_days) * 100.0, 2)

    @property
    def abnormal_minutes(self) -> float:
        return round(self.abnormal_hours * 60.0, 2)

    @property
    def avg_stay_min(self) -> float:
        if self.abnormal_count <= 0:
            return 0.0
        return round(self.abnormal_hours * 60.0 / self.abnormal_count, 2)

    @property
    def avg_abnormal_per_day(self) -> float:
        if self.num_days <= 0:
            return 0.0
        return round(self.abnormal_count / self.num_days, 2)


def overall_summary(day_results: List[DayResult],
                    denom_hours: float = DEFAULT_DENOM_HOURS) -> OverallSummary:
    if not day_results:
        return OverallSummary(denom_hours=denom_hours)

    distinct = set()
    for d in day_results:
        distinct.update(d.all_cars)

    cars = aggregate_cars(day_results)
    points = aggregate_points(day_results)

    worst = max(day_results, key=lambda d: d.abnormal_rate(denom_hours))
    best = min(day_results, key=lambda d: d.abnormal_rate(denom_hours))

    return OverallSummary(
        num_days=len(day_results),
        distinct_cars=len(distinct),
        car_days=sum(d.car_count for d in day_results),
        abnormal_count=sum(d.abnormal_count for d in day_results),
        abnormal_hours=round(sum(d.abnormal_hours for d in day_results), 4),
        denom_hours=denom_hours,
        day_abnormal_hours=round(sum(d.day.abnormal_hours for d in day_results), 4),
        night_abnormal_hours=round(sum(d.night.abnormal_hours for d in day_results), 4),
        num_saturdays=sum(1 for d in day_results if d.is_saturday),
        worst_day=worst,
        best_day=best,
        top_car=cars[0] if cars else None,
        top_point=points[0] if points else None,
    )


# --- Mẫu theo thứ trong tuần ---------------------------------------------------

@dataclass
class WeekdayStat:
    weekday: int                    # 0 = Thứ Hai ... 6 = Chủ Nhật
    name: str
    num_days: int = 0
    abnormal_count: int = 0
    abnormal_hours: float = 0.0
    car_days: int = 0
    denom_hours: float = DEFAULT_DENOM_HOURS

    @property
    def abnormal_rate(self) -> float:
        if self.car_days <= 0 or self.denom_hours <= 0:
            return 0.0
        return round(self.abnormal_hours / (self.denom_hours * self.car_days) * 100.0, 2)


def weekday_pattern(day_results: List[DayResult],
                    denom_hours: float = DEFAULT_DENOM_HOURS) -> List[WeekdayStat]:
    """Gộp theo thứ trong tuần (thứ mấy hay bất thường nhất)."""
    stats = [WeekdayStat(weekday=i, name=WEEKDAY_VI[i], denom_hours=denom_hours)
             for i in range(7)]
    for d in day_results:
        s = stats[d.base_date.weekday()]
        s.num_days += 1
        s.abnormal_count += d.abnormal_count
        s.abnormal_hours += d.abnormal_hours
        s.car_days += d.car_count
    for s in stats:
        s.abnormal_hours = round(s.abnormal_hours, 4)
    return stats


# --- So sánh ca ngày / ca đêm --------------------------------------------------

@dataclass
class ShiftAggregate:
    label: str                      # 'Ca ngày' | 'Ca đêm'
    abnormal_count: int = 0
    abnormal_hours: float = 0.0
    car_days: int = 0
    denom_hours: float = DEFAULT_DENOM_HOURS

    @property
    def abnormal_rate(self) -> float:
        if self.car_days <= 0 or self.denom_hours <= 0:
            return 0.0
        return round(self.abnormal_hours / (self.denom_hours * self.car_days) * 100.0, 2)

    @property
    def abnormal_min(self) -> float:
        return round(self.abnormal_hours * 60.0, 2)


def daynight_split(day_results: List[DayResult],
                   denom_hours: float = DEFAULT_DENOM_HOURS) -> List[ShiftAggregate]:
    """Trả về [ca ngày, ca đêm] đã cộng dồn toàn bộ dữ liệu."""
    day_agg = ShiftAggregate(label="Ca ngày", denom_hours=denom_hours)
    night_agg = ShiftAggregate(label="Ca đêm", denom_hours=denom_hours)
    for d in day_results:
        day_agg.abnormal_count += d.day.abnormal_count
        day_agg.abnormal_hours += d.day.abnormal_hours
        day_agg.car_days += d.day.car_count
        night_agg.abnormal_count += d.night.abnormal_count
        night_agg.abnormal_hours += d.night.abnormal_hours
        night_agg.car_days += d.night.car_count
    day_agg.abnormal_hours = round(day_agg.abnormal_hours, 4)
    night_agg.abnormal_hours = round(night_agg.abnormal_hours, 4)
    return [day_agg, night_agg]


# --- Phân nhóm mức độ nặng -----------------------------------------------------

@dataclass
class SeverityBucket:
    label: str
    min_minutes: float
    max_minutes: float              # float('inf') cho nhóm cuối
    count: int = 0
    abnormal_hours: float = 0.0

    @property
    def abnormal_min(self) -> float:
        return round(self.abnormal_hours * 60.0, 2)


def severity_buckets(day_results: List[DayResult]) -> List[SeverityBucket]:
    """Phân nhóm các lần bất thường theo thời gian dừng (mức độ nghiêm trọng)."""
    buckets = [
        SeverityBucket("Ngắn (< 20 phút)", 0, 20),
        SeverityBucket("Vừa (20 - 40 phút)", 20, 40),
        SeverityBucket("Dài (40 - 60 phút)", 40, 60),
        SeverityBucket("Rất dài (> 60 phút)", 60, float("inf")),
    ]
    for d in day_results:
        for shift in (d.day, d.night):
            for rec in shift.records:
                m = rec.stay_min
                for b in buckets:
                    if b.min_minutes <= m < b.max_minutes:
                        b.count += 1
                        b.abnormal_hours += rec.stay_sec / 3600.0
                        break
    for b in buckets:
        b.abnormal_hours = round(b.abnormal_hours, 4)
    return buckets


# --- Chuỗi xu hướng theo ngày --------------------------------------------------

def trend_series(day_results: List[DayResult],
                 denom_hours: float = DEFAULT_DENOM_HOURS) -> List[Tuple[date, float]]:
    """Danh sách (ngày, tỷ lệ bất thường %) theo thứ tự thời gian - để vẽ biểu đồ."""
    days = sorted(day_results, key=lambda d: d.base_date)
    return [(d.base_date, d.abnormal_rate(denom_hours)) for d in days]
