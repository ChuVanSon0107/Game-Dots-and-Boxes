# Tài liệu logic AI Bot - Dots and Boxes

Tài liệu này giải thích logic hiện tại của AI trong file `ai.py`. Mục tiêu là để thành viên trong nhóm có thể đọc nhanh, hiểu đúng ý tưởng thuật toán và dùng làm nền tảng khi thuyết trình.

## 1. Mục tiêu của AI

AI được thiết kế để chơi Dots and Boxes trên nhiều kích thước bàn, từ 3x3, 4x4 đến các bàn lớn hơn như 6x6, 7x7, 8x8. Mục tiêu trực tiếp là chọn một nước đi hợp lệ giúp AI tối đa hóa hiệu số điểm cuối trận.

Tuy nhiên, Dots and Boxes không thể chơi tốt nếu chỉ nhìn điểm trước mắt. Ở cuối ván, người chơi mạnh phải biết giữ quyền kiểm soát chuỗi. Vì vậy AI hiện tại theo đuổi ba mục tiêu chiến thuật:

- Không tự tạo ô 3 cạnh cho đối thủ nếu vẫn còn nước an toàn.
- Khi buộc phải mở chuỗi, chọn nước mở ít thiệt hại nhất.
- Khi đang ăn chuỗi, biết lúc nào nên ăn hết và lúc nào nên hy sinh 2 hoặc 4 ô cuối để ép đối thủ mở chuỗi tiếp theo.

Các kỹ thuật chính đang được dùng:

- Minimax kết hợp Alpha-Beta pruning.
- Iterative Deepening với giới hạn thời gian mặc định `4.0` giây.
- Transposition Table để cache trạng thái đã tính.
- Candidate pruning để giảm số nhánh trên bàn lớn.
- Chain theory, parity và hard-hearted handout trong endgame.
- Forcing-move ordering để so sánh trực tiếp giữa greedy capture và sacrifice.

Toàn bộ logic AI nằm trong `ai.py`. UI chỉ gọi API công khai `get_best_move()`.

## 2. Dữ liệu trạng thái AI sử dụng

AI làm việc trên đối tượng `GameState`, gồm các trường quan trọng:

| Trường | Ý nghĩa |
|---|---|
| `rows`, `cols` | Kích thước bàn cờ theo số ô |
| `h_edges` | Ma trận cạnh ngang đã vẽ |
| `v_edges` | Ma trận cạnh dọc đã vẽ |
| `boxes` | Chủ sở hữu từng ô, `0` là chưa ai ăn |
| `edges_count` | Số cạnh đã vẽ quanh mỗi ô |
| `current_player` | Người đang có lượt |
| `score_player1`, `score_player2` | Điểm hiện tại |
| `moves_remaining` | Số cạnh còn lại |

Hai hàm quan trọng trong `rules.py` là:

- `apply_move(state, move)`: thử một nước đi, cập nhật cạnh, điểm, lượt chơi và trả về `undo_info`.
- `undo_move(state, move, undo_info)`: hoàn tác chính xác nước vừa thử.

Minimax dùng cặp hàm này liên tục. AI không copy state ở mỗi node, mà apply rồi undo để tiết kiệm thời gian và bộ nhớ.

## 3. Phân loại nước đi

AI không xem mọi cạnh hợp lệ là ngang nhau. Mỗi nước đi được phân loại theo tác động lên các ô xung quanh.

### 3.1. Capture move

Capture move là nước đi hoàn thành ít nhất một ô. Hàm kiểm tra:

```python
would_complete_box(state, move)
```

Nếu kết quả lớn hơn `0`, nước đi đó ăn được ô. Người ăn ô sẽ được cộng điểm và giữ lượt, nên capture move thường tạo ra các chuỗi ăn liên tiếp.

### 3.2. Safe move

Safe move là nước đi không tạo ô 3 cạnh cho đối thủ. Hàm kiểm tra:

```python
would_create_third_edge(state, move)
```

