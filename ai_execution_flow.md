# Luồng chạy logic AI Bot - Dots and Boxes

Tài liệu này mô tả thứ tự thực thi của AI từ lúc UI yêu cầu một nước đi đến lúc AI trả về đối tượng `Move`. Tài liệu phù hợp để giải thích trong phần thuyết trình vì tập trung vào "code chạy theo luồng nào".

## 1. Sơ đồ tổng quan

```text
UI đến lượt AI
    -> copy state hiện tại
    -> chạy thread nền gọi get_best_move()
        -> khởi tạo deadline 4 giây
        -> chọn base_depth
        -> xóa Transposition Table
        -> sinh candidate ban đầu
            -> nếu có forcing moves:
                -> _order_forcing_moves()
            -> nếu không:
                -> _order_moves()
        -> iterative deepening
            -> minimax(depth = 1)
            -> minimax(depth = 2)
            -> ...
            -> dừng khi hết depth hoặc gần hết giờ
        -> trả best_move
    -> UI nhận ai_move_pending
    -> UI apply move thật lên board
```

## 2. UI gọi AI

Trong `ui.py`, AI không chạy trực tiếp trên main thread. Khi đến lượt bot:

1. UI kiểm tra game chưa kết thúc và `current_player` đúng là AI.
2. UI tạo bản sao của `GameState`.
3. UI chạy background worker.
4. Worker gọi:

```python
ai.get_best_move(state_copy, ai_player=ai_player)
```

Lý do phải dùng state copy:

- AI sẽ apply/undo rất nhiều nước đi trong minimax.
- State thật đang được UI render không nên bị thay đổi trong lúc AI suy nghĩ.
- Cách này giúp Pygame không bị đứng khi AI tính toán.

## 3. Entry point: `get_best_move()`

Hàm công khai của AI:

```python
get_best_move(state, ai_player=2, base_depth=None, time_limit=4.0)
```

Đây là hàm duy nhất UI cần gọi.

## 4. Bước 1 - Khởi tạo thời gian

Ngay đầu `get_best_move()`, AI tạo deadline:

```python
start_time = time.perf_counter()
_search_deadline = start_time + time_limit
_search_timed_out = False
```

Với code hiện tại, `time_limit` mặc định là `4.0` giây.

Deadline này được dùng ở hai nơi:

- Vòng iterative deepening trong `get_best_move()`.
- Bên trong từng lời gọi đệ quy của `minimax()`.

## 5. Bước 2 - Chọn base depth

Nếu không truyền `base_depth`, AI tự chọn theo số ô:

```text
rows * cols <= 9   -> base_depth = 8
rows * cols <= 16  -> base_depth = 6
rows * cols <= 25  -> base_depth = 5
rows * cols <= 36  -> base_depth = 4
rows * cols > 36   -> base_depth = 3
```

Bàn càng lớn thì base depth càng nhỏ để tránh nổ nhánh.

## 6. Bước 3 - Xóa Transposition Table

Mỗi lần AI tính một nước mới:

```python
_tt.clear()
```

Việc này giúp tránh dùng nhầm cache từ lượt trước. Trong một lần search, `_tt` vẫn được dùng để tái sử dụng kết quả giữa các nhánh và giữa các depth của iterative deepening.

## 7. Bước 4 - Sinh danh sách candidate ban đầu

AI gọi:

```python
forcing = get_forcing_moves(state)
```

Sau đó chia hai trường hợp.

### 7.1. Có forcing moves

Nếu có forcing moves:

```python
legal_moves = _order_forcing_moves(state, forcing, ai_player)
```

Forcing moves gồm:

- Nước ăn ô ngay.
- Nước sacrifice/hard-hearted handout.

`_order_forcing_moves()` rất quan trọng vì nó quyết định thứ tự giữa greedy capture và sacrifice.

### 7.2. Không có forcing move

Nếu không có forcing move:

```python
legal_moves = _order_moves(state, get_legal_moves(state))
```

`_order_moves()` sẽ lọc theo pha:

1. Capture move nếu có.
2. Safe move nếu không có capture.
3. Risky move nếu hết safe move.

## 8. Bước 5 - Xử lý trường hợp đặc biệt

Sau khi có `legal_moves`:

- Nếu danh sách rỗng, trả về `None`.
- Nếu chỉ có một move, trả về move đó.
- Nếu có nhiều move, bắt đầu iterative deepening.

## 9. Bước 6 - Tính max depth thích nghi

AI gọi:

```python
max_depth = _get_adaptive_depth(state, base_depth)
```

Luật tăng depth:

| `moves_remaining` | Depth tối đa |
|---:|---:|
| `<= 10` | `min(remaining, 22)` |
| `<= 16` | `base_depth + 4` |
| `<= 22` | `base_depth + 2` |
| `<= 30` | `base_depth + 1` |
| Lớn hơn | `base_depth` |

Cuối game còn ít cạnh hơn, nên AI có thể search sâu hơn.

## 10. Bước 7 - Iterative Deepening

AI chạy minimax từ depth nhỏ đến depth lớn:

