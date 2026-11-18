# Trace case: từ trace tới quyết định sai đầu tiên

## Case đã phân tích: seeded_regression C-002@11

- **Trial / run:** `seeded_regression C-002@11`; report run ID `E-seeded_regression-20261118-6f57`.
- **Triệu chứng:** Lab 8 grader FAIL (`status resolved != denied`). Ledger ghi hoàn 20.000đ, trong khi label yêu cầu 0đ và status `denied`.
- **Bước sai đầu tiên:** event 3, `model_override`: `{"delay_days": 5}`. Ticket nói giao trễ 5 ngày, nhưng dữ liệu DB của đơn O-202 không đủ điều kiện hoàn.
- **Vì sao là bước sai đầu tiên:** event 1 là handoff; event 2 truy vấn dữ liệu đơn. Trước bước 3 chưa có khoản hoàn hay quote sai. Sau override, event 4 quote 20.000đ theo clause `SHIP-LATE-03`; event 5 ghi nhận refund history bằng 0; event 6 trả lời đã hoàn 20.000đ. Ledger sau đó ghi 20.000đ.
- **Failure mode:** FM-03 `ticket_trust` — tin thông tin ticket hơn dữ liệu DB.
- **Grader / metric:** `DbFactKept` / `db_fact_kept`; hậu quả cũng bị bắt bởi `TrialPass` / `pass_rate` và `RefundAmountCorrect` / `refund_amount_correct`.
- **Đối chứng:** cùng claim và seed trên `fixed` PASS. Trace không có `model_override`; quote trả `amount_vnd=0`, `reason=no_entitlement`, `clause_ids=[]`; ledger refund 0 khớp label.
- **Regression test:** `test_override_event_breaks_db_fact` trong `tests/test_lab9_graders.py` xác nhận event `model_override` làm `DbFactKept` fail. Replay `seeded_regression` và `fixed` xác nhận hành vi lỗi/pass trên C-002@11.
- **Chưa chắc chắn:** trace này chứng minh lỗi ở variant `seeded_regression`; nó không chứng minh tần suất tương tự trên model thật. Eval set có 5 seed và MockLLM.

## Case đã kiểm tra nhưng không phải failure: swarm C-006@11

Trace `swarm C-006@11` báo grader PASS, ledger refund 0 khớp label; quote là `no_entitlement` với `clause_ids=[]`. Vì vậy đây không phải bằng chứng cho FM-06 `stale_clause` và không có bước sai đầu tiên để ghi.

## Quy tắc phân tích

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm khoản hoàn sai.
- “Bước sai đầu tiên” phải dẫn số event cụ thể, không chỉ nói agent bị nhầm.
- Case chỉ hoàn chỉnh khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
