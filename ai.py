"""
ai.py — Dots and Boxes AI
==========================
Được nâng cấp và sửa lỗi toàn diện dựa trên lý thuyết Berlekamp's Chain:
1. Pha 1: Minimax trên Safe moves (Cố gắng kiểm soát Parity).
2. Pha 2: Ăn tham (Greedy) hoặc Hy sinh (Sacrifice/Double-cross) chuẩn xác.
"""

import math
import time
from models import GameState, Move
from rules import apply_move, undo_move, is_terminal, get_affected_boxes

# ============================================================
#  Transposition Table
# ============================================================
EXACT      = 0
LOWERBOUND = 1
UPPERBOUND = 2

_tt: dict = {}
_TT_MAX    = 300_000

def _tt_clear():
    global _tt
    _tt = {}

def _state_key(state: GameState):
    h = tuple(tuple(row) for row in state.h_edges)
    v = tuple(tuple(row) for row in state.v_edges)
    return (h, v, state.current_player)

# ============================================================
#  CƠ BẢN: Helper functions
# ============================================================
def get_legal_moves(state: GameState):
    moves = []
    for r in range(state.rows + 1):
        for c in range(state.cols):
            if not state.h_edges[r][c]:
                moves.append(Move('H', r, c))
    for r in range(state.rows):
        for c in range(state.cols + 1):
            if not state.v_edges[r][c]:
                moves.append(Move('V', r, c))
    return moves

def _creates_third_edge(state: GameState, move: Move) -> int:
    """Đếm số box sẽ bị biến thành 3 cạnh (nguy hiểm) nếu đi nước này."""
    count = 0
    for br, bc in get_affected_boxes(move, state.rows, state.cols):
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 2:
            count += 1
    return count

def _get_safe_moves(state: GameState):
    """Nước đi KHÔNG tạo ra box 3 cạnh cho đối thủ."""
    return [m for m in get_legal_moves(state) if _creates_third_edge(state, m) == 0]

def _box_neighbors_edge_status(state: GameState, r: int, c: int):
    """Trả về danh sách 4 láng giềng: [(nr, nc, edge_is_drawn)]"""
    rows, cols = state.rows, state.cols
    res = []
    if r > 0: res.append((r - 1, c, bool(state.h_edges[r][c])))
    if r < rows - 1: res.append((r + 1, c, bool(state.h_edges[r + 1][c])))
    if c > 0: res.append((r, c - 1, bool(state.v_edges[r][c])))
    if c < cols - 1: res.append((r, c + 1, bool(state.v_edges[r][c + 1])))
    return res

def _get_missing_edge(state: GameState, br: int, bc: int):
    """Lấy cạnh chưa vẽ duy nhất của box."""
    if not state.h_edges[br][bc]: return Move('H', br, bc)
    if not state.h_edges[br + 1][bc]: return Move('H', br + 1, bc)
    if not state.v_edges[br][bc]: return Move('V', br, bc)
    if not state.v_edges[br][bc + 1]: return Move('V', br, bc + 1)
    return None

def _get_shared_undrawn_edge(state: GameState, r1: int, c1: int, r2: int, c2: int):
    """Cạnh chung CHƯA VẼ giữa 2 box."""
    if r1 == r2:
        col = max(c1, c2)
        if not state.v_edges[r1][col]: return Move('V', r1, col)
    elif c1 == c2:
        row = max(r1, r2)
        if not state.h_edges[row][c1]: return Move('H', row, c1)
    return None

