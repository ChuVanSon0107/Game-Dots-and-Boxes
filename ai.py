import math
from models import GameState, Move
from rules import get_affected_boxes, apply_move, undo_move, is_terminal

# ============================================================
#  Transposition Table
# ============================================================
EXACT      = 0
LOWERBOUND = 1
UPPERBOUND = 2

_tt     = {}
_tt_max = 300_000


def _tt_clear():
    global _tt
    _tt = {}


def _state_key(state: GameState):
    h = tuple(v for row in state.h_edges for v in row)
    v = tuple(v for row in state.v_edges for v in row)
    return (h, v, state.current_player)


def _move_key(m: Move):
    return (m.edge_type, m.r, m.c)


def _key_to_move(k):
    return Move(k[0], k[1], k[2])


# ============================================================
#  Helpers cơ bản
# ============================================================

def _get_legal_moves(state: GameState):
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


def _completes_box(state: GameState, move: Move) -> int:
    """Số box hoàn thành nếu đi nước này."""
    n = 0
    for br, bc in get_affected_boxes(move, state.rows, state.cols):
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 3:
            n += 1
    return n


def _creates_third_edge(state: GameState, move: Move) -> int:
    """Số box bị tạo thành 3 cạnh (sẽ cho đối thủ ăn) nếu đi nước này."""
    n = 0
    for br, bc in get_affected_boxes(move, state.rows, state.cols):
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 2:
            n += 1
    return n


def _is_drawn(state: GameState, move: Move) -> bool:
    if move.edge_type == 'H':
        return bool(state.h_edges[move.r][move.c])
    return bool(state.v_edges[move.r][move.c])


def _get_missing_edge(state: GameState, br: int, bc: int):
    """Trả về cạnh còn thiếu của box 3-edge."""
    r, c = br, bc
    if not state.h_edges[r][c]:     return Move('H', r,   c)
    if not state.h_edges[r+1][c]:   return Move('H', r+1, c)
    if not state.v_edges[r][c]:     return Move('V', r,   c)
    if not state.v_edges[r][c+1]:   return Move('V', r,   c+1)
    return None


# ============================================================
#  Phân loại nước đi
# ============================================================

def _classify_moves(state: GameState):
    """
    Trả về 3 nhóm nước đi:
      capture_moves : ăn được >= 1 box ngay lập tức
      safe_moves    : không tạo box 3 cạnh cho đối thủ
      risky_moves   : tạo box 3 cạnh (kèm số box nguy hiểm)
    """
    capture_moves = []
    safe_moves    = []
    risky_moves   = []   # list of (move, danger_count)

    for r in range(state.rows + 1):
        for c in range(state.cols):
            if not state.h_edges[r][c]:
                m = Move('H', r, c)
                if _completes_box(state, m):
                    capture_moves.append(m)
                elif _creates_third_edge(state, m) == 0:
                    safe_moves.append(m)
                else:
                    risky_moves.append((m, _creates_third_edge(state, m)))

    for r in range(state.rows):
        for c in range(state.cols + 1):
            if not state.v_edges[r][c]:
                m = Move('V', r, c)
                if _completes_box(state, m):
                    capture_moves.append(m)
                elif _creates_third_edge(state, m) == 0:
                    safe_moves.append(m)
                else:
                    risky_moves.append((m, _creates_third_edge(state, m)))

    risky_moves.sort(key=lambda x: x[1])   # ít nguy hiểm lên trước
    return capture_moves, safe_moves, risky_moves


# ============================================================
#  Double-Cross helpers
# ============================================================

def _open_neighbors(state: GameState, r, c):
    """Các box kề (nr, nc) qua cạnh CHƯA vẽ, chưa bị sở hữu."""
    rows, cols = state.rows, state.cols
    res = []
    if r > 0     and not state.h_edges[r][c]     and state.boxes[r-1][c] == 0: res.append((r-1, c))
    if r < rows-1 and not state.h_edges[r+1][c]  and state.boxes[r+1][c] == 0: res.append((r+1, c))
    if c > 0     and not state.v_edges[r][c]     and state.boxes[r][c-1] == 0: res.append((r, c-1))
    if c < cols-1 and not state.v_edges[r][c+1]  and state.boxes[r][c+1] == 0: res.append((r, c+1))
    return res


