# Tài liệu mô tả logic AI Bot - Dots and Boxes

## 1. Mục tiêu của AI

AI trong project được thiết kế để chơi Dots and Boxes trên nhiều kích thước bàn cờ, từ bàn nhỏ như 3x3, 4x4 đến bàn lớn hơn như 6x6, 7x7. Mục tiêu chính là chọn nước đi giúp AI tối đa hóa hiệu số điểm cuối trận, đồng thời tránh tự mở chuỗi cho đối thủ khi vẫn còn nước an toàn.

Logic hiện tại kết hợp các nhóm kỹ thuật chính:

- Minimax kết hợp cắt tỉa Alpha-Beta.
- Candidate pruning: lọc nước đi theo từng pha game trước khi đưa vào minimax.
- Chain theory: nhận diện chain, loop, double-cross và parity ở cuối game.
- Time management: iterative deepening kết hợp deadline nội bộ để tránh làm đơ giao diện.

Toàn bộ logic AI nằm trong `ai.py`. UI chỉ gọi API công khai `get_best_move()`.

## 2. Dữ liệu trạng thái AI sử dụng

AI làm việc trên đối tượng `GameState`, gồm các trường quan trọng:

- `h_edges`: ma trận các cạnh ngang.
- `v_edges`: ma trận các cạnh dọc.
- `boxes`: ma trận chủ sở hữu từng ô. Giá trị `0` là chưa ai ăn, `1` và `2` là người chơi.
- `edges_count`: số cạnh đã vẽ quanh mỗi ô.
- `current_player`: người đang có lượt.
- `score_player1`, `score_player2`: điểm hiện tại.
- `moves_remaining`: số cạnh còn lại.

Hai hàm `apply_move()` và `undo_move()` trong `rules.py` là nền tảng của minimax. AI thử một nước đi bằng `apply_move()`, đi sâu xuống nhánh con, sau đó gọi `undo_move()` để trả board về trạng thái ban đầu.

## 3. Phân loại nước đi

AI không xem mọi cạnh hợp lệ là như nhau. Mỗi nước đi được phân loại theo ảnh hưởng của nó lên các ô xung quanh.

### 3.1. Capture move

Capture move là nước đi hoàn thành một hoặc nhiều ô. Hàm `would_complete_box(state, move)` trả về số ô sẽ được ăn nếu đi nước này.

Capture move rất quan trọng vì người đi:

- Được cộng điểm.
- Được giữ lượt.
- Có thể kích hoạt chuỗi ăn liên tiếp.

### 3.2. Safe move

Safe move là nước đi không tạo bất kỳ ô nào có đúng 3 cạnh cho đối thủ. Hàm `would_create_third_edge(state, move)` trả về số ô sẽ bị đẩy lên 3 cạnh.

Nếu còn safe move, AI ưu tiên chỉ search trên safe move. Đây là điểm quan trọng giúp AI mạnh hơn trên bàn lớn: không tự mở cơ hội ăn điểm cho đối thủ khi vẫn còn đường an toàn.

### 3.3. Risky move

Risky move là nước đi tạo ra ít nhất một ô 3 cạnh. Nếu đối thủ chơi tốt, họ có thể ăn ô đó và tiếp tục ăn theo chuỗi.

Risky move chỉ được xét khi không còn safe move. Khi buộc phải mở chuỗi, AI sắp xếp risky move theo mức thiệt hại ước lượng bằng `_estimate_opened_chain_loss()`.

## 4. Candidate pruning theo pha game

Hàm `_order_moves(state, moves, tt_best_key=None)` vừa sắp xếp nước đi, vừa lọc bớt số nhánh search.

Thứ tự xử lý:

1. Nếu có capture move, ưu tiên nhóm capture move.
2. Nếu không có capture move nhưng còn safe move, chỉ giữ safe move.
3. Nếu không còn safe move, mới xét risky move.
4. Danh sách cuối cùng được giới hạn bởi `_candidate_limit()` để bàn 6x6, 7x7 không bị nổ nhánh.

