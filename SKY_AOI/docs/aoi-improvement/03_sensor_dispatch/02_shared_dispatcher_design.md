# Shared Vision Dispatcher — Compact Playbook

**File:** `sky.py` · **Workstream:** `03_sensor_dispatch`  
**Nguồn:** `11_refactor_plan.md` §5–8, `08_model_dispatch.md`, `05_runtime_flow.md`, `10_risks_and_bugs.md`  
**Luật:** Một callable `dispatch_vision(self, image, …)` map `select_model` → `show_image_*`; **Phase 1 không đổi behavior manual** — chỉ refactor lời gọi.

**Điều kiện:** `01_sensor_mode_guard.md` (SENSOR-001/002) đã ship trên mọi trạm sensor.

> Line analysis: `go_run2` L795–832 / L829, `go_run3` L834–1911. **Ctrl+F anchor** — line drift. Pre-check: F `def go_run2`, F `def go_run3` phải tồn tại.

---

## Improvement Purpose

Mục tiêu của cải tiến này là thay hardcode `show_image_MR6500` trong sensor path bằng shared dispatcher `dispatch_vision(select_model, image)` — một map model → pipeline, dùng chung cho `go_run2` (sensor) và `go_run3` (manual). Hướng cải tiến dài hạn sau khi short-term guard đã ship.

## Before Improvement

Trước cải tiến, dispatch vision duplicate và không nhất quán: `go_run2` luôn gọi MR6500; `go_run3` có chuỗi `elif select_model` dài với logic lặp. Thêm model mới = sửa nhiều chỗ; sensor path không thể mở rộng an toàn; unknown model dễ stall (thiếu else — xem RT-001).

## After Improvement

Sau cải tiến, `MODEL_REGISTRY` + `dispatch_vision()` map `select_model` → `show_image_*` với flag `sensor_capable`. Phase 1 refactor lời gọi không đổi behavior manual; Phase 2 `go_run2` dùng dispatcher thay hardcode. Thêm model = thêm registry entry; sensor chỉ model có `sensor_capable=True`.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm duplicate dispatch logic — ít nhánh sót khi thêm model |
| Operator experience         | N/A trực tiếp (behavior giữ nguyên phase 1) |
| MES/SFIS integrity          | N/A |
| Maintainability             | Single dispatcher thay chuỗi elif; incremental PR theo model |
| Debugging / troubleshooting | Unknown model → log + Fail tập trung trong dispatcher |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | go_run2 hardcode MR6500; go_run3 elif chain | dispatch_vision() shared entry point |
| Error handling   | Unknown model stall ở cuối go_run3 | Registry lookup + explicit Fail |
| Operator impact  | Không đổi phase 1 manual path | Không đổi phase 1 |
| Production risk  | Wrong pipeline khi config sai | Guard + dispatcher giảm drift khi mở rộng |

---

## Per-Fix Detail

### SENSOR-D00

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` (prerequisite) |
| Related doc | `01_sensor_mode_guard.md` |
| Fix IDs | SENSOR-001, SENSOR-002 |
| Anchor | G617 / F `def startprogram` |

#### Current Problem

Dispatcher Phase 2 mở rộng sensor path trước khi guard ship → rủi ro chạy vision sai model qua `dispatch_vision` khi config vẫn cho phép combo nguy hiểm.

#### Before Improvement

`go_run2` hardcode MR6500 nhưng không có lớp policy chặn non-MR6500 + sensor tại Start.

#### Required Change

Ship **SENSOR-001/002** trên mọi trạm sensor trước khi merge SENSOR-D01+. Verify SKY+sensor blocked tại Start.

#### After Improvement

Guard là prerequisite — dispatcher chỉ nhận traffic sensor đã validate MR6500-only (hoặc explicit reject trong D02).

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Lớp an toàn rẻ trước refactor dispatch |
| Operator experience | Blocked rõ tại Start nếu config sai |
| MES/SFIS integrity | Tránh wrong pipeline trong giai đoạn chuyển đổi |
| Maintainability | Guard và dispatcher tách phase rõ |
| Debugging / troubleshooting | D00 test: SKY+sensor vẫn blocked sau mọi PR dispatcher |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-D00 | SENSOR-002 deployed | SKY + `is_sensor=True`, Start | Blocked tại Start; không vào `go_run2` |
| T-D00b | Sau mỗi PR dispatcher | Cùng setup | Vẫn blocked (regression guard) |

#### Rollback

Không rollback D00 — giữ sensor guard sau dispatcher. Nếu revert guard: wrong pipeline risk quay lại.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 (file `01_sensor_mode_guard.md`) | Prerequisite bắt buộc trước Month 1 dispatcher work |

---

### SENSOR-D01

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` (+ module-level registry) |
| Function | (new), before `go_run2` |
| Anchor | G795 / F `def go_run2` |
| Insert point | Ngay **trước** `def go_run2(self):` |

