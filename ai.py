import math
from models import GameState, Move
from rules import get_affected_boxes, apply_move, undo_move, is_terminal


# ============================================================
#  Transposition Table
# ============================================================
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

_tt = {}
_tt_max = 500000


def _state_key(state: GameState):
    """Tạo hashable key từ trạng thái bàn cờ cho transposition table."""
    h = tuple(val for row in state.h_edges for val in row)
    v = tuple(val for row in state.v_edges for val in row)
    return (h, v, state.current_player)


def _move_key(move: Move):
    return (move.edge_type, move.r, move.c)


def _key_to_move(key):
    return Move(key[0], key[1], key[2])


# ============================================================
#  Utility helpers
# ============================================================

def get_legal_moves(state: GameState):
    """Sinh toàn bộ nước đi hợp lệ từ trạng thái hiện tại."""
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


def would_complete_box(state: GameState, move: Move):
    """Trả về số box hoàn thành nếu đi nước này."""
    completed = 0
    for br, bc in get_affected_boxes(move, state.rows, state.cols):
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 3:
            completed += 1
    return completed


def would_create_third_edge(state: GameState, move: Move):
    """Trả về số ô bị tạo thành 3 cạnh (cho đối thủ ăn)."""
    created = 0
    for br, bc in get_affected_boxes(move, state.rows, state.cols):
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 2:
            created += 1
    return created


def get_safe_moves(state: GameState):
    """Tìm nước đi an toàn (không tạo ô 3 cạnh)."""
    return [m for m in get_legal_moves(state) if would_create_third_edge(state, m) == 0]


# ============================================================
#  Chain detection — Nền tảng cho Double-Cross
# ============================================================

def _find_capturable_chains(state: GameState):
    """
    Tìm các chuỗi (chain) box có thể ăn liên tiếp.

    Một chain bắt đầu từ box có 3 cạnh, rồi đi theo các box kề nhau
    chia sẻ cạnh chưa vẽ (mỗi box kế tiếp có 2 cạnh → sẽ thành 3
    khi ta ăn box trước đó).

    Returns: list of chains, mỗi chain = list of (box_r, box_c)
             theo thứ tự ăn (box đầu có 3 cạnh)
    """
    rows, cols = state.rows, state.cols
    visited = set()
    chains = []

    for r in range(rows):
        for c in range(cols):
            if (r, c) in visited or state.boxes[r][c] != 0:
                continue
            if state.edges_count[r][c] != 3:
                continue

            # Tìm chain từ box (r,c) có 3 cạnh
            chain = [(r, c)]
            visited.add((r, c))

            # Đi dọc theo chain: tìm box kề chia sẻ cạnh chưa vẽ
            # và có 2 cạnh (sẽ thành 3 khi ta ăn box hiện tại)
            cr, cc = r, c
            while True:
                found_next = False
                for nr, nc, shared_drawn in _get_box_neighbors_with_edge(state, cr, cc):
                    if (nr, nc) in visited or state.boxes[nr][nc] != 0:
                        continue
                    # Box kề chia sẻ cạnh chưa vẽ VÀ có đúng 2 cạnh
                    if not shared_drawn and state.edges_count[nr][nc] == 2:
                        chain.append((nr, nc))
                        visited.add((nr, nc))
                        cr, cc = nr, nc
                        found_next = True
                        break
                if not found_next:
                    break

            chains.append(chain)

    return chains


def _get_box_neighbors_with_edge(state, r, c):
    """
    Trả về danh sách (nr, nc, shared_edge_drawn) cho các box kề box (r,c).
    shared_edge_drawn = True nếu cạnh chung đã được vẽ.
    """
    rows, cols = state.rows, state.cols
    neighbors = []
    # Trên: box (r-1, c) — cạnh chung là h_edges[r][c]
    if r > 0:
        neighbors.append((r - 1, c, state.h_edges[r][c]))
    # Dưới: box (r+1, c) — cạnh chung là h_edges[r+1][c]
    if r < rows - 1:
        neighbors.append((r + 1, c, state.h_edges[r + 1][c]))
    # Trái: box (r, c-1) — cạnh chung là v_edges[r][c]
    if c > 0:
        neighbors.append((r, c - 1, state.v_edges[r][c]))
    # Phải: box (r, c+1) — cạnh chung là v_edges[r][c+1]
    if c < cols - 1:
        neighbors.append((r, c + 1, state.v_edges[r][c + 1]))
    return neighbors