`_candidate_limit()` đặt giới hạn theo số ô:

| Điều kiện | Số candidate tối đa |
|---|---:|
| `rows * cols <= 16` | 28 |
| `rows * cols <= 36` | 18 |
| Lớn hơn | 14 |

Lý do cần giới hạn là bàn lớn có rất nhiều cạnh hợp lệ. Nếu đưa tất cả vào minimax, branching factor quá lớn và AI sẽ không kịp trả lời trong thời gian cho phép.

## 5. Cách chấm điểm safe move và risky move

### 5.1. `_safe_move_score()`

Safe move được chấm điểm theo các tiêu chí:

- Hạn chế tạo thêm ô có 2 cạnh, vì ô 2 cạnh dễ trở thành vật liệu tạo chain.
- Ưu tiên nước tác động ít ô hơn khi cần giữ thế trận ổn định.
- Dùng khoảng cách tới trung tâm làm tiêu chí phụ để thứ tự ổn định.
- Dùng `_move_key()` để kết quả sắp xếp có tính deterministic.

### 5.2. `_risky_move_score()`

Risky move được chấm điểm theo:

- `_estimate_opened_chain_loss()`: sau khi thử đi nước này, ước lượng chuỗi lớn nhất mà đối thủ có thể bắt đầu ăn.
- Số ô bị tạo thành 3 cạnh.
- Điểm phụ từ `_safe_move_score()`.

Mục tiêu là nếu bắt buộc phải mở chuỗi, AI sẽ mở chuỗi ít thiệt hại nhất.

## 6. Forcing moves và double-cross

Hàm `get_forcing_moves(state)` sinh các nước đi ép buộc khi có ô đang có 3 cạnh.

Các loại nước có thể xuất hiện:

- Nước ăn ô ngay: lấy cạnh còn thiếu của ô 3 cạnh bằng `_get_missing_edge()`.
- Nước sacrifice/double-cross trong một số tình huống chain tới hạn.

Quy trình:

1. `_find_capturable_chains()` tìm các chain có thể ăn liên tiếp.
2. Với mỗi chain, AI thêm nước ăn ô đầu chain.
3. Nếu chain đang ở điểm có thể double-cross, AI thêm nước sacrifice.
4. Fallback: quét toàn board, nếu còn ô 3 cạnh nào chưa được thêm thì thêm nước ăn ô đó.

Điểm cần lưu ý: AI hiện tại không return ngay khi chỉ có một forcing move ở top-level. Forcing move vẫn được đưa vào minimax, vì sau nước ăn đó có thể còn chuỗi hoặc vấn đề tempo cần được đánh giá tiếp.

## 7. Phân tích chain và loop

### 7.1. `_find_capturable_chains()`

Hàm này dùng cho tình huống đã có ô 3 cạnh. Nó tìm các chuỗi có thể ăn liên tiếp sau khi vẽ cạnh còn thiếu.

Điều kiện lan chuỗi:

- Ô kế bên chưa bị ăn.
- Chia sẻ một cạnh chưa vẽ với ô hiện tại.
- `edges_count >= 2`, vì những ô này có khả năng thành ô 3 cạnh sau khi ăn ô trước.

### 7.2. `_analyze_chains_and_loops()`

Hàm này dùng trong heuristic endgame. Nó phân tích các component gồm những ô chưa bị ăn, có `edges_count >= 2`, và nối nhau qua cạnh chưa vẽ.

Sau khi tìm component, AI đếm số neighbor của mỗi ô trong component:

- Nếu mọi ô có đúng 2 neighbor và độ dài component >= 4, đó là closed loop.
- Nếu không phải loop và độ dài component >= 3, đó là open chain.

Kết quả trả về:

```python
(open_chains, closed_loops)
```

