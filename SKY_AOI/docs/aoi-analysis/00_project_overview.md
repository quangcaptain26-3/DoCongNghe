# Tổng quan dự án — SKY AOI (`sky.py`)

## File này làm gì

`sky.py` (~5.571 dòng) là **ứng dụng desktop PyQt5 đơn khối** cho kiểm tra quang học tự động (AOI) các sản phẩm phần cứng mạng (Cisco C1000/C1200/C1300, SKY, MR6500, HH4K, Nanook, v.v.). Ứng dụng điều phối:

- Chụp ảnh camera (Basler qua `basler_my`)
- Kích hoạt cảm biến IO (Advantech PCI-1756 qua `IoCard`)
- Kiểm tra thị giác (OpenCV, barcode, OCR, Cambrian AI, YOLO)
- Tải lên MES (SFIS qua `sfisapi`)
- Hiển thị GUI và đếm đạt/không đạt

Ghi chú dòng 1–4 (tiếng Trung): chọn file model; camera + điểm + suy luận + thông tin kiểm thử tích lũy.

## Loại ứng dụng

**Ứng dụng desktop GUI** — không phải CLI hay dịch vụ headless. Ứng dụng Qt một tiến trình, hướng sự kiện, với vòng lặp kiểm thử chặn luồng trên luồng UI.

## Điểm vào

```text
if __name__ == "__main__":          # L5552
  app = QApplication(sys.argv)
  demo = Demo()
  demo.show()
  sys.exit(app.exec_())
```

## Các class chính

| Class | Dòng | Vai trò |
|-------|------|---------|
| `Demo` | L139–5420 | Cửa sổ chính; ~95% logic |
| `Uihand` | L121–126 | Trung tâm tín hiệu PyQt cho điều phối kiểm thử |
| `ReadDataMatrixCode` | L5500–5512 | Helper giải mã DataMatrix |
| `Runthread` | L5514–5538 | Worker QThread cho PaddleOCR |
| `Mytest` | L129–136 | QThread timeout — **không dùng (đã comment)** |
| `Scan` | L5485–5498 | Dialog quét — **không được tham chiếu trong luồng runtime** |

## Luồng runtime (mức cao)

1. **Khởi động** — `Demo.__init__`: logging, `config.json`, SFIS, khám phá camera, JSON model, nối tín hiệu.
2. **Chờ** — Vòng lặp sự kiện Qt; người vận hành chọn model/route qua UI.
3. **Bắt đầu** — `startprogram()`: mở camera, khởi tạo thẻ IO (nếu chế độ sensor), vào vòng lặp kiểm thử `while True`.
4. **Mỗi DUT** — `go_run1` (quét) → `go_run2` (sensor + chụp) hoặc `go_run3` (chụp thủ công + thị giác).
5. **Thị giác** — `show_image_<MODEL>()` đặt `stepN`, Đạt/Không đạt, bộ đếm, tải lên SFIS tùy chọn.
6. **Dừng** — `stopprogram()` / `closeEvent()`: đặt `stop_program`, giải phóng IO, đóng camera.

## Thư viện bên ngoài (trong `sky.py`)

PyQt5, OpenCV, NumPy, PIL, pypylon, pylibdmtx, pyzbar, PaddleOCR, paddle, suds, pega_inference (`SampleClientV2`), json, logging, threading, Queue.

## Module bên ngoài — Thiếu trong workspace

| Module | Dùng cho |
|--------|----------|
| `UI` (`Ui_MainWindow`) | Bố cục UI Qt Designer |
| `basler_my.camera` | Wrapper camera Basler |
| `sfisapi` | Client SOAP SFIS/MES |
| `ioCardNew.IoCard` | PCI-1756 DIO (import **đã comment** L29) |
| `ipex_check_yolo.camera_check_ipex` | model ipex_check (import **đã comment** L37) |
| `yolov5.classify.predict_change` | Suy luận YOLO (import **đã comment** L7; nhánh chết) |
| `config.json` | Cấu hình app lúc runtime |
| JSON model/point/sample + JPG | ROI công thức, mẫu chuẩn, bộ đếm |
| `profile/pci1756.xml` | Profile thẻ IO |
| `source/` (có thể ghi) | Ảnh OCR/vết xước lúc runtime |

**Bản đồ ranh giới đầy đủ:** `07_camera_io_sfis.md`

## Vùng mã quan trọng

| Vùng | Dòng (xấp xỉ) | Nội dung |
|------|---------------|----------|
| Hằng số module | L46–112 | Chuỗi kiểm tra OCR/nhãn theo từng model Cisco |
| `Demo.__init__` | L146–374 | Khởi tạo, SFIS, camera, nạp model, tín hiệu |
| Helper cấu hình | L376–648 | Route, đếm, chọn model, client suy luận |
| **Điều phối** | L660–1912 | `startprogram`, `go_run1/2/3` |
| Pipeline thị giác | L1913–5161 | `show_image_*`, helper |
| Hash/so sánh | L5318–5397 | `HH4K_compare`, `pHash`, `cmHash` |
| Dừng/dọn dẹp | L5398–5420 | `stopprogram`, `closeEvent` |
| Helper | L5485–5538 | Scan, barcode, luồng OCR |
| Điểm vào | L5552–5563 | `main` |

## Phạm vi workspace

Repo hiện tại **chỉ** chứa `sky.py`. Tất cả phụ thuộc trên phải có trên máy triển khai.
