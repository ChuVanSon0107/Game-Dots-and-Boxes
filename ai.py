"""
ai.py — Dots and Boxes AI (Grandmaster Edition)
==========================
Được nâng cấp và sửa lỗi toàn diện dựa trên lý thuyết Berlekamp's Chain:
1. Hard-Hearted Handout: Ép đối thủ phải ăn chuỗi 2 và mở chuỗi tiếp theo.
2. Perfect Parity Predictor: Minimax mô phỏng trước kết quả cuối game từ Pha 1.
3. Iterative Deepening & Transposition Table siêu tốc.
"""

import math
import time
from models import GameState, Move
from rules import apply_move, undo_move, is_terminal, get_affected_boxes

EXACT      = 0
LOWERBOUND = 1
UPPERBOUND = 2

_tt: dict = {}
_TT_MAX    = 500_000

def _tt_clear():
    global _tt
    _tt = {}

def _state_key(state: GameState):
    h = tuple(tuple(row) for row in state.h_edges)
    v = tuple(tuple(row) for row in state.v_edges)
    return (h, v, state.current_player)

def get_legal_moves(state: GameState):
    moves = []
    for r in range(state.rows + 1):
        for c in range(state.cols):
            if not state.h_edges[r][c]: moves.append(Move('H', r, c))
    for r in range(state.rows):
        for c in range(state.cols + 1):
            if not state.v_edges[r][c]: moves.append(Move('V', r, c))
    return moves

def _creates_third_edge(state: GameState, move: Move) -> int:
    count = 0
    for br, bc in get_affected_boxes(move, state.rows, state.cols):
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 2:
            count += 1
    return count

def _get_safe_moves(state: GameState):
    return [m for m in get_legal_moves(state) if _creates_third_edge(state, m) == 0]

def _box_neighbors_edge_status(state: GameState, r: int, c: int):
    rows, cols = state.rows, state.cols
    res = []
    if r > 0: res.append((r - 1, c, bool(state.h_edges[r][c])))
    if r < rows - 1: res.append((r + 1, c, bool(state.h_edges[r + 1][c])))
    if c > 0: res.append((r, c - 1, bool(state.v_edges[r][c])))
    if c < cols - 1: res.append((r, c + 1, bool(state.v_edges[r][c + 1])))
    return res

def _get_missing_edge(state: GameState, br: int, bc: int):
    if not state.h_edges[br][bc]: return Move('H', br, bc)
    if not state.h_edges[br + 1][bc]: return Move('H', br + 1, bc)
    if not state.v_edges[br][bc]: return Move('V', br, bc)
    if not state.v_edges[br][bc + 1]: return Move('V', br, bc + 1)
    return None

def _get_shared_undrawn_edge(state: GameState, r1: int, c1: int, r2: int, c2: int):
    if r1 == r2:
        col = max(c1, c2)
        if not state.v_edges[r1][col]: return Move('V', r1, col)
    elif c1 == c2:
        row = max(r1, r2)
        if not state.h_edges[row][c1]: return Move('H', row, c1)
    return None

def _find_all_chains_info(state: GameState):
    """Tìm tất cả các chuỗi chưa bị mở."""
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

            # Xác định xem chuỗi này có phải là vòng kín (Loop) hay không
            comp_set = set(comp)
            is_loop = True
            for r, c in comp:
                deg = sum(1 for nr, nc, d in _box_neighbors_edge_status(state, r, c) if not d and (nr, nc) in comp_set)
                if deg != 2:
                    is_loop = False
                    break

            chains.append((comp, is_loop))
    return chains

def _predict_phase2_score(state: GameState, ai_player: int) -> float:
    """Mô phỏng toán học kết quả ván đấu nếu không còn nước an toàn."""
    score_p1 = state.score_player1
    score_p2 = state.score_player2
    
    chains = _find_all_chains_info(state)
    short_chains = []
    long_chains = []
    for cells, is_loop in chains:
        n = len(cells)
        if (is_loop and n >= 4) or (not is_loop and n >= 3):
            long_chains.append(n)
        else:
            short_chains.append(n)
            
    short_chains.sort()
    current_turn = state.current_player
    
    # 1. Hai bên luân phiên nhét chuỗi ngắn cho nhau
    for length in short_chains:
        opponent = 2 if current_turn == 1 else 1
        if opponent == 1: score_p1 += length
        else: score_p2 += length
        current_turn = opponent # Đẩy lượt cho đối thủ
        
    # 2. Xử lý các chuỗi dài
    N = len(long_chains)
    if N > 0:
        long_loser = current_turn
        
        total_long_points = sum(long_chains)
        loser_points = 2 * (N - 1)
        winner_points = total_long_points - loser_points
        
        if long_loser == 1:
            score_p1 += loser_points
            score_p2 += winner_points
        else:
            score_p2 += loser_points
            score_p1 += winner_points

    # 3. Phạt nhẹ các ô có 2 cạnh để tránh AI tạo rủi ro trong Pha 1
    boxes_2 = sum(1 for r in range(state.rows) for c in range(state.cols)
                  if state.boxes[r][c] == 0 and state.edges_count[r][c] == 2)

    score_diff = score_p1 - score_p2
    if ai_player == 2: score_diff = -score_diff
    
    return score_diff * 1000 - boxes_2 * 10