#### Current Problem

Không có registry map `select_model` → pipeline. Unknown model và duplicate dispatch logic rải rác — thêm model = sửa nhiều chỗ.

#### Before Improvement

`go_run2` gọi trực tiếp `show_image_MR6500`; `go_run3` có chuỗi `elif select_model` dài. Không có `get_model_spec` hay fail path tập trung.

#### Required Change

**Chèn** `ModelSpec` dataclass, `MODEL_REGISTRY` (phase 1: MR6500), `get_model_spec()`, và method `dispatch_vision(self, image, step=None, stepname=None)` trên class `Demo`.

#### After Improvement

Single entry point `dispatch_vision` — unknown model → log + `resultcolor("Fail")` + `wait_test=True`. Registry mở rộng từng PR (D04/D05).

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Unknown model fail tập trung, không stall im lặng |
| Operator experience | N/A phase 1 (behavior giữ nguyên cho model đã có) |
| MES/SFIS integrity | N/A |
| Maintainability | Thêm model = thêm registry entry |
| Debugging / troubleshooting | Log `Unknown select_model` một chỗ |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-D01 | Registry deployed; `select_model` giả | Gọi `dispatch_vision` | Log unknown + Fail; không exception |
| T-D01b | MR6500 | `dispatch_vision(shan)` | Gọi `show_image_MR6500` như trước |

#### Rollback

Xóa dataclass/registry/`dispatch_vision`; khôi phục gọi trực tiếp `show_image_*`. Revert D03+ callers nếu đã migrate.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Month 1+ / Month 2 (PR-1) | Refactor foundation — cần regression baseline MR6500 |

---

### SENSOR-D02

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `go_run2` |
| Anchor | G829 / F `show_image_MR6500(self.shan)` trong `go_run2` |
| Insert point | Sau `self.shan=shan`, trước `self.wait_test=True` |

#### Current Problem

Sensor path hardcode `show_image_MR6500(self.shan)` — bug gốc: bỏ qua `select_model` (analysis L829).

#### Before Improvement

Mọi trigger sensor → MR6500 pipeline dù recipe là SKY/WP/Button_check (nếu guard chưa ship).

#### Required Change

**Đổi** `show_image_MR6500(self.shan)` → `get_model_spec` check `sensor_capable` + `dispatch_vision(self.shan)`; reject nếu spec None hoặc `not sensor_capable`.

#### After Improvement

Với D00 guard: chỉ MR6500 tới đây; dispatch tương đương behavior cũ. Defense-in-depth nếu guard bypass.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Sensor dispatch qua registry thay hardcode |
| Operator experience | N/A (MR6500 behavior giữ nguyên) |
| MES/SFIS integrity | Đúng pipeline khi mở rộng sensor_capable sau audit |
| Maintainability | 1 dòng thay hardcode — sẵn sàng multi-model sensor |
| Debugging / troubleshooting | Log `Sensor dispatch rejected` nếu policy fail |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-D02 | Sensor MR6500 trên clone | Trigger DUT | Vision output giống baseline |
| T-D02b | Guard + D02 | SKY+sensor | Vẫn blocked tại Start (D00) |

