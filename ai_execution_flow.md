# Luồng chạy logic AI Bot - Dots and Boxes

Tài liệu này mô tả thứ tự thực thi của AI từ khi UI yêu cầu một nước đi cho đến khi AI trả về đối tượng `Move`.

## 1. Tổng quan luồng chạy

```text
UI (_handle_ai_turn)
    -> copy.deepcopy(GameState)
    -> background thread gọi ai.get_best_move()
        -> khởi tạo timer, deadline, depth
        -> tìm forcing moves
        -> tạo danh sách candidate moves
        -> iterative deepening
            -> minimax(depth = 1)
            -> minimax(depth = 2)
            -> ... đến max_depth hoặc hết giờ
        -> trả về best_move
    -> UI nhận ai_move_pending
    -> UI apply move thật lên board
```

## 2. UI gọi AI

Trong `ui.py`, khi đến lượt bot, UI không tính trực tiếp trên main thread. Thay vào đó:

1. Kiểm tra game chưa kết thúc và `current_player` đúng là AI.
2. Tạo bản sao của game state bằng `copy.deepcopy()`.
3. Chạy thread nền `_ai_compute_worker`.
4. Thread nền gọi:

```python
ai.get_best_move(state_copy, ai_player=ai_player)
```

Cách này giúp Pygame vẫn render được màn hình trong lúc AI đang suy nghĩ.

## 3. Entry point: `get_best_move()`

`get_best_move()` là API công khai của AI.

### 3.1. Khởi tạo thời gian

Đầu tiên AI tạo deadline:

```python
start_time = time.perf_counter()
_search_deadline = start_time + time_limit
_search_timed_out = False
```

Deadline này được dùng cả trong vòng iterative deepening và trong đệ quy `minimax()`.

### 3.2. Chọn base depth

Nếu không truyền `base_depth`, AI chọn theo số ô:

```text
<= 9 ô   -> base_depth = 8
<= 16 ô  -> base_depth = 6
<= 25 ô  -> base_depth = 5
<= 36 ô  -> base_depth = 4
> 36 ô   -> base_depth = 3
```

Bàn lớn hơn sẽ có base depth nhỏ hơn để tránh nổ nhánh.

### 3.3. Xóa transposition table

Mỗi lần AI tính một nước mới, `_tt.clear()` được gọi để tránh dùng kết quả cũ không còn phù hợp với lượt hiện tại.

### 3.4. Tìm forcing moves

AI gọi:

```python
forcing = get_forcing_moves(state)
```

Nếu có forcing moves, danh sách candidate ban đầu là forcing moves.

Nếu không có forcing move, AI lấy toàn bộ legal moves rồi đưa qua `_order_moves()`:

```python
legal_moves = _order_moves(state, get_legal_moves(state))
```

Tại đây AI đã lọc theo pha safe/risky, không đem tất cả cạnh hợp lệ vào minimax.

### 3.5. Xử lý trường hợp đặc biệt

- Nếu không có legal move, trả về `None`.
- Nếu chỉ có một move, trả về move đó.
- Nếu có nhiều move, bắt đầu iterative deepening.

## 4. Iterative deepening

AI tính `max_depth` bằng `_get_adaptive_depth()`.

Sau đó chạy:

```python
for d in range(1, max_depth + 1):
    score, move = minimax(state, d, -math.inf, math.inf, ai_player)
```

Sau mỗi vòng:

1. Nếu timeout trong minimax, dừng và giữ best move của vòng trước.
2. Nếu có move mới, cập nhật `best_move`.
3. Nếu `abs(score) >= 9000`, xem như thấy kết quả rất mạnh và dừng.
4. Nếu ước lượng depth tiếp theo vượt `time_limit`, dừng.

Kết quả cuối cùng của `get_best_move()` là `best_move` tốt nhất đã tìm được trong thời gian cho phép.

## 5. Hàm `minimax()`

`minimax()` là hàm đệ quy tìm nước tối ưu trong cây game.

### 5.1. Kiểm tra timeout