# ============================================================
#  PHÂN TÍCH CHAIN / LOOPS (Berlekamp Nimstring Theory)
# ============================================================
def _count_long_regions(state: GameState) -> int:
    """
    Đếm số lượng 'Long Regions' (Chain dài >= 3 hoặc Loop dài >= 4) CHƯA BỊ MỞ.
    Đây chính là biến N cực kỳ quan trọng để quyết định Parity.
    """
    rows, cols = state.rows, state.cols
    visited = [[False] * cols for _ in range(rows)]
    long_count = 0

    for sr in range(rows):
        for sc in range(cols):
            if visited[sr][sc] or state.boxes[sr][sc] != 0:
                continue
            # Nếu box có 3 cạnh -> Nó đang bị ăn, KHÔNG tính vào Unopened Regions
            if state.edges_count[sr][sc] >= 3:
                visited[sr][sc] = True
                continue

            comp = []
            queue = [(sr, sc)]
            visited[sr][sc] = True
            has_3_edge = False

            while queue:
                r, c = queue.pop(0)
                comp.append((r, c))
                if state.edges_count[r][c] == 3:
                    has_3_edge = True

                for nr, nc, drawn in _box_neighbors_edge_status(state, r, c):
                    if not drawn and not visited[nr][nc] and state.boxes[nr][nc] == 0:
                        if state.edges_count[nr][nc] == 3:
                            has_3_edge = True
                        visited[nr][nc] = True
                        queue.append((nr, nc))

            if has_3_edge:
                continue

            n = len(comp)
            if n < 3: continue

            # Check xem có phải là Loop vòng kín không
            comp_set = set(comp)
            is_loop = True
            for r, c in comp:
                deg = sum(1 for nr, nc, d in _box_neighbors_edge_status(state, r, c) if not d and (nr, nc) in comp_set)
                if deg != 2:
                    is_loop = False
                    break

            if (is_loop and n >= 4) or (not is_loop and n >= 3):
                long_count += 1

    return long_count

def _analyze_capturable_component(state: GameState, sr: int, sc: int):
    """Tìm toàn bộ các box trong chain đang bị ăn (Opened Chain)."""
    comp = []
    visited = set()
    queue = [(sr, sc)]
    visited.add((sr, sc))

    while queue:
        r, c = queue.pop(0)
        comp.append((r, c))
        for nr, nc, drawn in _box_neighbors_edge_status(state, r, c):
            if not drawn and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc))

    # Trong một Opened Loop, sẽ có đúng 2 box sở hữu 3 cạnh ở 2 đầu
    three_edge_boxes = [(r, c) for r, c in comp if state.edges_count[r][c] == 3]
    is_opened_loop = (len(three_edge_boxes) == 2)
    sacrifice_size = 4 if is_opened_loop else 2

    return comp, len(comp), is_opened_loop, sacrifice_size, three_edge_boxes

def _get_sacrifice_edge(state: GameState, comp: list, is_opened_loop: bool):
    """Tìm Nước đi Hy sinh (Double-cross move) cực chuẩn."""
    if not is_opened_loop and len(comp) == 2:
        # Với chuỗi thẳng 2 ô: Cắt cạnh ngoài cùng của ô có 2 cạnh
        box_A = None
        box_B = None
        for r, c in comp:
            if state.edges_count[r][c] == 3: box_A = (r, c)
            else: box_B = (r, c)

        if box_B:
            # Lấy các láng giềng chưa vẽ của B, trừ láng giềng A
            for r_adj, c_adj, drawn in _box_neighbors_edge_status(state, box_B[0], box_B[1]):
                if not drawn and (r_adj, c_adj) != box_A:
                    return _get_shared_undrawn_edge(state, box_B[0], box_B[1], r_adj, c_adj)
            
            # Trúng biên bàn cờ
            br, bc = box_B
            shared = _get_shared_undrawn_edge(state, box_A[0], box_A[1], br, bc)
            edges = [
                (Move('H', br, bc), state.h_edges[br][bc]),
                (Move('H', br+1, bc), state.h_edges[br+1][bc]),
                (Move('V', br, bc), state.v_edges[br][bc]),
                (Move('V', br, bc+1), state.v_edges[br][bc+1])
            ]
            for move, drawn in edges:
                if not drawn:
                    if shared and move.edge_type == shared.edge_type and move.r == shared.r and move.c == shared.c:
                        continue
                    return move

    elif is_opened_loop and len(comp) == 4:
        # Với Loop 4 ô: Cắt cạnh chung giữa 2 ô đang có 2 cạnh
        boxes_2_edges = [(r, c) for r, c in comp if state.edges_count[r][c] == 2]
        if len(boxes_2_edges) == 2:
            b1, b2 = boxes_2_edges
            shared = _get_shared_undrawn_edge(state, b1[0], b1[1], b2[0], b2[1])
            if shared: return shared

    # Dự phòng an toàn: Cứ ăn tham
    return _get_missing_edge(state, comp[0][0], comp[0][1])