Trong đó mỗi phần tử là độ dài của chain hoặc loop.

## 8. Đánh giá chain control bằng `_evaluate_chains()`

Endgame của Dots and Boxes thường được quyết định bởi ai nắm quyền control các chain. Hàm `_evaluate_chains()` ước lượng lợi thế đó.

AI chuyển các cấu trúc thành region:

- Open chain: chi phí sacrifice là 2 ô.
- Closed loop: chi phí sacrifice là 4 ô.

Các region được sắp xếp theo `len - sac`. Region có lợi ít hơn được xử lý trước, region tốt nhất được để cuối.

Mô phỏng điểm:

- Ở các region đầu, controller ăn `len - sac`, victim nhận `sac`.
- Ở region cuối cùng, controller ăn trọn `len`, không cần sacrifice nữa.

Sau đó AI tính:

```text
net_chain_score = controller_points - victim_points
```

rồi đổi dấu về góc nhìn của `ai_player`.

Quy tắc parity trong code:

- Nếu số region là chẵn, người đang có lượt được xem là có cơ hội nắm control.
- Nếu số region là lẻ, control nghiêng về người còn lại.

Giá trị trả về của `_evaluate_chains()` được nhân thêm để có trọng số đủ lớn trong endgame.

## 9. Hàm heuristic `evaluate()`

Khi minimax chạm `depth <= 0` và không còn forcing move, AI dùng `evaluate()`.

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
| `chain_score * chain_weight` | Đánh giá quyền control chain/loop |
| `mobility_score` | Đánh giá bên nào còn safe move hoặc bị buộc mở chuỗi |
| `- boxes_2 * 3` | Phạt nhẹ việc có nhiều ô 2 cạnh trên board |

`chain_weight` thay đổi theo giai đoạn:

| Điều kiện | `chain_weight` | Ý nghĩa |
|---|---:|---|
| `boxes_safe > 2` | 1 | Midgame, ưu tiên điểm và safe move |
| `boxes_safe > 0` | 5 | Cận endgame, bắt đầu coi trọng parity |
| `boxes_safe == 0` | 15 | Endgame, chain control là yếu tố chính |

### 9.1. Mobility score và forced opener

Nếu không có ô nào đang ăn được (`capturable == 0`), AI đếm số safe move.

- Nếu còn safe move: bên đang đi được cộng một điểm nhỏ vì vẫn còn không gian điều khiển.
- Nếu không còn safe move: bên đang đi bị buộc mở chuỗi. AI ước lượng chuỗi thiệt hại nhỏ nhất và phạt bên đang đi.

Đây là heuristic quan trọng khi đánh với bot mạnh: không chỉ xem ai đang hơn điểm, mà còn xem ai sắp bị buộc phải mở quà cho đối thủ.

## 10. Minimax và Alpha-Beta

Hàm `minimax(state, depth, alpha, beta, ai_player)` là hàm tìm kiếm đệ quy.

Các bước chính:

1. Kiểm tra deadline bằng `_time_up()`. Nếu hết giờ, trả về heuristic và đánh dấu `_search_timed_out`.
2. Nếu game kết thúc, trả về hiệu số điểm nhân 10000.
3. Lấy forcing moves bằng `get_forcing_moves()`.
4. Nếu `depth <= 0` và không có forcing move, dùng `evaluate()`.
5. Tra cứu transposition table.
6. Xác định node max/min theo `state.current_player == ai_player`.
7. Nếu có forcing move, chỉ search forcing move.
8. Nếu không, lấy legal moves và lọc/sắp xếp bằng `_order_moves()`.
9. Thử từng move bằng `apply_move()`.
10. Nếu move ăn được ô, `current_player` không đổi, vì vậy depth không giảm. Nếu đổi lượt, depth giảm 1.
11. Gọi đệ quy `minimax()`.
12. Undo move bằng `undo_move()`.
13. Cập nhật `alpha`, `beta`, cắt nhánh khi `alpha >= beta`.
14. Lưu kết quả vào transposition table nếu không bị timeout.

