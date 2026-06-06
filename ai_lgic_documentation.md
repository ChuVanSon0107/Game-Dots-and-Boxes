# Tai lieu mo ta logic AI Bot - Dots and Boxes

## 1. Muc tieu cua AI

AI trong project nay duoc thiet ke de choi Dots and Boxes tren nhieu kich thuoc ban co, tu ban nho nhu 3x3, 4x4 den ban lon hon nhu 6x6, 7x7. Muc tieu khong chi la tim mot nuoc di hop le, ma la chon nuoc di giup AI toi da hoa hieu so diem cuoi tran.

Do Dots and Boxes co co che dac biet la nguoi an duoc o se duoc di tiep, AI khong the chi dung minimax theo luot chan/le thong thuong. Logic hien tai ket hop bon nhom y tuong:

- Minimax ket hop cat tia Alpha-Beta.
- Candidate pruning: chi dua cac nuoc dang xet vao minimax theo tung pha game.
- Chain theory: nhan dien chain, loop, double-cross va parity o endgame.
- Time management: iterative deepening ket hop deadline noi bo de UI khong bi treo.

Toan bo logic nam trong file `ai.py`. UI chi goi API cong khai `get_best_move()`.

## 2. Bieu dien trang thai lien quan den AI

AI lam viec tren doi tuong `GameState`, gom cac thong tin chinh:

- `h_edges`: ma tran cac canh ngang.
- `v_edges`: ma tran cac canh doc.
- `boxes`: ma tran chu so huu cua tung o, `0` la chua ai an, `1` va `2` la nguoi choi.
- `edges_count`: so canh da ve quanh moi o.
- `current_player`: nguoi dang co luot.
- `score_player1`, `score_player2`: diem hien tai.
- `moves_remaining`: so canh con lai.

Cac ham `apply_move()` va `undo_move()` trong `rules.py` la nen tang cua minimax. AI thu mot nuoc di bang `apply_move()`, de quy xuong nhanh con, sau do goi `undo_move()` de tra lai board ban dau.

## 3. Cac loai nuoc di co ban

AI phan loai nuoc di dua tren trang thai cac o bi anh huong.

### 3.1. Capture move

Capture move la nuoc di lam mot hoac nhieu o dat du 4 canh. Ham `would_complete_box(state, move)` tra ve so o se duoc an neu di nuoc nay.

Capture move rat quan trong vi:

- Nguoi di duoc cong diem.
- Nguoi di duoc giu luot.
- Co the kich hoat an lien tiep theo chuoi.

### 3.2. Safe move

Safe move la nuoc di khong tao bat ky o nao co dung 3 canh cho doi thu. Ham `would_create_third_edge(state, move)` tra ve so o se bi day len 3 canh.

Neu con safe move, AI uu tien chi search tren safe move. Day la thay doi quan trong de AI manh hon tren ban lon: thay vi search tat ca canh hop le, AI tranh tu mo qua cho doi thu khi van con duong an toan.

### 3.3. Risky move

Risky move la nuoc di tao ra it nhat mot o 3 canh. Neu doi thu toi uu, ho co the an o do va tiep tuc an chuoi.

Risky move chi duoc dua vao search khi khong con safe move. Khi buoc phai mo chuoi, AI sap xep risky move theo muc thiet hai uoc luong bang `_estimate_opened_chain_loss()`.

## 4. Candidate pruning theo pha game

Ham `_order_moves(state, moves, tt_best_key=None)` khong chi sap xep nuoc di, ma con loc bot nhanh search.

Thu tu xu ly:

1. Neu co capture move, tra ve nhom capture move truoc.
2. Neu khong co capture move nhung con safe move, chi giu safe move.
3. Neu khong con safe move, moi xet risky move.
4. Danh sach duoc gioi han boi `_candidate_limit()` de ban 6x6, 7x7 khong bi no nhanh.

`_candidate_limit()` hien tai dat gioi han theo so o:

| Kich thuoc logic | Candidate toi da |
|---|---:|
| `rows * cols <= 16` | 28 |
| `rows * cols <= 36` | 18 |
| Lon hon | 14 |

Ly do can gioi han: ban 7x7 co rat nhieu canh hop le, neu dua tat ca vao minimax thi branching factor qua lon. Candidate pruning dua kien thuc chien thuat vao truoc khi search.

## 5. Cham diem safe move va risky move

### 5.1. `_safe_move_score()`

Safe move duoc cham diem theo cac tieu chi:

- Han che tao them o co 2 canh, vi o 2 canh la vat lieu hinh thanh chain ve sau.
- Uu tien nuoc tac dong it o hon khi can giu the tran on dinh.
- Dung khoang cach toi trung tam lam tieu chi phu de co thu tu on dinh.
- Dung `_move_key()` de dam bao sap xep deterministic.

### 5.2. `_risky_move_score()`

Risky move duoc cham diem theo:

