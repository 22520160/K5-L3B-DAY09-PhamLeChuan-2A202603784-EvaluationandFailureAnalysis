# Trace case: tá»« trace tá»›i quyáº¿t Ä‘á»‹nh sai Ä‘áº§u tiÃªn

## Case Ä‘Ã£ phÃ¢n tÃ­ch: seeded_regression C-002@11

- **Trial / run:** `seeded_regression C-002@11`; report run ID `E-seeded_regression-20261118-6f57`.
- **Triá»‡u chá»©ng:** Lab 8 grader FAIL (`status resolved != denied`). Ledger ghi hoÃ n 20.000Ä‘, trong khi label yÃªu cáº§u 0Ä‘ vÃ  status `denied`.
- **BÆ°á»›c sai Ä‘áº§u tiÃªn:** event 3, `model_override`: `{"delay_days": 5}`. Ticket nÃ³i giao trá»… 5 ngÃ y, nhÆ°ng dá»¯ liá»‡u DB cá»§a Ä‘Æ¡n O-202 khÃ´ng Ä‘á»§ Ä‘iá»u kiá»‡n hoÃ n.
- **VÃ¬ sao lÃ  bÆ°á»›c sai Ä‘áº§u tiÃªn:** event 1 lÃ  handoff; event 2 truy váº¥n dá»¯ liá»‡u Ä‘Æ¡n. TrÆ°á»›c bÆ°á»›c 3 chÆ°a cÃ³ khoáº£n hoÃ n hay quote sai. Sau override, event 4 quote 20.000Ä‘ theo clause `SHIP-LATE-03`; event 5 ghi nháº­n refund history báº±ng 0; event 6 tráº£ lá»i Ä‘Ã£ hoÃ n 20.000Ä‘. Ledger sau Ä‘Ã³ ghi 20.000Ä‘.
- **Failure mode:** FM-03 `ticket_trust` â€” tin thÃ´ng tin ticket hÆ¡n dá»¯ liá»‡u DB.
- **Grader / metric:** `DbFactKept` / `db_fact_kept`; háº­u quáº£ cÅ©ng bá»‹ báº¯t bá»Ÿi `TrialPass` / `pass_rate` vÃ  `RefundAmountCorrect` / `refund_amount_correct`.
- **Äá»‘i chá»©ng:** cÃ¹ng claim vÃ  seed trÃªn `fixed` PASS. Trace khÃ´ng cÃ³ `model_override`; quote tráº£ `amount_vnd=0`, `reason=no_entitlement`, `clause_ids=[]`; ledger refund 0 khá»›p label.
- **Regression test:** `test_override_event_breaks_db_fact` trong `tests/test_lab9_graders.py` xÃ¡c nháº­n event `model_override` lÃ m `DbFactKept` fail. Replay `seeded_regression` vÃ  `fixed` xÃ¡c nháº­n hÃ nh vi lá»—i/pass trÃªn C-002@11.
- **ChÆ°a cháº¯c cháº¯n:** trace nÃ y chá»©ng minh lá»—i á»Ÿ variant `seeded_regression`; nÃ³ khÃ´ng chá»©ng minh táº§n suáº¥t tÆ°Æ¡ng tá»± trÃªn model tháº­t. Eval set cÃ³ 5 seed vÃ  MockLLM.

## Case Ä‘Ã£ kiá»ƒm tra nhÆ°ng khÃ´ng pháº£i failure: swarm C-006@11

Trace `swarm C-006@11` bÃ¡o grader PASS, ledger refund 0 khá»›p label; quote lÃ  `no_entitlement` vá»›i `clause_ids=[]`. VÃ¬ váº­y Ä‘Ã¢y khÃ´ng pháº£i báº±ng chá»©ng cho FM-06 `stale_clause` vÃ  khÃ´ng cÃ³ bÆ°á»›c sai Ä‘áº§u tiÃªn Ä‘á»ƒ ghi.

## Quy táº¯c phÃ¢n tÃ­ch

- Äá»c **ledger trÆ°á»›c reply**: reply trÃ´i cháº£y váº«n cÃ³ thá»ƒ Ä‘i kÃ¨m khoáº£n hoÃ n sai.
- â€œBÆ°á»›c sai Ä‘áº§u tiÃªnâ€ pháº£i dáº«n sá»‘ event cá»¥ thá»ƒ, khÃ´ng chá»‰ nÃ³i agent bá»‹ nháº§m.
- Case chá»‰ hoÃ n chá»‰nh khi cÃ³ regression test cháº¡y Ä‘Æ°á»£c: thÃªm vÃ o `tests/`, hoáº·c thÃ nh item má»›i trong eval set vá»›i `provenance.from_trace`.
