# -*- coding: utf-8 -*-
"""Cửa sổ chính của ứng dụng Phân tích AGV (PyQt5).

Tính năng:
  - Thêm nhiều thư mục log (nút, chọn thư mục cha tự động quét, kéo-thả).
  - Phân tích trong luồng riêng (QThread) -> giao diện không treo.
  - Tab Tổng quan (dashboard KPI + biểu đồ) để "nhìn phát là ra tất cả".
  - Kết quả theo tab: Tổng quan / Ngày / Điểm / Xe / Thứ 7 / Tuần / Tháng.
  - Cài đặt chỉnh sửa được (ngưỡng, thang máy, điểm loại trừ theo nhóm, giờ ca,
    số giờ mẫu số, ngưỡng màu, thư mục mặc định) và lưu ra point_settings.json.
  - Xuất Excel (công thức sống + biểu đồ) / CSV (kèm đầu vào + chú thích công thức).

Tương thích Python 3.8 + PyQt5.
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QThread, QTime, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTabWidget, QTimeEdit, QVBoxLayout, QWidget,
)

from ..core.abnormal import DayResult, detect_base_date, parse_folder
from ..core.config import Settings, app_dir, load_settings, save_settings
from ..core import aggregate, export
from .charts import BarChartWidget, KpiCard, TrendChartWidget

APP_TITLE = "Phân tích chất lượng AGV"

COLOR_OK = QColor(198, 239, 206)      # xanh nhạt
COLOR_WARN = QColor(255, 235, 156)    # vàng nhạt
COLOR_BAD = QColor(255, 199, 206)     # đỏ nhạt
COLOR_SAT = QColor(221, 235, 247)     # xanh dương nhạt (Thứ Bảy)

# Màu đậm cho biểu đồ
BAR_OK = QColor(80, 170, 110)
BAR_WARN = QColor(240, 180, 60)
BAR_BAD = QColor(220, 80, 80)
BAR_ACCENT = QColor(58, 118, 216)
BAR_ACCENT2 = QColor(140, 100, 200)


def _item(text, center=True, color: Optional[QColor] = None, bold=False) -> QTableWidgetItem:
    it = QTableWidgetItem("" if text is None else str(text))
    if center:
        it.setTextAlignment(Qt.AlignCenter)
    if color is not None:
        it.setBackground(color)
    if bold:
        f = it.font()
        f.setBold(True)
        it.setFont(f)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it


def make_table(headers: List[str], stretch_last=True) -> QTableWidget:
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    hh = t.horizontalHeader()
    hh.setSectionResizeMode(QHeaderView.ResizeToContents)
    if stretch_last:
        hh.setStretchLastSection(True)
    t.setSortingEnabled(False)
    return t


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    f = QFont()
    f.setPointSize(11)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet("color:#1F4E79; margin-top:6px;")
    return lbl


# --- Worker phân tích ---------------------------------------------------------

class AnalyzeWorker(QThread):
    progress = pyqtSignal(int, int, str)     # done, total, message
    finished_ok = pyqtSignal(object)         # List[DayResult]
    failed = pyqtSignal(str)

    def __init__(self, folders: List[Path], settings: Settings):
        super().__init__()
        self._folders = folders
        self._settings = settings

    def run(self):
        results: List[DayResult] = []
        total = len(self._folders)
        try:
            for i, folder in enumerate(self._folders, start=1):
                self.progress.emit(i - 1, total, "Đang phân tích: %s" % folder.name)
                try:
                    dr = parse_folder(folder, None, self._settings)
                    results.append(dr)
                    self.progress.emit(
                        i, total,
                        "Xong %s (%s) - %d lần bất thường" % (
                            folder.name, dr.base_date.isoformat(), dr.abnormal_count),
                    )
                except Exception as exc:  # noqa: BLE001
                    self.progress.emit(i, total, "LỖI %s: %s" % (folder.name, exc))
            self.finished_ok.emit(results)
        except Exception:  # noqa: BLE001
            self.failed.emit(traceback.format_exc())


# --- Cửa sổ chính -------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 820)
        self.setAcceptDrops(True)

        self._settings: Settings = load_settings()
        self._day_results: List[DayResult] = []
        self._worker: Optional[AnalyzeWorker] = None
        self._rate_ok = self._settings.rate_ok
        self._rate_warn = self._settings.rate_warn

        self._build_ui()
        self._apply_settings_to_ui(self._settings)
        self.statusBar().showMessage("Sẵn sàng. Hãy thêm thư mục log để bắt đầu.")

    # -- Màu theo tỷ lệ (ngưỡng động) -----------------------------------------

    def rate_color(self, rate: float) -> QColor:
        if rate >= self._rate_warn:
            return COLOR_BAD
        if rate >= self._rate_ok:
            return COLOR_WARN
        return COLOR_OK

    def rate_qcolor(self, rate: float) -> QColor:
        if rate >= self._rate_warn:
            return BAR_BAD
        if rate >= self._rate_ok:
            return BAR_WARN
        return BAR_OK

    # -- Xây dựng giao diện ---------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([440, 840])

        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.log.setPlaceholderText("Nhật ký hoạt động...")
        root.addWidget(self.log)

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)

        v.addWidget(_section_label("Danh sách thư mục log"))

        self.folder_table = make_table(["Thư mục", "Ngày", "Thứ", "Số file"], stretch_last=False)
        self.folder_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        v.addWidget(self.folder_table, 1)

        btns = QHBoxLayout()
        b_add = QPushButton("Thêm thư mục")
        b_add.setToolTip("Chọn một thư mục Log{ngày} chứa các file log .txt")
        b_add.clicked.connect(self.on_add_folder)
        b_parent = QPushButton("Thêm thư mục cha")
        b_parent.setToolTip("Chọn 1 thư mục cha -> tự động quét các thư mục con dạng Log{ngày}")
        b_parent.clicked.connect(self.on_add_parent)
        btns.addWidget(b_add)
        btns.addWidget(b_parent)
        v.addLayout(btns)

        btns2 = QHBoxLayout()
        b_del = QPushButton("Xóa mục chọn")
        b_del.clicked.connect(self.on_remove_selected)
        b_clear = QPushButton("Xóa tất cả")
        b_clear.clicked.connect(self.on_clear_folders)
        btns2.addWidget(b_del)
        btns2.addWidget(b_clear)
        v.addLayout(btns2)

        hint = QLabel("Mẹo: có thể KÉO-THẢ thư mục vào đây.")
        hint.setStyleSheet("color:#666; font-style:italic;")
        v.addWidget(hint)

        # Cài đặt trong vùng cuộn để không tràn màn hình
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(360)
        scroll.setWidget(self._build_settings_group())
        v.addWidget(scroll)

        self.b_analyze = QPushButton("PHÂN TÍCH")
        self.b_analyze.setMinimumHeight(40)
        self.b_analyze.setStyleSheet(
            "QPushButton{background:#2d7d46;color:white;font-weight:bold;border-radius:6px;font-size:14px;}"
            "QPushButton:hover{background:#35924f;}"
            "QPushButton:disabled{background:#9bbfa6;}")
        self.b_analyze.clicked.connect(self.on_analyze)
        v.addWidget(self.b_analyze)

        exp = QHBoxLayout()
        self.b_xlsx = QPushButton("Xuất Excel")
        self.b_xlsx.setToolTip("Xuất báo cáo Excel nhiều sheet, có công thức sống + biểu đồ")
        self.b_xlsx.clicked.connect(self.on_export_excel)
        self.b_xlsx.setEnabled(False)
        self.b_csv = QPushButton("Xuất CSV")
        self.b_csv.setToolTip("Xuất CSV kèm cột đầu vào và chú thích công thức")
        self.b_csv.clicked.connect(self.on_export_csv)
        self.b_csv.setEnabled(False)
        exp.addWidget(self.b_xlsx)
        exp.addWidget(self.b_csv)
        v.addLayout(exp)

        return w

    def _build_settings_group(self) -> QGroupBox:
        box = QGroupBox("Cài đặt phân tích")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignRight)

        self.sp_threshold = QSpinBox()
        self.sp_threshold.setRange(1, 240)
        self.sp_threshold.setSuffix(" phút")
        self.sp_threshold.setToolTip("Dừng quá ngưỡng này (trừ khi đang sạc) mới tính bất thường")
        form.addRow("Ngưỡng bất thường:", self.sp_threshold)

        self.cb_elevator = QCheckBox("Áp dụng ngưỡng riêng cho thang máy")
        form.addRow(self.cb_elevator)

        self.sp_elevator = QSpinBox()
        self.sp_elevator.setRange(1, 240)
        self.sp_elevator.setSuffix(" phút")
        form.addRow("Ngưỡng thang máy:", self.sp_elevator)

        self.ed_elevator_pts = QLineEdit()
        self.ed_elevator_pts.setPlaceholderText("vd: 221, 1294, 223, 1767")
        form.addRow("Điểm thang máy:", self.ed_elevator_pts)

        self.te_excluded = QPlainTextEdit()
        self.te_excluded.setMaximumHeight(70)
        self.te_excluded.setPlaceholderText("Mỗi dòng: Tên nhóm: điểm1, điểm2\nvd: Home: 232, 1025, 259")
        self.te_excluded.setToolTip("Điểm liệt kê ở đây không tính bất thường dù dừng bao lâu")
        form.addRow("Điểm loại trừ:", self.te_excluded)

        self.te_day_start = QTimeEdit()
        self.te_day_start.setDisplayFormat("HH:mm")
        self.te_day_end = QTimeEdit()
        self.te_day_end.setDisplayFormat("HH:mm")
        row_day = QHBoxLayout()
        row_day.addWidget(self.te_day_start)
        row_day.addWidget(QLabel("~"))
        row_day.addWidget(self.te_day_end)
        wday = QWidget(); wday.setLayout(row_day)
        form.addRow("Ca ngày:", wday)

        self.te_night_start = QTimeEdit()
        self.te_night_start.setDisplayFormat("HH:mm")
        self.te_night_end = QTimeEdit()
        self.te_night_end.setDisplayFormat("HH:mm")
        row_night = QHBoxLayout()
        row_night.addWidget(self.te_night_start)
        row_night.addWidget(QLabel("~ (hôm sau)"))
        row_night.addWidget(self.te_night_end)
        wnight = QWidget(); wnight.setLayout(row_night)
        form.addRow("Ca đêm:", wnight)

        self.sp_denom = QDoubleSpinBox()
        self.sp_denom.setRange(1.0, 48.0)
        self.sp_denom.setDecimals(1)
        self.sp_denom.setSuffix(" giờ")
        self.sp_denom.setToolTip("Số giờ mẫu số khi tính tỷ lệ (mặc định 24, giống bản gốc)")
        form.addRow("Số giờ mẫu số:", self.sp_denom)

        self.sp_rate_ok = QDoubleSpinBox()
        self.sp_rate_ok.setRange(0.0, 100.0)
        self.sp_rate_ok.setDecimals(1)
        self.sp_rate_ok.setSuffix(" %")
        form.addRow("Ngưỡng màu Tốt (dưới):", self.sp_rate_ok)

        self.sp_rate_warn = QDoubleSpinBox()
        self.sp_rate_warn.setRange(0.0, 100.0)
        self.sp_rate_warn.setDecimals(1)
        self.sp_rate_warn.setSuffix(" %")
        form.addRow("Ngưỡng màu Cảnh báo:", self.sp_rate_warn)

        self.ed_log_dir = QLineEdit()
        b_log_dir = QPushButton("Chọn")
        b_log_dir.clicked.connect(self.on_pick_log_dir)
        row_log = QHBoxLayout(); row_log.setContentsMargins(0, 0, 0, 0)
        row_log.addWidget(self.ed_log_dir); row_log.addWidget(b_log_dir)
        wlog = QWidget(); wlog.setLayout(row_log)
        form.addRow("Thư mục log mặc định:", wlog)

        self.ed_out_dir = QLineEdit()
        b_out_dir = QPushButton("Chọn")
        b_out_dir.clicked.connect(self.on_pick_out_dir)
        row_out = QHBoxLayout(); row_out.setContentsMargins(0, 0, 0, 0)
        row_out.addWidget(self.ed_out_dir); row_out.addWidget(b_out_dir)
        wout = QWidget(); wout.setLayout(row_out)
        form.addRow("Thư mục xuất mặc định:", wout)

        b_save = QPushButton("Lưu cài đặt vào point_settings.json")
        b_save.clicked.connect(self.on_save_settings)
        form.addRow(b_save)

        legend = QLabel("Màu tỷ lệ:  ● Tốt   ● Cảnh báo   ● Cao")
        legend.setStyleSheet("color:#555; font-size:11px;")
        form.addRow(legend)

        return box

    def _build_right_panel(self) -> QWidget:
        self.tabs = QTabWidget()

        self.tabs.addTab(self._build_dashboard_tab(), "Tổng quan")

        # Tab Theo ngày
        self.tbl_daily = make_table(
            ["Ngày", "Thứ", "Số xe", "Tổng bất thường",
             "Tỷ lệ ca ngày (%)", "Tỷ lệ ca đêm (%)", "Tỷ lệ cả ngày (%)", "Số file"])
        self.tbl_daily_detail = make_table(
            ["Ca", "Số xe", "Điểm", "Giờ đến", "Thời gian dừng (phút)"])
        self.tbl_daily.itemSelectionChanged.connect(self._on_daily_selected)
        self.tabs.addTab(self._vsplit(self.tbl_daily, self.tbl_daily_detail,
                                      "Tổng quan theo ngày", "Chi tiết bất thường ngày đã chọn"),
                         "Theo ngày")

        # Tab Theo điểm
        self.tbl_points = make_table(
            ["Điểm", "Số lượt bất thường", "Số xe liên quan",
             "Tổng thời gian (phút)", "Trung bình (phút)"])
        self.chart_points_tab = BarChartWidget()
        pt_wrap = QWidget(); pt_lay = QVBoxLayout(pt_wrap)
        pt_lay.setContentsMargins(6, 6, 6, 6)
        pt_lay.addWidget(_section_label("Xếp hạng điểm hay kẹt (top 12)"))
        pt_lay.addWidget(self.chart_points_tab)
        pt_lay.addWidget(_section_label("Chi tiết theo điểm"))
        pt_lay.addWidget(self.tbl_points, 1)
        self.tabs.addTab(pt_wrap, "Theo điểm")

        # Tab Theo xe
        self.tbl_cars = make_table(
            ["Số xe", "Số lượt bất thường", "Tổng thời gian (phút)", "Trung bình (phút)"])
        self.chart_cars_tab = BarChartWidget()
        car_wrap = QWidget(); car_lay = QVBoxLayout(car_wrap)
        car_lay.setContentsMargins(6, 6, 6, 6)
        car_lay.addWidget(_section_label("Xếp hạng xe bất thường (top 12)"))
        car_lay.addWidget(self.chart_cars_tab)
        car_lay.addWidget(_section_label("Chi tiết theo xe"))
        car_lay.addWidget(self.tbl_cars, 1)
        self.tabs.addTab(car_wrap, "Theo xe")

        # Tab Thứ 7
        self.tbl_sat = make_table(
            ["Ngày (Thứ 7)", "Số xe", "Tổng bất thường", "Giờ bất thường", "Tỷ lệ (%)"])
        self.tbl_sat_detail = make_table(
            ["Ca", "Số xe", "Điểm", "Giờ đến", "Thời gian dừng (phút)"])
        self.tbl_sat.itemSelectionChanged.connect(self._on_sat_selected)
        self.tabs.addTab(self._vsplit(self.tbl_sat, self.tbl_sat_detail,
                                      "Tóm tắt các ngày Thứ Bảy (AGV chạy khi nghỉ)",
                                      "Chi tiết Thứ Bảy đã chọn"),
                         "Thứ 7")

        # Tab Theo tuần
        self.tbl_week = make_table(
            ["Tuần (ISO)", "Từ ngày", "Đến ngày", "Số ngày", "Số xe",
             "Tổng bất thường", "Tỷ lệ bất thường (%)"])
        self.tbl_week_detail = make_table(
            ["Ngày", "Thứ", "Số xe", "Tổng bất thường", "Tỷ lệ cả ngày (%)"])
        self.tbl_week.itemSelectionChanged.connect(self._on_week_selected)
        self.tabs.addTab(self._vsplit(self.tbl_week, self.tbl_week_detail,
                                      "Chất lượng theo tuần (Thứ Hai - Chủ Nhật)",
                                      "Các ngày trong tuần đã chọn"),
                         "Theo tuần")

        # Tab Theo tháng
        self.tbl_month = make_table(
            ["Tháng", "Từ ngày", "Đến ngày", "Số ngày", "Số xe",
             "Tổng bất thường", "Tỷ lệ bất thường (%)"])
        self.tbl_month_detail = make_table(
            ["Ngày", "Thứ", "Số xe", "Tổng bất thường", "Tỷ lệ cả ngày (%)"])
        self.tbl_month.itemSelectionChanged.connect(self._on_month_selected)
        self.tabs.addTab(self._vsplit(self.tbl_month, self.tbl_month_detail,
                                      "Chất lượng theo tháng",
                                      "Các ngày trong tháng đã chọn"),
                         "Theo tháng")

        return self.tabs

    def _build_dashboard_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        v = QVBoxLayout(content)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        title = QLabel("Báo cáo chất lượng hoạt động AGV")
        tf = QFont(); tf.setPointSize(15); tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet("color:#1F4E79;")
        v.addWidget(title)
        self.lbl_dash_sub = QLabel("Chưa có dữ liệu. Hãy thêm thư mục log và bấm PHÂN TÍCH.")
        self.lbl_dash_sub.setStyleSheet("color:#666; font-style:italic;")
        v.addWidget(self.lbl_dash_sub)

        # Hàng KPI chính
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(8)
        self.kpi_days = KpiCard("Số ngày phân tích")
        self.kpi_cars = KpiCard("Tổng số xe")
        self.kpi_events = KpiCard("Tổng lượt bất thường")
        self.kpi_hours = KpiCard("Tổng giờ bất thường")
        self.kpi_rate = KpiCard("Tỷ lệ bất thường CHUNG")
        for i, card in enumerate(
                [self.kpi_days, self.kpi_cars, self.kpi_events, self.kpi_hours, self.kpi_rate]):
            kpi_grid.addWidget(card, 0, i)
        v.addLayout(kpi_grid)

        # Hàng điểm nhấn
        hl_grid = QGridLayout()
        hl_grid.setSpacing(8)
        self.kpi_worst = KpiCard("Ngày tệ nhất")
        self.kpi_best = KpiCard("Ngày tốt nhất")
        self.kpi_topcar = KpiCard("Xe cần chú ý nhất")
        self.kpi_toppoint = KpiCard("Điểm hay kẹt nhất")
        for i, card in enumerate(
                [self.kpi_worst, self.kpi_best, self.kpi_topcar, self.kpi_toppoint]):
            hl_grid.addWidget(card, 0, i)
        v.addLayout(hl_grid)

        # Biểu đồ xu hướng
        v.addWidget(_section_label("Xu hướng tỷ lệ bất thường theo ngày (%)"))
        self.chart_trend = TrendChartWidget()
        self.chart_trend.setMinimumHeight(210)
        v.addWidget(self.chart_trend)

        # Hai biểu đồ cạnh nhau: top điểm + top xe
        row2 = QHBoxLayout()
        col_a = QVBoxLayout()
        col_a.addWidget(_section_label("Top điểm hay kẹt (số lượt)"))
        self.chart_points = BarChartWidget()
        col_a.addWidget(self.chart_points)
        row2.addLayout(col_a, 1)
        col_b = QVBoxLayout()
        col_b.addWidget(_section_label("Top xe bất thường (số lượt)"))
        self.chart_cars = BarChartWidget()
        col_b.addWidget(self.chart_cars)
        row2.addLayout(col_b, 1)
        v.addLayout(row2)

        # Ca ngày/đêm + thứ trong tuần + mức độ nặng
        row3 = QHBoxLayout()
        col_c = QVBoxLayout()
        col_c.addWidget(_section_label("So sánh ca ngày / ca đêm (tỷ lệ %)"))
        self.chart_daynight = BarChartWidget()
        col_c.addWidget(self.chart_daynight)
        row3.addLayout(col_c, 1)
        col_d = QVBoxLayout()
        col_d.addWidget(_section_label("Mẫu theo thứ trong tuần (tỷ lệ %)"))
        self.chart_weekday = BarChartWidget()
        col_d.addWidget(self.chart_weekday)
        row3.addLayout(col_d, 1)
        v.addLayout(row3)

        v.addWidget(_section_label("Phân nhóm mức độ nặng (số lượt theo thời gian dừng)"))
        self.chart_severity = BarChartWidget()
        v.addWidget(self.chart_severity)

        v.addStretch(1)
        return scroll

    def _vsplit(self, top: QWidget, bottom: QWidget, top_label: str, bottom_label: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 6, 6, 6)
        sp = QSplitter(Qt.Vertical)
        top_wrap = QWidget(); tl = QVBoxLayout(top_wrap); tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(_section_label(top_label)); tl.addWidget(top)
        bot_wrap = QWidget(); bl = QVBoxLayout(bot_wrap); bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(_section_label(bottom_label)); bl.addWidget(bottom)
        sp.addWidget(top_wrap); sp.addWidget(bot_wrap)
        sp.setSizes([380, 260])
        v.addWidget(sp)
        return w

    # -- Cài đặt <-> giao diện ------------------------------------------------

    def _apply_settings_to_ui(self, s: Settings):
        self.sp_threshold.setValue(s.threshold_min)
        self.sp_elevator.setValue(s.elevator_threshold_min)
        self.cb_elevator.setChecked(bool(s.elevator_points))
        self.ed_elevator_pts.setText(", ".join(sorted(s.elevator_points)))
        self.te_excluded.setPlainText(self._format_excluded_groups(s.excluded_groups))
        self.te_day_start.setTime(QTime(s.day_start[0], s.day_start[1]))
        self.te_day_end.setTime(QTime(s.day_end[0], s.day_end[1]))
        self.te_night_start.setTime(QTime(s.night_start[0], s.night_start[1]))
        self.te_night_end.setTime(QTime(s.night_end[0], s.night_end[1]))
        self.sp_denom.setValue(s.denom_hours)
        self.sp_rate_ok.setValue(s.rate_ok)
        self.sp_rate_warn.setValue(s.rate_warn)
        self.ed_log_dir.setText(s.default_log_dir)
        self.ed_out_dir.setText(s.default_output_dir)
        self._rate_ok = s.rate_ok
        self._rate_warn = s.rate_warn

    @staticmethod
    def _format_excluded_groups(groups: Dict[str, List[str]]) -> str:
        lines = []
        for name, pts in groups.items():
            lines.append("%s: %s" % (name, ", ".join(str(p) for p in pts)))
        return "\n".join(lines)

    @staticmethod
    def _parse_points(text: str):
        out = set()
        for part in text.replace(";", ",").split(","):
            part = part.strip()
            if part:
                out.add(part)
        return out

    def _parse_excluded_groups(self, text: str) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for idx, line in enumerate(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                name, rest = line.split(":", 1)
                name = name.strip() or ("Nhóm %d" % (idx + 1))
            else:
                name, rest = ("Loại trừ", line)
            pts = [p.strip() for p in rest.replace(";", ",").split(",") if p.strip()]
            if pts:
                groups[name] = pts
        return groups

    def _read_settings_from_ui(self) -> Settings:
        elevator_pts = (self._parse_points(self.ed_elevator_pts.text())
                        if self.cb_elevator.isChecked() else set())
        groups = self._parse_excluded_groups(self.te_excluded.toPlainText())
        s = Settings(
            threshold_min=self.sp_threshold.value(),
            elevator_threshold_min=self.sp_elevator.value(),
            excluded_groups=groups,
            elevator_points=elevator_pts,
            day_start=(self.te_day_start.time().hour(), self.te_day_start.time().minute()),
            day_end=(self.te_day_end.time().hour(), self.te_day_end.time().minute()),
            night_start=(self.te_night_start.time().hour(), self.te_night_start.time().minute()),
            night_end=(self.te_night_end.time().hour(), self.te_night_end.time().minute()),
            denom_hours=self.sp_denom.value(),
            rate_ok=self.sp_rate_ok.value(),
            rate_warn=self.sp_rate_warn.value(),
            default_log_dir=self.ed_log_dir.text().strip(),
            default_output_dir=self.ed_out_dir.text().strip(),
        )
        return s

    # -- Quản lý thư mục ------------------------------------------------------

    def _existing_folders(self):
        return {self.folder_table.item(r, 0).data(Qt.UserRole)
                for r in range(self.folder_table.rowCount())}

    def _add_folder_row(self, folder: Path):
        folder = Path(folder)
        if str(folder) in {str(p) for p in self._existing_folders()}:
            return False
        d = detect_base_date(folder)
        files = list(folder.glob("Log*.txt"))
        r = self.folder_table.rowCount()
        self.folder_table.insertRow(r)
        it0 = _item(folder.name, center=False)
        it0.setData(Qt.UserRole, folder)
        it0.setToolTip(str(folder))
        self.folder_table.setItem(r, 0, it0)
        self.folder_table.setItem(r, 1, _item(d.isoformat() if d else "?"))
        self.folder_table.setItem(r, 2, _item(aggregate.weekday_name(d) if d else "?",
                                              color=COLOR_SAT if (d and d.weekday() == 5) else None))
        self.folder_table.setItem(r, 3, _item(len(files)))
        return True

    def on_add_folder(self):
        start = self.ed_log_dir.text().strip() or ""
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục log", start)
        if folder:
            if self._add_folder_row(Path(folder)):
                self._log("Đã thêm: %s" % folder)
            else:
                self._log("Đã có trong danh sách: %s" % folder)

    def on_add_parent(self):
        start = self.ed_log_dir.text().strip() or ""
        parent = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục cha (chứa các thư mục Log...)", start)
        if not parent:
            return
        parent_path = Path(parent)
        count = 0
        candidates = sorted([p for p in parent_path.iterdir() if p.is_dir()])
        for sub in candidates:
            if detect_base_date(sub) is not None and list(sub.glob("Log*.txt")):
                if self._add_folder_row(sub):
                    count += 1
        if count == 0 and detect_base_date(parent_path) is not None:
            if self._add_folder_row(parent_path):
                count = 1
        self._log("Đã thêm %d thư mục từ: %s" % (count, parent))
        if count == 0:
            QMessageBox.information(self, "Thông báo",
                                    "Không tìm thấy thư mục con dạng Log{ngày} có file log.")

    def on_remove_selected(self):
        rows = sorted({i.row() for i in self.folder_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.folder_table.removeRow(r)

    def on_clear_folders(self):
        self.folder_table.setRowCount(0)

    def on_pick_log_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục log mặc định",
                                                  self.ed_log_dir.text().strip() or "")
        if folder:
            self.ed_log_dir.setText(folder)

    def on_pick_out_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất mặc định",
                                                  self.ed_out_dir.text().strip() or "")
        if folder:
            self.ed_out_dir.setText(folder)

    # -- Kéo thả --------------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        added = 0
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                if detect_base_date(p) is not None and list(p.glob("Log*.txt")):
                    added += 1 if self._add_folder_row(p) else 0
                else:
                    for sub in sorted([x for x in p.iterdir() if x.is_dir()]):
                        if detect_base_date(sub) is not None and list(sub.glob("Log*.txt")):
                            added += 1 if self._add_folder_row(sub) else 0
        if added:
            self._log("Kéo-thả: đã thêm %d thư mục." % added)

    # -- Phân tích ------------------------------------------------------------

    def on_analyze(self):
        folders = [self.folder_table.item(r, 0).data(Qt.UserRole)
                   for r in range(self.folder_table.rowCount())]
        if not folders:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Hãy thêm ít nhất một thư mục log.")
            return

        self._settings = self._read_settings_from_ui()
        self._rate_ok = self._settings.rate_ok
        self._rate_warn = self._settings.rate_warn
        self.b_analyze.setEnabled(False)
        self.b_xlsx.setEnabled(False)
        self.b_csv.setEnabled(False)
        self.progress.setValue(0)
        self._log("=== Bắt đầu phân tích %d thư mục ===" % len(folders))

        self._worker = AnalyzeWorker(folders, self._settings)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_analyze_done)
        self._worker.failed.connect(self._on_analyze_failed)
        self._worker.start()

    def _on_progress(self, done: int, total: int, message: str):
        pct = int(done / total * 100) if total else 0
        self.progress.setValue(pct)
        self._log(message)
        self.statusBar().showMessage(message)

    def _on_analyze_failed(self, tb: str):
        self.b_analyze.setEnabled(True)
        self._log("LỖI NGHIÊM TRỌNG:\n" + tb)
        QMessageBox.critical(self, "Lỗi", "Phân tích thất bại:\n" + tb)

    def _on_analyze_done(self, results: List[DayResult]):
        self._day_results = sorted(results, key=lambda d: d.base_date)
        self.b_analyze.setEnabled(True)
        self.b_xlsx.setEnabled(bool(results))
        self.b_csv.setEnabled(bool(results))
        self.progress.setValue(100)
        self._populate_all()
        n_sat = sum(1 for d in self._day_results if d.is_saturday)
        self._log("=== Hoàn tất: %d ngày, %d ngày Thứ Bảy ===" % (len(results), n_sat))
        self.statusBar().showMessage(
            "Hoàn tất: %d ngày dữ liệu. Xem kết quả ở các tab bên phải." % len(results))
        self.tabs.setCurrentIndex(0)

    # -- Đổ dữ liệu vào bảng --------------------------------------------------

    def _populate_all(self):
        self._populate_dashboard()
        self._populate_daily()
        self._populate_points()
        self._populate_cars()
        self._populate_saturday()
        self._populate_weekly()
        self._populate_monthly()

    def _denom(self) -> float:
        return self._settings.denom_hours

    def _populate_dashboard(self):
        days = self._day_results
        denom = self._denom()
        if not days:
            return
        summ = aggregate.overall_summary(days, denom)

        d0 = min(d.base_date for d in days).isoformat()
        d1 = max(d.base_date for d in days).isoformat()
        self.lbl_dash_sub.setText(
            "Khoảng dữ liệu: %s → %s   |   Số giờ mẫu số: %g giờ/ngày   |   %d ngày Thứ Bảy"
            % (d0, d1, denom, summ.num_saturdays))

        rate = summ.abnormal_rate
        rate_accent = self._accent_hex(rate)
        self.kpi_days.set_value(summ.num_days, "ngày dữ liệu", "#3a76d8")
        self.kpi_cars.set_value(summ.distinct_cars, "xe khác nhau", "#8c64c8")
        self.kpi_events.set_value(summ.abnormal_count,
                                  "TB %.1f lượt/ngày" % summ.avg_abnormal_per_day, "#d88a3a")
        self.kpi_hours.set_value("%.1f" % (summ.abnormal_hours),
                                 "TB dừng %.1f phút/lượt" % summ.avg_stay_min, "#d88a3a")
        self.kpi_rate.set_value("%.2f%%" % rate, "toàn bộ dữ liệu", rate_accent)

        if summ.worst_day:
            wr = summ.worst_day.abnormal_rate(denom)
            self.kpi_worst.set_value(summ.worst_day.base_date.isoformat(),
                                     "%s - %.2f%%" % (aggregate.weekday_name(summ.worst_day.base_date), wr),
                                     self._accent_hex(wr))
        if summ.best_day:
            br = summ.best_day.abnormal_rate(denom)
            self.kpi_best.set_value(summ.best_day.base_date.isoformat(),
                                    "%s - %.2f%%" % (aggregate.weekday_name(summ.best_day.base_date), br),
                                    self._accent_hex(br))
        if summ.top_car:
            self.kpi_topcar.set_value("Xe %s" % summ.top_car.car_id,
                                      "%d lượt - %.1f phút" % (summ.top_car.abnormal_count,
                                                               summ.top_car.abnormal_min),
                                      "#c0504d")
        if summ.top_point:
            self.kpi_toppoint.set_value("Điểm %s" % summ.top_point.point_id,
                                        "%d lượt - %d xe" % (summ.top_point.abnormal_count,
                                                             summ.top_point.car_count),
                                        "#c0504d")

        # Xu hướng
        series = aggregate.trend_series(days, denom)
        points = [(d.strftime("%m-%d"), v) for d, v in series]
        self.chart_trend.set_data(points, suffix="%",
                                  thresholds=[(self._rate_ok, BAR_WARN), (self._rate_warn, BAR_BAD)])

        # Top điểm / top xe
        top_points = aggregate.aggregate_points(days)[:10]
        self.chart_points.set_data(
            [("Điểm %s" % p.point_id, p.abnormal_count, BAR_ACCENT) for p in top_points])
        top_cars = aggregate.aggregate_cars(days)[:10]
        self.chart_cars.set_data(
            [("Xe %s" % c.car_id, c.abnormal_count, BAR_ACCENT2) for c in top_cars])

        # Ca ngày / đêm
        dn = aggregate.daynight_split(days, denom)
        self.chart_daynight.set_data(
            [(a.label, a.abnormal_rate, self.rate_qcolor(a.abnormal_rate)) for a in dn], suffix="%")

        # Thứ trong tuần (chỉ hiện các thứ có dữ liệu)
        wp = [s for s in aggregate.weekday_pattern(days, denom) if s.num_days > 0]
        self.chart_weekday.set_data(
            [(s.name, s.abnormal_rate, self.rate_qcolor(s.abnormal_rate)) for s in wp], suffix="%")

        # Mức độ nặng
        buckets = aggregate.severity_buckets(days)
        sev_colors = [BAR_OK, BAR_WARN, QColor(230, 130, 60), BAR_BAD]
        self.chart_severity.set_data(
            [(b.label, b.count, sev_colors[i]) for i, b in enumerate(buckets)])

    def _accent_hex(self, rate: float) -> str:
        if rate >= self._rate_warn:
            return "#c0504d"
        if rate >= self._rate_ok:
            return "#e0a030"
        return "#2d7d46"

    def _populate_daily(self):
        t = self.tbl_daily
        t.setRowCount(0)
        denom = self._denom()
        for d in self._day_results:
            r = t.rowCount(); t.insertRow(r)
            day_rate = d.day.abnormal_rate(denom)
            night_rate = d.night.abnormal_rate(denom)
            full_rate = d.abnormal_rate(denom)
            sat = d.is_saturday
            t.setItem(r, 0, _item(d.base_date.isoformat(), color=COLOR_SAT if sat else None))
            t.setItem(r, 1, _item(aggregate.weekday_name(d.base_date), color=COLOR_SAT if sat else None))
            t.setItem(r, 2, _item(d.car_count))
            t.setItem(r, 3, _item(d.abnormal_count))
            t.setItem(r, 4, _item(day_rate, color=self.rate_color(day_rate)))
            t.setItem(r, 5, _item(night_rate, color=self.rate_color(night_rate)))
            t.setItem(r, 6, _item(full_rate, color=self.rate_color(full_rate)))
            t.setItem(r, 7, _item(d.log_file_count))
            t.item(r, 0).setData(Qt.UserRole, d)
        if t.rowCount():
            t.selectRow(0)

    def _fill_detail_records(self, table: QTableWidget, day: DayResult):
        table.setRowCount(0)
        for shift in (day.day, day.night):
            label = "Ca ngày" if shift.label == "day" else "Ca đêm"
            by_car = shift.abnormal_by_car()
            for car_id in sorted(by_car.keys()):
                for rec in by_car[car_id]:
                    r = table.rowCount(); table.insertRow(r)
                    table.setItem(r, 0, _item(label))
                    table.setItem(r, 1, _item(car_id))
                    table.setItem(r, 2, _item("Điểm %s" % rec.point_id))
                    table.setItem(r, 3, _item(rec.arrival_time.strftime("%H:%M:%S")))
                    table.setItem(r, 4, _item(rec.stay_min))

    def _selected_day(self, table: QTableWidget) -> Optional[DayResult]:
        rows = {i.row() for i in table.selectedIndexes()}
        if not rows:
            return None
        r = min(rows)
        it = table.item(r, 0)
        return it.data(Qt.UserRole) if it else None

    def _on_daily_selected(self):
        d = self._selected_day(self.tbl_daily)
        if d:
            self._fill_detail_records(self.tbl_daily_detail, d)

    def _populate_points(self):
        days = self._day_results
        stats = aggregate.aggregate_points(days)
        t = self.tbl_points
        t.setRowCount(0)
        for ps in stats:
            r = t.rowCount(); t.insertRow(r)
            t.setItem(r, 0, _item("Điểm %s" % ps.point_id))
            t.setItem(r, 1, _item(ps.abnormal_count))
            t.setItem(r, 2, _item(ps.car_count))
            t.setItem(r, 3, _item(ps.abnormal_min))
            t.setItem(r, 4, _item(ps.avg_min))
        self.chart_points_tab.set_data(
            [("Điểm %s" % p.point_id, p.abnormal_count, BAR_ACCENT) for p in stats[:12]])

    def _populate_cars(self):
        stats = aggregate.aggregate_cars(self._day_results)
        t = self.tbl_cars
        t.setRowCount(0)
        for cs in stats:
            r = t.rowCount(); t.insertRow(r)
            t.setItem(r, 0, _item(cs.car_id))
            t.setItem(r, 1, _item(cs.abnormal_count))
            t.setItem(r, 2, _item(cs.abnormal_min))
            t.setItem(r, 3, _item(cs.avg_min))
        self.chart_cars_tab.set_data(
            [("Xe %s" % c.car_id, c.abnormal_count, BAR_ACCENT2) for c in stats[:12]])

    def _populate_saturday(self):
        t = self.tbl_sat
        t.setRowCount(0)
        denom = self._denom()
        sats = [d for d in self._day_results if d.is_saturday]
        for d in sats:
            r = t.rowCount(); t.insertRow(r)
            rate = d.abnormal_rate(denom)
            t.setItem(r, 0, _item(d.base_date.isoformat(), color=COLOR_SAT))
            t.setItem(r, 1, _item(d.car_count))
            t.setItem(r, 2, _item(d.abnormal_count))
            t.setItem(r, 3, _item(round(d.abnormal_hours, 2)))
            t.setItem(r, 4, _item(rate, color=self.rate_color(rate)))
            t.item(r, 0).setData(Qt.UserRole, d)
        if t.rowCount():
            t.selectRow(0)
        else:
            self.tbl_sat_detail.setRowCount(0)

    def _on_sat_selected(self):
        d = self._selected_day(self.tbl_sat)
        if d:
            self._fill_detail_records(self.tbl_sat_detail, d)

    def _populate_period_table(self, table: QTableWidget, summaries):
        table.setRowCount(0)
        for s in summaries:
            r = table.rowCount(); table.insertRow(r)
            table.setItem(r, 0, _item(s.label))
            table.setItem(r, 1, _item(s.date_start.isoformat() if s.date_start else "-"))
            table.setItem(r, 2, _item(s.date_end.isoformat() if s.date_end else "-"))
            table.setItem(r, 3, _item(s.num_days))
            table.setItem(r, 4, _item(s.distinct_car_count))
            table.setItem(r, 5, _item(s.abnormal_count))
            table.setItem(r, 6, _item(s.abnormal_rate, color=self.rate_color(s.abnormal_rate)))
            table.item(r, 0).setData(Qt.UserRole, s)
        if table.rowCount():
            table.selectRow(0)

    def _fill_period_detail(self, table: QTableWidget, summary):
        table.setRowCount(0)
        if not summary:
            return
        denom = self._denom()
        for d in summary.sorted_days():
            r = table.rowCount(); table.insertRow(r)
            rate = d.abnormal_rate(denom)
            sat = d.is_saturday
            table.setItem(r, 0, _item(d.base_date.isoformat(), color=COLOR_SAT if sat else None))
            table.setItem(r, 1, _item(aggregate.weekday_name(d.base_date),
                                      color=COLOR_SAT if sat else None))
            table.setItem(r, 2, _item(d.car_count))
            table.setItem(r, 3, _item(d.abnormal_count))
            table.setItem(r, 4, _item(rate, color=self.rate_color(rate)))

    def _populate_weekly(self):
        self._weeks = aggregate.weekly_summaries(self._day_results, self._denom())
        self._populate_period_table(self.tbl_week, self._weeks)

    def _on_week_selected(self):
        rows = {i.row() for i in self.tbl_week.selectedIndexes()}
        if rows:
            it = self.tbl_week.item(min(rows), 0)
            self._fill_period_detail(self.tbl_week_detail, it.data(Qt.UserRole) if it else None)

    def _populate_monthly(self):
        self._months = aggregate.monthly_summaries(self._day_results, self._denom())
        self._populate_period_table(self.tbl_month, self._months)

    def _on_month_selected(self):
        rows = {i.row() for i in self.tbl_month.selectedIndexes()}
        if rows:
            it = self.tbl_month.item(min(rows), 0)
            self._fill_period_detail(self.tbl_month_detail, it.data(Qt.UserRole) if it else None)

    # -- Xuất file ------------------------------------------------------------

    def _default_out_dir(self) -> Path:
        out = self.ed_out_dir.text().strip()
        if out and Path(out).exists():
            return Path(out)
        return app_dir()

    def on_export_excel(self):
        if not self._day_results:
            return
        default = str(self._default_out_dir() / "BaoCao_AGV.xlsx")
        path, _ = QFileDialog.getSaveFileName(self, "Lưu báo cáo Excel", default, "Excel (*.xlsx)")
        if not path:
            return
        try:
            export.export_full_report(self._day_results, Path(path),
                                      self._settings.threshold_min, self._settings.denom_hours)
            self._log("Đã xuất Excel: %s" % path)
            QMessageBox.information(self, "Thành công", "Đã xuất báo cáo:\n%s" % path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Lỗi", "Xuất Excel thất bại:\n%s" % exc)

    def on_export_csv(self):
        if not self._day_results:
            return
        default = str(self._default_out_dir() / "TongQuan_AGV.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Lưu CSV tổng quan", default, "CSV (*.csv)")
        if not path:
            return
        try:
            export.export_summary_csv(self._day_results, Path(path), self._settings.denom_hours)
            self._log("Đã xuất CSV: %s" % path)
            QMessageBox.information(self, "Thành công", "Đã xuất CSV:\n%s" % path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Lỗi", "Xuất CSV thất bại:\n%s" % exc)

    def on_save_settings(self):
        s = self._read_settings_from_ui()
        try:
            path = save_settings(s)
            self._settings = s
            self._rate_ok = s.rate_ok
            self._rate_warn = s.rate_warn
            if self._day_results:
                self._populate_all()
            self._log("Đã lưu cài đặt: %s" % path)
            QMessageBox.information(self, "Thành công", "Đã lưu cài đặt vào:\n%s" % path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Lỗi", "Lưu cài đặt thất bại:\n%s" % exc)

    # -- Tiện ích -------------------------------------------------------------

    def _log(self, msg: str):
        self.log.appendPlainText(msg)