def _shared_edge(state: GameState, r1, c1, r2, c2):
    """Cạnh chung CHƯA vẽ giữa 2 box kề nhau. None nếu không có."""
    if r1 == r2:
        col = max(c1, c2)
        m = Move('V', r1, col)
    elif c1 == c2:
        row = max(r1, r2)
        m = Move('H', row, c1)
    else:
        return None
    return None if _is_drawn(state, m) else m


def _find_chain(state: GameState, start_r, start_c):
    """
    Tìm chuỗi box bắt đầu từ (start_r, start_c) có edges_count == 3.
    Chuỗi lan sang box kề có edges_count == 2 (sẽ thành 3 sau khi ăn).

    Trả về:
      chain      : list[(r,c)] theo thứ tự
      is_loop    : True nếu đuôi nối về đầu (vòng kín)
      tail_extra : (r,c) box 3-edge kề đuôi nhưng ngoài chain, hoặc None
    """
    if state.boxes[start_r][start_c] != 0 or state.edges_count[start_r][start_c] != 3:
        return [], False, None

    chain   = [(start_r, start_c)]
    visited = {(start_r, start_c)}
    cr, cc  = start_r, start_c

    while True:
        nxt = None
        for nr, nc in _open_neighbors(state, cr, cc):
            if (nr, nc) in visited or state.boxes[nr][nc] != 0:
                continue
            if state.edges_count[nr][nc] == 2:      # sẽ thành 3 sau khi ta ăn cr,cc
                nxt = (nr, nc)
                break
        if nxt is None:
            break
        chain.append(nxt)
        visited.add(nxt)
        cr, cc = nxt

    # Kiểm tra loop: đuôi kề đầu qua cạnh chưa vẽ
    is_loop = False
    if len(chain) >= 4:
        for nr, nc in _open_neighbors(state, cr, cc):
            if (nr, nc) == (start_r, start_c):
                is_loop = True
                break

    # Kiểm tra closed-chain: đuôi kề box 3-edge khác (ngoài chain)
    tail_extra = None
    if not is_loop:
        for nr, nc in _open_neighbors(state, cr, cc):
            if (nr, nc) not in visited and state.boxes[nr][nc] == 0:
                if state.edges_count[nr][nc] == 3:
                    tail_extra = (nr, nc)
                    break

    return chain, is_loop, tail_extra


def _compute_dc_options(state: GameState):
    """
    Tính toán các lựa chọn Double-Cross / Sacrifice.

    Mỗi option:
      partial_moves : list[Move] — ăn trước khi sacrifice (có thể rỗng)
      sacrifice     : Move       — nước vẽ cạnh sacrifice
      keep          : int        — số box mình ăn được
      give          : int        — số box nhường đối thủ

    Hàm KHÔNG modify state.
    """
    options  = []
    checked  = set()

    for r in range(state.rows):
        for c in range(state.cols):
            if (r, c) in checked:
                continue
            if state.boxes[r][c] != 0 or state.edges_count[r][c] != 3:
                continue

            chain, is_loop, tail_extra = _find_chain(state, r, c)
            if not chain:
                continue
            for b in chain:
                checked.add(b)

            n = len(chain)

            # --- Closed loop (vòng kín, n >= 4) ---
            if is_loop and n >= 4:
                keep  = max(0, n - 4)
                give  = 4
                idx_a = keep - 1 if keep > 0 else n // 2 - 1
                idx_b = keep     if keep > 0 else n // 2
                sac   = _shared_edge(state, chain[idx_a][0], chain[idx_a][1],
                                            chain[idx_b][0], chain[idx_b][1])
                if sac is None:
                    continue
                pmoves = [_get_missing_edge(state, chain[i][0], chain[i][1])
                          for i in range(keep)]
                if None in pmoves:
                    continue
                options.append({'partial_moves': pmoves, 'sacrifice': sac,
                                'keep': keep, 'give': give})

            # --- Closed chain (đuôi kề box 3-edge ngoài chain) ---
            elif tail_extra is not None:
                full  = chain + [tail_extra]
                fn    = len(full)
                mid   = fn // 2
                sac   = _shared_edge(state, full[mid-1][0], full[mid-1][1],
                                            full[mid][0],   full[mid][1])
                if sac is None:
                    continue
                # Không ăn gì, sacrifice toàn bộ → giữ tempo
                options.append({'partial_moves': [], 'sacrifice': sac,
                                'keep': 0, 'give': fn})

            # --- Open chain (n >= 3) ---
            elif n >= 3:
                keep  = n - 2
                give  = 2
                sac   = _shared_edge(state, chain[keep-1][0], chain[keep-1][1],
                                            chain[keep][0],   chain[keep][1])
                if sac is None:
                    continue
                pmoves = [_get_missing_edge(state, chain[i][0], chain[i][1])
                          for i in range(keep)]
                if None in pmoves:
                    continue
                options.append({'partial_moves': pmoves, 'sacrifice': sac,
                                'keep': keep, 'give': give})

    return options


