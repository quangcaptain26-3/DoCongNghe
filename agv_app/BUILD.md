# Hướng dẫn build & chạy - AGV Analyzer

Ứng dụng phân tích chất lượng hoạt động của AGV (tỷ lệ bất thường) từ các thư mục log.
Tương thích **Python 3.8** (môi trường công ty). Không dùng pandas/numpy.

Giao diện hoàn toàn **tiếng Việt có dấu**, thiết kế theo hướng "sếp nhìn phát là hiểu".

## 1. Tính năng chính
- Thêm nhiều thư mục log cùng lúc (nút, chọn thư mục cha tự quét, hoặc kéo-thả).
- Giữ nguyên logic phát hiện bất thường của bản gốc (`ptich_agv/abnormalAnalyse.py`).
- **Tab Tổng quan (dashboard)**: thẻ KPI + biểu đồ xu hướng + xếp hạng điểm/xe +
  so sánh ca ngày/đêm + mẫu theo thứ + phân nhóm mức độ nặng.
- Các tab chi tiết: Theo ngày / Theo điểm / Theo xe / Thứ 7 / Theo tuần / Theo tháng.
- **Xuất Excel** nhiều sheet, có **công thức sống** (bấm vào ô là thấy cách tính,
  sửa đầu vào thì số tự đổi) và **biểu đồ** ngay trong sheet Tổng quan.
- **Xuất CSV** kèm cột đầu vào và khối chú thích công thức để tự kiểm chứng.
- **Cài đặt mở rộng**: ngưỡng bất thường, thang máy, điểm loại trừ (theo nhóm),
  giờ ca, số giờ mẫu số, ngưỡng màu, thư mục log/xuất mặc định; lưu ra
  `point_settings.json`.

## 2. Yêu cầu môi trường build
- Windows 10/11 **64-bit**.
- **Python 3.8.10 (x64)** (dùng để build; máy chạy .exe KHÔNG cần Python).

## 3. Tạo môi trường và cài thư viện (chỉ làm 1 lần)
Chạy từ **thư mục gốc dự án** (nơi chứa thư mục `agv_app`):

```powershell
py -3.8 -m venv .venv38
.\.venv38\Scripts\python.exe -m pip install --upgrade pip
.\.venv38\Scripts\python.exe -m pip install -r agv_app\requirements.txt
```

Các phiên bản PINNED (tương thích 3.8):
- PyQt5 5.15.10 + PyQt5-Qt5 5.15.2 + PyQt5-sip 12.13.0
- openpyxl 3.1.2 (đủ để tạo công thức + biểu đồ trong Excel)
- pyinstaller 5.13.2

> Biểu đồ trong ứng dụng được vẽ bằng `QPainter` (tự vẽ), không cần thư viện
> biểu đồ ngoài, giữ gói nhẹ và "bật là chạy".

## 4. Chạy thử (chế độ phát triển)
```powershell
.\.venv38\Scripts\python.exe -m agv_app.main
```

## 5. Build ra file .exe (onedir - bật lên chạy ngay)

> **QUAN TRỌNG:** PyInstaller bị lỗi khi **đường dẫn dự án chứa ký tự có dấu**
> (vd `Dự án CNTT`) -> lỗi `WinError 123`. Vì vậy HÃY DÙNG SCRIPT tự động build ở
> đường dẫn ASCII bên dưới. (App sau khi build vẫn chạy tốt ở thư mục có dấu.)

