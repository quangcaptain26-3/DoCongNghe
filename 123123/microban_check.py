import os
import re
import cv2
import pandas as pd
from tkinter import Tk, filedialog


def has_microban(image_path, template, threshold=0.55):
    img = cv2.imread(image_path)
    if img is None:
        return False

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val >= threshold


def parse_filename(filename):
    pattern = r'^([A-Z0-9]+)_(STEP\s*\d+)_([0-9]+)\.(jpg|jpeg|png)$'
    match = re.match(pattern, filename, re.IGNORECASE)

    if match:
        return match.group(1), match.group(2), match.group(3)

    return '', '', ''


def main():
    root = Tk()
    root.withdraw()

    folder = filedialog.askdirectory(title='Select Image Folder')
    if not folder:
        print('No folder selected.')
        return

    template_path = os.path.join(os.path.dirname(__file__), 'microban_template.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if template is None:
        print('Cannot find microban_template.jpg')
        return

    rows = []

    for file in os.listdir(folder):
        if not file.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        fullpath = os.path.join(folder, file)
        mac, step, timestamp = parse_filename(file)

        rows.append({
            'MAC': mac,
            'STEP': step,
            'Timestamp': timestamp,
            'File Name': file,
            'MicroBan': 'OK' if has_microban(fullpath, template) else 'NG'
        })

    df = pd.DataFrame(rows)
    output_excel = os.path.join(folder, 'MicroBan_Result.xlsx')
    df.sort_values(by=['MAC', 'STEP'], inplace=True)
    df.to_excel(output_excel, index=False)

    print('Done:', output_excel)


if __name__ == '__main__':
    main()
