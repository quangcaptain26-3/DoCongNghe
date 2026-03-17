"""
Factory Dashboard - 3x3 Grid
Thư viện: tkinter (built-in), random, math (built-in)
Chạy: python main.py
"""
import tkinter as tk
from tkinter import font
import random
import math
import time
from collections import deque

# ─── CONFIG ───────────────────────────────────────────────
# Bảng màu tối ưu cho dashboard trong môi trường nhà máy (tương phản cao, ít chói).
BG       = "#0a0f1e"
CARD_BG  = "#0d1530"
BORDER   = "#1a2a4a"
ACCENT   = "#00d4ff"
GREEN    = "#00ff88"
YELLOW   = "#ffd700"
RED      = "#ff4444"
ORANGE   = "#ff8c00"
WHITE    = "#e8f0fe"
DIM      = "#4a6080"

# Nhịp refresh tách theo “mức độ động” để UI mượt mà nhưng không tốn CPU vô ích:
# - FAST: animation/đối tượng chuyển động (AGV)
# - MEDIUM: biểu đồ + số liệu cập nhật theo nhịp giây
# - SLOW: KPI lớn/thống kê tích luỹ, không cần cập nhật liên tục
REFRESH_FAST   = 100   # ms  - AGV, gauges
REFRESH_MEDIUM = 1000  # ms  - charts, counters
REFRESH_SLOW   = 5000  # ms  - big KPIs


# ─── CHART HELPERS ─────────────────────────────────────────
def _draw_axes_and_grid(cv: tk.Canvas, *, W: int, H: int, pad: int,
                        xlabel: str = "", ylabel: str = "",
                        grid_x: int = 5, grid_y: int = 4,
                        axis_color: str = BORDER, grid_color: str = "#132242",
                        text_color: str = DIM):
    """
    Vẽ trục + grid cơ bản trên Tkinter Canvas.

    Lưu ý thiết kế:
    - Tkinter Canvas không có “coordinate system” sẵn như Matplotlib, nên ta tự quy ước
      vùng plot (x0,y0)-(x1,y1) để các panel dùng chung và vẽ nhất quán.
    - Hàm này chỉ lo phần nền (axes/grid/labels) và trả về vùng plot để phần vẽ dữ liệu
      không bị phụ thuộc vào layout chi tiết của từng card.

    Returns: (x0, y0, x1, y1) vùng plot (đã trừ padding & label).
    """
    # dành chỗ cho label trục
    lx = 26 if ylabel else 10
    by = 18 if xlabel else 8
    x0, y0 = pad + lx, pad
    x1, y1 = W - pad, H - pad - by
    if x1 <= x0 + 10 or y1 <= y0 + 10:
        return x0, y0, x1, y1

    # grid
    if grid_y > 0:
        for i in range(1, grid_y + 1):
            y = y0 + int(i * (y1 - y0) / (grid_y + 1))
            cv.create_line(x0, y, x1, y, fill=grid_color)
    if grid_x > 0:
        for i in range(1, grid_x + 1):
            x = x0 + int(i * (x1 - x0) / (grid_x + 1))
            cv.create_line(x, y0, x, y1, fill=grid_color)

    # axes
    cv.create_line(x0, y1, x1, y1, fill=axis_color, width=1)
    cv.create_line(x0, y0, x0, y1, fill=axis_color, width=1)

    # labels
    if xlabel:
        cv.create_text((x0 + x1) // 2, H - pad - 2,
                       text=xlabel, fill=text_color,
                       font=("Consolas", 7), anchor="s")
    if ylabel:
        cv.create_text(pad + 10, (y0 + y1) // 2,
                       text=ylabel, fill=text_color,
                       font=("Consolas", 7), angle=90)
    return x0, y0, x1, y1


class RollingBuffer:
    def __init__(self, maxlen: int, init=None):
        # Dùng deque(maxlen=...) để tự động “cuộn” lịch sử (rolling window)
        # mà không phải pop(0) (O(n)) trên list.
        self.buf = deque(maxlen=maxlen)
        if init is not None:
            for v in init:
                self.buf.append(v)

    def append(self, v):
        self.buf.append(v)

    def values(self):
        return list(self.buf)

    def __len__(self):
        return len(self.buf)


# ══════════════════════════════════════════════════════════
class Card(tk.Frame):
    """Khung card tái sử dụng"""
    def __init__(self, parent, title="", **kw):
        super().__init__(parent, bg=CARD_BG,
                         highlightbackground=BORDER,
                         highlightthickness=1, **kw)
        if title:
            # Title dùng font nhỏ + accent để thống nhất tất cả card,
            # giúp mắt người vận hành quét thông tin nhanh.
            tk.Label(self, text=title, bg=CARD_BG, fg=ACCENT,
                     font=("Consolas", 9, "bold")).pack(anchor="w", padx=8, pady=(6,0))


