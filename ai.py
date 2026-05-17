import math
from models import GameState, Move
from rules import get_affected_boxes, apply_move, undo_move, is_terminal


# ============================================================
#  Transposition Table
# ============================================================
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

_tt = {}          # {state_key: (depth, score, flag, best_move_key)}
_tt_max = 500000  # Giới hạn kích thước TT


def _state_key(state: GameState):
    """Tạo hashable key từ trạng thái bàn cờ cho transposition table."""
    h = tuple(val for row in state.h_edges for val in row)
    v = tuple(val for row in state.v_edges for val in row)
    return (h, v, state.current_player)


def _move_key(move: Move):
    """Tạo hashable key cho nước đi."""
    return (move.edge_type, move.r, move.c)


def _key_to_move(key):
    """Chuyển key thành Move object."""
    return Move(key[0], key[1], key[2])


# ============================================================
#  Utility helpers
# ============================================================

def get_legal_moves(state: GameState):
    """
    Sinh toàn bộ nước đi hợp lệ từ trạng thái hiện tại
    """
    moves = []

    # Ngang
    for r in range(state.rows + 1):
        for c in range(state.cols):
            if not state.h_edges[r][c]:
                moves.append(Move('H', r, c))

    # Dọc
    for r in range(state.rows):
        for c in range(state.cols + 1):
            if not state.v_edges[r][c]:
                moves.append(Move('V', r, c))

    return moves


def would_complete_box(state: GameState, move: Move):
    """
    Kiểm tra nước đi có ăn box ngay không (Trả về số box hoàn thành)
    """
    completed = 0
    affected = get_affected_boxes(move, state.rows, state.cols)

    for br, bc in affected:
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 3:
            completed += 1

    return completed


def would_create_third_edge(state: GameState, move: Move):
    """
    Kiểm tra nước đi này có làm tạo ra box 3 cạnh cho đối thủ không
    (Trả về số cạnh 3 tạo ra).
    """
    created = 0
    affected = get_affected_boxes(move, state.rows, state.cols)

    for br, bc in affected:
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 2:
            created += 1

    return created


def get_safe_moves(state: GameState):
    """
    Tìm nước đi an toàn: Lọc từ danh sách nước đi hợp lệ những nước
    KHÔNG tạo ra cạnh 3.
    """
    moves = []

    legal_moves = get_legal_moves(state)

    for move in legal_moves:
        if would_create_third_edge(state, move) == 0:
            moves.append(move)

    return moves


# ============================================================
#  Force-capture: Tối ưu hóa quan trọng nhất cho Dots and Boxes
# ============================================================

def _force_captures(state: GameState):
    """
    Ăn tất cả các box có thể ăn (greedy).

    Trong D&B, ăn box LUÔN là nước đi tối ưu vì:
    - Được +1 điểm
    - Được đi thêm lượt

    Bằng cách ăn hết trước khi phân nhánh, ta loại bỏ hoàn toàn
    các nhánh capture ra khỏi cây minimax → giảm branching factor cực lớn.

    Returns: list of (move, undo_info) - để hoàn tác sau
    """
    captures = []
    while True:
        found = False
        # Tìm nước ăn box trong cạnh ngang
        for r in range(state.rows + 1):
            for c in range(state.cols):
                if not state.h_edges[r][c]:
                    move = Move('H', r, c)
                    if would_complete_box(state, move) > 0:
                        undo_info = apply_move(state, move)
                        captures.append((move, undo_info))
                        found = True
                        break
            if found:
                break

        if found:
            continue

        # Tìm nước ăn box trong cạnh dọc
        for r in range(state.rows):
            for c in range(state.cols + 1):
                if not state.v_edges[r][c]:
                    move = Move('V', r, c)
                    if would_complete_box(state, move) > 0:
                        undo_info = apply_move(state, move)
                        captures.append((move, undo_info))
                        found = True
                        break
            if found:
                break

        if not found:
            break

    return captures


def _undo_captures(state: GameState, captures: list):
    """Hoàn tác chuỗi force-capture theo thứ tự ngược."""
    for move, undo_info in reversed(captures):
        undo_move(state, move, undo_info)


# ============================================================
#  Heuristic evaluation function
# ============================================================