### Cách 1 (khuyên dùng) - script tự động:
```powershell
powershell -ExecutionPolicy Bypass -File agv_app\build\build.ps1
```
Script sẽ: tạo thư mục build ASCII (`%USERPROFILE%\agv_build`), tạo venv 3.8, cài
thư viện, build, rồi chép kết quả về `dist\AGV_Analyzer\` của dự án.

### Cách 2 - thủ công (chỉ khi dự án nằm ở đường dẫn ASCII, không dấu):
```powershell
.\.venv38\Scripts\pyinstaller.exe agv_app\build\agv_app.spec --noconfirm
```

Kết quả:
```
dist\AGV_Analyzer\AGV_Analyzer.exe   <-- nháy đúp để chạy
```
Toàn bộ thư mục `dist\AGV_Analyzer\` là app độc lập:
- **Chép cả thư mục** sang máy khác (Windows 64-bit) là chạy được ngay, không cần cài Python.
- Dạng **onedir** nên bật lên là có ngay (không phải giải nén ra temp).
- App CHẠY được ở đường dẫn có dấu; chỉ riêng quá trình BUILD mới cần đường dẫn ASCII.

## 6. Đưa lên GitHub
- Nén `dist\AGV_Analyzer\` thành `AGV_Analyzer.zip` rồi tải lên (Release hoặc LFS).
- Người dùng tải về, giải nén, chạy `AGV_Analyzer.exe`.

## 7. Tùy chỉnh cấu hình
File `point_settings.json` (nằm trong bản đóng gói và có thể đặt cạnh .exe) chứa:
- `threshold_min`: ngưỡng dừng bất thường chung (mặc định 12 phút).
- `denom_hours`: số giờ mẫu số khi tính tỷ lệ (mặc định 24).
- `excluded_points`: điểm không tính bất thường, GIỮ THEO NHÓM (Home/Charging).
- `elevator`: điểm thang máy + ngưỡng riêng (mặc định 3 phút).
- `shift`: giờ ca ngày/đêm.
- `display`: ngưỡng màu tốt/cảnh báo (%).
- `paths`: thư mục log / thư mục xuất mặc định.

Trong app cũng có khung **Cài đặt** để chỉnh trực tiếp và bấm "Lưu cài đặt".

## 8. Lưu ý quan trọng
- **Kiến trúc**: file .exe build trên Windows-x64 chỉ chạy trên **Windows 64-bit**.
- **Tỷ lệ bất thường vs file xlsx cũ**: các file `Log{ngày}_day.xlsx/_night.xlsx` cũ
  được tạo TRƯỚC khi có quy tắc "ngưỡng thang máy 3 phút". App mới mặc định ÁP DỤNG
  quy tắc này (theo `point_settings.json`) nên số liệu có thể cao hơn file cũ.
  Nếu muốn số khớp file cũ: bỏ tick "Áp dụng ngưỡng riêng cho thang máy" rồi phân tích lại.
- **Công thức trong Excel**: được lưu ở dạng chuẩn (SUM/ROUND/IF...) nên chạy được
  với Excel mọi ngôn ngữ; mở file lên Excel sẽ tự tính.

## 9. Phương án .exe 1 file (tùy chọn)
Nếu muốn gọn thành 1 file duy nhất (đều chạy được mọi nơi, nhưng lần đầu mở hơi chậm
do giải nén ra thư mục tạm), sửa `agv_app\build\agv_app.spec`:
- Xóa phần `COLLECT(...)`.
- Trong `EXE(...)` đổi thành: thêm `a.binaries, a.zipfiles, a.datas,` và đặt
  `exclude_binaries=False`, `name="AGV_Analyzer"`.
Rồi build lại. Kết quả: `dist\AGV_Analyzer.exe` (1 file).

## Cấu trúc dự án
```
agv_app/
  main.py               # điểm khởi chạy
  point_settings.json   # cấu hình (có thể sửa)
  requirements.txt      # thư viện pinned cho Python 3.8
  core/
    config.py           # nạp/lưu cấu hình + resource_path
    abnormal.py         # đọc log, phát hiện bất thường (suy ra ngày từ thư mục)
    aggregate.py        # tổng hợp + phân tích (điểm/xe/KPI/thứ/ca/mức độ nặng)
    export.py           # xuất Excel (công thức + biểu đồ) + CSV
  gui/
    main_window.py      # giao diện PyQt5 (dashboard + các tab)
    charts.py           # widget biểu đồ vẽ bằng QPainter
  build/
    agv_app.spec        # cấu hình đóng gói PyInstaller
  BUILD.md              # tài liệu này
```