Ngay đầu hàm:

```python
if _time_up():
    _search_timed_out = True
    return evaluate(state, ai_player), None
```

Điều này giúp AI thoát khỏi đệ quy sau khi hết thời gian.

### 5.2. Kiểm tra terminal

Nếu hết move:

```python
return score_diff * 10000, None
```

Hệ số 10000 làm trạng thái thắng/thua thật sự quan trọng hơn heuristic.

### 5.3. Sinh forcing moves

AI gọi `get_forcing_moves()` ở mỗi node.

Nếu có forcing move, minimax chỉ xét các move này, vì trong Dots and Boxes các ô 3 cạnh và chain đang mở là phần cần xử lý trước.

### 5.4. Điều kiện dừng heuristic

Nếu `depth <= 0` và không có forcing move:

```python
return evaluate(state, ai_player), None
```

Nếu vẫn có forcing move, AI tiếp tục search để xử lý hết chuỗi capture quan trọng.

### 5.5. Tra cứu transposition table

AI tạo key:

```python
(h_edges, v_edges, boxes, current_player, score_player1, score_player2)
```

Nếu trạng thái đã được tính ở depth bằng hoặc sâu hơn, AI có thể dùng lại điểm đã cache hoặc thu hẹp cửa sổ alpha/beta.

### 5.6. Xác định max node hay min node

```python
is_max = (state.current_player == ai_player)
```

- Nếu `is_max == True`, AI chọn điểm cao nhất.
- Nếu `is_max == False`, AI giả định đối thủ chọn điểm thấp nhất cho AI.

Không dùng depth chẵn/lẻ để xác định max/min, vì trong Dots and Boxes ăn ô sẽ được đi tiếp.

### 5.7. Chọn danh sách move để search

Nếu có forcing move:

```python
ordered = forcing_moves
```

Nếu không:

```python
legal_moves = get_legal_moves(state)
ordered = _order_moves(state, legal_moves, tt_best_key)
```

`_order_moves()` có thể cắt bot risky moves nếu vẫn còn safe moves.

### 5.8. Thử từng move

Với mỗi move:

1. Kiểm tra timeout.
2. `apply_move(state, move)`.
3. Tính `next_depth`:
   - Nếu sau khi apply, `current_player` vẫn là người vừa đi, nghĩa là move ăn được ô, depth không giảm.
   - Nếu đổi lượt, depth giảm 1.
4. Gọi đệ quy `minimax()`.
5. `undo_move(state, move, undo_info)`.
6. Cập nhật best value và best move.
7. Cập nhật alpha/beta.
8. Nếu `alpha >= beta`, cắt nhánh.

## 6. Luồng của `_order_moves()`

`_order_moves()` nhận một danh sách move và trả về danh sách đã lọc/sắp xếp.

```text
_order_moves()
    -> tìm capture moves
        -> nếu có: sắp xếp capture và return
    -> tìm safe moves
        -> nếu có: chỉ giữ safe moves, sắp xếp bằng _safe_move_score
    -> nếu hết safe:
        -> sắp xếp risky moves bằng _risky_move_score
    -> dedupe và giới hạn số candidate
```

### 6.1. Khi có capture moves

AI ưu tiên những move ăn được nhiều ô hơn:

```python
captures.sort(key=lambda move: (-would_complete_box(...), _risky_move_score(...)))
```

### 6.2. Khi còn safe moves

AI chỉ giữ safe moves. Đây là pha đầu/midgame quan trọng nhất: không tạo ô 3 cạnh cho đối thủ nếu chưa bắt buộc.

### 6.3. Khi hết safe moves

AI buộc phải mở chuỗi. Lúc này risky moves được sắp xếp theo `_estimate_opened_chain_loss()` để mở chuỗi ít thiệt hại nhất.

## 7. Luồng của `get_forcing_moves()`