def _decide_and_get_first_move(state: GameState) -> Move:
    """Hàm lõi cho Pha 2 - Khi đã có box để ăn."""
    start_box = None
    for r in range(state.rows):
        for c in range(state.cols):
            if state.boxes[r][c] == 0 and state.edges_count[r][c] == 3:
                start_box = (r, c)
                break
        if start_box: break

    if not start_box: return None

    comp, n, is_opened_loop, sacrifice_size, three_edge_boxes = _analyze_capturable_component(state, start_box[0], start_box[1])

    if n > sacrifice_size:
        # Tham lam: Chưa đến ngưỡng hi sinh, cứ ăn tiếp!
        return _get_missing_edge(state, three_edge_boxes[0][0], three_edge_boxes[0][1])
    elif n == sacrifice_size:
        # Tại điểm quyết định: Kiểm tra Parity để xem có nên hi sinh không
        N_remaining = _count_long_regions(state)
        do_sacrifice = (N_remaining % 2 == 1) # Nếu LẺ -> Mình bất lợi -> BUỘC PHẢI HY SINH

        if do_sacrifice:
            return _get_sacrifice_edge(state, comp, is_opened_loop)
        else:
            return _get_missing_edge(state, three_edge_boxes[0][0], three_edge_boxes[0][1])
    else:
        # Quá ngắn không thể hy sinh
        return _get_missing_edge(state, three_edge_boxes[0][0], three_edge_boxes[0][1])

# ============================================================
#  PHA 2: Mở Chain (Forced Opening)
# ============================================================
def _best_forced_opening(state: GameState):
    """Không còn lựa chọn an toàn, buộc phải tự mở 1 chain cho đối thủ."""
    rows, cols = state.rows, state.cols
    visited = [[False] * cols for _ in range(rows)]
    chains = []

    for sr in range(rows):
        for sc in range(cols):
            if visited[sr][sc] or state.boxes[sr][sc] != 0 or state.edges_count[sr][sc] >= 3:
                continue

            comp = []
            queue = [(sr, sc)]
            visited[sr][sc] = True
            while queue:
                r, c = queue.pop(0)
                comp.append((r, c))
                for nr, nc, drawn in _box_neighbors_edge_status(state, r, c):
                    if not drawn and not visited[nr][nc] and state.boxes[nr][nc] == 0 and state.edges_count[nr][nc] < 3:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

            chains.append(comp)

    if not chains:
        legal = get_legal_moves(state)
        return legal[0] if legal else None

    # Ưu tiên mở các chuỗi ngắn nhất (tốt nhất là <= 2 box) để đối thủ không hy sinh được
    chains.sort(key=len)
    short_chains = [c for c in chains if len(c) <= 2]
    
    if short_chains:
        best_comp = short_chains[0]
        best_cell = min(best_comp, key=lambda rc: state.edges_count[rc[0]][rc[1]])
        return _get_missing_edge(state, best_cell[0], best_cell[1]) or _pick_opening_edge(state, best_cell[0], best_cell[1])

    # Nếu buộc phải mở chuỗi dài, dùng Minimax 1-ply để chọn chuỗi ít bất lợi nhất
    N_current = _count_long_regions(state)
    best_move = None
    best_parity = -999

    for comp in chains:
        best_cell = min(comp, key=lambda rc: state.edges_count[rc[0]][rc[1]])
        move = _pick_opening_edge(state, best_cell[0], best_cell[1])
        if not move: continue
        
        N_after = N_current - 1
        advantage = 1 if (N_after % 2 == 1) else -1
        
        if advantage > best_parity:
            best_parity = advantage
            best_move = move

    return best_move if best_move else _pick_opening_edge(state, chains[0][0][0], chains[0][0][1])

def _pick_opening_edge(state: GameState, br: int, bc: int):
    if not state.h_edges[br][bc]: return Move('H', br, bc)
    if not state.h_edges[br + 1][bc]: return Move('H', br + 1, bc)
    if not state.v_edges[br][bc]: return Move('V', br, bc)
    if not state.v_edges[br][bc + 1]: return Move('V', br, bc + 1)
    return None