- `_estimate_opened_chain_loss()`: sau khi thu di nuoc nay, uoc luong chuoi doi thu co the bat dau an lon nhat.
- So o bi tao thanh 3 canh.
- Diem phu tu `_safe_move_score()`.

Muc tieu la neu bat buoc phai mo chuoi, AI mo chuoi ngan/it thiet hai nhat truoc.

## 6. Phat hien forcing moves va double-cross

Ham `get_forcing_moves(state)` sinh cac nuoc di ep buoc khi co o dang co 3 canh.

Luon co hai nhom nuoc co the xuat hien:

- Nuoc an o ngay: lay canh con thieu cua o 3 canh bang `_get_missing_edge()`.
- Nuoc sacrifice/double-cross trong mot so tinh huong chain toi han.

Quy trinh:

1. `_find_capturable_chains()` tim cac chain co the an lien tiep. Chain bat dau tu o 3 canh, sau do lan qua cac o ke nhau bang canh chua ve.
2. Voi moi chain, AI them nuoc an o dau chain.
3. Neu chain dang o diem co the double-cross, AI them nuoc sacrifice.
4. Fallback: quet toan bo board, neu con o 3 canh nao chua duoc them thi them nuoc an o do.

Diem can luu y: AI hien tai khong return ngay khi chi co mot forcing move o top-level. Forcing move van duoc dua vao minimax, vi sau nuoc an do co the con chuoi va tempo phia sau can duoc danh gia.

## 7. Phan tich chain va loop

### 7.1. `_find_capturable_chains()`

Ham nay dung cho tinh huong da co o 3 canh. No tim cac chuoi co the an lien tiep sau khi ve canh con thieu.

Dieu kien lan chuoi:

- O ke ben chua bi an.
- Chia se mot canh chua ve voi o hien tai.
- `edges_count >= 2`, vi nhung o nay co kha nang thanh o 3 canh sau khi an o truoc.

### 7.2. `_analyze_chains_and_loops()`

Ham nay dung trong heuristic endgame. No phan tich cac component gom nhung o chua bi an, co `edges_count >= 2`, va noi nhau qua canh chua ve.

Sau khi tim component, AI dem so neighbor cua moi o trong component:

- Neu moi o co dung 2 neighbor va do dai component >= 4, do la closed loop.
- Neu khong phai loop va do dai component >= 3, do la open chain.

Ket qua tra ve:

```python
(open_chains, closed_loops)
```

Trong do moi phan tu la do dai cua chain hoac loop.

## 8. Danh gia chain control bang `_evaluate_chains()`

Endgame cua Dots and Boxes thuong duoc quyet dinh boi ai nam quyen control cac chain. Ham `_evaluate_chains()` uoc luong loi the do.

AI chuyen cac cau truc thanh region:

- Open chain: chi phi sacrifice la 2 o.
- Closed loop: chi phi sacrifice la 4 o.

Cac region duoc sap xep theo `len - sac`. Region co loi it hon duoc xu ly truoc, region tot nhat duoc de cuoi.

Mo phong diem:

- O cac region dau, controller an `len - sac`, victim nhan `sac`.
- O region cuoi cung, controller an tron `len`, khong can sacrifice nua.

Sau do AI tinh `net_chain_score = controller_points - victim_points` va doi dau ve goc nhin cua `ai_player`.

Quy tac parity trong code:

- Neu so region la chan, nguoi dang co luot duoc xem la co co hoi nam control.
- Neu so region la le, control nghieng ve nguoi con lai.

Gia tri tra ve cua `_evaluate_chains()` duoc nhan them de co trong so du lon trong endgame.

## 9. Ham heuristic `evaluate()`

Khi minimax cham toi `depth <= 0` va khong con forcing move, AI dung `evaluate()`.

Cong thuc tong quat:

```text
score = score_diff * 100
      + cap_score
      + chain_score * chain_weight
      + mobility_score
      - boxes_2 * 3
```

Y nghia tung thanh phan:

| Thanh phan | Vai tro |
|---|---|
| `score_diff * 100` | Uu tien diem that cua AI so voi doi thu |
| `cap_score` | Thuong/phat co hoi an o 3 canh theo luot hien tai |
| `chain_score * chain_weight` | Danh gia control chain/loop trong midgame va endgame |
| `mobility_score` | Danh gia ben nao con safe move hoac bi buoc mo chuoi |
| `- boxes_2 * 3` | Phat nhe viec co nhieu o 2 canh tren board |

`chain_weight` thay doi theo giai doan:

| Dieu kien | `chain_weight` | Y nghia |
|---|---:|---|
| `boxes_safe > 2` | 1 | Midgame, uu tien diem va safe move |
| `boxes_safe > 0` | 5 | Can endgame, bat dau coi trong parity |
| `boxes_safe == 0` | 15 | Endgame, chain control la yeu to chinh |

### 9.1. Mobility score va forced opener

Neu khong co o nao dang an duoc (`capturable == 0`), AI dem so safe move.

