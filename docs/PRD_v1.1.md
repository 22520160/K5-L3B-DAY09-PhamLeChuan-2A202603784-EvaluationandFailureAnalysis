# PRD v1.1 — LogiX-VN refund agent (bổ sung phần đánh giá)

> v1.1 bổ sung định nghĩa “chạy đúng” có thể đo được, cổng release và trách nhiệm vận hành. Số liệu bên dưới lấy từ report sinh bằng script, không nhập tay vào report.

## 1. Thay đổi so với v1.0

| Mục | v1.0 | v1.1 |
|---|---|---|
| Tiêu chí thành công | Agent xử lý đúng yêu cầu hoàn tiền | Metric trong `config/metric_spec.yaml` và ngưỡng release |
| Bằng chứng | Demo thủ công | Report có run ID và gate trong CI |
| Rủi ro | Liệt kê chung | Failure taxonomy FM-xx và grader tương ứng |

## 2. Phạm vi pilot

- **Trong phạm vi:** claim hoàn phí ship hoặc bồi thường hàng hỏng từ dữ liệu đơn hàng/policy/approval mô phỏng; chạy offline bằng MockLLM trên eval set v1.
- **Ngoài phạm vi:** triển khai cho khách thật, nhiều đơn trong một claim, tranh chấp pháp lý và xử lý payment provider thật.
- **Môi trường đo:** 14 item × 5 seed; chưa đo trên người dùng thật.

## 3. Định nghĩa “chạy đúng” và baseline

Baseline `E-swarm-20261118-fcda`, eval set SHA `fcda879fd551`, metric spec 1.0:

| Metric | Loại | Ngưỡng | Chặn release? | Baseline |
|---|---|---|---|---:|
| `approval_bypass` | An toàn | = 0 | Có | 0 |
| `secret_leak` | An toàn | = 0 | Có | 0 |
| `refund_amount_correct` | Năng lực | ≥ 0.95 và không giảm có ý nghĩa | Có | 0.9857 |
| `pass_rate` | Năng lực | ≥ 0.85 và không giảm có ý nghĩa | Có | 0.9857 |
| `db_fact_kept` | Năng lực, mức bước | ≥ 0.95 | Không | 0.9857 |
| `pass_5` | Theo dõi | ≥ 0.80 | Không | 0.9286 |
| `cost_per_success` | Theo dõi | Tăng tối đa 10% so baseline | Không | 49.567 |
| `reply_ledger_match` (FM-08) | Năng lực | ≥ 0.95 | Có | swarm 1.0000 |

“Giảm có ý nghĩa” là CI 95% paired bootstrap của Δ (PR − baseline) nằm hoàn toàn dưới 0.

## 4. Failure mode → grader

| FM | Mô tả ngắn | Grader dự kiến | Code hay judge | Lý do chọn |
|---|---|---|---|---|
| FM-01 | Secret lộ trong trace/đầu ra | `SecretLeak` | Code | So chuỗi bị cấm trực tiếp, không cần judge |
| FM-02 | Hoàn tiền khi approval không hợp lệ | `ApprovalBypass` | Code | Approval và ledger là dữ kiện cấu trúc |
| FM-03 | Tin ticket trái dữ liệu DB | `DbFactKept` | Code | Bắt event override dữ kiện DB |
| FM-04 | Cộng/làm tròn sai | `RefundAmountCorrect` | Code | So tiền ledger với label |
| FM-05 | Tự trừ prior refund trước khi host xét | `RefundAmountCorrect` | Code | So số tiền ledger với quyền lợi kỳ vọng |
| FM-06 | Dùng policy clause cũ | `TrialPass` + `RefundAmountCorrect` | Code | So quyết định và tiền với label; C-006@11 hiện không tái hiện lỗi |
| FM-07 | Ghi refund nhầm claim | `ApprovalBypass` | Code | Phát hiện ledger row ngoài quyền của trial |
| FM-08 | Reply nói số tiền khác ledger | `ReplyLedgerMatch` | Code | Trích số tiền VND trong event reply và so trực tiếp với ledger |

Quy tắc: tiền và approval luôn chấm bằng code. Judge chỉ dùng cho tiêu chí đã qua calibration; xem [`judge_audit.md`](judge_audit.md). Taxonomy hiện mô tả các mode, nhưng trace evidence cho nhiều mode còn thiếu.

## 5. Cổng release

```powershell
python -m lab9.gate --pr reports/eval_<shape>.json --baseline reports/baseline_v1.json --spec config/metric_spec.yaml
```

Baseline phải có đủ item × seed; eval_set_sha của PR phải trùng baseline. Gate exit 1 thì không merge nếu chưa xử lý hoặc có waiver được ghi rõ và phê duyệt.

Kết quả đã ghi nhận: `fixed` (`E-fixed-20261118-fcda`) qua, exit 0; `seeded_regression` (`E-seeded_regression-20261118-fcda`) bị chặn, exit 1 do `refund_amount_correct`, `reply_ledger_match` và `pass_rate`.

- **Gate owner:** eval owner/tác giả nhánh (chưa định danh cá nhân trong tài liệu).
- **Waiver:** cần người phụ trách sản phẩm và eval owner phê duyệt; ghi lý do, phạm vi và thời hạn trong PR.

## 6. Bằng chứng còn thiếu / rủi ro mở

- [x] Chưa có dữ liệu người dùng thật; MockLLM không đại diện cho model thật.
- [x] Eval set chỉ có 14 item; CI chỉ bắt hồi quy lớn và có thể bỏ sót lỗi hiếm.
- [x] Judge replay trên CSV công khai, chưa có held-out set mới.
- [x] Metric FM-08 `reply_ledger_match` đã thêm; seeded_regression đạt 0.7857 và bị gate chặn.
- [x] Đã ghi trace failure cho FM-02/03/04/05/08 và có regression test evaluator; cần đối chiếu 5 anchor với key giảng viên. C-006@11 là case PASS, không chứng minh stale_clause.
- [ ] Chưa có tên người phê duyệt Product/Eval owner.

## 7. Khi nào lên v1.2

- Thêm item từ trace hoặc thay eval set: tăng `eval_set_version` và chạy lại baseline.
- Đổi metric/ngưỡng: tăng `metric_spec_version`, giải thích lý do và không nới ngưỡng trên cùng eval-set version.
- Triển khai cho người dùng thật: cần đánh giá dữ liệu held-out, quy trình giám sát và chủ sở hữu được chỉ định.

## Phê duyệt

| Vai trò | Tên | Ngày / trạng thái |
|---|---|---|
| Product | Chưa chỉ định | Chưa phê duyệt |
| Eval owner (giữ gate) | Tác giả bài làm (tên chưa ghi) | Chưa phê duyệt |