## 11. Transposition Table

`_tt` là dictionary cache kết quả search.

Key được tạo bởi `_state_key()`:

```python
(h_edges, v_edges, boxes, current_player, score_player1, score_player2)
```

Việc thêm `boxes` và điểm số vào key là quan trọng, vì trong Dots and Boxes cùng một tập cạnh có thể gắn với điểm hoặc owner khác nhau tùy thứ tự ăn ô.

Mỗi entry lưu:

```python
(depth, score, flag, best_move_key)
```

`flag` có 3 loại:

| Flag | Ý nghĩa |
|---|---|
| `EXACT` | Điểm chính xác ở depth đó |
| `LOWERBOUND` | Điểm thực tế >= score |
| `UPPERBOUND` | Điểm thực tế <= score |

## 12. Iterative deepening và deadline

`get_best_move()` không search thẳng một depth lớn. Thay vào đó, nó chạy từ depth 1 đến `max_depth`.

Sau mỗi depth:

- Nếu tìm được move tốt hơn, cập nhật `best_move`.
- Nếu điểm rất lớn (`abs(score) >= 9000`), xem như thấy kết quả chắc chắn và dừng.
- Nếu ước lượng vòng sau vượt `time_limit`, dừng.
- Nếu minimax chạm deadline nội bộ, dừng và trả về best move của depth trước.

Deadline nội bộ dùng các biến:

- `_search_deadline`
- `_search_timed_out`
- `_time_up()`

Nhờ đó AI không chỉ kiểm tra thời gian giữa các iteration, mà còn có thể thoát trong lúc đang đệ quy.

## 13. Adaptive depth theo kích thước và giai đoạn

Nếu user không truyền `base_depth`, AI tự chọn theo số ô:

| Số ô | Base depth |
|---:|---:|
| `<= 9` | 8 |
| `<= 16` | 6 |
| `<= 25` | 5 |
| `<= 36` | 4 |
| Lớn hơn | 3 |

Sau đó `_get_adaptive_depth()` tăng depth khi số move còn lại ít:

| `moves_remaining` | Depth tối đa |
|---:|---:|
| `<= 10` | `min(remaining, 22)` |
| `<= 16` | `base_depth + 4` |
| `<= 22` | `base_depth + 2` |
| `<= 30` | `base_depth + 1` |
| Lớn hơn | `base_depth` |

Ý tưởng: đầu game và bàn lớn cần pruning mạnh; cuối game còn ít move hơn nên có thể search sâu.

## 14. Điểm mạnh và giới hạn

Điểm mạnh:

- Tránh mở ô 3 cạnh khi vẫn còn safe move.
- Biết ước lượng thiệt hại khi buộc phải mở chuỗi.
- Có phân tích chain/loop và parity cho endgame.
- Có deadline nội bộ để tránh treo UI.
- Chạy được trên bàn 4x4, 6x6, 7x7 nhờ candidate pruning.

Giới hạn:

- Chưa phải solver tuyệt đối cho mọi kích thước board.
- Phân tích Nimstring mới ở mức heuristic, chưa tính đầy đủ Sprague-Grundy hoặc nimber.
- Double-cross hiện được sinh ở một số điểm tới hạn, chưa bao phủ toàn bộ chiến thuật endgame nâng cao.
- Kết quả phụ thuộc vào `time_limit` và độ sâu search thực tế.

## 15. Tóm tắt ngắn gọn

AI hiện tại có thể hiểu theo một câu:

> Nếu có ô ăn được thì xét các nước ép buộc; nếu không có thì chỉ chơi safe move; nếu hết safe move thì mở chuỗi ít thiệt hại nhất; tất cả được đánh giá bằng minimax, chain heuristic, transposition table và deadline thời gian.