# ============================================================
#  PHA 1: MINIMAX (Đánh giá cục diện)
# ============================================================
def _evaluate(state: GameState, ai_player: int) -> float:
    """Hàm đánh giá cục diện. Ưu tiên kiểm soát Parity thay vì chỉ đếm điểm."""
    score_diff = state.score_player1 - state.score_player2
    if ai_player == 2:
        score_diff = -score_diff

    N = _count_long_regions(state)
    is_ai_turn = (state.current_player == ai_player)

    # N CHẴN -> ai mở trước (current_player) BẤT LỢI
    # N LẺ -> ai mở trước (current_player) CÓ LỢI
    if N % 2 == 1:
        parity_advantage = 100 if is_ai_turn else -100
    else:
        parity_advantage = -100 if is_ai_turn else 100

    boxes_2 = sum(1 for r in range(state.rows) for c in range(state.cols)
                  if state.boxes[r][c] == 0 and state.edges_count[r][c] == 2)

    return score_diff * 1000 + parity_advantage - boxes_2 * 5

def _minimax_phase1(state: GameState, depth: int, alpha: float, beta: float, ai_player: int):
    global _tt

    if is_terminal(state):
        diff = state.score_player1 - state.score_player2
        return (diff * 10000 if ai_player == 1 else -diff * 10000), None

    safe_moves = _get_safe_moves(state)
    if not safe_moves or depth <= 0:
        return _evaluate(state, ai_player), None

    alpha_orig = alpha
    key = _state_key(state)
    
    if key in _tt:
        tt_depth, tt_score, tt_flag, tt_mk = _tt[key]
        if tt_depth >= depth:
            if tt_flag == EXACT: return tt_score, None
            elif tt_flag == LOWERBOUND: alpha = max(alpha, tt_score)
            elif tt_flag == UPPERBOUND: beta = min(beta, tt_score)
            if alpha >= beta: return tt_score, None

    is_max = (state.current_player == ai_player)
    best_val = -math.inf if is_max else math.inf
    best_move = safe_moves[0]

    for m in safe_moves:
        undo = apply_move(state, m)
        val, _ = _minimax_phase1(state, depth - 1, alpha, beta, ai_player)
        undo_move(state, m, undo)

        if is_max:
            if val > best_val: best_val, best_move = val, m
            alpha = max(alpha, val)
        else:
            if val < best_val: best_val, best_move = val, m
            beta = min(beta, val)
        if alpha >= beta: break

    if len(_tt) < _TT_MAX:
        flag = EXACT
        if best_val <= alpha_orig: flag = UPPERBOUND
        elif best_val >= beta - 1: flag = LOWERBOUND
        _tt[key] = (depth, best_val, flag, None)

    return best_val, best_move

# ============================================================
#  HÀM GỌI CHÍNH
# ============================================================
def get_best_move(state: GameState, ai_player: int = 2, base_depth: int = None, time_limit: float = 3.0) -> Move:
    _tt_clear()
    start_time = time.time()

    if base_depth is None:
        total = state.rows * state.cols
        if total <= 16: base_depth = 6
        elif total <= 36: base_depth = 4
        else: base_depth = 3

    # Bước 1: Nếu có hộp ăn ngay được -> Xử lý chuỗi (Ăn hoặc Hy sinh)
    capture_move = _decide_and_get_first_move(state)
    if capture_move:
        return capture_move

    # Bước 2: Tìm nước đi an toàn (Pha 1)
    safe_moves = _get_safe_moves(state)
    if safe_moves:
        best_move = safe_moves[0]
        # Iterative Deepening
        for d in range(1, base_depth + 1):
            if time.time() - start_time > time_limit * 0.8: break
            val, move = _minimax_phase1(state, d, -math.inf, math.inf, ai_player)
            if move: best_move = move
            if abs(val) > 9000: break
        return best_move

    # Bước 3: Không còn nước an toàn, buộc mở Chain (Pha 2)
    return _best_forced_opening(state)