# ══════════════════════════════════════════════════════════
# CELL 1 – ENERGY
# ══════════════════════════════════════════════════════════
class EnergyPanel(Card):
    def __init__(self, parent):
        super().__init__(parent, title="⚡ ENERGY")
        self.vals = {"elec": 44.0, "water": 12.5, "temp_in": 22.0, "temp_out": 20.8}
        # Rolling history cho từng chỉ số: hiển thị mini sparkline giúp “đọc xu hướng”
        # mà vẫn nhẹ (chỉ vẽ 1 polyline mảnh / metric, không smooth).
        self._hist = {
            "elec": RollingBuffer(40, init=[self.vals["elec"]] * 10),
            "water": RollingBuffer(40, init=[self.vals["water"]] * 10),
            "temp_in": RollingBuffer(40, init=[self.vals["temp_in"]] * 10),
            "temp_out": RollingBuffer(40, init=[self.vals["temp_out"]] * 10),
        }
        # Gợi ý thay dữ liệu thật:
        # - elec (kWh): đọc từ meter / SCADA
        # - water (m³): đọc từ flow meter
        # - temp_in/out (°C): đọc từ sensor/PLC
        self._build()
        self._tick()

    def _build(self):
        f = tk.Frame(self, bg=CARD_BG)
        f.pack(fill="both", expand=True, padx=8, pady=4)

        rows = [
            ("Electricity", "elec",  "kWh", YELLOW),
            ("Water",       "water", "m³",  ACCENT),
            ("Temp In",     "temp_in","°C", GREEN),
            ("Temp Out",    "temp_out","°C",ORANGE),
        ]
        self._labels = {}
        for name, key, unit, color in rows:
            r = tk.Frame(f, bg=CARD_BG)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=name, bg=CARD_BG, fg=DIM,
                     font=("Consolas", 8), width=11, anchor="w").pack(side="left")
            lv = tk.Label(r, text="--", bg=CARD_BG, fg=color,
                          font=("Consolas", 11, "bold"), width=6, anchor="e")
            lv.pack(side="left")
            tk.Label(r, text=unit, bg=CARD_BG, fg=DIM,
                     font=("Consolas", 7)).pack(side="left", padx=2)

            # Mini chart (sparkline + progress overlay) để nhìn “mức + trend”.
            cv = tk.Canvas(r, bg=CARD_BG, height=18, highlightthickness=0)
            cv.pack(side="right", padx=4, fill="both", expand=True)
            self._labels[key] = (lv, cv, color, unit)

    def _tick(self):
        # Panel dạng “monitoring”: cập nhật nhẹ quanh giá trị hiện tại để nhìn có dao động
        # như dữ liệu thực tế, tránh nhảy biên độ lớn gây khó đọc.
        # Tham số biên độ (-0.3..0.3) là “độ rung” mô phỏng; tăng lên nếu muốn dữ liệu sống hơn.
        for k in self.vals:
            self.vals[k] += random.uniform(-0.3, 0.3)
        maxv = {"elec": 80, "water": 30, "temp_in": 40, "temp_out": 40}
        # maxv là “thang” để scale progress/sparkline ổn định (không auto-scale theo từng tick).
        # Khi nối dữ liệu thật, nên map maxv theo định mức/giới hạn vận hành.
        for key, (lv, cv, color, unit) in self._labels.items():
            v = round(self.vals[key], 1)
            lv.config(text=f"{v:.1f}")
            # Clamp 0..1 để thanh progress không bị vẽ lệch khi dữ liệu vượt range.
            pct = min(max(v / maxv[key], 0), 1)

            # cập nhật history
            self._hist[key].append(v)
            hist = self._hist[key].values()

            # vẽ mini chart: 1 nền + 1 progress + 1 sparkline (nhẹ)
            cv.delete("all")
            W = cv.winfo_width() or 120
            H = cv.winfo_height() or 18
            pad = 2

            # nền + progress (dạng bar mỏng phía dưới)
            bar_h = 5
            bx0, by0 = pad, H - pad - bar_h
            bx1, by1 = W - pad, H - pad
            cv.create_rectangle(bx0, by0, bx1, by1, fill=BORDER, outline="")
            cv.create_rectangle(bx0, by0, bx0 + int((bx1 - bx0) * pct), by1,
                                fill=color, outline="")

            # sparkline (phía trên): scale theo cửa sổ gần nhất nhưng giới hạn bằng maxv để ổn định
            sx0, sy0 = pad, pad
            sx1, sy1 = W - pad, by0 - 2
            cv.create_rectangle(sx0, sy0, sx1, sy1, outline="#132242", width=1)
            # grid rất nhẹ
            mid = (sy0 + sy1) // 2
            cv.create_line(sx0, mid, sx1, mid, fill="#132242")

            if len(hist) >= 2 and sx1 > sx0 and sy1 > sy0:
                # Với dữ liệu mô phỏng: clamp 0..maxv để tránh “vọt” làm mất cân biểu đồ.
                vmax = float(maxv[key])
                pts = []
                for i, hv in enumerate(hist):
                    x = sx0 + int(i / max(1, (len(hist) - 1)) * (sx1 - sx0))
                    y = sy1 - int(min(max(hv, 0.0), vmax) / vmax * (sy1 - sy0))
                    pts += [x, y]
                if len(pts) >= 4:
                    cv.create_line(*pts, fill=color, width=1, smooth=False)

            # nhãn nhỏ góc phải (để nhìn nhanh mà không cần nhìn sang value)
            cv.create_text(W - pad, pad, text=f"{v:.1f}{unit}",
                           anchor="ne", fill=DIM, font=("Consolas", 7))
        self.after(REFRESH_MEDIUM, self._tick)


# ══════════════════════════════════════════════════════════
# CELL 2 – AGV ROUTE (chạy theo hình chữ nhật)
# ══════════════════════════════════════════════════════════
class AGVPanel(Card):
    """
    Mỗi AGV chạy theo 1 vòng chữ nhật lồng nhau (margin khác nhau).
    Vị trí được tính theo perimeter chuẩn hoá 0..1.
    """
    def __init__(self, parent):
        super().__init__(parent, title="🚗 AGV ROUTE")
        self.cv = tk.Canvas(self, bg="#060d1a", highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=8, pady=4)

        # margin (px từ edge) cho 3 rect lồng nhau
        self.margins = [8, 22, 36]
        colors  = [ACCENT,   GREEN,    YELLOW]
        labels  = ["MAT-AGV","PCB-AGV","FG-AGV"]
        speeds  = [0.004,    0.006,    0.003]   # tốc độ khác nhau

        self.agvs = []
        for i in range(3):
            self.agvs.append({
                "margin": self.margins[i],
                "color":  colors[i],
                "label":  labels[i],
                "speed":  speeds[i],
                "t":      i / 3,          # lệch pha
            })
        self._tick()

    # ── tính tọa độ (x,y) trên perimeter chữ nhật ──────────
    @staticmethod
    def _rect_pos(t, x0, y0, x1, y1):
        """
        t ∈ [0,1) → (px, py) đi clockwise quanh rect.

        Ý tưởng: chuẩn hoá chuyển động theo “chiều dài đường đi” (perimeter),
        để dù rect to/nhỏ thì tốc độ theo pixel vẫn tương đối đều.
        """
        W = x1 - x0
        H = y1 - y0
        perim = 2 * (W + H)
        d = (t % 1.0) * perim

        if d < W:                        # top  →
            return x0 + d, y0
        d -= W
        if d < H:                        # right ↓
            return x1, y0 + d
        d -= H
        if d < W:                        # bottom ←
            return x1 - d, y1
        d -= W
        return x0, y1 - d               # left  ↑

    def _tick(self):
        W = self.cv.winfo_width()  or 300
        H = self.cv.winfo_height() or 180
        self.cv.delete("all")

        # Vẽ “map” nền tối giản: chủ yếu để tạo ngữ cảnh chuyển động,
        # không nhằm mô phỏng layout xưởng chi tiết.
        self.cv.create_rectangle(4, 4, W-4, H-4,
                                  outline="#1a3a5a", width=1, dash=(4,4))

        for agv in self.agvs:
            m = agv["margin"]
            x0, y0, x1, y1 = m, m, W-m, H-m
            if x1 <= x0 or y1 <= y0:
                continue

            # Vẽ đường chạy (rect) của từng AGV: dash để tách khỏi nền.
            self.cv.create_rectangle(x0, y0, x1, y1,
                                      outline=agv["color"],
                                      width=1, dash=(6, 4))

            # Cập nhật “tham số tiến độ” t rồi suy ra (x,y) trên perimeter.
            agv["t"] += agv["speed"]
            px, py = self._rect_pos(agv["t"], x0, y0, x1, y1)

            # vẽ xe (hình chữ nhật nhỏ giống xe)
            r = 5
            self.cv.create_rectangle(px-r, py-r+1, px+r, py+r-1,
                                      fill=agv["color"], outline="")
            # label phía trên
            self.cv.create_text(px, py - r - 4,
                                 text=agv["label"],
                                 fill=agv["color"],
                                 font=("Consolas", 6, "bold"))

        self.after(REFRESH_FAST, self._tick)