def _open_chain(state: GameState, comp: list, is_loop: bool) -> Move:
    """Hàm lõi khắc phục lỗi: Cách mở chuỗi an toàn nhất."""
    n = len(comp)
    if n == 1:
        return _get_missing_edge(state, comp[0][0], comp[0][1])
    
    if n == 2 and not is_loop:
        # CỰC KỲ QUAN TRỌNG: Mở chuỗi 2 bằng cách VẼ CẠNH CHUNG (Hard-Hearted Handout)
        # Nước đi này ép cả 2 ô thành 3 cạnh, buộc đối thủ phải ăn và mở chuỗi tiếp theo.
        r1, c1 = comp[0]
        r2, c2 = comp[1]
        shared = _get_shared_undrawn_edge(state, r1, c1, r2, c2)
        if shared: return shared
        return _get_missing_edge(state, r1, c1)
        
    if not is_loop:
        # Mở chuỗi dài: Tìm ô ở đầu mút (chỉ có 1 cạnh chung với chuỗi) và cắt cạnh ngoài
        for r, c in comp:
            shared_count = sum(1 for nr, nc, d in _box_neighbors_edge_status(state, r, c) if not d and (nr, nc) in comp)
            if shared_count == 1:
                for move, drawn in [
                    (Move('H', r, c), state.h_edges[r][c]),
                    (Move('H', r+1, c), state.h_edges[r+1][c]),
                    (Move('V', r, c), state.v_edges[r][c]),
                    (Move('V', r, c+1), state.v_edges[r][c+1])
                ]:
                    if not drawn:
                        nr, nc = r, c
                        if move.edge_type == 'H': nr = r - 1 if move.r == r else r + 1
                        else: nc = c - 1 if move.c == c else c + 1
                        if (nr, nc) not in comp:
                            return move
        return _get_missing_edge(state, comp[0][0], comp[0][1])
    else:
        # Vòng kín: Cắt ngẫu nhiên 1 cạnh
        return _get_missing_edge(state, comp[0][0], comp[0][1])

def _best_forced_opening(state: GameState):
    """Pha 2: Không còn nước an toàn, buộc phải tự mở 1 chain cho đối thủ."""
    chains = _find_all_chains_info(state)
    if not chains:
        legal = get_legal_moves(state)
        return legal[0] if legal else None

    # Ưu tiên mở các chuỗi ngắn nhất trước
    chains.sort(key=lambda x: len(x[0]))
    short_chains = [c for c in chains if len(c[0]) <= 2]
    
    if short_chains:
        return _open_chain(state, short_chains[0][0], short_chains[0][1])

    # Nếu buộc phải mở chuỗi dài, mở chuỗi ngắn nhất trong số các chuỗi dài
    return _open_chain(state, chains[0][0], chains[0][1])

def _analyze_capturable_component(state: GameState, sr: int, sc: int):
    """Phân tích chuỗi đang bị ăn."""
    comp = []
    visited = set()
    queue = [(sr, sc)]
    visited.add((sr, sc))

    while queue:
        r, c = queue.pop(0)
        comp.append((r, c))
        for nr, nc, drawn in _box_neighbors_edge_status(state, r, c):
            if not drawn and (nr, nc) not in visited and state.boxes[nr][nc] == 0:
                visited.add((nr, nc))
                queue.append((nr, nc))

    three_edge_boxes = [(r, c) for r, c in comp if state.edges_count[r][c] == 3]
    is_opened_loop = (len(three_edge_boxes) == 2)
    sacrifice_size = 4 if is_opened_loop else 2

    return comp, len(comp), is_opened_loop, sacrifice_size, three_edge_boxes

