# Judge audit

Chạy replay offline, không cần API key:

```powershell
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

## Kết quả hiệu chuẩn

| Tiêu chí | n | κ | Precision | Recall | Đạt floors (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---:|---:|---:|---:|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng có kiểm tra: đạt ngưỡng; audit cho thấy judge bỏ sót sắc thái xưng hô/giọng điệu và đôi lúc quá khắt khe với câu ngắn hoặc từ “refund”. |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | Loại: recall thấp; bỏ sót nhiều câu báo sai số tiền hoàn. |

Tỷ lệ FAIL quan sát và hiệu chỉnh Rogan–Gladen: `tone_ok` 0.280 → 0.300; `helpful` 0.090 → 0.300.

## 10 case bất đồng đã audit thủ công

Human label được dùng làm nhãn tham chiếu trong bộ replay. Với các case helpful, ghi chú CSV nêu rõ số tiền trong reply khác ledger.

| # | Tiêu chí / case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---:|---|---|---|---|---|
| 1 | tone_ok / H-008 | PASS | FAIL | Người | “Em… nha” quá suồng sã với khách; judge nhầm là thân thiện. |
| 2 | tone_ok / H-017 | PASS | FAIL | Người | Dùng “bạn” với khách lớn tuổi; judge nhầm là thân thiện. |
| 3 | tone_ok / H-029 | PASS | FAIL | Người | “Không cần nhắn thêm” mang giọng ra lệnh; judge chỉ chú ý lời mở đầu lịch sự. |
| 4 | tone_ok / H-042 | FAIL | PASS | Người | Câu ngắn nhưng đủ ý và lịch sự; judge phạt vì cho rằng thiếu lời xin lỗi. |
| 5 | tone_ok / H-051 | FAIL | PASS | Người | “Refund” là từ được CS LogiX cho phép; judge phạt quá mức vì dùng tiếng Anh. |
| 6 | helpful / HL-015 | PASS | FAIL | Người | Reply báo 55.000đ, ledger ghi 40.000đ. |
| 7 | helpful / HL-016 | PASS | FAIL | Người | Reply báo 55.000đ cho O-404, ledger ghi 35.000đ; lời xin lỗi dài không sửa được thông tin sai. |
| 8 | helpful / HL-020 | PASS | FAIL | Người | Reply báo 90.000đ, ledger ghi 120.000đ. |
| 9 | helpful / HL-028 | PASS | FAIL | Người | Reply báo 50.000đ cho O-677, ledger ghi 35.000đ. |
| 10 | helpful / HL-035 | PASS | FAIL | Người | Reply báo 50.000đ cho O-303, ledger ghi 35.000đ. |


## Điều chỉnh rubric từ audit

- **Tone:** chấm theo quy tắc xưng hô và giọng điệu có ví dụ rõ; không coi “Dạ” là đủ để vượt qua câu mang tính ra lệnh, và không tự động phạt câu ngắn hoặc từ “refund” được LogiX cho phép. Không bắt buộc câu xin lỗi nếu câu trả lời lịch sự, đủ thông tin và không gây hiểu nhầm.
- **Helpful:** kiểm tra số tiền và mã đơn với ledger làm điều kiện bắt buộc trước khi xét độ lịch sự/đầy đủ. Lời xin lỗi dài không thể bù cho số tiền hoàn sai. Judge helpful hiện recall 0.300 nên vẫn bị loại khỏi gate; kiểm tra tiền dùng code grader.
## Kết luận

- **Helpful bị loại** vì recall 0.300 thấp hơn floor 0.700. Năm case audit minh họa một lỗi nghiêm trọng: judge bỏ qua số tiền trong reply không khớp ledger, dù câu trả lời có vẻ lịch sự và hữu ích.
- **Tone đạt floors** trên tập replay này, nhưng nên dùng có kiểm tra. Audit cho thấy judge chưa nhất quán với cách xưng hô, giọng ra lệnh, câu trả lời ngắn và từ tiếng Anh được cho phép.
- **Giới hạn:** kết quả chỉ phản ánh hai bộ replay công khai. Cần audit trên dữ liệu mới có nhãn người để xác nhận khả năng tổng quát hóa; các kết luận “ai đúng” ở đây dựa trên nhãn human và ghi chú được cung cấp trong CSV.