- Neu con safe move: ben dang di co them diem nho vi van con khong gian dieu khien.
- Neu khong con safe move: ben dang di bi buoc mo chuoi. AI uoc luong chuoi thiet hai nho nhat va phat ben dang di.

Day la heuristic quan trong khi danh voi bot manh: khong chi xem ai dang hon diem, ma xem ai sap bi buoc phai mo qua cho doi thu.

## 10. Minimax va Alpha-Beta

Ham `minimax(state, depth, alpha, beta, ai_player)` la ham tim kiem de quy.

Cac buoc chinh:

1. Kiem tra deadline bang `_time_up()`. Neu het gio, tra ve heuristic va danh dau `_search_timed_out`.
2. Neu game ket thuc, tra ve hieu so diem nhan 10000.
3. Lay forcing moves bang `get_forcing_moves()`.
4. Neu `depth <= 0` va khong co forcing move, dung `evaluate()`.
5. Tra cuu transposition table.
6. Xac dinh node max/min theo `state.current_player == ai_player`.
7. Neu co forcing move, chi search forcing move.
8. Neu khong, lay legal moves va loc/sap xep bang `_order_moves()`.
9. Thu tung move bang `apply_move()`.
10. Neu move an duoc o, `current_player` khong doi, vi vay depth khong giam. Neu doi luot, depth giam 1.
11. Goi de quy `minimax()`.
12. Undo move bang `undo_move()`.
13. Cap nhat `alpha`, `beta`, cat nhanh khi `alpha >= beta`.
14. Luu ket qua vao transposition table neu khong bi timeout.

## 11. Transposition Table

`_tt` la dictionary cache ket qua search.

Key duoc tao boi `_state_key()`:

```python
(h_edges, v_edges, boxes, current_player, score_player1, score_player2)
```

Viec them `boxes` va diem so vao key la quan trong, vi trong Dots and Boxes cung mot tap canh co the gan voi diem/owner khac nhau tuy thu tu an o.

Moi entry luu:

```python
(depth, score, flag, best_move_key)
```

`flag` co 3 loai:

| Flag | Y nghia |
|---|---|
| `EXACT` | Diem chinh xac o depth do |
| `LOWERBOUND` | Diem thuc te >= score |
| `UPPERBOUND` | Diem thuc te <= score |

## 12. Iterative deepening va deadline

`get_best_move()` khong search thang mot depth lon. Thay vao do no chay tu depth 1 den `max_depth`.

Sau moi depth:

- Neu tim duoc move tot hon, cap nhat `best_move`.
- Neu diem rat lon (`abs(score) >= 9000`), xem nhu thay ket qua chac chan va dung.
- Neu uoc luong vong sau vuot `time_limit`, dung.
- Neu minimax cham deadline noi bo, dung va tra ve best move cua depth truoc.

Deadline noi bo dung cac bien:

- `_search_deadline`
- `_search_timed_out`
- `_time_up()`

Nho do AI khong chi kiem tra thoi gian giua cac iteration, ma con co the thoat trong luc dang de quy.

## 13. Adaptive depth theo kich thuoc va giai doan

Neu user khong truyen `base_depth`, AI tu chon theo so o:

| So o | Base depth |
|---:|---:|
| `<= 9` | 8 |
| `<= 16` | 6 |
| `<= 25` | 5 |
| `<= 36` | 4 |
| Lon hon | 3 |

Sau do `_get_adaptive_depth()` tang depth khi so move con lai it:

| `moves_remaining` | Depth toi da |
|---:|---:|
| `<= 10` | `min(remaining, 22)` |
| `<= 16` | `base_depth + 4` |
| `<= 22` | `base_depth + 2` |
| `<= 30` | `base_depth + 1` |
| Lon hon | `base_depth` |

Y tuong: dau game va ban lon can pruning manh; cuoi game it move hon nen co the search sau.

## 14. Diem manh va gioi han

Diem manh:

- Tranh mo o 3 canh khi van con safe move.
- Biet uoc luong thiet hai khi buoc phai mo chuoi.
- Co phan tich chain/loop va parity cho endgame.
- Co deadline noi bo de tranh treo UI.
- Chay duoc tren ban 4x4, 6x6, 7x7 nho candidate pruning.

Gioi han:

- Chua phai solver tuyet doi cho moi kich thuoc board.
- Phan tich Nimstring moi o muc heuristic, chua tinh day du Sprague-Grundy/nimber.
- Double-cross hien duoc sinh o mot so diem toi han, chua bao phu tat ca chien thuat endgame nang cao.
- Ket qua phu thuoc vao `time_limit` va do sau search thuc te.

## 15. Tom tat ngan gon

AI hien tai co the hieu theo mot cau:

> Neu co o an duoc thi xem cac nuoc ep buoc; neu khong co thi chi choi safe move; neu het safe move thi mo chuoi it thiet hai nhat; tat ca duoc danh gia bang minimax, chain heuristic, transposition table va deadline thoi gian.