# ============================================================
#  Heuristic evaluation
# ============================================================

def _analyze_chains(state: GameState):
    """Trả về (open_chains, closed_loops) — danh sách độ dài."""
    rows, cols = state.rows, state.cols
    visited    = [[False] * cols for _ in range(rows)]
    open_chains, closed_loops = [], []

    for sr in range(rows):
        for sc in range(cols):
            if visited[sr][sc] or state.boxes[sr][sc] != 0:
                continue

            # BFS component qua cạnh chưa vẽ
            comp  = []
            stack = [(sr, sc)]
            visited[sr][sc] = True
            while stack:
                cr, cc = stack.pop()
                comp.append((cr, cc))
                for nr, nc in _open_neighbors(state, cr, cc):
                    if not visited[nr][nc]:
                        visited[nr][nc] = True
                        stack.append((nr, nc))

            n = len(comp)
            if n < 2:
                continue

            comp_set = set(comp)
            all_deg2 = all(
                sum(1 for nr, nc in _open_neighbors(state, cr, cc) if (nr, nc) in comp_set) == 2
                for cr, cc in comp
            )
            if all_deg2 and n >= 4:
                closed_loops.append(n)
            elif not all_deg2 and n >= 3:
                open_chains.append(n)

    return open_chains, closed_loops


def evaluate(state: GameState, ai_player: int) -> float:
    if ai_player == 1:
        diff = state.score_player1 - state.score_player2
    else:
        diff = state.score_player2 - state.score_player1

    open_chains, closed_loops = _analyze_chains(state)

    # Berlekamp parity: số regions lẻ → current player có lợi
    total_regions = len(open_chains) + len(closed_loops)
    chain_net     = sum(c - 2 for c in open_chains) + sum(l - 4 for l in closed_loops)

    ai_is_current       = (state.current_player == ai_player)
    current_has_parity  = (total_regions % 2 == 1)

    if ai_is_current == current_has_parity:
        parity = total_regions * 6 + chain_net * 4
    else:
        parity = -(total_regions * 6 + chain_net * 4)

    danger = sum(
        1 for r in range(state.rows) for c in range(state.cols)
        if state.boxes[r][c] == 0 and state.edges_count[r][c] == 2
    )

    return diff * 120 + parity - danger * 2


# ============================================================
#  Core Minimax
# ============================================================

