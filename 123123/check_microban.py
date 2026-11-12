import os
import re
import cv2
import pandas as pd

# ==========================
# CONFIG
# ==========================
IMAGE_FOLDER = r"images"
TEMPLATE_FILE = r"template_microban.jpg"

OUTPUT_EXCEL = "Microban_Result.xlsx"

# threshold
MATCH_THRESHOLD = 0.45

# ==========================
# LOAD TEMPLATE
# ==========================
template = cv2.imread(TEMPLATE_FILE, 0)

if template is None:
    raise Exception("Cannot load template_microban.jpg")

tw, th = template.shape[::-1]

results = []

# ==========================
# PROCESS IMAGES
# ==========================
for filename in os.listdir(IMAGE_FOLDER):

    if not filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".bmp")
    ):
        continue

    img_path = os.path.join(
        IMAGE_FOLDER,
        filename
    )

    img = cv2.imread(img_path)

    if img is None:
        continue

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    h, w = gray.shape

    # ROI vùng Microban
    roi = gray[
        int(h * 0.65):int(h * 0.90),
        int(w * 0.15):int(w * 0.55)
    ]

    result = cv2.matchTemplate(
        roi,
        template,
        cv2.TM_CCOEFF_NORMED
    )

    _, max_val, _, _ = cv2.minMaxLoc(result)

    microban = "YES" if max_val > MATCH_THRESHOLD else "NO"

    # lấy MAC từ tên file
    mac = ""

    m = re.match(
        r'([0-9A-Fa-f]{12})_',
        filename
    )

    if m:
        mac = m.group(1).upper()

    results.append({
        "MAC Address": mac,
        "Result": microban,
        "Score": round(max_val, 4),
        "Filename": filename
    })

    print(
        f"{filename} --> {microban} ({max_val:.3f})"
    )

# ==========================
# EXPORT EXCEL
# ==========================
df = pd.DataFrame(results)

df.sort_values(
    by="MAC Address",
    inplace=True
)

df.to_excel(
    OUTPUT_EXCEL,
    index=False,
    engine="openpyxl"
)

print()
print(f"Saved: {OUTPUT_EXCEL}")