Nếu kết quả bằng `0`, nước đi được xem là an toàn. Khi không có forcing move, AI ưu tiên chỉ xét safe move. Đây là lớp phòng thủ quan trọng giúp AI không mở điểm miễn phí cho đối thủ.

### 3.3. Risky move

Risky move là nước tạo ra ít nhất một ô 3 cạnh. Nếu đối thủ chơi tốt, họ có thể ăn ô đó và tiếp tục ăn theo chuỗi.

Risky move chỉ được xét khi không còn safe move. Khi phải mở chuỗi, AI sắp xếp risky move theo mức thiệt hại ước lượng bằng `_estimate_opened_chain_loss()`.

### 3.4. Sacrifice / Hard-hearted handout

Sacrifice là nước không ăn ô ngay, nhưng cố ý để lại một phần nhỏ của chuỗi cho đối thủ:

- Open chain: thường nhường 2 ô cuối.
- Loop hoặc cấu trúc đóng: thường nhường 4 ô cuối.

Mục đích không phải là tặng điểm vô cớ. Mục đích là để đối thủ ăn phần nhỏ đó xong phải mở chuỗi tiếp theo, còn AI giữ quyền kiểm soát endgame.

## 4. Candidate pruning theo pha game

Hàm `_order_moves(state, moves, tt_best_key=None)` vừa sắp xếp nước đi, vừa lọc bớt số nhánh search.

Thứ tự xử lý hiện tại:

1. Nếu có capture move, ưu tiên nhóm capture.
2. Nếu không có capture nhưng còn safe move, chỉ giữ safe move.
3. Nếu không còn safe move, mới xét risky move.
4. Danh sách cuối cùng được giới hạn bởi `_candidate_limit()`.

Giới hạn candidate hiện tại:

| Điều kiện | Số candidate tối đa |
|---|---:|
| `rows * cols <= 16` | 32 |
| `rows * cols <= 36` | 24 |
| Lớn hơn | 18 |

Lý do cần pruning: bàn lớn có rất nhiều cạnh hợp lệ. Nếu đưa tất cả vào minimax, AI sẽ không kịp trả nước trong 4 giây.

## 5. Chấm điểm safe move và risky move

### 5.1. Safe move score

Safe move được chấm bằng `_safe_move_score()`. Hàm này bắt đầu bằng `_safe_pressure_score()`, sau đó cộng thêm các tiêu chí phụ.

Ý tưởng của `_safe_pressure_score()`:

- Thử đi safe move.
- Đếm số safe move đối thủ còn lại.
- Nếu đối thủ hết safe move và không có forcing move, ước lượng thiệt hại đối thủ buộc phải mở chuỗi.
- Xem lợi thế chain sau nước đi.

Vì tuple score được sort tăng dần, AI ưu tiên safe move làm đối thủ còn ít safe reply hơn. Đây là cách AI "dồn" đối thủ tới thời điểm phải mở chuỗi.

Các tiêu chí phụ trong `_safe_move_score()`:

- Hạn chế tạo thêm ô 2 cạnh.
- Ưu tiên nước tác động ít ô hơn khi cần giữ thế ổn định.
- Ưu tiên nước chạm ô trống khi có lợi.
- Dùng khoảng cách tới trung tâm và `_move_key()` để thứ tự ổn định.

### 5.2. Risky move score

Risky move được chấm bằng `_risky_move_score()`.

Các tiêu chí chính:

- `_estimate_opened_chain_loss()`: nếu đi nước này, chuỗi lớn nhất đối thủ có thể bắt đầu ăn là bao nhiêu.
- `_post_move_chain_advantage()`: lợi thế chain sau nước đi.
- Số ô bị tạo thành 3 cạnh.
- Khoảng cách tới trung tâm và `_move_key()`.

Mục tiêu: nếu buộc phải mở chuỗi, AI chọn nước mở ít thiệt hại nhất.

## 6. Forcing moves