def _minimax(state: GameState, depth: int,
             alpha: float, beta: float, ai_player: int) -> tuple:
    """
    Minimax + Alpha-Beta + Transposition Table.

    Luồng xử lý:
    ┌─────────────────────────────────────────────────────────┐
    │  1. Terminal / depth-0 → trả về evaluate               │
    │                                                         │
    │  2. Có capture moves?                                   │
    │     └─ YES → gọi _handle_captures (xét DC vs greedy)   │
    │                                                         │
    │  3. Có safe moves?                                      │
    │     └─ YES → minimax trên safe moves                    │
    │                                                         │
    │  4. Chỉ còn risky moves                                 │
    │     └─ minimax trên risky moves (ít nguy hiểm nhất)     │
    └─────────────────────────────────────────────────────────┘
    """
    global _tt

    if is_terminal(state):
        d = (state.score_player1 - state.score_player2) if ai_player == 1 \
            else (state.score_player2 - state.score_player1)
        return d * 10000, None

    if depth <= 0:
        return evaluate(state, ai_player), None

    # TT lookup
    alpha_orig = alpha
    key        = _state_key(state)
    tt_best    = None

    if key in _tt:
        td, ts, tf, tm = _tt[key]
        if td >= depth:
            if   tf == EXACT:      return ts, _key_to_move(tm)
            elif tf == LOWERBOUND: alpha = max(alpha, ts)
            elif tf == UPPERBOUND: beta  = min(beta,  ts)
            if alpha >= beta:      return ts, _key_to_move(tm)
        tt_best = tm

    # Phân loại nước đi
    cap_moves, safe_moves, risky_moves = _classify_moves(state)

    is_max = (state.current_player == ai_player)

    # --- Có box ăn được ---
    if cap_moves:
        best_val, best_move = _handle_captures(
            state, depth, alpha, beta, ai_player, is_max, cap_moves
        )

    # --- Không có box ăn, còn safe move ---
    elif safe_moves:
        ordered    = _order_safe(safe_moves, tt_best)
        best_move  = ordered[0]
        best_val   = -math.inf if is_max else math.inf

        for move in ordered:
            ui  = apply_move(state, move)
            val, _ = _minimax(state, depth - 1, alpha, beta, ai_player)
            undo_move(state, move, ui)

            if is_max:
                if val > best_val:
                    best_val, best_move = val, move
                alpha = max(alpha, val)
            else:
                if val < best_val:
                    best_val, best_move = val, move
                beta = min(beta, val)

            if alpha >= beta:
                break

    # --- Chỉ còn risky move ---
    elif risky_moves:
        ordered   = _order_risky(risky_moves, tt_best)
        best_move = ordered[0]
        best_val  = -math.inf if is_max else math.inf

        for move in ordered:
            ui  = apply_move(state, move)
            val, _ = _minimax(state, depth - 1, alpha, beta, ai_player)
            undo_move(state, move, ui)

            if is_max:
                if val > best_val:
                    best_val, best_move = val, move
                alpha = max(alpha, val)
            else:
                if val < best_val:
                    best_val, best_move = val, move
                beta = min(beta, val)

            if alpha >= beta:
                break

    else:
        return evaluate(state, ai_player), None

    # TT store
    if best_move and len(_tt) < _tt_max:
        flag = EXACT
        if   best_val <= alpha_orig: flag = UPPERBOUND
        elif best_val >= beta:       flag = LOWERBOUND
        _tt[key] = (depth, best_val, flag, _move_key(best_move))

    return best_val, best_move


def _order_safe(safe_moves, tt_best):
    if not tt_best:
        return safe_moves
    ordered = [m for m in safe_moves if _move_key(m) == tt_best]
    ordered += [m for m in safe_moves if _move_key(m) != tt_best]
    return ordered


def _order_risky(risky_moves, tt_best):
    """risky_moves đã sort theo danger tăng dần."""
    moves = [m for m, _ in risky_moves]
    if not tt_best:
        return moves
    ordered = [m for m in moves if _move_key(m) == tt_best]
    ordered += [m for m in moves if _move_key(m) != tt_best]
    return ordered


# ============================================================
#  Xử lý khi có capture: Greedy vs Double-Cross
# ============================================================