def _get_missing_edge(state, box_r, box_c):
    """
    Tìm cạnh còn thiếu của box có 3 cạnh.
    Returns: Move hoặc None
    """
    r, c = box_r, box_c
    # Top edge: h_edges[r][c]
    if not state.h_edges[r][c]:
        return Move('H', r, c)
    # Bottom edge: h_edges[r+1][c]
    if not state.h_edges[r + 1][c]:
        return Move('H', r + 1, c)
    # Left edge: v_edges[r][c]
    if not state.v_edges[r][c]:
        return Move('V', r, c)
    # Right edge: v_edges[r][c+1]
    if not state.v_edges[r][c + 1]:
        return Move('V', r, c + 1)
    return None


def _get_shared_edge(state, r1, c1, r2, c2):
    """
    Tìm cạnh chung chưa vẽ giữa 2 box kề nhau.
    Returns: Move hoặc None
    """
    if r1 == r2:  # Cùng hàng → cạnh dọc
        col = max(c1, c2)
        if not state.v_edges[r1][col]:
            return Move('V', r1, col)
    elif c1 == c2:  # Cùng cột → cạnh ngang
        row = max(r1, r2)
        if not state.h_edges[row][c1]:
            return Move('H', row, c1)
    return None


# ============================================================
#  Smart Force-Capture: Greedy + Double-Cross options
# ============================================================

def _force_captures_greedy(state: GameState):
    """Ăn tất cả box có thể (greedy, không double-cross)."""
    captures = []
    while True:
        found = False
        for r in range(state.rows + 1):
            for c in range(state.cols):
                if not state.h_edges[r][c]:
                    move = Move('H', r, c)
                    if would_complete_box(state, move) > 0:
                        captures.append((move, apply_move(state, move)))
                        found = True
                        break
            if found:
                break
        if found:
            continue
        for r in range(state.rows):
            for c in range(state.cols + 1):
                if not state.v_edges[r][c]:
                    move = Move('V', r, c)
                    if would_complete_box(state, move) > 0:
                        captures.append((move, apply_move(state, move)))
                        found = True
                        break
            if found:
                break
        if not found:
            break
    return captures


def _undo_captures(state, captures):
    """Hoàn tác chuỗi capture theo thứ tự ngược."""
    for move, undo_info in reversed(captures):
        undo_move(state, move, undo_info)