```python
for d in range(1, max_depth + 1):
    elapsed = time.perf_counter() - start_time
    estimated_next = max(last_iter_time * 5, 0.02)

    if d > 1 and (elapsed + estimated_next) > time_limit:
        break

    score, move = minimax(state, d, -math.inf, math.inf, ai_player)
```

Sau mỗi vòng:

1. Nếu minimax timeout, dừng.
2. Nếu có move mới, cập nhật `best_move`.
3. Nếu `abs(score) >= 9000`, xem như đã thấy trạng thái rất mạnh và dừng.
4. Nếu vòng tiếp theo có nguy cơ vượt `time_limit`, dừng.

Kết quả cuối cùng là best move tốt nhất từ vòng đã hoàn tất.

## 11. Luồng trong `minimax()`

Hàm chính:

```python
minimax(state, depth, alpha, beta, ai_player)
```

Thứ tự chạy:

```text
minimax()
    -> kiểm tra timeout bằng _time_up()
    -> nếu terminal: trả final score
    -> sinh forcing_moves
    -> nếu depth <= 0 và không có forcing: evaluate()
    -> tra cứu Transposition Table
    -> xác định max node hay min node
    -> chọn danh sách move
        -> nếu có forcing: _order_forcing_moves()
        -> nếu không: _order_moves()
    -> thử từng move
        -> apply_move()
        -> tính next_depth
        -> gọi minimax() đệ quy
        -> undo_move()
        -> cập nhật best value
        -> cập nhật alpha/beta
        -> cắt nhánh nếu alpha >= beta
    -> lưu vào Transposition Table
    -> trả best value và best move
```

## 12. Vì sao depth không luôn giảm?

Trong Dots and Boxes, nếu người chơi ăn được ô thì được đi tiếp. Vì vậy sau khi apply move:

```python
next_depth = depth if undo_info['previous_player'] == state.current_player else depth - 1
```

Ý nghĩa:

- Nếu `current_player` sau move vẫn là người vừa đi, tức là người đó ăn được ô và giữ lượt. Depth không giảm.
- Nếu lượt chuyển sang người khác, depth giảm 1.

Đây là điểm khác các game luân phiên lượt cố định như cờ vua hoặc caro.

## 13. Luồng của `_order_moves()`

`_order_moves()` dùng khi không có forcing move.

```text
_order_moves()
    -> lấy candidate limit bằng _candidate_limit()
    -> nếu có capture moves:
        -> sort capture theo số ô ăn được
        -> dedupe và return
    -> nếu có safe moves:
        -> sort bằng _safe_move_score()
        -> dedupe, giới hạn candidate và return
    -> nếu hết safe:
        -> sort risky bằng _risky_move_score()
        -> dedupe, giới hạn candidate và return
```

Candidate limit hiện tại:

```text
<= 16 ô  -> 32 candidate
<= 36 ô  -> 24 candidate
> 36 ô   -> 18 candidate
```

## 14. Luồng của `get_forcing_moves()`

```text
get_forcing_moves()
    -> chains = _find_capturable_chains()
    -> với mỗi chain:
        -> thêm nước ăn ô đầu chain bằng _get_missing_edge()
        -> thêm các nước sacrifice từ _get_sacrifice_moves()
    -> fallback quét toàn board:
        -> nếu còn ô 3 cạnh, thêm nước ăn ô đó
    -> return moves
```

Hàm dùng set `seen` để tránh thêm trùng move.

Forcing moves vẫn được đưa vào minimax. AI không return ngay chỉ vì thấy có nước ăn, vì sau nước ăn có thể xuất hiện quyết định quan trọng: ăn hết hay sacrifice.

## 15. Luồng sinh sacrifice

Hàm:

```python
_get_sacrifice_moves(state, chain)
```

Luồng xử lý:

```text
_get_sacrifice_moves()
    -> nếu chain quá ngắn: return []
    -> handout_size = _handout_size_for_component()
    -> nếu len(chain) < handout_size: return []
    -> duyệt toàn bộ legal moves
        -> bỏ move ăn điểm ngay
        -> bỏ move không chạm component
        -> thử move bằng apply_move()
        -> tìm phần component trở thành capturable
        -> undo move
        -> nếu số ô capturable == handout_size:
            -> thêm vào candidates
    -> sort candidates
    -> return candidates
```

Điểm cần nhớ khi thuyết trình:

> Sacrifice hiện tại không dựa cứng vào hình dạng cụ thể. AI thử nước đi và kiểm tra kết quả sau move: có để lại đúng phần handout cho đối thủ hay không.

## 16. Luồng xếp forcing moves

Hàm:

```python
_order_forcing_moves(state, moves, ai_player)
```

Luồng xử lý:

```text
_order_forcing_moves()
    -> với mỗi forcing move:
        -> score = _resolved_forcing_score()
    -> nếu node của AI: sort điểm cao trước
    -> nếu node của đối thủ: sort điểm thấp trước
    -> return danh sách move đã sắp xếp
```

## 17. Luồng của `_resolved_forcing_score()`