# ══════════════════════════════════════════════════════════
# CELL 3 – PCBA STORAGE
# ══════════════════════════════════════════════════════════
class PCBAPanel(Card):
    def __init__(self, parent):
        super().__init__(parent, title="📦 PCBA STORAGE")
        self.data = {"60": (0,0,320), "70": (0,0,280), "FG": (469,911,449)}
        # Rolling history cho stock từng loại để nhìn xu hướng (tăng/giảm) thay vì “pattern ngẫu nhiên”.
        # Stock history:
        # - cửa sổ 60 điểm (tương ứng 60 giây nếu REFRESH_MEDIUM=1s)
        # - init 10 điểm để sparkline không bị “trống” lúc mới mở app
        self._stock_hist = {k: RollingBuffer(60, init=[v[2]] * 10) for k, v in self.data.items()}
        self._build()
        self._tick()

    def _build(self):
        f = tk.Frame(self, bg=CARD_BG)
        f.pack(fill="both", expand=True, padx=8, pady=4)
        self._cells = {}
        for col, (key, (used, total, stock)) in enumerate(self.data.items()):
            cf = tk.Frame(f, bg=BORDER, padx=1, pady=1)
            cf.grid(row=0, column=col, padx=3, pady=2, sticky="nsew")
            f.columnconfigure(col, weight=1)
            inner = tk.Frame(cf, bg=CARD_BG)
            inner.pack(fill="both", expand=True, padx=4, pady=4)

            tk.Label(inner, text=key, bg=CARD_BG, fg=WHITE,
                     font=("Consolas", 12, "bold")).pack()
            lstock = tk.Label(inner, text=f"{stock}", bg=CARD_BG, fg=GREEN,
                              font=("Consolas", 10, "bold"))
            lstock.pack()
            tk.Label(inner, text="stock", bg=CARD_BG, fg=DIM,
                     font=("Consolas", 7)).pack()

            cv = tk.Canvas(inner, bg=CARD_BG, height=40,
                           highlightthickness=0)
            cv.pack(fill="both", expand=True, pady=4)
            self._cells[key] = (lstock, cv)

    def _tick(self):
        for key, (lstock, cv) in self._cells.items():
            used, total, stock = self.data[key]
            # Mô phỏng biến động kho: bước nhảy nhỏ để trông giống tiêu thụ/nhập kho từng chút.
            stock = max(0, stock + random.randint(-2, 2))
            self.data[key] = (used, total, stock)
            lstock.config(text=str(stock))
            # Trend “stock theo thời gian” (rolling window) để dễ phát hiện tụt kho bất thường.
            self._stock_hist[key].append(stock)
            cv.delete("all")
            W = cv.winfo_width() or 120
            H = cv.winfo_height() or 40
            pad = 6
            x0, y0, x1, y1 = _draw_axes_and_grid(
                cv, W=W, H=H, pad=pad, xlabel="t", ylabel="Stock",
                grid_x=4, grid_y=2
            )
            hist = self._stock_hist[key].values()
            if len(hist) >= 2 and x1 > x0 and y1 > y0:
                # Auto-scale theo rolling window để thấy biến động rõ,
                # đồng thời nới biên nếu dữ liệu “phẳng” để đường không dính trục.
                vmin = min(hist)
                vmax = max(hist)
                # Nới biên chút để đường không “dính” sát trục khi dữ liệu phẳng.
                if vmax - vmin < 5:
                    vmax = vmin + 5
                rng = max(1.0, (vmax - vmin))
                pts = []
                for i, v in enumerate(hist):
                    x = x0 + int(i / max(1, (len(hist) - 1)) * (x1 - x0))
                    y = y1 - int((v - vmin) / rng * (y1 - y0))
                    pts += [x, y]
                # Ngưỡng màu đơn giản: nếu stock đang giảm mạnh, đổi màu cảnh báo.
                color = GREEN if hist[-1] >= hist[0] else YELLOW
                if len(pts) >= 4:
                    cv.create_line(*pts, fill=color, width=1, smooth=True)
                cv.create_text(x1, y0, text=f"{hist[-1]}", anchor="ne",
                               fill=WHITE, font=("Consolas", 7))
        self.after(REFRESH_MEDIUM, self._tick)