def _handle_captures(state: GameState, depth: int,
                     alpha: float, beta: float,
                     ai_player: int, is_max: bool,
                     cap_moves: list) -> tuple:
    """
    Khi có box ăn được, so sánh 2 chiến lược:

    A) GREEDY: Ăn hết tất cả box có thể → minimax tiếp từ state mới
       - Luôn là nước đi hợp lệ, là baseline

    B) DOUBLE-CROSS: Ăn một phần chain + sacrifice cạnh giữa
       → Nhường 2-4 box, nhưng đối thủ phải mở chain tiếp theo (tempo)
       → Chỉ đáng nếu score sau DC > score greedy

    Trả về (best_score, first_move_to_play).
    """

    # === Nhánh A: Greedy ===
    greedy_caps   = []
    first_greedy  = cap_moves[0]

    # Ăn hết
    while True:
        found = False
        for r in range(state.rows + 1):
            for c in range(state.cols):
                if not state.h_edges[r][c]:
                    m = Move('H', r, c)
                    if _completes_box(state, m):
                        greedy_caps.append((m, apply_move(state, m)))
                        found = True
                        break
            if found: break
        if not found:
            for r in range(state.rows):
                for c in range(state.cols + 1):
                    if not state.v_edges[r][c]:
                        m = Move('V', r, c)
                        if _completes_box(state, m):
                            greedy_caps.append((m, apply_move(state, m)))
                            found = True
                            break
                if found: break
        if not found:
            break

    score_greedy, _ = _minimax(state, depth - 1, alpha, beta, ai_player)

    # Undo greedy
    for move, ui in reversed(greedy_caps):
        undo_move(state, move, ui)

    # === Nhánh B: Double-Cross ===
    # Chỉ xét DC khi depth đủ sâu (cần nhìn xa để thấy lợi ích tempo)
    best_val  = score_greedy
    best_move = first_greedy

    if depth >= 2:
        dc_options = _compute_dc_options(state)

        for opt in dc_options:
            # Bỏ qua nếu closed-chain sacrifice quá nhiều và còn đang ở depth cao
            # (closed-chain chỉ đáng xét gần cuối game)
            if opt['give'] > opt['keep'] + 2 and opt['keep'] == 0 and depth > 3:
                continue

            # Apply partial captures
            partial_done = []
            valid = True
            for pm in opt['partial_moves']:
                if not _is_drawn(state, pm) and _completes_box(state, pm) > 0:
                    partial_done.append((pm, apply_move(state, pm)))
                else:
                    valid = False
                    break

            if not valid:
                for m, ui in reversed(partial_done):
                    undo_move(state, m, ui)
                continue

            sac = opt['sacrifice']
            if _is_drawn(state, sac):
                for m, ui in reversed(partial_done):
                    undo_move(state, m, ui)
                continue

            # Nước đi đầu tiên của sequence này
            first_dc = partial_done[0][0] if partial_done else sac

            # Apply sacrifice
            sac_ui = apply_move(state, sac)
            dc_score, _ = _minimax(state, depth - 1, alpha, beta, ai_player)
            undo_move(state, sac, sac_ui)

            for m, ui in reversed(partial_done):
                undo_move(state, m, ui)

            # Chọn nếu tốt hơn
            if is_max and dc_score > best_val:
                best_val  = dc_score
                best_move = first_dc
            elif not is_max and dc_score < best_val:
                best_val  = dc_score
                best_move = first_dc

    return best_val, best_move


# ============================================================
#  Adaptive depth + Iterative Deepening
# ============================================================

def _adaptive_depth(state: GameState, base: int) -> int:
    r = state.moves_remaining
    if   r <= 8:  return min(r, 24)
    elif r <= 14: return base + 5
    elif r <= 20: return base + 3
    elif r <= 28: return base + 1
    return base


def _iterative_deepening(state: GameState, ai_player: int,
                         max_depth: int, time_limit: float, t0: float):
    import time
    best_move  = None
    last_time  = 0.0

    for d in range(1, max_depth + 1):
        elapsed = time.time() - t0
        if d > 2 and (elapsed + last_time * 6) > time_limit:
            break

        t1 = time.time()
        score, move = _minimax(state, d, -math.inf, math.inf, ai_player)
        last_time = time.time() - t1

        if move:
            best_move = move

        if abs(score) >= 9000:
            break

    return best_move


# ============================================================
#  Public API
# ============================================================

def get_best_move(state: GameState, ai_player: int = 2,
                  base_depth: int = None, time_limit: float = 3.0):
    """
    Tìm nước đi tốt nhất cho AI.

    Luồng quyết định:
    1. Có box ăn được → _minimax xét greedy vs DC, trả về nước tốt nhất
    2. Có safe move   → _minimax chọn safe move tốt nhất
    3. Chỉ có risky   → _minimax chọn risky ít thiệt nhất
    """
    import time
    t0 = time.time()

    if base_depth is None:
        total = state.rows * state.cols
        if   total <= 9:  base_depth = 7
        elif total <= 16: base_depth = 5
        elif total <= 25: base_depth = 4
        elif total <= 49: base_depth = 3
        else:             base_depth = 2

    _tt_clear()

    legal = _get_legal_moves(state)
    if not legal:
        return None
    if len(legal) == 1:
        return legal[0]

    depth = _adaptive_depth(state, base_depth)
    move  = _iterative_deepening(state, ai_player, depth, time_limit, t0)
    return move if move else legal[0]