def evaluate(state: GameState, ai_player: int):
    """
    Hàm đánh giá trạng thái bàn cờ cho thuật toán Minimax.
    """
    # Hiệu số điểm trực tiếp
    if ai_player == 1:
        score_diff = state.score_player1 - state.score_player2
    else:
        score_diff = state.score_player2 - state.score_player1

    # Đếm ô theo số cạnh
    capturable = 0
    boxes_2 = 0

    for r in range(state.rows):
        for c in range(state.cols):
            if state.boxes[r][c] == 0:
                ec = state.edges_count[r][c]
                if ec == 3:
                    capturable += 1
                elif ec == 2:
                    boxes_2 += 1

    # Ô 3 cạnh: có lợi nếu lượt mình, bất lợi nếu lượt đối thủ
    if state.current_player == ai_player:
        cap_score = capturable * 50
    else:
        cap_score = -capturable * 50

    # Chain analysis
    chain_score = _evaluate_chains(state, ai_player)

    return score_diff * 100 + cap_score + chain_score * 8 - boxes_2 * 2


def _evaluate_chains(state: GameState, ai_player: int):
    """Phân tích chuỗi (chain) – chiến thuật endgame."""
    rows, cols = state.rows, state.cols
    visited = [[False] * cols for _ in range(rows)]
    long_chains = 0

    for r in range(rows):
        for c in range(cols):
            if state.boxes[r][c] == 0 and state.edges_count[r][c] >= 2 and not visited[r][c]:
                chain_len = 0
                stack = [(r, c)]

                while stack:
                    cr, cc = stack.pop()
                    if visited[cr][cc]:
                        continue
                    if state.boxes[cr][cc] != 0 or state.edges_count[cr][cc] < 2:
                        continue

                    visited[cr][cc] = True
                    chain_len += 1

                    # Tìm ô kề chia sẻ cạnh chưa vẽ
                    if cr > 0 and not state.h_edges[cr][cc] and not visited[cr-1][cc]:
                        stack.append((cr - 1, cc))
                    if cr < rows - 1 and not state.h_edges[cr+1][cc] and not visited[cr+1][cc]:
                        stack.append((cr + 1, cc))
                    if cc > 0 and not state.v_edges[cr][cc] and not visited[cr][cc-1]:
                        stack.append((cr, cc - 1))
                    if cc < cols - 1 and not state.v_edges[cr][cc+1] and not visited[cr][cc+1]:
                        stack.append((cr, cc + 1))

                if chain_len >= 3:
                    long_chains += 1

    # Số chain dài chẵn → có lợi cho người đang đi
    if state.current_player == ai_player:
        return 3 * long_chains if long_chains % 2 == 0 else -3 * long_chains
    else:
        return 3 * long_chains if long_chains % 2 == 1 else -3 * long_chains


# ============================================================
#  Move ordering (sau force-capture, chỉ còn non-capture moves)
# ============================================================

def _order_moves(state: GameState, moves: list, tt_best_key=None):
    """
    Sắp xếp nước đi để alpha-beta cắt tỉa tốt hơn.

    Thứ tự:
    1. TT best move (nước tốt nhất từ lần search trước)
    2. Nước an toàn (không tạo ô 3 cạnh)
    3. Nước nguy hiểm (tạo ô 3 cạnh cho đối thủ)
    """
    tt_move = None
    safe = []
    risky = []

    for move in moves:
        mk = _move_key(move)
        if tt_best_key and mk == tt_best_key:
            tt_move = move
            continue

        third = would_create_third_edge(state, move)
        if third == 0:
            safe.append(move)
        else:
            risky.append((move, third))

    risky.sort(key=lambda x: x[1])
    ordered = safe + [m for m, _ in risky]

    # TT best move luôn được thử đầu tiên
    if tt_move:
        ordered.insert(0, tt_move)

    return ordered


# ============================================================
#  Minimax + Alpha-Beta Pruning + TT + Force-Capture
# ============================================================

