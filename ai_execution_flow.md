# Luong chay logic AI Bot - Dots and Boxes

Tai lieu nay mo ta thu tu thuc thi cua AI tu khi UI yeu cau mot nuoc di cho den khi AI tra ve doi tuong `Move`.

## 1. Tong quan luong chay

```text
UI (_handle_ai_turn)
    -> copy.deepcopy(GameState)
    -> background thread goi ai.get_best_move()
        -> khoi tao timer, deadline, depth
        -> tim forcing moves
        -> tao danh sach candidate moves
        -> iterative deepening
            -> minimax(depth = 1)
            -> minimax(depth = 2)
            -> ... den max_depth hoac het gio
        -> tra ve best_move
    -> UI nhan ai_move_pending
    -> UI apply move that len board
```

## 2. UI goi AI

Trong `ui.py`, khi den luot bot, UI khong tinh truc tiep tren main thread. Thay vao do:

1. Kiem tra game chua ket thuc va `current_player` dung la AI.
2. Tao ban sao cua game state bang `copy.deepcopy()`.
3. Chay thread nen `_ai_compute_worker`.
4. Thread nen goi:

```python
ai.get_best_move(state_copy, ai_player=ai_player)
```

Cach nay giup Pygame van render duoc man hinh trong luc AI dang suy nghi.

## 3. Entry point: `get_best_move()`

`get_best_move()` la API cong khai cua AI.

### 3.1. Khoi tao thoi gian

Dau tien AI tao deadline:

```python
start_time = time.perf_counter()
_search_deadline = start_time + time_limit
_search_timed_out = False
```

Deadline nay duoc dung ca trong vong iterative deepening va trong de quy `minimax()`.

### 3.2. Chon base depth

Neu khong truyen `base_depth`, AI chon theo so o:

```text
<= 9 o   -> base_depth = 8
<= 16 o  -> base_depth = 6
<= 25 o  -> base_depth = 5
<= 36 o  -> base_depth = 4
> 36 o   -> base_depth = 3
```

Ban lon hon se co base depth nho hon de tranh no nhanh.

### 3.3. Xoa transposition table

Moi lan AI tinh mot nuoc moi, `_tt.clear()` duoc goi de tranh dung ket qua cu khong con phu hop voi luot hien tai.

### 3.4. Tim forcing moves

AI goi:

```python
forcing = get_forcing_moves(state)
```

Neu co forcing moves, danh sach candidate ban dau la forcing moves.

Neu khong co forcing move, AI lay toan bo legal moves roi dua qua `_order_moves()`:

```python
legal_moves = _order_moves(state, get_legal_moves(state))
```

Tai day AI da loc theo pha safe/risky, khong phai dem tat ca canh hop le vao minimax.

### 3.5. Xu ly truong hop dac biet

- Neu khong co legal move, tra ve `None`.
- Neu chi co mot move, tra ve move do.
- Neu co nhieu move, bat dau iterative deepening.

## 4. Iterative deepening

AI tinh `max_depth` bang `_get_adaptive_depth()`.

Sau do chay:

```python
for d in range(1, max_depth + 1):
    score, move = minimax(state, d, -math.inf, math.inf, ai_player)
```

Sau moi vong:

1. Neu timeout trong minimax, dung va giu best move cua vong truoc.
2. Neu co move moi, cap nhat `best_move`.
3. Neu `abs(score) >= 9000`, xem nhu thay ket qua rat manh va dung.
4. Neu uoc luong depth tiep theo vuot `time_limit`, dung.

Ket qua cuoi cung cua `get_best_move()` la `best_move` tot nhat da tim duoc trong thoi gian cho phep.

## 5. Ham `minimax()`

`minimax()` la ham de quy tim nuoc toi uu trong cay game.

### 5.1. Kiem tra timeout

Ngay dau ham:

```python
if _time_up():
    _search_timed_out = True
    return evaluate(state, ai_player), None
```

Dieu nay giup AI thoat khoi de quy sau khi het thoi gian.

### 5.2. Kiem tra terminal

Neu het move:

```python
return score_diff * 10000, None
```

He so 10000 lam trang thai thang/thua that su quan trong hon heuristic.

### 5.3. Sinh forcing moves

AI goi `get_forcing_moves()` o moi node.

Neu co forcing move, minimax chi xet cac move nay, vi trong Dots and Boxes cac o 3 canh va chain dang mo la phan bat buoc can xu ly truoc.

### 5.4. Dieu kien dung heuristic

Neu `depth <= 0` va khong co forcing move:

```python
return evaluate(state, ai_player), None
```

Neu van co forcing move, AI tiep tuc search de xu ly het chuoi capture quan trong.

### 5.5. Tra cuu transposition table

AI tao key:

```python
(h_edges, v_edges, boxes, current_player, score_player1, score_player2)
```

Neu trang thai da duoc tinh o depth bang hoac sau hon, AI co the dung lai diem da cache hoac thu hep cua so alpha/beta.

### 5.6. Xac dinh max node hay min node

```python
is_max = (state.current_player == ai_player)
```