```text
get_forcing_moves()
    -> _find_capturable_chains()
    -> với mỗi chain:
        -> thêm move ăn ô đầu chain
        -> nếu chain tới hạn double-cross:
            -> thêm move sacrifice
    -> fallback quét mọi ô 3 cạnh
    -> return moves
```

Hàm này dùng set `seen` để tránh thêm trùng move.

Forcing moves không được return ngay ở top-level, mà vẫn được đưa vào minimax để AI nhìn tiếp hậu quả sau đó.

## 8. Luồng của `_find_capturable_chains()`

```text
_find_capturable_chains()
    -> quét từng box
    -> nếu box chưa bị ăn và edges_count == 3:
        -> bắt đầu chain
        -> lan sang box kế qua cạnh chưa vẽ
        -> chỉ lan sang box có edges_count >= 2
    -> return danh sách chain
```

Hàm này phục vụ các tình huống đang có ô có thể ăn ngay.

## 9. Luồng của `_analyze_chains_and_loops()`

```text
_analyze_chains_and_loops()
    -> quét từng box chưa bị ăn có edges_count >= 2
    -> DFS/BFS qua các cạnh chưa vẽ
    -> tạo connected component
    -> đếm neighbor của mỗi box trong component
    -> component có mọi box đúng 2 neighbor và dài >= 4: closed loop
    -> component không phải loop và dài >= 3: open chain
    -> return (open_chains, closed_loops)
```

Hàm này không phải để chọn move trực tiếp, mà để chấm điểm endgame trong `_evaluate_chains()`.

## 10. Luồng của `evaluate()`

`evaluate()` được gọi khi search chạm depth giới hạn hoặc timeout.

```text
evaluate()
    -> tính score_diff
    -> đếm capturable, boxes_2, boxes_safe
    -> tính cap_score
    -> tính chain_score bằng _evaluate_chains()
    -> chọn chain_weight theo boxes_safe
    -> tính mobility_score
    -> return tổng điểm heuristic
```

Điểm dương nghĩa là tốt cho AI, điểm âm nghĩa là tốt cho đối thủ.

## 11. Luồng timeout và trả kết quả

AI có hai lớp quản lý thời gian:

1. Ngoài `get_best_move()`: ước lượng xem có nên bắt đầu depth tiếp theo không.
2. Trong `minimax()`: dùng `_time_up()` để thoát khỏi đệ quy nếu đã qua deadline.

Nếu timeout xảy ra trong depth hiện tại, AI không tin kết quả chưa hoàn tất của depth đó. Nó dừng lại và trả `best_move` của depth trước.

## 12. UI nhận và apply move

Sau khi `get_best_move()` trả về:

1. Worker thread gán move vào `ai_move_pending`.
2. Main loop của UI thấy `ai_move_pending != None`.
3. UI đợi một khoảng delay ngắn để người chơi quan sát.
4. UI gọi `_apply_move_with_effects(move)`.
5. `rules.apply_move()` cập nhật board thật.
6. Nếu AI ăn được ô, AI tiếp tục được đi; nếu không, lượt chuyển về người chơi.

## 13. Tóm tắt bằng pseudo-code

```python
def get_best_move(state):
    setup_deadline()
    choose_base_depth()
    clear_transposition_table()

    forcing = get_forcing_moves(state)
    if forcing:
        candidates = forcing
    else:
        candidates = _order_moves(state, get_legal_moves(state))

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
def minimax(state, depth, alpha, beta):
    if time_up():
        return evaluate(state)

    if terminal(state):
        return final_score(state)

    forcing = get_forcing_moves(state)
    if depth <= 0 and not forcing:
        return evaluate(state)

    if transposition_table_hit():
        use_cached_result()

    moves = forcing or _order_moves(state, get_legal_moves(state))

    for move in moves:
        undo = apply_move(state, move)
        next_depth = depth if same_player_gets_extra_turn() else depth - 1
        value = minimax(state, next_depth, alpha, beta)
        undo_move(state, move, undo)

        update_best_value()
        update_alpha_beta()
        if alpha >= beta:
            break

    store_to_transposition_table()
    return best_value, best_move
```
