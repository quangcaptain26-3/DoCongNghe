"""
AGV Log Analyzer
Kéo thả hoặc chọn file .txt log AGV → tự động lọc và hiển thị lên 5 grid
Chỉ dùng thư viện built-in: tkinter, re, collections, datetime
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
from collections import defaultdict
from datetime import datetime


# ─────────────────────────── PARSER ────────────────────────────

LOG_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+(.*)"
)

def parse_log(text):
    events = {
        "tasks":      [],   # MES task assignments
        "agv_status": [],   # online / offline / disconnect
        "elevator":   [],   # elevator calls & door events
        "targets":    [],   # target point changes
        "errors":     [],   # failed HTTP reports
    }

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = LOG_RE.match(line)
        if not m:
            continue
        ts_raw, msg = m.group(1).strip(), m.group(2).strip()
        try:
            ts = datetime.strptime(ts_raw, "%Y-%m-%d  %H:%M:%S.%f")
        except ValueError:
            try:
                ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                ts = None
        ts_str = ts.strftime("%H:%M:%S.%f")[:-3] if ts else ts_raw

        # ── Tasks ──
        if "分配给" in msg and "号车" in msg:
            m2 = re.search(r"任务(\S+)分配给(\d+)号车", msg)
            if m2:
                events["tasks"].append({
                    "time": ts_str,
                    "task_id": m2.group(1)[:16] + "…",
                    "car_id": m2.group(2),
                    "event": "分配任务",
                })
        elif "接受MES任务产生" in msg:
            pts = re.findall(r'"point":\s*"(\d+)"', msg)
            acts = re.findall(r'"action":\s*"(\w+)"', msg)
            summary = "  →  ".join(
                f"{p}({a})" for p, a in zip(pts, acts)
            ) or msg[:40]
            events["tasks"].append({
                "time": ts_str,
                "task_id": "MES",
                "car_id": "—",
                "event": summary,
            })

        # ── AGV Status ──
        elif "AGV已经连接" in msg:
            ip_m = re.search(r"(\d+\.\d+\.\d+\.\d+)AGV已经连接(\d+)", msg)
            if ip_m:
                events["agv_status"].append({
                    "time": ts_str,
                    "car_ip": ip_m.group(1),
                    "status": "🟢 连接",
                    "detail": f"状态码 {ip_m.group(2)}",
                })
        elif "AGV已经掉线" in msg:
            car_m = re.search(r"(\d+)号AGV已经掉线", msg)
            cid = car_m.group(1) if car_m else "?"
            events["agv_status"].append({
                "time": ts_str,
                "car_ip": f"车#{cid}",
                "status": "🔴 掉线",
                "detail": "连接断开",
            })

        # ── Elevator ──
        elif "号车呼叫电梯" in msg:
            em = re.search(r"(\d+)号车呼叫电梯(\d+)到(\d+)楼", msg)
            if em:
                events["elevator"].append({
                    "time": ts_str,
                    "car_id": em.group(1),
                    "elevator": em.group(2),
                    "action": f"呼叫→{em.group(3)}楼",
                })
        elif re.match(r"^\d+开门$", msg):
            eid = re.match(r"^(\d+)开门$", msg).group(1)
            events["elevator"].append({
                "time": ts_str,
                "car_id": "—",
                "elevator": eid,
                "action": "🚪 开门",
            })
        elif re.match(r"^\d+关门$", msg):
            eid = re.match(r"^(\d+)关门$", msg).group(1)
            events["elevator"].append({
                "time": ts_str,
                "car_id": "—",
                "elevator": eid,
                "action": "🚪 关门",
            })
        elif "号agv，到" in msg and "释放电梯" in msg:
            rm = re.search(r"(\d+)号agv，到(\d+)楼释放电梯", msg)
            if rm:
                events["elevator"].append({
                    "time": ts_str,
                    "car_id": rm.group(1),
                    "elevator": "—",
                    "action": f"✅ 释放@{rm.group(2)}楼",
                })

        # ── Target Points ──
        elif "目标点：" in msg or "目标点2176" in msg:
            car_m = re.search(r"(\d+)目标点[：:]?\s*(\d*)", msg)
            if car_m:
                pt = car_m.group(2) or "2176(完成)"
                events["targets"].append({
                    "time": ts_str,
                    "car_id": car_m.group(1),
                    "target": pt,
                    "note": "完成归位" if "2176" in msg else "",
                })

        # ── Errors ──
        elif "失败" in msg or "掉线" in msg and "AGV" not in msg:
            # HTTP report failures
            if "连接http" in msg and "失败" in msg:
                task_m = re.search(r'"taskId":"([^"]+)"', msg)
                car_m2 = re.search(r'"carId":(\d+)', msg)
                kind = "taskEnd" if "taskEnd" in msg else "taskStart"
                retry_m = re.search(r"上报(\d+)-", msg)
                events["errors"].append({
                    "time": ts_str,
                    "car_id": car_m2.group(1) if car_m2 else "?",
                    "type": kind,
                    "retry": retry_m.group(1) if retry_m else "?",
                    "detail": "无法连接MES服务器",
                })

    return events


# ─────────────────────────── GUI ────────────────────────────

DARK_BG   = "#0f1117"
PANEL_BG  = "#1a1d27"
HEADER_BG = "#12151f"
ACCENT    = "#4f8ef7"
ACCENT2   = "#f7934f"
TEXT_PRI  = "#e8eaf2"
TEXT_SEC  = "#8890a8"
GREEN     = "#3dd68c"
RED       = "#f75f5f"
BORDER    = "#2a2d3e"

GRID_CONFIGS = [
    {
        "key":  "tasks",
        "title":"📋 任务列表",
        "cols": [("time","时间",110), ("car_id","车号",60), ("task_id","任务ID",130), ("event","内容",300)],
    },
    {
        "key":  "agv_status",
        "title":"🤖 AGV 状态",
        "cols": [("time","时间",110), ("car_ip","IP/车号",130), ("status","状态",90), ("detail","详情",120)],
    },
    {
        "key":  "elevator",
        "title":"🛗 电梯事件",
        "cols": [("time","时间",110), ("car_id","车号",60), ("elevator","电梯",60), ("action","动作",160)],
    },
    {
        "key":  "targets",
        "title":"🎯 目标点",
        "cols": [("time","时间",110), ("car_id","车号",60), ("target","目标点",80), ("note","备注",120)],
    },
    {
        "key":  "errors",
        "title":"⚠️ 错误 / 重试",
        "cols": [("time","时间",110), ("car_id","车号",60), ("type","类型",80), ("retry","第N次",55), ("detail","说明",220)],
    },
]


class AGVApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AGV Log Analyzer")
        self.geometry("1280x820")
        self.configure(bg=DARK_BG)
        self.minsize(900, 600)

        self._setup_style()
        self._build_ui()

    # ── Style ──────────────────────────────────────────────────
    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame",       background=DARK_BG)
        style.configure("Panel.TFrame", background=PANEL_BG)

        style.configure("Treeview",
            background=PANEL_BG, foreground=TEXT_PRI,
            fieldbackground=PANEL_BG, rowheight=24,
            borderwidth=0, font=("Consolas", 9),
        )
        style.configure("Treeview.Heading",
            background=HEADER_BG, foreground=ACCENT,
            font=("Segoe UI", 9, "bold"), relief="flat",
        )
        style.map("Treeview",
            background=[("selected", "#2a3a5c")],
            foreground=[("selected", TEXT_PRI)],
        )
        style.configure("TScrollbar",
            background=PANEL_BG, troughcolor=DARK_BG,
            arrowcolor=TEXT_SEC, borderwidth=0,
        )

    # ── UI ─────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=HEADER_BG, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="AGV  LOG  ANALYZER",
                 bg=HEADER_BG, fg=ACCENT,
                 font=("Courier New", 15, "bold")).pack(side="left", padx=20, pady=12)

        self.status_var = tk.StringVar(value="未加载文件")
        tk.Label(hdr, textvariable=self.status_var,
                 bg=HEADER_BG, fg=TEXT_SEC,
                 font=("Segoe UI", 9)).pack(side="left", padx=8)

        btn = tk.Button(hdr, text="  📂  打开 .txt 文件  ",
                        command=self._open_file,
                        bg=ACCENT, fg="white",
                        activebackground="#3a6fd8", activeforeground="white",
                        font=("Segoe UI", 9, "bold"),
                        relief="flat", cursor="hand2", padx=10, pady=6)
        btn.pack(side="right", padx=16, pady=10)

        # Summary bar
        self.sum_frame = tk.Frame(self, bg=DARK_BG)
        self.sum_frame.pack(fill="x", padx=12, pady=(8,0))
        self.badges = {}
        for cfg in GRID_CONFIGS:
            f = tk.Frame(self.sum_frame, bg=PANEL_BG, padx=14, pady=6)
            f.pack(side="left", padx=5)
            tk.Label(f, text=cfg["title"], bg=PANEL_BG,
                     fg=TEXT_SEC, font=("Segoe UI", 8)).pack()
            lbl = tk.Label(f, text="—", bg=PANEL_BG,
                           fg=ACCENT, font=("Courier New", 14, "bold"))
            lbl.pack()
            self.badges[cfg["key"]] = lbl

        # Grid area (2 rows: top 3, bottom 2)
        grid_area = tk.Frame(self, bg=DARK_BG)
        grid_area.pack(fill="both", expand=True, padx=12, pady=8)

        top_row = tk.Frame(grid_area, bg=DARK_BG)
        top_row.pack(fill="both", expand=True)
        bot_row = tk.Frame(grid_area, bg=DARK_BG)
        bot_row.pack(fill="both", expand=True, pady=(6,0))

        self.trees = {}
        for i, cfg in enumerate(GRID_CONFIGS):
            parent = top_row if i < 3 else bot_row
            self._make_grid(parent, cfg)

    def _make_grid(self, parent, cfg):
        frame = tk.Frame(parent, bg=PANEL_BG,
                         highlightbackground=BORDER,
                         highlightthickness=1)
        frame.pack(side="left", fill="both", expand=True,
                   padx=(0,6) if parent.winfo_children().__len__() > 0 else 0)

        # Title bar
        title_bar = tk.Frame(frame, bg=HEADER_BG, height=30)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text=cfg["title"],
                 bg=HEADER_BG, fg=TEXT_PRI,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10, pady=5)

        # Treeview
        cols = [c[0] for c in cfg["cols"]]
        tv = ttk.Treeview(frame, columns=cols, show="headings",
                          selectmode="browse")
        for key, label, width in cfg["cols"]:
            tv.heading(key, text=label)
            tv.column(key, width=width, minwidth=40, anchor="w")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)

        # Alternating row colors
        tv.tag_configure("odd",  background="#1e2130")
        tv.tag_configure("even", background=PANEL_BG)
        tv.tag_configure("err",  foreground=RED)
        tv.tag_configure("ok",   foreground=GREEN)

        self.trees[cfg["key"]] = (tv, cfg["cols"])

    # ── File open ──────────────────────────────────────────────
    def _open_file(self):
        path = filedialog.askopenfilename(
            title="选择 AGV 日志文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
            return

        events = parse_log(text)
        self._populate(events)

        lines = text.count("\n")
        fname = path.split("/")[-1].split("\\")[-1]
        self.status_var.set(f"✅  {fname}   共 {lines} 行")

    def _populate(self, events):
        for cfg in GRID_CONFIGS:
        
            key = cfg["key"]
            tv, cols = self.trees[key]
            tv.delete(*tv.get_children())

            rows = events.get(key, [])
            self.badges[key].config(text=str(len(rows)))

            for idx, row in enumerate(rows):
                vals = [row.get(c[0], "") for c in cols]
                tag = "odd" if idx % 2 else "even"
                # color coding
                if key == "errors":
                    tag = "err"
                elif key == "agv_status":
                    status = row.get("status","")
                    if "连接" in status:
                        tag = "ok"
                    elif "掉线" in status:
                        tag = "err"
                tv.insert("", "end", values=vals, tags=(tag,))


if __name__ == "__main__":
    app = AGVApp()
    app.mainloop()