def minimax(state: GameState, depth: int, alpha: float, beta: float,
            ai_player: int):
    """
    Thuật toán Minimax với:
    - Alpha-Beta Pruning
    - Transposition Table
    - Force-Capture optimization

    Returns: (score, best_move)
    """
    global _tt

    # --- Bước 1: Force-capture tất cả box có thể ăn ---
    captures = _force_captures(state)
    first_capture = captures[0][0] if captures else None

    # --- Base cases ---
    if is_terminal(state):
        if ai_player == 1:
            diff = state.score_player1 - state.score_player2
        else:
            diff = state.score_player2 - state.score_player1
        score = diff * 10000
        _undo_captures(state, captures)
        return score, first_capture

    if depth <= 0:
        score = evaluate(state, ai_player)
        _undo_captures(state, captures)
        return score, first_capture

    # --- Bước 2: Transposition Table lookup ---
    alpha_orig = alpha
    beta_orig = beta
    key = _state_key(state)
    tt_best_key = None

    if key in _tt:
        tt_depth, tt_score, tt_flag, tt_mk = _tt[key]
        if tt_depth >= depth:
            if tt_flag == EXACT:
                _undo_captures(state, captures)
                return tt_score, first_capture or _key_to_move(tt_mk)
            elif tt_flag == LOWERBOUND:
                alpha = max(alpha, tt_score)
            elif tt_flag == UPPERBOUND:
                beta = min(beta, tt_score)
            if alpha >= beta:
                _undo_captures(state, captures)
                return tt_score, first_capture or _key_to_move(tt_mk)
        # Dùng TT best move cho move ordering dù depth không đủ
        tt_best_key = tt_mk

    # --- Bước 3: Sinh nước đi (chỉ non-capture, vì đã force-capture) ---
    is_max = (state.current_player == ai_player)
    legal_moves = get_legal_moves(state)

    if not legal_moves:
        score = evaluate(state, ai_player)
        _undo_captures(state, captures)
        return score, first_capture

    ordered = _order_moves(state, legal_moves, tt_best_key)
    best_move = ordered[0]

    # --- Bước 4: Alpha-Beta search ---
    if is_max:
        best_val = -math.inf
        for move in ordered:
            undo_info = apply_move(state, move)
            # Sau force-capture, mọi move đều non-capture → luôn đổi lượt
            val, _ = minimax(state, depth - 1, alpha, beta, ai_player)
            undo_move(state, move, undo_info)

            if val > best_val:
                best_val = val
                best_move = move
            alpha = max(alpha, val)
            if alpha >= beta:
                break
    else:
        best_val = math.inf
        for move in ordered:
            undo_info = apply_move(state, move)
            val, _ = minimax(state, depth - 1, alpha, beta, ai_player)
            undo_move(state, move, undo_info)

            if val < best_val:
                best_val = val
                best_move = move
            beta = min(beta, val)
            if alpha >= beta:
                break

    # --- Bước 5: Lưu vào Transposition Table ---
    if len(_tt) < _tt_max:
        if best_val <= alpha_orig:
            flag = UPPERBOUND
        elif best_val >= beta_orig:
            flag = LOWERBOUND
        else:
            flag = EXACT
        _tt[key] = (depth, best_val, flag, _move_key(best_move))

    # --- Bước 6: Hoàn tác force-capture và trả kết quả ---
    _undo_captures(state, captures)
    return best_val, first_capture or best_move


# ============================================================
#  Adaptive depth
# ============================================================

def _get_adaptive_depth(state: GameState, base_depth: int):
    """Tự động tăng depth khi game gần kết thúc."""
    remaining = state.moves_remaining

    if remaining <= 10:
        return min(remaining, 22)
    elif remaining <= 16:
        return base_depth + 4
    elif remaining <= 22:
        return base_depth + 2
    elif remaining <= 30:
        return base_depth + 1
    else:
        return base_depth


# ============================================================
#  Public API
# ============================================================

def get_best_move(state: GameState, ai_player: int = 2, base_depth: int = None,
                   time_limit: float = 1.5):
    """
    Tìm nước đi tốt nhất cho AI bằng Minimax + Alpha-Beta Pruning.

    Tham số:
    - state: trạng thái bàn cờ hiện tại
    - ai_player: số hiệu người chơi AI (mặc định = 2)
    - base_depth: độ sâu tìm kiếm cơ bản (None = tự tính theo board size)
    - time_limit: giới hạn thời gian tính (giây, mặc định 1.5s)

    Returns:
        Move – nước đi tốt nhất tìm được
    """
    global _tt

    import time
    start_time = time.time()

    # Auto-scale depth theo kích thước board
    if base_depth is None:
        total_boxes = state.rows * state.cols
        if total_boxes <= 9:       # 3x3
            base_depth = 4
        elif total_boxes <= 16:    # 4x4
            base_depth = 3
        elif total_boxes <= 25:    # 5x5
            base_depth = 3
        elif total_boxes <= 49:    # 7x7
            base_depth = 2
        else:                      # 8x8+
            base_depth = 2

    # Clear TT mỗi lần gọi (giữ cache từ iterative deepening)
    _tt.clear()

    legal_moves = get_legal_moves(state)
    if not legal_moves:
        return None

    # Greedy: ăn box ngay nếu có
    for move in legal_moves:
        if would_complete_box(state, move) > 0:
            return move

    if len(legal_moves) == 1:
        return legal_moves[0]

    # Iterative Deepening với time limit
    depth = _get_adaptive_depth(state, base_depth)
    best_move = legal_moves[0]

    for d in range(1, depth + 1):
        # Kiểm tra time limit trước mỗi iteration
        elapsed = time.time() - start_time
        if d > 1 and elapsed > time_limit * 0.6:
            # Đã dùng >60% thời gian → dừng, không đủ time cho depth tiếp
            break

        score, move = minimax(state, d, -math.inf, math.inf, ai_player)
        if move:
            best_move = move

    return best_move