#### Rollback

Khôi phục `self.show_image_MR6500(self.shan)` tại G829.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Month 1+ / Month 2 (PR-1) | Cùng PR với D01/D03; regression sensor MR6500 |

---

### SENSOR-D03

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `go_run3` |
| Anchor | G839 / F `select_model=="MR6500"` trong `go_run3` |
| Insert point | Nhánh MR6500: sau `get_image`, trước `wait_test` |

#### Current Problem

Nhánh manual MR6500 gọi trực tiếp `show_image_MR6500` — duplicate với sensor path, không dùng dispatcher.

#### Before Improvement

Manual và sensor MR6500 là hai lời gọi riêng — drift khi sửa pipeline MR6500.

#### Required Change

**Đổi** `self.show_image_MR6500(self.shan)` → `self.dispatch_vision(self.shan)` trong nhánh `if self.select_model=="MR6500"`.

#### After Improvement

Manual MR6500 đi qua `dispatch_vision` — behavior phase 1 không đổi; một chỗ sửa cho cả manual + sensor.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Đồng bộ manual/sensor MR6500 qua registry |
| Operator experience | Pass/fail/count không đổi |
| MES/SFIS integrity | N/A |
| Maintainability | PR-1 hoàn tất MR6500 trên cả hai path |
| Debugging / troubleshooting | Cùng log path unknown/fail |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-D03 | Manual MR6500 | 1 Pass + 1 Fail cycle | Không regression pass/fail/count |

#### Rollback

`dispatch_vision` → `show_image_MR6500` trong nhánh MR6500 `go_run3`.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Month 1+ / Month 2 (PR-1) | Low-risk — cùng PR D01+D02 |

---

### SENSOR-D04

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `go_run3` (per model) |
| Anchor | G940+ / F `show_image_SKY`, `show_image_HH4K`, etc. |
| Insert point | Trong step loop từng model, sau `get_image` |

#### Current Problem

Mỗi model manual gọi `show_image_*` trực tiếp — thêm/sửa model phải tìm mọi call site trong chuỗi `elif`.

#### Before Improvement

SKY, HH4K, Button_check, WP, Nanook, ipex — mỗi model có `show_image_*` riêng trong `go_run3` step loops.

#### Required Change

**Đổi** từng `show_image_*` → `dispatch_vision(..., stepname=…)` hoặc `dispatch_vision(shan)` — **chỉ đổi lời gọi vision**, giữ orchestration `go_run3` (QMessageBox, step flags).

#### After Improvement

Registry chứa entry per model; thêm model mới = registry + một nhánh orchestration (hoặc collapse sau). Incremental PR: Button_check/ipex → HH4K → WP/Nanook → SKY.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm sót nhánh khi thêm model |
| Operator experience | Behavior giữ nguyên từng PR |
| MES/SFIS integrity | N/A |
| Maintainability | Migrate từng model — không big-bang |
| Debugging / troubleshooting | Full step matrix per PR trước merge |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-D04 | Model đã migrate (từng PR) | Full step matrix model đó | Kết quả từng step giống baseline |

#### Rollback

Revert từng `dispatch_vision` → `show_image_*` theo model đã migrate trong PR đó.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Month 2 (PR-2 Button_check/ipex) | Low-risk models trước |
| Month 2–3 (PR-3 HH4K, PR-4 Cisco via D05, PR-5 WP/Nanook) | Medium risk — full matrix mỗi PR |
| Month 3 (PR-6 SKY) | High risk — SKY cuối cùng |

---

