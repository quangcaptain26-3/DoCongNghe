# Đồ thị gọi hàm — Mức cao

Phạm vi: chỉ điều phối và phân phối. Chi tiết bên trong thị giác (`show_image_*`) là lá.

## Khởi động ứng dụng

```text
main                                    # L5552
└── Demo.__init__                       # L146
    ├── create_log()                    # L157
    ├── json.load('config.json')        # L158
    ├── sfisapi.do_sfis()               # L168  [nếu SFIS bật]
    │   └── mysfis.loginout()           # L180–193
    ├── camera().search_get_device()    # L209–210
    ├── json.load(model JSON)           # L226+  [nếu choose_model đã đặt]
    │   ├── SampleClientV2()            # L257+  [nếu cambrian]
    │   └── get_version()               # L281
    ├── nạp barcode_point, model_point, count_object
    └── nối tín hiệu UI + Uihand        # L357–370
```

## Phiên kiểm thử (Người dùng nhấn Bắt đầu)

```text
pushButton_2.clicked
└── startprogram()                      # L660
    ├── camera() → self.ekkoshan        # L662
    ├── IoCard()                        # L673  [nếu is_sensor]
    └── while True:                     # L687 hoặc L703
        ├── [wait_test] emit test1
        │   └── go_run1()               # L736
        │       ├── QInputDialog        # [chỉ Button_check]
        │       └── scan_sta = True
        ├── [scan_sta] emit test2 HOẶC test3
        │   ├── go_run2()               # L795  [is_sensor=True]
        │   │   ├── iocard.get_io_signal()
        │   │   ├── ekkoshan.get_image()
        │   │   └── show_image_MR6500()   ⚠ hardcode
        │   └── go_run3()               # L834  [is_sensor=False]
        │       └── [nhánh theo select_model]
        │           ├── show_image_MR6500
        │           ├── camera_check_ipex  [ipex_check]
        │           ├── show_image_HH4K      [HH4K, tối đa 4×]
        │           ├── show_image_SKY       [SKY/SKY_4G, tối đa 6×]
        │           ├── show_image_C1000_8FP_E_2G_L  [biến thể Cisco]
        │           ├── show_image_Button_check
        │           ├── show_image_WP
        │           └── show_image_Nanook
        └── [stop_program] break → bật lại nút Bắt đầu
```

## Lá pipeline thị giác (không mở rộng)

```text
show_image_<MODEL>(image, stepname?)
├── crop ROI từ model_point / barcode_point JSON
├── [tùy chọn] ReadDataMatrixCode.decode / pyzbar.decode
├── [tùy chọn] PaddleOCR / Runthread (QThread)
├── [tùy chọn] get_inference_result() → client.predict_images()
├── [tùy chọn] yolov5_inference() → predict_change.run()
├── [tùy chọn] HH4K_compare / pHash / cmHash
├── đặt self.stepN, resultcolor, updatecount, UI_show
└── [tùy chọn] mysfis.data_upload()
```

## Dừng / Tắt

```text
pushButton_3.clicked
└── stopprogram()                       # L5398
    ├── stop_program = True
    ├── iocard.instantDioCtrlDispose()  # try
    └── ekkoshan.close_camera()         # try

đóng cửa sổ
└── closeEvent()                        # L5411
    └── (dọn dẹp giống stopprogram)
```

## Nhánh không dùng / chết (không có caller trong sky.py)

```text
show_image(image_path)                  # L1913 — không tham chiếu
show_image_SKY_yolo(...)                # L3109 — không tham chiếu
Mytest.run()                            # cách dùng đã comment L679–681
Dialog Scan                             # L5485 — không bao giờ khởi tạo
trainstart()                            # chỉ in debug
change_camera() / savelog()             # thân stub `1`
```

## Đồ thị tín hiệu (Uihand)

```text
startprogram
  └── myuihand.test1.emit()  →  go_run1
  └── myuihand.test2.emit()  →  go_run2   [chế độ sensor]
  └── myuihand.test3.emit()  →  go_run3   [chế độ thủ công]
  └── myuihand.textbox.emit() → get_rightnow
  └── myuihand.clear_show.emit() → clear_showing
```
