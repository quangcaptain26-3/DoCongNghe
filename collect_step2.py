import os
import shutil
import threading
import queue
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

class Step2Collector:
    def __init__(self, root):
        self.root = root
        self.root.title("STEP 2 Image Collector")
        self.root.geometry("780x520")
        self.root.minsize(700, 480)

        self.stop_event = threading.Event()
        self.ui_queue = queue.Queue()
        self.running = False

        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.case_var = tk.BooleanVar(value=False)

        self.total_var = tk.StringVar(value="0")
        self.matched_var = tk.StringVar(value="0")
        self.copied_var = tk.StringVar(value="0")
        self.error_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="Sẵn sàng")

        self._build_ui()
        self.root.after(100, self._process_ui_queue)

    def _build_ui(self):
        pad = {"padx": 12, "pady": 7}

        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=14, pady=14)

        title = ttk.Label(main, text="STEP 2 IMAGE COLLECTOR",
                          font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w", pady=(0, 12))

        # Source
        ttk.Label(main, text="Thư mục gốc:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        src_frame = ttk.Frame(main)
        src_frame.pack(fill="x", **pad)
        ttk.Entry(src_frame, textvariable=self.src_var).pack(side="left", fill="x", expand=True)
        ttk.Button(src_frame, text="Chọn...", command=self.choose_source, width=12).pack(side="left", padx=(8, 0))

        # Destination
        ttk.Label(main, text="Thư mục lưu:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        dst_frame = ttk.Frame(main)
        dst_frame.pack(fill="x", **pad)
        ttk.Entry(dst_frame, textvariable=self.dst_var).pack(side="left", fill="x", expand=True)
        ttk.Button(dst_frame, text="Chọn...", command=self.choose_destination, width=12).pack(side="left", padx=(8, 0))

        opts = ttk.Frame(main)
        opts.pack(fill="x", pady=(4, 8))
        ttk.Checkbutton(opts, text="Quét cả thư mục con",
                        variable=self.recursive_var).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(opts, text="Phân biệt hoa/thường",
                        variable=self.case_var).pack(side="left")

        # Buttons
        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=(2, 10))
        self.start_btn = ttk.Button(btns, text="▶  BẮT ĐẦU THU ẢNH",
                                    command=self.start, width=22)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(btns, text="■  DỪNG", command=self.stop,
                                   width=12, state="disabled")
        self.stop_btn.pack(side="left", padx=8)

        # Progress
        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 10))

        # Stats
        stats = ttk.LabelFrame(main, text="Thống kê")
        stats.pack(fill="x", pady=(0, 10))

        labels = [
            ("File đã quét", self.total_var),
            ("File STEP 2", self.matched_var),
            ("Đã copy", self.copied_var),
            ("Lỗi", self.error_var),
        ]
        for i, (name, var) in enumerate(labels):
            box = ttk.Frame(stats)
            box.grid(row=0, column=i, sticky="ew", padx=10, pady=10)
            stats.columnconfigure(i, weight=1)
            ttk.Label(box, text=name).pack()
            ttk.Label(box, textvariable=var, font=("Segoe UI", 16, "bold")).pack()

        ttk.Label(main, text="Nhật ký:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        log_frame = ttk.Frame(main)
        log_frame.pack(fill="both", expand=True)

        self.log = tk.Text(log_frame, height=10, state="disabled",
                           font=("Consolas", 9), wrap="none")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(main, textvariable=self.status_var,
                  relief="sunken", anchor="w").pack(fill="x", pady=(8, 0))

    def choose_source(self):
        path = filedialog.askdirectory(title="Chọn thư mục gốc chứa ảnh")
        if path:
            self.src_var.set(path)

    def choose_destination(self):
        path = filedialog.askdirectory(title="Chọn thư mục lưu ảnh STEP 2")
        if path:
            self.dst_var.set(path)

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start(self):
        if self.running:
            return

        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()

        if not src or not os.path.isdir(src):
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục gốc hợp lệ.")
            return

        if not dst:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu.")
            return

        try:
            os.makedirs(dst, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Lỗi", f"Không tạo được thư mục lưu:\n{e}")
            return

        # Không cho destination nằm bên trong source khi quét recursive,
        # tránh việc collector tự quét lại file vừa copy.
        try:
            src_real = os.path.realpath(src)
            dst_real = os.path.realpath(dst)
            if self.recursive_var.get() and (
                os.path.commonpath([src_real, dst_real]) == src_real
            ):
                messagebox.showerror(
                    "Cấu hình không hợp lệ",
                    "Thư mục lưu không nên nằm bên trong thư mục gốc khi bật 'Quét cả thư mục con'."
                )
                return
        except ValueError:
            pass

        self.total_var.set("0")
        self.matched_var.set("0")
        self.copied_var.set("0")
        self.error_var.set("0")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        self.stop_event.clear()
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.start(12)
        self.status_var.set("Đang quét và thu ảnh...")

        threading.Thread(
            target=self.collect,
            args=(src, dst, self.recursive_var.get(), self.case_var.get()),
            daemon=True
        ).start()

    def stop(self):
        if self.running:
            self.stop_event.set()
            self.status_var.set("Đang dừng...")

    @staticmethod
    def unique_destination(dst_dir, filename):
        target = os.path.join(dst_dir, filename)
        if not os.path.exists(target):
            return target

        stem, ext = os.path.splitext(filename)
        counter = 1
        while True:
            target = os.path.join(dst_dir, f"{stem}__{counter}{ext}")
            if not os.path.exists(target):
                return target
            counter += 1

    def collect(self, src, dst, recursive, case_sensitive):
        start_time = time.time()
        total = matched = copied = errors = 0

        needle = "STEP 2" if case_sensitive else "step 2"

        # os.walk + scandir-style DirEntry iteration:
        # không đọc nội dung ảnh, chỉ kiểm tra metadata/tên file.
        try:
            if recursive:
                walker = os.walk(src)
            else:
                try:
                    entries = list(os.scandir(src))
                except OSError as e:
                    self.ui_queue.put(("error", f"Không thể đọc thư mục: {e}"))
                    return
                walker = [(src, [], entries)]

            for root_dir, dirs, files in walker:
                if self.stop_event.is_set():
                    break

                # Khi recursive, os.walk trả DirEntry? Không; files là tên.
                for item in files:
                    if self.stop_event.is_set():
                        break

                    name = item.name if hasattr(item, "name") else item
                    total += 1

                    ext = os.path.splitext(name)[1].lower()
                    if ext not in IMAGE_EXTS:
                        continue

                    check_name = name if case_sensitive else name.lower()
                    if needle not in check_name:
                        continue

                    matched += 1
                    source_file = os.path.join(root_dir, name)
                    target_file = self.unique_destination(dst, name)

                    try:
                        # copy2 giữ timestamp/metadata cơ bản.
                        shutil.copy2(source_file, target_file)
                        copied += 1

                        if copied <= 20 or copied % 100 == 0:
                            self.ui_queue.put(
                                ("log", f"✓ {name}")
                            )
                    except Exception as e:
                        errors += 1
                        self.ui_queue.put(
                            ("log", f"✗ {name} -> {e}")
                        )

                    if total % 500 == 0:
                        self.ui_queue.put(
                            ("stats", total, matched, copied, errors)
                        )

            elapsed = time.time() - start_time
            stopped = self.stop_event.is_set()

            self.ui_queue.put(
                ("done", total, matched, copied, errors, elapsed, stopped)
            )

        except Exception as e:
            self.ui_queue.put(("error", f"Lỗi nghiêm trọng: {e}"))

    def _process_ui_queue(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                kind = msg[0]

                if kind == "log":
                    self.write_log(msg[1])

                elif kind == "stats":
                    _, total, matched, copied, errors = msg
                    self.total_var.set(f"{total:,}")
                    self.matched_var.set(f"{matched:,}")
                    self.copied_var.set(f"{copied:,}")
                    self.error_var.set(f"{errors:,}")

                elif kind == "done":
                    _, total, matched, copied, errors, elapsed, stopped = msg
                    self.total_var.set(f"{total:,}")
                    self.matched_var.set(f"{matched:,}")
                    self.copied_var.set(f"{copied:,}")
                    self.error_var.set(f"{errors:,}")

                    self.running = False
                    self.progress.stop()
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")

                    speed = copied / elapsed if elapsed > 0 else 0

                    if stopped:
                        self.status_var.set(
                            f"Đã dừng | Copy {copied:,} ảnh | {elapsed:.1f}s"
                        )
                        self.write_log("=== ĐÃ DỪNG ===")
                    else:
                        self.status_var.set(
                            f"Hoàn tất | {copied:,} ảnh | {elapsed:.1f}s | "
                            f"{speed:.1f} ảnh/s"
                        )
                        self.write_log(
                            f"=== HOÀN TẤT: {copied:,} ảnh | {elapsed:.1f}s | "
                            f"{speed:.1f} ảnh/s ==="
                        )

                elif kind == "error":
                    self.running = False
                    self.progress.stop()
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.status_var.set("Có lỗi xảy ra")
                    self.write_log("ERROR: " + msg[1])
                    messagebox.showerror("Lỗi", msg[1])

        except queue.Empty:
            pass

        self.root.after(100, self._process_ui_queue)


if __name__ == "__main__":
    root = tk.Tk()

    # Windows DPI awareness nếu có thể.
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = Step2Collector(root)
    root.mainloop()