### SENSOR-D05

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` / `MODEL_REGISTRY` |
| Function | Registry build (trong D01 block) |
| Anchor | G1292 / F `select_model == "C1000-8FP-E-2G-L"` trong `go_run3` |

#### Current Problem

12 model Cisco alias dùng chung handler nhưng registry/chuỗi `elif` duplicate — khó maintain alias list.

#### Before Improvement

12 nhánh `elif select_model == "C1000-…"` riêng trong `go_run3` (hoặc tương đương).

#### Required Change

**Append** vào `MODEL_REGISTRY`: `CISCO_MODELS` tuple → shared `ModelSpec` → `show_image_C1000_8FP_E_2G_L`, `sensor_capable=False`.

#### After Improvement

Một `ModelSpec` cho cả family; alias lookup qua `get_model_spec`. `go_run3` có thể giữ elif đến PR-4 hoặc collapse dần.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Alias miss ít hơn khi thêm SKU Cisco |
| Operator experience | Barcode match đúng qua handler chung |
| MES/SFIS integrity | N/A |
| Maintainability | 12 model → 1 registry entry |
| Debugging / troubleshooting | Test 1 alias đại diện + spot check |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-D05 | 12 model Cisco alias | 1 cycle mỗi alias đại diện | Cùng handler; barcode match đúng |

#### Rollback

Xóa Cisco entries khỏi `MODEL_REGISTRY`; khôi phục elif chain nếu đã collapse.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Month 2–3 (PR-4) | Medium risk — 12 alias, full step matrix |

---

### SENSOR-D06

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `go_run3` (end) / `dispatch_vision` |
| Anchor | G1910 / F `def show_image(self,image_path)` |
| Related | `RT-001` trong `01_wait_test_stall_fix.md` |

#### Current Problem

Unknown `select_model` cuối `go_run3` có thể return im lặng — stall `wait_test` (thiếu else).

#### Before Improvement

Typo model hoặc model mới chưa có nhánh → không vision, không `wait_test=True`.

#### Required Change

Registry lookup trong `dispatch_vision` đã handle unknown → Fail + `wait_test=True`. Đồng bộ với **RT-001** `else` fallback cuối `go_run3` nếu orchestration không gọi dispatcher.

#### After Improvement

Unknown model → log + Fail + recover — line sẵn sàng DUT tiếp.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Không treo wait_test trên typo model |
| Operator experience | Thấy "Unknown model" thay vì app đứng im |
| MES/SFIS integrity | N/A |
| Maintainability | Fail path tập trung registry + RT-001 |
| Debugging / troubleshooting | Log model string lỗi |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-D06 | Model JSON typo / giả | Start 1 chu kỳ | Log unknown; `wait_test=True`; DUT tiếp |

#### Rollback

Xóa unknown handling trong dispatcher; **không** rollback RT-001 else nếu đã ship.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Month 2–3 | Cùng phase D04 hoặc sau RT-001 Week 1 |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **SENSOR-D00** | Prerequisite guard | — | `01_sensor_mode_guard.md` SENSOR-002 | Ship guard trước | SKY+sensor blocked |
| **SENSOR-D01** | Registry + wrapper chưa có | G795 / F `def go_run2` | Ngay **trước** `def go_run2` · **Sai:** trong `show_image_MR6500` | **Chèn** `MODEL_REGISTRY`, `get_model_spec`, `dispatch_vision` | Unknown model → log + Fail |
| **SENSOR-D02** | `go_run2` hardcode MR6500 | G829 / F `show_image_MR6500(self.shan)` trong `go_run2` | Sau `self.shan=shan`, trước `self.wait_test=True` · **Sai:** branch MR6500 trong `go_run3` | **Đổi** 1 dòng → `dispatch_vision` | Sensor MR6500 giống trước |
| **SENSOR-D03** | `go_run3` MR6500 trùng logic | G839 / F `select_model=="MR6500"` trong `go_run3` | Nhánh MR6500: sau `get_image`, trước `wait_test` · **Sai:** `go_run2` | **Đổi** `show_image_MR6500` → `dispatch_vision` | Manual MR6500 không đổi |
| **SENSOR-D04** | Các model khác — từng PR | G940 / F `show_image_SKY(self.shan1` | Trong step loop SKY `go_run3` · **Sai:** đổi QMessageBox orchestration | **Đổi** từng `show_image_*` → `dispatch_vision(..., stepname=…)` | Full step matrix SKY |
| **SENSOR-D05** | Cisco 12 alias | G1292 / F `select_model == "C1000-8FP-E-2G-L"` | Đầu nhánh Cisco `go_run3` · **Sai:** copy 12 spec riêng | Registry alias → 1 `ModelSpec` | 12 model cùng handler |
| **SENSOR-D06** | Unknown model cuối `go_run3` | G1910 / F `def show_image(self,image_path)` | Cuối `go_run3`, trước `def show_image` · **Sai:** trong nhánh WP | Xem `RT-001` trong `01_wait_test_stall_fix.md` | Typo model → recover |

**Ship (incremental):** D00 → D01 → D02 → D03 → (D04 từng model) → D05 → D06

| PR | Scope | Risk |
|----|-------|------|
| PR-1 | D01 + D02 + D03 | Low |
| PR-2 | D04 Button_check, ipex | Low |
| PR-3 | D04 HH4K | Medium |
| PR-4 | D05 Cisco | Medium |
| PR-5 | D04 WP, Nanook | Medium |
| PR-6 | D04 SKY | High |

---

## Kiến trúc (target)

```text
Demo class (phase 1 — chưa tách file):
  MODEL_REGISTRY: dict[str, ModelSpec]
  get_model_spec(select_model) -> ModelSpec | None
  dispatch_vision(self, image, step=None, stepname=None)

go_run2 (sensor):  get_image → dispatch_vision (chỉ sensor_capable=True)
go_run3 (manual):  step loop giữ nguyên → dispatch_vision thay show_image_*
```

| Model | `sensor_capable` | Lý do |
|-------|------------------|-------|
| MR6500 | **Yes** | 1 frame, không modal |
| ipex_check | Maybe (sau audit) | 1 step |
| HH4K, SKY, Cisco, Button_check, WP, Nanook | **No** | Multi-step + modal — guard vẫn chặn sensor |

---

## Diff patches

### SENSOR-D01 · registry + `dispatch_vision`, trước `go_run2` G795

**Đúng chỗ:** class `Demo`, ngay trước `def go_run2(self):` · **Sai:** file module riêng (phase 2)

```python
# TRƯỚC
    def go_run1(self):
        ...

    def go_run2(self):
        while self.stop_program==False:

# SAU — thêm (rút gọn phase 1; mở rộng registry từng PR)
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class ModelSpec:
    select_model: str
    pipeline_fn: str          # method name on Demo, e.g. "show_image_MR6500"
    steps: int
    sensor_capable: bool
    requires_stepname: bool   # True for SKY/WP/HH4K/Nanook step loops

MODEL_REGISTRY = {
    "MR6500": ModelSpec("MR6500", "show_image_MR6500", 1, True, False),
    # PR-2+: "Button_check", "ipex_check", ...
    # PR-3+: "HH4K", ...
    # PR-4+: Cisco aliases, ...
    # PR-6+: "SKY", "SKY_4G", ...
}

def get_model_spec(select_model: str) -> Optional[ModelSpec]:
    return MODEL_REGISTRY.get(select_model)

# Trong class Demo:
    def dispatch_vision(self, image_numpy, step=None, stepname=None):
        spec = get_model_spec(self.select_model)
        if spec is None:
            logging.error(f"Unknown select_model: {self.select_model}")
            self.myuihand.textbox.emit(f"Unknown model: {self.select_model}")
            self.resultcolor("Fail")
            self.wait_test = True
            return None
        fn = getattr(self, spec.pipeline_fn)
        if stepname is not None:
            return fn(image_numpy, stepname)
        if step is not None:
            return fn(image_numpy, step)
        return fn(image_numpy)

    def go_run2(self):
        while self.stop_program==False:
```

Rollback: xóa dataclass/registry/`dispatch_vision`; khôi phục gọi trực tiếp `show_image_*`.

---

### SENSOR-D02 · `go_run2` G829 — thay hardcode

**Đúng chỗ:** trong `go_run2`, nhánh `sensor_start`, sau `self.shan=shan` · **Sai:** sửa `go_run3`

```python
# TRƯỚC (analysis L825–830)
                time.sleep(5)
                ekko,shan=self.ekkoshan.get_image()
                self.shan=shan
                self.show_image_MR6500(self.shan)
                self.wait_test=True

# SAU — với guard đã ship, chỉ MR6500 tới đây; dispatch tương đương MR6500
                time.sleep(5)
                ekko,shan=self.ekkoshan.get_image()
                self.shan=shan
                spec = get_model_spec(self.select_model)
                if spec is None or not spec.sensor_capable:
                    logging.error(
                        f"Sensor dispatch rejected: model={self.select_model} "
                        f"sensor_capable={getattr(spec, 'sensor_capable', None)}"
                    )
                    self.resultcolor("Fail")
                    self.wait_test = True
                    return
                self.dispatch_vision(self.shan)
                self.wait_test = True
```

Rollback: khôi phục `self.show_image_MR6500(self.shan)`.

---

### SENSOR-D03 · `go_run3` nhánh MR6500 G839

**Đúng chỗ:** `go_run3` đầu hàm, `if self.select_model=="MR6500":` · **Sai:** `go_run2`

```python
# TRƯỚC (analysis L834–859, rút gọn)
    def go_run3(self):
        QApplication.processEvents()
        if self.select_model=="MR6500":
            logging.info("DUT FOUND,start camera")
            self.myuihand.textbox.emit("DUT FOUND,start camera")
            ekko, shan = self.ekkoshan.get_image()
            self.shan = shan
            self.show_image_MR6500(self.shan)
            self.wait_test=True

# SAU
    def go_run3(self):
        QApplication.processEvents()
        if self.select_model=="MR6500":
            logging.info("DUT FOUND,start camera")
            self.myuihand.textbox.emit("DUT FOUND,start camera")
            ekko, shan = self.ekkoshan.get_image()
            self.shan = shan
            self.dispatch_vision(self.shan)
            self.wait_test=True
```

Rollback: `dispatch_vision` → `show_image_MR6500`.

---

### SENSOR-D04 · mẫu SKY step loop G940 (1 trong 6 bước — lặp cho PR-6)

**Đúng chỗ:** trong nhánh SKY `go_run3`, sau `get_image` STEP N · **Sai:** đổi `QMessageBox.question` / logic `if self.stepN`

```python
# TRƯỚC
                self.show_image_SKY(self.shan1,"STEP 1")

# SAU
                self.dispatch_vision(self.shan1, stepname="STEP 1")
```

Lặp tương tự: `show_image_HH4K` → `dispatch_vision(shan, stepname="STEP N")`, `show_image_Button_check` → `dispatch_vision(shan)`, v.v. **Chỉ đổi lời gọi vision** — giữ orchestration `go_run3`.

---

### SENSOR-D05 · Cisco aliases (thêm vào `MODEL_REGISTRY` trong D01)

**Đúng chỗ:** dict `MODEL_REGISTRY` · **Sai:** 12 nhánh `elif` riêng trong `go_run3`

```python
# SAU — append vào build registry (sau MR6500)
CISCO_MODELS = (
    "C1000-8FP-E-2G-L", "C1000-8P-2G-L", "C1000-8T-2G-L",
    "C1200-8FP-2G", "C1200-8P-E-2G", "C1200-8T-E-2G",
    "C1300-8P-E-2G", "C1300-8T-E-2G", "C1000-8FP-2G-L",
    "C1000-8P-E-2G-L", "C1300-8FP-2G", "C1000-8T-E-2G-L",
)
_cisco_spec = ModelSpec("CISCO_FAMILY", "show_image_C1000_8FP_E_2G_L", 2, False, False)
for _name in CISCO_MODELS:
    MODEL_REGISTRY[_name] = _cisco_spec
```

`go_run3` giữ nguyên chuỗi `elif select_model == "C1000-…"` đến khi PR-4 collapse — hoặc thay entry bằng `get_model_spec` + step loop chung.

---

## Ma trận dispatch hiện tại (reference — không duplicate pipeline internals)

| Path | Analysis | Dispatcher | Ghi chú |
|------|----------|------------|---------|
| Sensor | `go_run2` L795–832 | Hardcode `show_image_MR6500` L829 | D02 fix |
| Manual | `go_run3` L834–1911 | Chuỗi `elif select_model` | D03–D06 từng PR |

Chi tiết từng pipeline: `docs/aoi-analysis/13`–`19`.

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-D01 | SENSOR-D01 | Registry deployed; model JSON `model` giả | Gọi `dispatch_vision` | Log unknown + Fail; không exception |
| T-D02 | SENSOR-D02 | Sensor MR6500 trên clone | Trigger DUT | Vision output giống baseline trước patch |
| T-D03 | SENSOR-D03 | Manual MR6500 | 1 Pass + 1 Fail cycle | Không regression pass/fail/count |
| T-D04 | SENSOR-D04 | Model đã migrate (từng PR) | Full step matrix model đó | Kết quả từng step giống baseline |
| T-D05 | SENSOR-D05 | 12 model Cisco alias | 1 cycle mỗi alias đại diện | Cùng handler; barcode match đúng |

## Test regression (mỗi PR)

| Area | Test |
|------|------|
| Manual MR6500 | Pass/fail không đổi (D03) |
| Sensor MR6500 | Trigger → vision giống trước (D02) |
| Guard + dispatcher | SKY + sensor vẫn **blocked** tại Start (D00) |
| Model đã migrate | Full step matrix từ `11_refactor_plan.md` §9 |
| Unknown model | `get_model_spec` None → `wait_test=True` (D06) |

---

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| SENSOR-D00 (guard) | Week 1 (file `01`) | Prerequisite |
| SENSOR-D01–D03 (PR-1) | Month 1+ / Month 2 | Refactor lời gọi MR6500 — cần regression baseline |
| SENSOR-D04 Button_check/ipex (PR-2) | Month 2 | Low-risk models trước |
| SENSOR-D04 HH4K (PR-3), D05 Cisco (PR-4) | Month 2–3 | Medium risk — full step matrix mỗi PR |
| SENSOR-D04 WP/Nanook (PR-5), SKY (PR-6) | Month 3 | High risk — SKY cuối cùng |

Không big-bang: mỗi PR một model, giữ guard sau khi dispatcher ship.

## Rollback theo stage

| Stage | Rollback |
|-------|----------|
| D02 `go_run2` | Khôi phục `show_image_MR6500(self.shan)` tại G829 |
| D03+ manual calls | Revert từng `dispatch_vision` → `show_image_*` |
| D01 registry | Xóa module/block; git restore elif chain |
| Mở rộng `sensor_capable` | Set `False`; dựa guard D00 |

**Giữ sensor guard** sau dispatcher — lớp an toàn rẻ.

---

## Ngoài scope Month 3 (ghi chú)

Sensor multi-step (SKY 6 bước qua trigger): Option D — sensor chỉ MR6500 — khuyến nghị đến khi có spec sản phẩm. Xem thảo luận Option A–D trong bản design cũ; không ship mở `sensor_capable` cho multi-step không test.

---

## Smoke (5 phút)

- [ ] D02 sensor MR6500 pass/fail giống baseline
- [ ] D03 manual MR6500 không regression
- [ ] D00 SKY+sensor vẫn blocked tại Start
- [ ] Unknown model không treo `wait_test` (D06)

## Ref

`01_sensor_mode_guard.md` · `01_wait_test_stall_fix.md` RT-001 · `08_model_dispatch.md` · `11_refactor_plan.md` §8