# ══════════════════════════════════════════════════════════
# CELL 4 – SMT DASHBOARD (Equipment)
# ══════════════════════════════════════════════════════════
class SMTEquipPanel(Card):
    def __init__(self, parent):
        super().__init__(parent, title="🔧 SMT EQUIPMENT")
        self._build()
        self._tick()

    def _build(self):
        f = tk.Frame(self, bg=CARD_BG)
        f.pack(fill="both", expand=True, padx=8, pady=4)

        # Line status grid
        self.status_frame = tk.Frame(f, bg=CARD_BG)
        self.status_frame.pack(fill="x")
        self._dots = []
        for i in range(14):
            r, c = divmod(i, 7)
            dot = tk.Label(self.status_frame, text=f"L{i+1:02d}",
                           bg=GREEN, fg="#000", font=("Consolas", 7, "bold"),
                           width=4, relief="flat")
            dot.grid(row=r, column=c, padx=1, pady=1)
            self._dots.append(dot)

        # Output by hour - mini bar chart
        tk.Label(f, text="Output/Hour", bg=CARD_BG, fg=DIM,
                 font=("Consolas", 8)).pack(anchor="w", pady=(6,0))
        self.bar_cv = tk.Canvas(f, bg=CARD_BG, height=50,
                                highlightthickness=0)
        self.bar_cv.pack(fill="both", expand=True)
        # History theo thời gian: giữ N giờ gần nhất để biểu đồ có “xu hướng”,
        # tránh cảm giác nhảy ngẫu nhiên mỗi lần refresh.
        self._hour_hist = RollingBuffer(10, init=[random.randint(300, 600) for _ in range(10)])

        # Accum output
        self.accum_lbl = tk.Label(f, text="Accum: 0", bg=CARD_BG,
                                  fg=YELLOW, font=("Consolas", 10, "bold"))
        self.accum_lbl.pack(anchor="w")
        self.accum = 12400

    def _tick(self):
        # Dots là trạng thái line (OK/NG). Mục tiêu: nhìn nhanh “line nào đỏ”.
        # Tỷ lệ NG mô phỏng ~15% (random.random() > 0.15). Giảm giá trị này nếu muốn “ổn định” hơn.
        for dot in self._dots:
            ok = random.random() > 0.15
            dot.config(bg=GREEN if ok else RED, fg="#000" if ok else WHITE)

        # bar chart
        self.bar_cv.delete("all")
        W = self.bar_cv.winfo_width() or 200
        H = self.bar_cv.winfo_height() or 50
        pad = 6
        x0, y0, x1, y1 = _draw_axes_and_grid(
            self.bar_cv, W=W, H=H, pad=pad, xlabel="Hour", ylabel="Output",
            grid_x=4, grid_y=3
        )
        # Rolling history: mỗi tick thêm 1 điểm; deque sẽ tự loại điểm cũ nhất khi đầy.
        # Đây là chỗ bạn thay bằng output thực theo giờ nếu có dữ liệu thật.
        self._hour_hist.append(random.randint(300, 600))
        hours = self._hour_hist.values()
        if not hours:
            self.after(REFRESH_MEDIUM, self._tick)
            return
        bw = max(6, (x1 - x0) // len(hours) - 2)
        mx = max(max(hours), 1)
        for i, v in enumerate(hours):
            x = x0 + i * (bw + 2) + 1
            h = int(v / mx * max(1, (y1 - y0) - 2))
            self.bar_cv.create_rectangle(x, y1 - h, x + bw, y1,
                                         fill=ACCENT, outline="")

        self.accum += random.randint(20, 80)
        self.accum_lbl.config(text=f"Accum: {self.accum:,}")
        self.after(REFRESH_MEDIUM, self._tick)


# ══════════════════════════════════════════════════════════
# CELL 5 – SMT LINE KPI
# ══════════════════════════════════════════════════════════
class SMTKPIPanel(Card):
    def __init__(self, parent):
        super().__init__(parent, title="📊 SMT LINE KPI")
        self._build()
        self._tick()

    def _build(self):
        f = tk.Frame(self, bg=CARD_BG)
        f.pack(fill="both", expand=True, padx=8, pady=4)

        # Big KPI row
        kpi_row = tk.Frame(f, bg=CARD_BG)
        kpi_row.pack(fill="x")
        for label, val, color in [("Lines", "5/14", ACCENT),
                                   ("Utilization", "35.7%", YELLOW),
                                   ("Yield", "97%", GREEN)]:
            kf = tk.Frame(kpi_row, bg=BORDER, padx=1, pady=1)
            kf.pack(side="left", expand=True, fill="both", padx=2)
            inner = tk.Frame(kf, bg=CARD_BG)
            inner.pack(fill="both", expand=True, padx=4, pady=4)
            lv = tk.Label(inner, text=val, bg=CARD_BG, fg=color,
                          font=("Consolas", 12, "bold"))
            lv.pack()
            tk.Label(inner, text=label, bg=CARD_BG, fg=DIM,
                     font=("Consolas", 7)).pack()

            if label == "Utilization":
                self._util_lbl = lv
            elif label == "Yield":
                self._yield_lbl = lv

        # Placement error trend
        tk.Label(f, text="Placement Error Trend", bg=CARD_BG, fg=DIM,
                 font=("Consolas", 8)).pack(anchor="w", pady=(6,0))
        self.err_cv = tk.Canvas(f, bg=CARD_BG, height=45,
                                highlightthickness=0)
        self.err_cv.pack(fill="both", expand=True)
        # Lịch sử dài hơn để đường trend “mượt” và nhìn ra xu hướng.
        self._errs = RollingBuffer(40, init=[random.uniform(0.1, 0.5) for _ in range(40)])

    def _tick(self):
        # Ở đây KPI là dữ liệu mô phỏng; nếu nối dữ liệu thật (MES/DB),
        # chỉ cần thay phần sinh random bằng query.
        # Khoảng random 30..45 và 94..99 là “range vận hành giả lập”.
        util = round(random.uniform(30, 45), 1)
        yld  = round(random.uniform(94, 99), 1)
        self._util_lbl.config(text=f"{util}%")
        self._yield_lbl.config(text=f"{yld}%")

        # line chart
        # Placement error mô phỏng: biên nhỏ để đường trend có nhấp nhô nhưng không “loạn”.
        self._errs.append(random.uniform(0.05, 0.6))
        self.err_cv.delete("all")
        W = self.err_cv.winfo_width() or 200
        H = self.err_cv.winfo_height() or 45
        pad = 6
        x0, y0, x1, y1 = _draw_axes_and_grid(
            self.err_cv, W=W, H=H, pad=pad, xlabel="t", ylabel="Err",
            grid_x=5, grid_y=3
        )
        errs = self._errs.values()
        n = len(errs)
        pts = []
        # Scale theo vmax động để tận dụng chiều cao plot,
        # nhưng vẫn giữ ổn định tương đối nhờ rolling window cố định.
        vmax = max(max(errs), 0.001)
        for i, v in enumerate(errs):
            x = x0 + int(i / max(1, (n - 1)) * max(1, (x1 - x0)))
            y = y1 - int(v / vmax * max(1, (y1 - y0)))
            pts += [x, y]
        if len(pts) >= 4:
            self.err_cv.create_line(*pts, fill=RED, width=1, smooth=True)
        self.after(REFRESH_MEDIUM, self._tick)


# ══════════════════════════════════════════════════════════
# CELL 6 – SHIPMENT
# ══════════════════════════════════════════════════════════
class ShipmentPanel(Card):
    def __init__(self, parent):
        super().__init__(parent, title="🚢 SHIPMENT")
        self._build()
        self._tick()

    def _build(self):
        f = tk.Frame(self, bg=CARD_BG)
        f.pack(fill="both", expand=True, padx=8, pady=4)

        row1 = tk.Frame(f, bg=CARD_BG)
        row1.pack(fill="x")
        self._dlbl = self._make_kpi(row1, "Daily", "0", GREEN)
        self._wlbl = self._make_kpi(row1, "Week", "0", YELLOW)
        self._mlbl = self._make_kpi(row1, "Month", "0", ACCENT)

        # Canvas chính: bố cục 2 cột để “cân” hơn (trái: gauge, phải: trend)
        self.arc_cv = tk.Canvas(f, bg=CARD_BG, height=86, highlightthickness=0)
        self.arc_cv.pack(fill="both", expand=True, pady=4)
        self._completion = 56.5
        # Lưu lịch sử completion để hiển thị “quá khứ gần” (sparkline) ngay trong card.
        self._comp_hist = RollingBuffer(60, init=[self._completion for _ in range(60)])
        # Lưu lịch sử output để sparkline có ý nghĩa (không chỉ completion)
        self._daily_hist = RollingBuffer(60, init=[8000] * 10)
        # Giá trị nền để tạo random-walk (biến động mạnh nhưng vẫn “có trend”).
        # Nếu nối dữ liệu thật, có thể bỏ các biến *_val này và append trực tiếp số liệu vào buffer.
        self._daily_val = 8000.0
        self._weekly_val = 48000.0
        self._monthly_val = 180000.0

    def _make_kpi(self, parent, label, val, color):
        kf = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        kf.pack(side="left", expand=True, fill="both", padx=2)
        inner = tk.Frame(kf, bg=CARD_BG)
        inner.pack(fill="both", expand=True, padx=4, pady=4)
        lv = tk.Label(inner, text=val, bg=CARD_BG, fg=color,
                      font=("Consolas", 11, "bold"))
        lv.pack()
        tk.Label(inner, text=label, bg=CARD_BG, fg=DIM,
                 font=("Consolas", 7)).pack()
        return lv

    def _tick(self):
        # Tạo biến động “đậm” cho Trends nhưng vẫn nhẹ CPU:
        # - random-walk + mean reversion nhẹ để không trôi vô hạn
        # - spike hiếm (như sự kiện đơn hàng/đứt chuyền) để nhìn rõ biến động
        def _step(val, target, step, spike, lo, hi, spike_p=0.08):
            # mean reversion kéo về target
            val += (target - val) * 0.05
            # dao động thường
            val += random.uniform(-step, step)
            # spike hiếm
            if random.random() < spike_p:
                val += random.choice([-1, 1]) * random.uniform(spike * 0.6, spike)
            return max(lo, min(hi, val))

        # Ý nghĩa tham số:
        # - target: mức “kỳ vọng” để giá trị dao động quanh
        # - step: biên dao động thường mỗi tick (càng lớn càng rung)
        # - spike: biên “sốc” hiếm (càng lớn càng dễ thấy biến động mạnh)
        # - lo/hi: chặn biên để không ra giá trị vô lý
        # - spike_p: xác suất xuất hiện spike (0.04~0.08 là đủ thấy nhưng không quá dày)
        self._daily_val = _step(self._daily_val, 8200.0, step=650.0, spike=2200.0, lo=2000.0, hi=14000.0)
        self._weekly_val = _step(self._weekly_val, 50000.0, step=5200.0, spike=18000.0, lo=15000.0, hi=90000.0, spike_p=0.05)
        self._monthly_val = _step(self._monthly_val, 185000.0, step=18000.0, spike=55000.0, lo=60000.0, hi=320000.0, spike_p=0.04)

        d = int(self._daily_val)
        w = int(self._weekly_val)
        m = int(self._monthly_val)
        self._dlbl.config(text=f"{d:,}")
        self._wlbl.config(text=f"{w//1000}K")
        self._mlbl.config(text=f"{m//1000}K")

        # Clamp 0..100 để gauge không bị vượt biên khi dữ liệu dao động.
        # Completion biến động mạnh hơn (nhưng không “giật” vô lý) bằng random-walk + spike hiếm.
        comp_target = 68.0
        # 0.06 là “độ kéo về target”: lớn hơn thì ổn định nhanh hơn, nhỏ hơn thì trôi tự do hơn.
        self._completion += (comp_target - self._completion) * 0.06
        # Biên rung thường
        self._completion += random.uniform(-2.2, 2.2)
        # Spike hiếm (sự cố/đột biến chất lượng)
        if random.random() < 0.06:
            self._completion += random.choice([-1, 1]) * random.uniform(4.0, 9.0)
        self._completion = max(0, min(100, self._completion))
        self.arc_cv.delete("all")
        W = self.arc_cv.winfo_width() or 200
        H = self.arc_cv.winfo_height() or 86
        pad = 6
        # rolling history for completion (sparkline nhỏ)
        self._comp_hist.append(self._completion)
        self._daily_hist.append(d)

        # ── layout: 2 cột ─────────────────────────────
        # Trái: gauge + % lớn (tối đa ~45% chiều ngang)
        split = int(W * 0.46)
        left_x0, left_x1 = pad, max(pad + 80, split - pad)
        right_x0, right_x1 = left_x1 + pad, W - pad

        # divider nhẹ để “tách khối” nhưng không nặng
        self.arc_cv.create_line(left_x1 + pad//2, pad, left_x1 + pad//2, H - pad,
                                fill="#132242")

        # ── LEFT: semi gauge (gọn) ────────────────────
        gw = left_x1 - left_x0
        gh = H - pad * 2
        # đặt gauge hơi thấp để chừa chỗ label nhỏ phía trên
        cx = left_x0 + gw // 2
        cy = pad + gh - 6
        r = max(18, min(gw // 2 - 6, gh - 16))

        self.arc_cv.create_text(left_x0 + 2, pad, text="Completion",
                                anchor="nw", fill=DIM, font=("Consolas", 7))
        self.arc_cv.create_arc(cx - r, cy - r, cx + r, cy + r,
                               start=180, extent=180, style="arc",
                               outline=BORDER, width=8)
        ext = int(180 * self._completion / 100)
        self.arc_cv.create_arc(cx - r, cy - r, cx + r, cy + r,
                               start=180, extent=ext, style="arc",
                               outline=GREEN if self._completion >= 70 else (YELLOW if self._completion >= 50 else RED),
                               width=8)
        # % to, canh giữa, tránh “đè” lên sparkline như layout cũ
        col = GREEN if self._completion >= 70 else (YELLOW if self._completion >= 50 else RED)
        self.arc_cv.create_text(cx, cy - r // 2,
                                text=f"{self._completion:.1f}%",
                                fill=col, font=("Consolas", 14, "bold"))

        # ── RIGHT: 2 sparklines (completion + daily) ──
        # Mục tiêu: nhìn “xu hướng” rõ hơn, không bị mỏng/khó đọc.
        self.arc_cv.create_text(right_x0 + 2, pad, text="Trends",
                                anchor="nw", fill=DIM, font=("Consolas", 7))

        # completion sparkline
        c_hist = self._comp_hist.values()
        d_hist = self._daily_hist.values()
        box_h = max(18, (H - pad*2 - 14) // 2)
        c_y0 = pad + 12
        c_y1 = c_y0 + box_h
        d_y0 = c_y1 + 8
        d_y1 = min(H - pad, d_y0 + box_h)

        def _spark(x0, y0, x1, y1, values, vmin, vmax, color, label):
            self.arc_cv.create_rectangle(x0, y0, x1, y1, outline=BORDER, width=1)
            self.arc_cv.create_text(x0 + 4, y0 + 2, text=label, anchor="nw",
                                    fill=DIM, font=("Consolas", 7))
            mid = (y0 + y1) // 2
            self.arc_cv.create_line(x0, mid, x1, mid, fill="#132242")
            if len(values) < 2 or x1 <= x0 or y1 <= y0:
                return
            rng = max(1e-6, (vmax - vmin))
            pts = []
            for i, v in enumerate(values):
                x = x0 + int(i / max(1, (len(values) - 1)) * (x1 - x0))
                y = y1 - int((v - vmin) / rng * (y1 - y0))
                pts += [x, y]
            if len(pts) >= 4:
                # smooth=False để nhẹ CPU hơn
                self.arc_cv.create_line(*pts, fill=color, width=1, smooth=False)

        rx0 = right_x0
        rx1 = right_x1
        _spark(rx0, c_y0, rx1, c_y1, c_hist, 0.0, 100.0, col, "Comp%")

        # daily sparkline: auto-scale nhẹ theo rolling window để thấy biến động
        if d_hist:
            dvmin = min(d_hist)
            dvmax = max(d_hist)
            if dvmax - dvmin < 200:
                dvmax = dvmin + 200
        else:
            dvmin, dvmax = 0, 1
        _spark(rx0, d_y0, rx1, d_y1, d_hist, float(dvmin), float(dvmax), ACCENT, "Daily")
        self.after(REFRESH_SLOW, self._tick)


# ══════════════════════════════════════════════════════════
# CELL 7 – PVN OUTPUT
# ══════════════════════════════════════════════════════════
class PVNPanel(Card):
    def __init__(self, parent):
        super().__init__(parent, title="🏭 PVN OUTPUT")
        self._build()
        self._tick()

    def _build(self):
        f = tk.Frame(self, bg=CARD_BG)
        f.pack(fill="both", expand=True, padx=8, pady=4)

        top = tk.Frame(f, bg=CARD_BG)
        top.pack(fill="x")
        self._total = tk.Label(top, text="65%", bg=CARD_BG, fg=YELLOW,
                               font=("Consolas", 18, "bold"))
        self._total.pack(side="left", padx=8)
        info = tk.Frame(top, bg=CARD_BG)
        info.pack(side="left")
        tk.Label(info, text="Total Output", bg=CARD_BG, fg=DIM,
                 font=("Consolas", 8)).pack(anchor="w")
        self._output_lbl = tk.Label(info, text="Units: 0", bg=CARD_BG,
                                    fg=WHITE, font=("Consolas", 9))
        self._output_lbl.pack(anchor="w")

        # Horizontal bar chart - top lines
        tk.Label(f, text="Top Lines", bg=CARD_BG, fg=DIM,
                 font=("Consolas", 8)).pack(anchor="w", pady=(4,0))
        # Tách riêng vùng bar chart và vùng sparkline history để tránh vẽ tràn/chồng khi card bị co hẹp.
        chart_row = tk.Frame(f, bg=CARD_BG)
        chart_row.pack(fill="both", expand=True)
        self.bar_cv = tk.Canvas(chart_row, bg=CARD_BG, height=70, highlightthickness=0)
        self.bar_cv.pack(side="left", fill="both", expand=True)
        # Sparkline canvas cố định bề rộng để layout ổn định
        self.spark_cv = tk.Canvas(chart_row, bg=CARD_BG, width=70, highlightthickness=0)
        self.spark_cv.pack(side="right", fill="y")
        self._units = 42000
        # Mỗi line có buffer riêng để có thể vẽ sparkline theo thời gian cho từng line.
        self._line_hist = {
            "L01": RollingBuffer(30, init=[random.randint(70, 100) for _ in range(30)]),
            "L03": RollingBuffer(30, init=[random.randint(60, 95) for _ in range(30)]),
            "L05": RollingBuffer(30, init=[random.randint(50, 90) for _ in range(30)]),
            "L07": RollingBuffer(30, init=[random.randint(40, 85) for _ in range(30)]),
            "L09": RollingBuffer(30, init=[random.randint(30, 80) for _ in range(30)]),
        }

    def _tick(self):
        pct = random.randint(55, 80)
        self._total.config(text=f"{pct}%")
        self._units += random.randint(50, 150)
        self._output_lbl.config(text=f"Units: {self._units:,}")

        self.bar_cv.delete("all")
        self.spark_cv.delete("all")
        W = self.bar_cv.winfo_width() or 200
        H = self.bar_cv.winfo_height() or 70
        pad = 6
        x0, y0, x1, y1 = _draw_axes_and_grid(
            self.bar_cv, W=W, H=H, pad=pad, xlabel="Line", ylabel="Score",
            grid_x=4, grid_y=3
        )

        # Rolling history cho từng line: mỗi tick thêm 1 điểm, hiển thị “latest” + sparkline.
        for name, buf in self._line_hist.items():
            lo, hi = {
                "L01": (70, 100),
                "L03": (60, 95),
                "L05": (50, 90),
                "L07": (40, 85),
                "L09": (30, 80),
            }[name]
            buf.append(random.randint(lo, hi))

        latest = [(name, self._line_hist[name].values()[-1]) for name in self._line_hist.keys()]
        # Sort để “Top Lines” đúng nghĩa (cao lên trước), còn sparkline vẫn giữ theo line tương ứng.
        latest.sort(key=lambda t: t[1], reverse=True)

        # Bar chart chỉ lo “latest ranking” (Top Lines) để dễ đọc; sparkline chuyển sang canvas riêng.
        bh = max(10, (y1 - y0) // max(1, len(latest)) - 2)
        for i, (name, v) in enumerate(latest):
            y = y0 + i * (bh + 2) + 1
            # Trừ chỗ cho label/value để không bị tràn sang phải
            bar_max_w = max(10, (x1 - x0) - 70)
            w = int(v / 100 * bar_max_w)
            color = GREEN if v > 80 else (YELLOW if v > 60 else RED)
            # bar
            self.bar_cv.create_rectangle(x0 + 32, y, x0 + 32 + w, y + bh,
                                         fill=color, outline="")
            # label line
            self.bar_cv.create_text(x0 + 28, y + bh // 2, text=name,
                                    fill=DIM, font=("Consolas", 7),
                                    anchor="e")
            # value
            self.bar_cv.create_text(x0 + 34 + w + 2, y + bh // 2, text=f"{v}",
                                    fill=WHITE, font=("Consolas", 7),
                                    anchor="w")

        # ── Sparkline canvas (history) ─────────────────────────────
        sW = self.spark_cv.winfo_width() or 70
        sH = self.spark_cv.winfo_height() or H
        spad = 6
        # tiêu đề dọc nhỏ gọn
        self.spark_cv.create_text(sW // 2, spad, text="Hist", fill=DIM,
                                  font=("Consolas", 7), anchor="n")
        # vẽ sparkline theo thứ tự Top Lines (để nhìn line mạnh nhất trước)
        # Mỗi line 1 ô nhỏ, không smooth để nhẹ.
        inner_y0 = spad + 12
        row_h = max(10, (sH - inner_y0 - spad) // max(1, len(latest)) - 2)
        for i, (name, _) in enumerate(latest):
            y0s = inner_y0 + i * (row_h + 2)
            y1s = y0s + row_h
            if y1s > sH - spad:
                break
            x0s, x1s = spad, sW - spad
            self.spark_cv.create_rectangle(x0s, y0s, x1s, y1s, outline=BORDER, width=1)
            # mid line
            self.spark_cv.create_line(x0s, (y0s + y1s)//2, x1s, (y0s + y1s)//2, fill="#132242")
            hist = self._line_hist[name].values()
            if len(hist) >= 2:
                pts = []
                for j, hv in enumerate(hist):
                    px = x0s + int(j / max(1, (len(hist) - 1)) * (x1s - x0s))
                    py = y1s - int(hv / 100 * (y1s - y0s))
                    pts += [px, py]
                if len(pts) >= 4:
                    self.spark_cv.create_line(*pts, fill=ACCENT, width=1, smooth=False)
        self.after(REFRESH_MEDIUM, self._tick)


# ══════════════════════════════════════════════════════════
# CELL 8 – YIELD RATE TABLE
# ══════════════════════════════════════════════════════════
class YieldPanel(Card):
    def __init__(self, parent):
        super().__init__(parent, title="✅ YIELD RATE")
        self._build()
        self._tick()

    def _build(self):
        f = tk.Frame(self, bg=CARD_BG)
        f.pack(fill="both", expand=True, padx=8, pady=4)
        headers = ["Line", "Target", "Actual", "Status"]
        widths   = [5, 7, 7, 6]
        hrow = tk.Frame(f, bg=BORDER)
        hrow.pack(fill="x", pady=(0,2))
        for h, w in zip(headers, widths):
            tk.Label(hrow, text=h, bg=BORDER, fg=DIM,
                     font=("Consolas", 8, "bold"), width=w).pack(side="left")

        self._rows = []
        self._row_frames = []
        for i in range(7):
            rf = tk.Frame(f, bg=CARD_BG)
            rf.pack(fill="x", pady=1)
            cells = []
            for w in widths:
                lbl = tk.Label(rf, text="", bg=CARD_BG, fg=WHITE,
                               font=("Consolas", 8), width=w)
                lbl.pack(side="left")
                cells.append(lbl)
            self._rows.append(cells)
            self._row_frames.append(rf)

    def _tick(self):
        for i, (cells, rf) in enumerate(zip(self._rows, self._row_frames)):
            line   = f"L{i+1:02d}"
            target = 97.0
            # Yield mô phỏng: actual dao động quanh target để có cả OK/NG.
            actual = round(random.uniform(93, 100), 1)
            ok     = actual >= target
            status = "OK" if ok else "NG"
            color  = GREEN if ok else RED
            cells[0].config(text=line,   fg=DIM)
            cells[1].config(text=f"{target}%", fg=DIM)
            cells[2].config(text=f"{actual}%", fg=color)
            cells[3].config(text=status, fg=color)
            rf.config(bg="#0a1a0a" if ok else "#1a0a0a")
            for c in cells: c.config(bg=rf["bg"])
        self.after(REFRESH_MEDIUM, self._tick)


# ══════════════════════════════════════════════════════════
# CELL 9 – SYSTEM STATUS / CLOCK
# ══════════════════════════════════════════════════════════
class StatusPanel(Card):
    def __init__(self, parent):
        super().__init__(parent, title="🖥  SYSTEM STATUS")
        self._build()
        self._tick()

    def _build(self):
        f = tk.Frame(self, bg=CARD_BG)
        f.pack(fill="both", expand=True, padx=8, pady=4)

        self._clock = tk.Label(f, text="00:00:00", bg=CARD_BG, fg=ACCENT,
                               font=("Consolas", 16, "bold"))
        self._clock.pack(pady=(0,4))

        self._date = tk.Label(f, text="", bg=CARD_BG, fg=DIM,
                              font=("Consolas", 8))
        self._date.pack()

        # System metrics
        metrics = [("OEE", "78.4%", GREEN),
                   ("MTTR", "12 min", YELLOW),
                   ("Downtime", "2.1%", RED),
                   ("DB", "Online", GREEN),
                   ("MES", "Online", GREEN),
                   ("Network", "OK", GREEN)]
        self._mlabels = {}
        for name, val, color in metrics:
            r = tk.Frame(f, bg=CARD_BG)
            r.pack(fill="x", pady=1)
            tk.Label(r, text=f"  {name}", bg=CARD_BG, fg=DIM,
                     font=("Consolas", 8), width=10, anchor="w").pack(side="left")
            lv = tk.Label(r, text=val, bg=CARD_BG, fg=color,
                          font=("Consolas", 8, "bold"))
            lv.pack(side="left")
            self._mlabels[name] = (lv, color)

        # Mini trend (rolling history) để panel “System Status” không chỉ là số tĩnh:
        # - OEE (0..100)
        # - Downtime (0..5%) hiển thị trên chart riêng ngay dưới
        tk.Label(f, text="Trends", bg=CARD_BG, fg=DIM,
                 font=("Consolas", 8)).pack(anchor="w", pady=(6,0))
        self.trend_cv = tk.Canvas(f, bg=CARD_BG, height=60, highlightthickness=0)
        self.trend_cv.pack(fill="both", expand=True)
        self._oee_hist = RollingBuffer(60, init=[78.0] * 20)
        self._dt_hist = RollingBuffer(60, init=[2.0] * 20)
        # init ngắn để chart có “đường” ngay khi mở, tránh cảm giác trống.

    def _tick(self):
        now = time.localtime()
        self._clock.config(text=time.strftime("%H:%M:%S", now))
        self._date.config(text=time.strftime("%Y-%m-%d  |  Factory: BG6", now))

        # System metrics mô phỏng:
        # - OEE: 75..85% (vận hành tương đối ổn)
        # - Downtime: 1..4% (có thể nhảy lên vùng cảnh báo >3%)
        oee = round(random.uniform(75, 85), 1)
        self._mlabels["OEE"][0].config(text=f"{oee}%")
        dt  = round(random.uniform(1, 4), 1)
        self._mlabels["Downtime"][0].config(text=f"{dt}%",
            fg=RED if dt>3 else YELLOW)

        # update rolling buffers
        self._oee_hist.append(oee)
        self._dt_hist.append(dt)

        # draw trend canvas (2 vùng: OEE phía trên, Downtime phía dưới)
        self.trend_cv.delete("all")
        W = self.trend_cv.winfo_width() or 220
        H = self.trend_cv.winfo_height() or 60
        pad = 6

        # OEE plot (top half)
        o_x0, o_y0, o_x1, o_y1 = pad + 26, pad, W - pad, H // 2 - 4
        self.trend_cv.create_text(pad + 10, (o_y0 + o_y1)//2, text="OEE", angle=90,
                                  fill=DIM, font=("Consolas", 7))
        self.trend_cv.create_rectangle(o_x0, o_y0, o_x1, o_y1, outline=BORDER, width=1)
        self.trend_cv.create_line(o_x0, (o_y0+o_y1)//2, o_x1, (o_y0+o_y1)//2, fill="#132242")
        o = self._oee_hist.values()
        if len(o) >= 2 and o_x1 > o_x0 and o_y1 > o_y0:
            pts = []
            for i, v in enumerate(o):
                x = o_x0 + int(i / max(1, (len(o) - 1)) * (o_x1 - o_x0))
                y = o_y1 - int(v / 100.0 * (o_y1 - o_y0))
                pts += [x, y]
            if len(pts) >= 4:
                self.trend_cv.create_line(*pts, fill=GREEN, width=1, smooth=True)

        # Downtime plot (bottom half)
        d_x0, d_y0, d_x1, d_y1 = pad + 26, H // 2 + 4, W - pad, H - pad - 12
        self.trend_cv.create_text(pad + 10, (d_y0 + d_y1)//2, text="DT%", angle=90,
                                  fill=DIM, font=("Consolas", 7))
        self.trend_cv.create_rectangle(d_x0, d_y0, d_x1, d_y1, outline=BORDER, width=1)
        self.trend_cv.create_line(d_x0, (d_y0+d_y1)//2, d_x1, (d_y0+d_y1)//2, fill="#132242")
        dvals = self._dt_hist.values()
        if len(dvals) >= 2 and d_x1 > d_x0 and d_y1 > d_y0:
            # Scale downtime theo 0..5% để chart ổn định (không bị “phóng đại” do auto-scale).
            scale_max = 5.0
            pts = []
            for i, v in enumerate(dvals):
                x = d_x0 + int(i / max(1, (len(dvals) - 1)) * (d_x1 - d_x0))
                y = d_y1 - int(min(v, scale_max) / scale_max * (d_y1 - d_y0))
                pts += [x, y]
            if len(pts) >= 4:
                col = RED if dt > 3 else YELLOW
                self.trend_cv.create_line(*pts, fill=col, width=1, smooth=True)

        # xlabel chung
        self.trend_cv.create_text((pad + 26 + (W - pad)) // 2, H - pad,
                                  text="t", fill=DIM, font=("Consolas", 7), anchor="s")
        self.after(REFRESH_MEDIUM, self._tick)


# ══════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════
class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Factory Dashboard")
        self.configure(bg=BG)
        # Fullscreen để chạy trên màn hình TV/monitor ở xưởng; mặc định tắt để dev/debug dễ.
        self.attributes("-fullscreen", False)
        self.geometry("1280x720")
        self.minsize(900, 600)

        # Header bar
        hdr = tk.Frame(self, bg="#06091a", height=28)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  ◉  FACTORY MONITORING SYSTEM  —  BG6 PVN",
                 bg="#06091a", fg=ACCENT,
                 font=("Consolas", 10, "bold")).pack(side="left", pady=4)
        self._hdr_status = tk.Label(hdr, text="● LIVE", bg="#06091a",
                                    fg=GREEN, font=("Consolas", 9))
        self._hdr_status.pack(side="right", padx=12)
        tk.Button(hdr, text="[F]", bg="#06091a", fg=DIM,
                  relief="flat", font=("Consolas", 9),
                  command=self._toggle_fullscreen).pack(side="right")

        # 3x3 Grid:
        # - weight=1 để các ô co giãn theo cửa sổ
        # - uniform để các hàng/cột “đều nhau”, tránh card bị méo tỉ lệ
        grid = tk.Frame(self, bg=BG)
        grid.pack(fill="both", expand=True, padx=4, pady=4)
        for r in range(3):
            grid.rowconfigure(r, weight=1, minsize=1, uniform="row")
        for c in range(3):
            grid.columnconfigure(c, weight=1, minsize=1, uniform="col")

        panels = [
            EnergyPanel,    AGVPanel,       PCBAPanel,
            SMTEquipPanel,  SMTKPIPanel,    ShipmentPanel,
            PVNPanel,       YieldPanel,     StatusPanel,
        ]
        for i, PanelClass in enumerate(panels):
            r, c = divmod(i, 3)
            p = PanelClass(grid)
            p.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")

        self._blink = True
        self._blink_tick()
        # Phím tắt:
        # - F11: fullscreen (toggle cho tiện khi demo/vận hành)
        # - ESC: thoát fullscreen nhanh
        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

    def _blink_tick(self):
        # Blink “LIVE” để tạo cảm giác hệ thống đang cập nhật realtime,
        # đồng thời là indicator đơn giản nếu UI bị treo (blink ngừng).
        self._blink = not self._blink
        self._hdr_status.config(fg=GREEN if self._blink else DIM)
        self.after(800, self._blink_tick)

    def _toggle_fullscreen(self):
        # Toggle bằng nút [F] hoặc F11.
        fs = self.attributes("-fullscreen")
        self.attributes("-fullscreen", not fs)


if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()