def _find_double_cross_options(state: GameState):
    """
    Tìm các lựa chọn sacrifice (double-cross / quad sacrifice).

    - Open chain (≥3 box): ăn trừ 2 cuối → sacrifice 2 box
    - Closed loop (≥4 box): ăn trừ 4 cuối → sacrifice 4 box
      (vẽ cạnh giữa chia 4 box thành 2 cặp)

    Returns: list of (captures_partial, sacrifice_move)
    """
    chains = _find_capturable_chains(state)
    if not chains:
        return []

    options = []

    for chain in chains:
        n = len(chain)
        if n < 3:
            continue

        # Xác định đây là open chain hay có thể là loop
        # Kiểm tra: box cuối chain có kết nối ngược về box đầu không?
        first_box = chain[0]
        last_box = chain[-1]
        is_loop = False

        if n >= 4:
            # Kiểm tra shared edge chưa vẽ giữa last và first
            shared = _get_shared_edge(state, last_box[0], last_box[1],
                                      first_box[0], first_box[1])
            if shared is not None:
                is_loop = True

        if is_loop and n >= 4:
            # === CLOSED LOOP: Quad sacrifice (chừa 4 box cuối) ===
            leave_count = min(4, n)
            capture_count = n - leave_count

            if capture_count < 1:
                # Loop quá nhỏ (4 box), sacrifice = toàn bộ
                # Tìm sacrifice edge: cạnh giữa box[1] và box[2]
                if n >= 4:
                    mid = n // 2
                    sac = _get_shared_edge(state, chain[mid-1][0], chain[mid-1][1],
                                           chain[mid][0], chain[mid][1])
                    if sac and not _is_edge_drawn(state, sac):
                        # Không ăn gì, chỉ sacrifice
                        options.append(([], sac))
                continue

            # Ăn capture_count box đầu, chừa leave_count box cuối
            sac_a = chain[-(leave_count // 2 + 1)]
            sac_b = chain[-(leave_count // 2)]
            sacrifice = _get_shared_edge(state, sac_a[0], sac_a[1],
                                         sac_b[0], sac_b[1])
            if sacrifice is None:
                continue

            partial_captures = _try_partial_capture(state, chain, capture_count)
            if partial_captures is not None:
                if not _is_edge_drawn(state, sacrifice):
                    options.append((partial_captures, sacrifice))
                else:
                    _undo_captures(state, partial_captures)
            # else: undo already done in _try_partial_capture

        else:
            # === OPEN CHAIN: Double-cross (chừa 2 box cuối) ===
            last2_a = chain[-2]
            last2_b = chain[-1]
            sacrifice = _get_shared_edge(state, last2_a[0], last2_a[1],
                                         last2_b[0], last2_b[1])
            if sacrifice is None:
                continue

            capture_count = n - 2
            partial_captures = _try_partial_capture(state, chain, capture_count)
            if partial_captures is not None:
                if not _is_edge_drawn(state, sacrifice):
                    options.append((partial_captures, sacrifice))
                else:
                    _undo_captures(state, partial_captures)

    return options


def _try_partial_capture(state, chain, count):
    """
    Thử ăn 'count' box đầu tiên trong chain.
    Returns: list of (move, undo_info) nếu thành công, None nếu thất bại.
    Nếu thất bại, tự undo tất cả.
    """
    captures = []
    for i in range(count):
        br, bc = chain[i]
        if state.edges_count[br][bc] >= 3 and state.boxes[br][bc] == 0:
            missing = _get_missing_edge(state, br, bc)
            if missing and would_complete_box(state, missing) > 0:
                captures.append((missing, apply_move(state, missing)))
            else:
                _undo_captures(state, captures)
                return None
        else:
            _undo_captures(state, captures)
            return None
    return captures if captures else None


def _is_edge_drawn(state, move):
    """Kiểm tra cạnh đã được vẽ chưa."""
    if move.edge_type == 'H':
        return state.h_edges[move.r][move.c]
    return state.v_edges[move.r][move.c]


# ============================================================
#  Heuristic evaluation
# ============================================================

def evaluate(state: GameState, ai_player: int):
    """Hàm đánh giá trạng thái cho Minimax."""
    if ai_player == 1:
        score_diff = state.score_player1 - state.score_player2
    else:
        score_diff = state.score_player2 - state.score_player1

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

    if state.current_player == ai_player:
        cap_score = capturable * 50
    else:
        cap_score = -capturable * 50

    chain_score = _evaluate_chains(state, ai_player)

    return score_diff * 100 + cap_score + chain_score * 15 - boxes_2 * 3


def _analyze_chains_and_loops(state: GameState):
    """
    Phân tích board thành open chains và closed loops.

    Open chain: dãy box nối tiếp, có ≥1 đầu "mở" (box chỉ có 1 neighbor
                trong chuỗi). Sacrifice = 2 box.
    Closed loop: vòng kín, mọi box có đúng 2 neighbor trong chuỗi.
                 Sacrifice = 4 box.

    Returns: (open_chains, closed_loops)
        - open_chains: list of chain lengths (chỉ chain ≥ 3)
        - closed_loops: list of loop lengths (chỉ loop ≥ 4)
    """
    rows, cols = state.rows, state.cols
    visited = [[False] * cols for _ in range(rows)]
    open_chains = []
    closed_loops = []

    for r in range(rows):
        for c in range(cols):
            if visited[r][c] or state.boxes[r][c] != 0:
                continue
            if state.edges_count[r][c] < 2:
                continue

            # BFS tìm connected component qua cạnh chưa vẽ
            component = []
            adj_count = {}  # Đếm số neighbor trong component cho mỗi box
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                if visited[cr][cc] or state.boxes[cr][cc] != 0:
                    continue
                if state.edges_count[cr][cc] < 2:
                    continue
                visited[cr][cc] = True
                component.append((cr, cc))
                adj_count[(cr, cc)] = 0

                neighbors = []
                if cr > 0 and not state.h_edges[cr][cc]:
                    neighbors.append((cr - 1, cc))
                if cr < rows - 1 and not state.h_edges[cr + 1][cc]:
                    neighbors.append((cr + 1, cc))
                if cc > 0 and not state.v_edges[cr][cc]:
                    neighbors.append((cr, cc - 1))
                if cc < cols - 1 and not state.v_edges[cr][cc + 1]:
                    neighbors.append((cr, cc + 1))

                for nr, nc in neighbors:
                    if not visited[nr][nc] and state.boxes[nr][nc] == 0 and state.edges_count[nr][nc] >= 2:
                        stack.append((nr, nc))

            # Đếm adjacency trong component
            comp_set = set(component)
            is_loop = True
            for cr, cc in component:
                count = 0
                if (cr - 1, cc) in comp_set and not state.h_edges[cr][cc]:
                    count += 1
                if (cr + 1, cc) in comp_set and not state.h_edges[cr + 1][cc]:
                    count += 1
                if (cr, cc - 1) in comp_set and not state.v_edges[cr][cc]:
                    count += 1
                if (cr, cc + 1) in comp_set and not state.v_edges[cr][cc + 1]:
                    count += 1
                if count != 2:
                    is_loop = False

            n = len(component)
            if is_loop and n >= 4:
                closed_loops.append(n)
            elif not is_loop and n >= 3:
                open_chains.append(n)

    return open_chains, closed_loops


def _evaluate_chains(state: GameState, ai_player: int):
    """
    Đánh giá chain control dựa trên Berlekamp's Nimstring theory.

    - Mỗi open chain (≥3): người kiểm soát sacrifice 2 box, ăn phần còn lại
    - Mỗi closed loop (≥4): người kiểm soát sacrifice 4 box, ăn phần còn lại
    - Tổng "looney moves" = số chain + số loop = quyết định parity

    Parity rule: nếu tổng looney moves CHẴN → người đi trước (trong endgame)
    có lợi. Nếu LẺ → người đi sau có lợi.
    """
    open_chains, closed_loops = _analyze_chains_and_loops(state)

    # Tổng "controllable regions" = quyết định ai phải mở chain đầu tiên
    total_regions = len(open_chains) + len(closed_loops)

    # Ước tính net score impact
    # Nếu bạn control: bạn ăn (chain_len - 2) mỗi open chain, (loop_len - 4) mỗi loop
    # Nếu đối thủ control: ngược lại
    chain_value = sum(ch - 2 for ch in open_chains)  # net gain per chain
    loop_value = sum(lp - 4 for lp in closed_loops)   # net gain per loop
    total_value = chain_value + loop_value

    # Parity: chẵn regions → current player có lợi
    if state.current_player == ai_player:
        if total_regions % 2 == 0:
            parity_score = total_regions * 8 + total_value * 3
        else:
            parity_score = -total_regions * 8 - total_value * 3
    else:
        if total_regions % 2 == 1:
            parity_score = total_regions * 8 + total_value * 3
        else:
            parity_score = -total_regions * 8 - total_value * 3

    return parity_score


# ============================================================
#  Move ordering
# ============================================================

def _order_moves(state, moves, tt_best_key=None):
    """Sắp xếp nước đi cho alpha-beta cắt tỉa tốt hơn."""
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
    if tt_move:
        ordered.insert(0, tt_move)
    return ordered


# ============================================================
#  Minimax + Alpha-Beta + TT + Force-Capture + Double-Cross
# ============================================================

def minimax(state: GameState, depth: int, alpha: float, beta: float,
            ai_player: int):
    """
    Minimax với Alpha-Beta Pruning, Transposition Table,
    Force-Capture optimization, và Double-Cross branching.
    """
    global _tt

    # --- Bước 1: Kiểm tra double-cross trước khi force-capture ---
    # Tìm xem có cơ hội double-cross không
    dc_options = []
    if depth >= 2:  # Chỉ xét double-cross ở depth đủ sâu
        dc_options = _find_double_cross_options(state)

    # Nếu có double-cross, ta sẽ thử CẢ HAI nhánh:
    #   A) Greedy (ăn hết)
    #   B) Double-cross (ăn trừ 2 cuối + sacrifice)
    # Rồi chọn nhánh tốt hơn.

    if dc_options:
        # Có ít nhất 1 double-cross option
        # Nhánh A: Greedy capture (undo dc partial, do full greedy)
        # Undo partial captures từ dc detection
        for partial_caps, sac_move in dc_options:
            _undo_captures(state, partial_caps)

        return _minimax_with_dc(state, depth, alpha, beta, ai_player, dc_options)
    else:
        # Không có double-cross → chạy bình thường
        return _minimax_core(state, depth, alpha, beta, ai_player)


def _minimax_with_dc(state, depth, alpha, beta, ai_player, dc_options):
    """
    Minimax có xét double-cross.
    Thử 2 nhánh: greedy vs double-cross, chọn nhánh tốt hơn.
    """
    is_max = (state.current_player == ai_player)

    # === Nhánh A: Greedy (ăn hết) ===
    score_greedy, move_greedy = _minimax_core(state, depth, alpha, beta, ai_player)

    # === Nhánh B: Double-cross (cho mỗi dc option) ===
    best_dc_score = -math.inf if is_max else math.inf
    best_dc_first_move = None

    for dc_partial_info, sacrifice_move in dc_options:
        # Thực hiện partial captures (ăn trừ 2 cuối)
        partial_caps = []
        valid = True
        for orig_move, _ in dc_partial_info:
            # Phải re-apply vì đã undo ở trên
            if would_complete_box(state, orig_move) > 0:
                partial_caps.append((orig_move, apply_move(state, orig_move)))
            else:
                valid = False
                break

        if not valid:
            _undo_captures(state, partial_caps)
            continue

        first_move = partial_caps[0][0] if partial_caps else sacrifice_move

        # Vẽ sacrifice edge (tạo 2 box 3 cạnh cho đối thủ)
        if not _is_edge_drawn(state, sacrifice_move):
            sac_undo = apply_move(state, sacrifice_move)

            # Recursive minimax từ state sau sacrifice
            dc_score, _ = _minimax_core(state, depth - 1, alpha, beta, ai_player)

            undo_move(state, sacrifice_move, sac_undo)
        else:
            dc_score = score_greedy  # Fallback

        _undo_captures(state, partial_caps)

        if is_max:
            if dc_score > best_dc_score:
                best_dc_score = dc_score
                best_dc_first_move = first_move
        else:
            if dc_score < best_dc_score:
                best_dc_score = dc_score
                best_dc_first_move = first_move

    # So sánh greedy vs double-cross
    if is_max:
        if best_dc_first_move and best_dc_score > score_greedy:
            return best_dc_score, best_dc_first_move
        return score_greedy, move_greedy
    else:
        if best_dc_first_move and best_dc_score < score_greedy:
            return best_dc_score, best_dc_first_move
        return score_greedy, move_greedy


def _minimax_core(state, depth, alpha, beta, ai_player):
    """Minimax core: force-capture greedy → search non-capture moves."""
    global _tt

    # Force-capture tất cả box
    captures = _force_captures_greedy(state)
    first_capture = captures[0][0] if captures else None

    # Base cases
    if is_terminal(state):
        if ai_player == 1:
            diff = state.score_player1 - state.score_player2
        else:
            diff = state.score_player2 - state.score_player1
        _undo_captures(state, captures)
        return diff * 10000, first_capture

    if depth <= 0:
        score = evaluate(state, ai_player)
        _undo_captures(state, captures)
        return score, first_capture

    # TT lookup
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
        tt_best_key = tt_mk

    # Sinh non-capture moves
    is_max = (state.current_player == ai_player)
    legal_moves = get_legal_moves(state)

    if not legal_moves:
        score = evaluate(state, ai_player)
        _undo_captures(state, captures)
        return score, first_capture

    ordered = _order_moves(state, legal_moves, tt_best_key)
    best_move = ordered[0]

    # Alpha-Beta search
    if is_max:
        best_val = -math.inf
        for move in ordered:
            undo_info = apply_move(state, move)
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

    # TT store
    if len(_tt) < _tt_max:
        if best_val <= alpha_orig:
            flag = UPPERBOUND
        elif best_val >= beta_orig:
            flag = LOWERBOUND
        else:
            flag = EXACT
        _tt[key] = (depth, best_val, flag, _move_key(best_move))

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
                   time_limit: float = 3.0):
    """
    Tìm nước đi tốt nhất cho AI bằng Minimax + Alpha-Beta Pruning
    với Double-Cross strategy.
    """
    global _tt
    import time
    start_time = time.time()

    if base_depth is None:
        total_boxes = state.rows * state.cols
        if total_boxes <= 9:
            base_depth = 6
        elif total_boxes <= 16:
            base_depth = 4
        elif total_boxes <= 25:
            base_depth = 3
        elif total_boxes <= 49:
            base_depth = 2
        else:
            base_depth = 2

    _tt.clear()

    legal_moves = get_legal_moves(state)
    if not legal_moves:
        return None

    # Greedy capture (luôn đúng ở top level — double-cross xét trong minimax)
    for move in legal_moves:
        if would_complete_box(state, move) > 0:
            return move

    if len(legal_moves) == 1:
        return legal_moves[0]

    # Iterative Deepening với time limit
    max_depth = _get_adaptive_depth(state, base_depth)
    best_move = legal_moves[0]
    last_iter_time = 0

    for d in range(1, max_depth + 1):
        elapsed = time.time() - start_time
        estimated_next = last_iter_time * 5
        if d > 2 and (elapsed + estimated_next) > time_limit:
            break

        iter_start = time.time()
        score, move = minimax(state, d, -math.inf, math.inf, ai_player)
        last_iter_time = time.time() - iter_start

        if move:
            best_move = move

        if abs(score) >= 9000:
            break

    return best_move