Forcing move là nhóm nước đi cần xử lý ưu tiên khi có ô 3 cạnh hoặc có chuỗi đang mở.

Hàm chính:

```python
get_forcing_moves(state)
```

Quy trình:

1. Gọi `_find_capturable_chains()` để tìm các chuỗi có thể ăn liên tiếp.
2. Với mỗi chain, thêm nước ăn ô đầu chain bằng `_get_missing_edge()`.
3. Gọi `_get_sacrifice_moves()` để thêm các nước handout hợp lệ.
4. Fallback: quét toàn board, nếu còn ô 3 cạnh chưa được thêm thì thêm nước ăn ô đó.

Điểm quan trọng: forcing move không chỉ là "ăn ngay". Nó gồm cả greedy capture và sacrifice. Sau khi sinh ra, các nước này được sắp xếp bằng `_order_forcing_moves()` để AI chọn đúng giữa ăn hết và hy sinh.

## 7. Logic sacrifice hiện tại

Đây là phần quan trọng nhất của phiên bản AI hiện tại.

### 7.1. Vấn đề cũ

Nếu chỉ sinh nước sacrifice mà không chấm đúng, AI vẫn có thể chọn greedy capture vì điểm tức thời cao hơn. Khi đó AI ăn hết chuỗi, vẫn giữ lượt, hết safe move và bị buộc phải tự mở chuỗi tiếp theo cho đối thủ.

### 7.2. Cách sinh sacrifice mới

Hàm `_get_sacrifice_moves(state, chain)` không còn dựa cứng vào vài pattern hình học như "chain đúng 2 ô" hoặc "loop đúng 4 ô". Thay vào đó, nó kiểm tra theo component:

1. `_handout_size_for_component()` xác định cần nhường 2 ô hay 4 ô.
2. Duyệt các legal move.
3. Loại move ăn điểm ngay, vì sacrifice đúng nghĩa không ăn ô ngay tại nước đó.
4. `_component_touched_by_move()` kiểm tra move có chạm component đang xét không.
5. `_capturable_boxes_after_move()` thử move và xem phần còn lại có trở thành capturable cho đối thủ không.
6. Chỉ nhận move nếu số ô capturable sau đó đúng bằng handout size.

Nói ngắn gọn: AI không hỏi "hình này có giống mẫu cũ không", mà hỏi "sau nước này có thật sự để lại đúng phần handout cho đối thủ không".

### 7.3. Cách chọn giữa greedy và sacrifice

Các forcing move được chấm bằng `_resolved_forcing_score()`.

Quy trình chấm:

1. Kiểm tra move có phải sacrifice bằng `_is_sacrifice_move()`.
2. Apply move đang xét.
3. Gọi `_play_greedy_forced_captures()` để mô phỏng các capture bắt buộc tiếp theo.
4. Chấm trạng thái bằng `evaluate()`.
5. Cộng thêm `_control_after_forced_resolution()` để xem sau khi chuỗi được resolve, ai đang bị buộc mở chuỗi.
6. Nếu move là handout và sau đó đối thủ phải đi, cộng thêm bonus kiểm soát.
7. Undo toàn bộ mô phỏng.

Ý nghĩa chiến thuật:

- Nếu greedy capture làm AI phải tự mở chuỗi kế tiếp, move đó bị phạt.
- Nếu sacrifice làm đối thủ ăn phần nhỏ rồi phải mở chuỗi kế tiếp, move đó được thưởng.
- Nếu đó là chuỗi cuối cùng, AI không hy sinh vô ích mà có xu hướng ăn hết.

## 8. Phân tích chain và loop

AI có hai lớp phân tích chuỗi.

### 8.1. `_find_capturable_chains()`

Hàm này dùng khi đã có ô 3 cạnh. Nó tìm các chuỗi đang có thể ăn liên tiếp.

Điều kiện lan chuỗi:

- Ô kế bên chưa bị ăn.
- Chia sẻ cạnh chưa vẽ với ô hiện tại.
- `edges_count >= 2`, vì ô đó có thể thành 3 cạnh sau khi ô trước bị ăn.