Đây là hàm giúp AI chọn đúng giữa greedy capture và sacrifice.

```text
_resolved_forcing_score(move)
    -> kiểm tra move có phải handout không
    -> apply move đang xét
    -> tự động chơi các capture bắt buộc tiếp theo bằng _play_greedy_forced_captures()
    -> score = evaluate() + _control_after_forced_resolution()
    -> nếu move là handout và sau đó đối thủ phải đi:
        -> cộng bonus kiểm soát
    -> undo toàn bộ capture bắt buộc
    -> undo move ban đầu
    -> return score
```

Ý nghĩa:

- Nếu ăn hết chuỗi làm AI bị buộc mở chuỗi kế tiếp, điểm bị giảm.
- Nếu sacrifice khiến đối thủ phải mở chuỗi kế tiếp, điểm được tăng.
- Nếu đó là chuỗi cuối cùng, AI không bị ép phải handout.

## 18. Luồng phân tích chain

### 18.1. `_find_capturable_chains()`

Dùng cho các chuỗi đang có thể ăn ngay:

```text
_find_capturable_chains()
    -> quét từng box
    -> nếu box chưa bị ăn và edges_count == 3:
        -> bắt đầu chain
        -> lan sang box kề qua cạnh chưa vẽ
        -> chỉ lan sang box có edges_count >= 2
    -> return danh sách chain
```

### 18.2. `_analyze_chains_and_loops()`

Dùng cho heuristic endgame:

```text
_analyze_chains_and_loops()
    -> quét box chưa bị ăn có edges_count >= 2
    -> DFS/BFS qua các cạnh chưa vẽ
    -> tạo connected component
    -> đếm neighbor trong component
    -> nếu mọi box đúng 2 neighbor và độ dài >= 4:
        -> closed loop
    -> nếu không phải loop và độ dài >= 3:
        -> open chain
    -> return (open_chains, closed_loops)
```

## 19. Luồng của `evaluate()`

`evaluate()` được gọi khi search không đi sâu thêm được.

```text
evaluate()
    -> tính score_diff
    -> đếm capturable, boxes_2, boxes_safe
    -> tính cap_score
    -> tính chain_score bằng _evaluate_chains()
    -> chọn chain_weight theo boxes_safe
    -> nếu không có ô capturable:
        -> tính mobility_score
            -> còn safe move: cộng/trừ nhẹ theo lượt
            -> hết safe move: phạt bên buộc phải mở chuỗi
    -> return tổng điểm heuristic
```

Điểm dương nghĩa là tốt cho AI. Điểm âm nghĩa là tốt cho đối thủ.

## 20. UI nhận kết quả

Sau khi worker thread tính xong:

1. Worker lưu move vào `ai_move_pending`.
2. Main loop của UI thấy có move chờ xử lý.
3. UI có thể delay ngắn để người chơi quan sát.
4. UI gọi hàm apply move thật lên board.
5. Nếu AI ăn ô, AI tiếp tục đi; nếu không, lượt chuyển về người chơi.

## 21. Pseudo-code tổng hợp

```python
def get_best_move(state, ai_player=2, time_limit=4.0):
    setup_deadline()
    choose_base_depth()
    clear_transposition_table()

    forcing = get_forcing_moves(state)
    if forcing:
        candidates = _order_forcing_moves(state, forcing, ai_player)
    else:
        candidates = _order_moves(state, get_legal_moves(state))

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    best_move = candidates[0]
    for depth in range(1, max_depth + 1):
        if not_enough_time_for_next_depth():
            break

        score, move = minimax(state, depth, -inf, inf, ai_player)

        if timed_out_inside_minimax():
            break
        if move:
            best_move = move

    return best_move
```

```python
def minimax(state, depth, alpha, beta, ai_player):
    if time_up():
        return evaluate(state), None

    if terminal(state):
        return final_score(state), None

    forcing = get_forcing_moves(state)
    if depth <= 0 and not forcing:
        return evaluate(state), None

    use_transposition_table_if_possible()

    if forcing:
        moves = _order_forcing_moves(state, forcing, ai_player)
    else:
        moves = _order_moves(state, get_legal_moves(state), tt_best_key)

    for move in moves:
        undo = apply_move(state, move)
        next_depth = depth if same_player_gets_extra_turn() else depth - 1
        value, _ = minimax(state, next_depth, alpha, beta, ai_player)
        undo_move(state, move, undo)

        update_best_value()
        update_alpha_beta()
        if alpha >= beta:
            break

    store_to_transposition_table()
    return best_value, best_move
```

## 22. Câu chốt khi thuyết trình

Nếu cần giải thích thật ngắn:

> AI đi theo ba lớp. Đầu tiên nó tránh tự mở ô 3 cạnh bằng safe move. Khi có chuỗi hoặc ô ăn được, nó xử lý forcing moves. Ở cuối chuỗi, AI không tham ăn hết ngay mà dùng `_resolved_forcing_score()` để quyết định nên greedy capture hay sacrifice, nhằm giữ quyền kiểm soát chain và ép đối thủ mở chuỗi tiếp theo.