- Neu `is_max == True`, AI chon diem cao nhat.
- Neu `is_max == False`, AI gia dinh doi thu chon diem thap nhat cho AI.

Khong dung depth chan/le de xac dinh max/min, vi trong Dots and Boxes an o se duoc di tiep.

### 5.7. Chon danh sach move de search

Neu co forcing move:

```python
ordered = forcing_moves
```

Neu khong:

```python
legal_moves = get_legal_moves(state)
ordered = _order_moves(state, legal_moves, tt_best_key)
```

`_order_moves()` co the cat bot risky moves neu van con safe moves.

### 5.8. Thu tung move

Voi moi move:

1. Kiem tra timeout.
2. `apply_move(state, move)`.
3. Tinh `next_depth`:
   - Neu sau khi apply, `current_player` van la nguoi vua di, nghia la move an duoc o, depth khong giam.
   - Neu doi luot, depth giam 1.
4. Goi de quy `minimax()`.
5. `undo_move(state, move, undo_info)`.
6. Cap nhat best value va best move.
7. Cap nhat alpha/beta.
8. Neu `alpha >= beta`, cat nhanh.

## 6. Luong cua `_order_moves()`

`_order_moves()` nhan mot danh sach move va tra ve danh sach da loc/sap xep.

```text
_order_moves()
    -> tim capture moves
        -> neu co: sap xep capture va return
    -> tim safe moves
        -> neu co: chi giu safe moves, sap xep bang _safe_move_score
    -> neu het safe:
        -> sap xep risky moves bang _risky_move_score
    -> dedupe va gioi han so candidate
```

### 6.1. Khi co capture moves

AI uu tien nhung move an duoc nhieu o hon:

```python
captures.sort(key=lambda move: (-would_complete_box(...), _risky_move_score(...)))
```

### 6.2. Khi con safe moves

AI chi giu safe moves. Day la pha dau/midgame quan trong nhat: khong tao o 3 canh cho doi thu neu chua bat buoc.

### 6.3. Khi het safe moves

AI buoc phai mo chuoi. Luc nay risky moves duoc sap xep theo `_estimate_opened_chain_loss()` de mo chuoi it thiet hai nhat.

## 7. Luong cua `get_forcing_moves()`

```text
get_forcing_moves()
    -> _find_capturable_chains()
    -> voi moi chain:
        -> them move an o dau chain
        -> neu chain toi han double-cross:
            -> them move sacrifice
    -> fallback quet moi o 3 canh
    -> return moves
```

Ham nay dung set `seen` de tranh them trung move.

Forcing moves khong duoc return ngay o top-level, ma van duoc dua vao minimax de AI nhin tiep hau qua sau do.

## 8. Luong cua `_find_capturable_chains()`

```text
_find_capturable_chains()
    -> quet tung box
    -> neu box chua bi an va edges_count == 3:
        -> bat dau chain
        -> lan sang box ke qua canh chua ve
        -> chi lan sang box co edges_count >= 2
    -> return danh sach chain
```

Ham nay phuc vu cac tinh huong dang co o co the an ngay.

## 9. Luong cua `_analyze_chains_and_loops()`

```text
_analyze_chains_and_loops()
    -> quet tung box chua bi an co edges_count >= 2
    -> DFS/BFS qua cac canh chua ve
    -> tao connected component
    -> dem neighbor cua moi box trong component
    -> component co moi box dung 2 neighbor va dai >= 4: closed loop
    -> component khong phai loop va dai >= 3: open chain
    -> return (open_chains, closed_loops)
```

Ham nay khong phai de chon move truc tiep, ma de cham diem endgame trong `_evaluate_chains()`.

## 10. Luong cua `evaluate()`

`evaluate()` duoc goi khi search cham depth gioi han hoac timeout.

```text
evaluate()
    -> tinh score_diff
    -> dem capturable, boxes_2, boxes_safe
    -> tinh cap_score
    -> tinh chain_score bang _evaluate_chains()
    -> chon chain_weight theo boxes_safe
    -> tinh mobility_score
    -> return tong diem heuristic
```

Diem duong nghia la tot cho AI, diem am nghia la tot cho doi thu.

## 11. Luong timeout va tra ket qua

AI co hai lop quan ly thoi gian:

1. Ngoai `get_best_move()`: uoc luong xem co nen bat dau depth tiep theo khong.
2. Trong `minimax()`: dung `_time_up()` de thoat khoi de quy neu da qua deadline.

Neu timeout xay ra trong depth hien tai, AI khong tin ket qua chua hoan tat cua depth do. No dung lai va tra `best_move` cua depth truoc.

## 12. UI nhan va apply move

Sau khi `get_best_move()` tra ve:

1. Worker thread gan move vao `ai_move_pending`.
2. Main loop cua UI thay `ai_move_pending != None`.
3. UI doi mot khoang delay ngan de nguoi choi quan sat.
4. UI goi `_apply_move_with_effects(move)`.
5. `rules.apply_move()` cap nhat board that.
6. Neu AI an duoc o, AI tiep tuc duoc di; neu khong, luot chuyen ve nguoi choi.

## 13. Tom tat bang pseudo-code

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