def _get_sacrifice_edge(state: GameState, comp: list, is_opened_loop: bool):
    """Tìm nước đi nhả xương (Double-cross)."""
    if not is_opened_loop and len(comp) == 2:
        box_A = box_B = None
        for r, c in comp:
            if state.edges_count[r][c] == 3: box_A = (r, c)
            else: box_B = (r, c)

        if box_B:
            for r_adj, c_adj, drawn in _box_neighbors_edge_status(state, box_B[0], box_B[1]):
                if not drawn and (r_adj, c_adj) != box_A:
                    return _get_shared_undrawn_edge(state, box_B[0], box_B[1], r_adj, c_adj)
            
            br, bc = box_B
            shared = _get_shared_undrawn_edge(state, box_A[0], box_A[1], br, bc)
            edges = [
                (Move('H', br, bc), state.h_edges[br][bc]),
                (Move('H', br+1, bc), state.h_edges[br+1][bc]),
                (Move('V', br, bc), state.v_edges[br][bc]),
                (Move('V', br, bc+1), state.v_edges[br][bc+1])
            ]
            for move, drawn in edges:
                if not drawn and (not shared or (move.edge_type != shared.edge_type or move.r != shared.r or move.c != shared.c)):
                    return move

    elif is_opened_loop and len(comp) == 4:
        boxes_2_edges = [(r, c) for r, c in comp if state.edges_count[r][c] == 2]
        if len(boxes_2_edges) == 2:
            b1, b2 = boxes_2_edges
            shared = _get_shared_undrawn_edge(state, b1[0], b1[1], b2[0], b2[1])
            if shared: return shared

    return _get_missing_edge(state, comp[0][0], comp[0][1])

def _decide_and_get_first_move(state: GameState) -> Move:
    """Kiểm tra có ô nào ăn được không, quyết định ăn tham hay hy sinh."""
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
        return _get_missing_edge(state, three_edge_boxes[0][0], three_edge_boxes[0][1])
    elif n == sacrifice_size:
        # Kiểm tra Parity: Đếm số lượng chuỗi dài còn lại trên bàn cờ
        N_remaining = sum(1 for c, is_l in _find_all_chains_info(state) if (is_l and len(c)>=4) or (not is_l and len(c)>=3))
        if N_remaining % 2 == 1:
            return _get_sacrifice_edge(state, comp, is_opened_loop)
    
    # Rơi vào trường hợp n < sacrifice_size (Do đối thủ đã hy sinh trước) -> Bắt buộc ăn tham
    return _get_missing_edge(state, three_edge_boxes[0][0], three_edge_boxes[0][1])

def _order_moves(state: GameState, moves: list):
    scored_moves = []
    for m in moves:
        penalty = 0
        for br, bc in get_affected_boxes(m, state.rows, state.cols):
            if state.edges_count[br][bc] == 1: penalty += 1 
        scored_moves.append((penalty, m))
    scored_moves.sort(key=lambda x: x[0])
    return [m for _, m in scored_moves]

def _minimax_phase1(state: GameState, depth: int, alpha: float, beta: float, ai_player: int):
    global _tt

    if is_terminal(state):
        diff = state.score_player1 - state.score_player2
        return (diff * 10000 if ai_player == 1 else -diff * 10000), None

    safe_moves = _get_safe_moves(state)
    if not safe_moves or depth <= 0:
        return _predict_phase2_score(state, ai_player), None

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
    
    ordered_moves = _order_moves(state, safe_moves)
    best_move = ordered_moves[0]

    for m in ordered_moves:
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

def get_best_move(state: GameState, ai_player: int = 2, base_depth: int = None, time_limit: float = 2.0) -> Move:
    _tt_clear()
    start_time = time.time()

    # Bước 1: Có ô để ăn không?
    capture_move = _decide_and_get_first_move(state)
    if capture_move: return capture_move

    # Bước 2: Tìm nước đi an toàn tối ưu (Pha 1)
    safe_moves = _get_safe_moves(state)
    if safe_moves:
        best_move = safe_moves[0]
        d = 1
        # Lặn sâu Iterative Deepening theo thời gian thực để tìm đường tốt nhất
        while time.time() - start_time < time_limit and d <= 30:
            val, move = _minimax_phase1(state, d, -math.inf, math.inf, ai_player)
            if move: best_move = move
            if abs(val) > 9000: break
            d += 1
        return best_move

    # Bước 3: Không còn nước an toàn, BẮT BUỘC NHẢ XƯƠNG (Pha 2)
    return _best_forced_opening(state)