Hàm này phục vụ `get_forcing_moves()`.

### 8.2. `_analyze_chains_and_loops()`

Hàm này dùng cho heuristic endgame. Nó phân tích toàn board thành các component gồm ô chưa bị ăn, có `edges_count >= 2`, nối nhau qua cạnh chưa vẽ.

Sau khi có component:

- Nếu mọi ô trong component có đúng 2 neighbor và độ dài >= 4, đó là closed loop.
- Nếu không phải loop và độ dài >= 3, đó là open chain.

Kết quả trả về:

```python
(open_chains, closed_loops)
```

Trong đó mỗi phần tử là độ dài của chain hoặc loop.

## 9. Đánh giá chain control bằng `_evaluate_chains()`

Endgame của Dots and Boxes thường được quyết định bởi quyền kiểm soát chuỗi. Hàm `_evaluate_chains()` ước lượng lợi thế đó.

AI chuyển các cấu trúc thành region:

- Open chain: chi phí sacrifice là 2 ô.
- Closed loop: chi phí sacrifice là 4 ô.

Các region được sắp xếp theo `len - sac`, tức lợi ích ròng khi controller giữ quyền điều khiển.

Mô phỏng điểm:

- Ở các region đầu, controller ăn `len - sac`, victim nhận `sac`.
- Ở region cuối cùng, controller ăn trọn `len`, không cần sacrifice.

Sau đó AI tính:

```text
net_chain_score = controller_points - victim_points
```

rồi đổi dấu về góc nhìn của `ai_player`.

Quy tắc parity trong code:

- Nếu tổng số region là chẵn, người đang có lượt được xem là có cơ hội nắm control.
- Nếu tổng số region là lẻ, control nghiêng về người còn lại.

Đây là heuristic, không phải solver toán học đầy đủ, nhưng giúp AI xử lý endgame tốt hơn nhiều so với chỉ nhìn điểm hiện tại.

## 10. Hàm heuristic `evaluate()`

Khi minimax chạm giới hạn độ sâu và không còn forcing move, AI dùng `evaluate()`.

Công thức tổng quát:

```text
score = score_diff * 100
      + cap_score
      + chain_score * chain_weight
      + mobility_score
      - boxes_2 * 3
```

Ý nghĩa từng thành phần:

| Thành phần | Vai trò |
|---|---|
| `score_diff * 100` | Ưu tiên điểm thật của AI so với đối thủ |
| `cap_score` | Thưởng/phạt cơ hội ăn ô 3 cạnh theo lượt hiện tại |
| `chain_score * chain_weight` | Đánh giá quyền kiểm soát chain/loop |
| `mobility_score` | Đánh giá bên nào còn safe move hoặc bị buộc mở chuỗi |
| `- boxes_2 * 3` | Phạt nhẹ việc có nhiều ô 2 cạnh trên board |

`chain_weight` thay đổi theo giai đoạn:

| Điều kiện | `chain_weight` | Ý nghĩa |
|---|---:|---|
| `boxes_safe > 2` | 1 | Midgame, chain theory chỉ là tín hiệu phụ |
| `boxes_safe > 0` | 5 | Cận endgame, bắt đầu coi trọng parity |
| `boxes_safe == 0` | 15 | Endgame, chain control là yếu tố chính |

## 11. Minimax và Alpha-Beta

Hàm chính:

```python
minimax(state, depth, alpha, beta, ai_player)
```

Các bước:

1. Kiểm tra deadline bằng `_time_up()`.
2. Nếu game kết thúc, trả về hiệu số điểm nhân `10000`.
3. Sinh forcing moves bằng `get_forcing_moves()`.
4. Nếu `depth <= 0` và không có forcing move, dùng `evaluate()`.
5. Tra cứu Transposition Table.
6. Xác định node max/min bằng `state.current_player == ai_player`.
7. Nếu có forcing move, sắp xếp bằng `_order_forcing_moves()`.
8. Nếu không có forcing move, lấy legal moves rồi sắp bằng `_order_moves()`.
9. Thử từng move bằng `apply_move()`.
10. Nếu người vừa đi ăn ô và được giữ lượt, depth không giảm; nếu đổi lượt, depth giảm 1.
11. Gọi đệ quy minimax.
12. Hoàn tác bằng `undo_move()`.
13. Cập nhật alpha/beta và cắt nhánh khi `alpha >= beta`.
14. Lưu kết quả vào Transposition Table nếu không timeout.

Điểm đặc biệt của Dots and Boxes: không thể dùng độ sâu chẵn/lẻ để xác định MAX/MIN, vì người chơi có thể được đi tiếp sau khi ăn ô.

## 12. Transposition Table

`_tt` là dictionary cache kết quả search.

Key được tạo bởi `_state_key()`:

```python
(h_edges, v_edges, boxes, current_player, score_player1, score_player2)
```

Việc đưa `boxes` và điểm số vào key là cần thiết, vì cùng một tập cạnh có thể dẫn tới điểm hoặc chủ sở hữu ô khác nhau tùy thứ tự ăn ô.

Mỗi entry lưu:

```python
(depth, score, flag, best_move_key)
```

`flag` có ba loại:

| Flag | Ý nghĩa |
|---|---|
| `EXACT` | Điểm chính xác ở depth đó |
| `LOWERBOUND` | Điểm thực tế >= score |
| `UPPERBOUND` | Điểm thực tế <= score |

## 13. Iterative Deepening và deadline

`get_best_move()` không search thẳng một depth lớn. Nó chạy từ depth 1 đến `max_depth`.

Mặc định:

```python
time_limit = 4.0
```

Deadline nội bộ dùng:

- `_search_deadline`
- `_search_timed_out`
- `_time_up()`

Sau mỗi vòng depth:

- Nếu tìm được move mới, cập nhật `best_move`.
- Nếu score rất lớn (`abs(score) >= 9000`), dừng sớm.
- Nếu ước lượng vòng sau vượt `time_limit`, dừng.
- Nếu minimax timeout bên trong, bỏ vòng chưa hoàn tất và trả best move của vòng trước.

## 14. Adaptive depth

Nếu không truyền `base_depth`, AI chọn theo số ô:

| Số ô | Base depth |
|---:|---:|
| `<= 9` | 8 |
| `<= 16` | 6 |
| `<= 25` | 5 |
| `<= 36` | 4 |
| Lớn hơn | 3 |

Sau đó `_get_adaptive_depth()` tăng depth khi game gần kết thúc:

| `moves_remaining` | Depth tối đa |
|---:|---:|
| `<= 10` | `min(remaining, 22)` |
| `<= 16` | `base_depth + 4` |
| `<= 22` | `base_depth + 2` |
| `<= 30` | `base_depth + 1` |
| Lớn hơn | `base_depth` |

Ý tưởng: đầu game cần pruning mạnh; cuối game còn ít cạnh hơn nên có thể search sâu hơn.

## 15. Tóm tắt để thuyết trình

Có thể trình bày AI theo 5 tầng:

1. **Luật chơi và state**: dùng `GameState`, `apply_move()`, `undo_move()`.
2. **Lọc nước đi**: ưu tiên capture, safe move, chỉ mở risky khi bắt buộc.
3. **Tìm kiếm**: minimax + alpha-beta + transposition table.
4. **Endgame**: phân tích chain, loop, parity.
5. **Sacrifice control**: so sánh greedy capture với hard-hearted handout bằng `_resolved_forcing_score()`.

Thông điệp chính:

> AI không chỉ tìm nước ăn điểm ngay. AI cố giữ quyền kiểm soát chuỗi: tránh mở chuỗi khi còn safe move, ép đối thủ hết safe move, và hy sinh 2/4 ô cuối khi điều đó buộc đối thủ phải mở chuỗi tiếp theo.
