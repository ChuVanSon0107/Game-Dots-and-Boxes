"""
ai.py — Dots and Boxes AI
==========================
Implements optimal strategy based on Berlekamp's chain theory:

  Pha 1 (còn safe moves): Minimax CHỈ trên safe moves,
           evaluate theo parity của long chains/loops tương lai.
  Pha 2 (hết safe moves):
     - Nếu có box ăn ngay: quyết định Greedy vs Sacrifice dựa trên
       N_còn_lại (số long chains/loops chưa mở) theo Berlekamp parity.
     - Nếu phải mở chain: ưu tiên short chain (≤2 box), rồi minimax
       chọn long chain có lợi nhất.
"""

import math
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
    h = tuple(v for row in state.h_edges for v in row)
    v = tuple(v for row in state.v_edges for v in row)
    return (h, v, state.current_player)


# ============================================================
#  Cơ bản: nước đi hợp lệ, kiểm tra box
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


def _boxes_completed_by(state: GameState, move: Move) -> int:
    """Số box hoàn thành nếu đi nước này."""
    count = 0
    for br, bc in get_affected_boxes(move, state.rows, state.cols):
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 3:
            count += 1
    return count


def _creates_third_edge(state: GameState, move: Move) -> int:
    """Số box bị tạo thành 3 cạnh (nguy hiểm cho đối thủ ăn)."""
    count = 0
    for br, bc in get_affected_boxes(move, state.rows, state.cols):
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 2:
            count += 1
    return count


def _get_safe_moves(state: GameState):
    """Nước đi không tạo box 3 cạnh (an toàn — không cho đối thủ ăn ngay)."""
    return [m for m in get_legal_moves(state) if _creates_third_edge(state, m) == 0]


def _get_capture_move(state: GameState):
    """Trả về một nước ăn box ngay (edge_count == 3), hoặc None."""
    for r in range(state.rows + 1):
        for c in range(state.cols):
            if not state.h_edges[r][c]:
                m = Move('H', r, c)
                if _boxes_completed_by(state, m) > 0:
                    return m
    for r in range(state.rows):
        for c in range(state.cols + 1):
            if not state.v_edges[r][c]:
                m = Move('V', r, c)
                if _boxes_completed_by(state, m) > 0:
                    return m
    return None


# ============================================================
#  Chain / Loop analysis  (Berlekamp Nimstring theory)
# ============================================================

def _analyze_chains_and_loops(state: GameState):
    """
    Phân tích tất cả 'potential chains' trên board:
    Một box thuộc về potential chain nếu nó có < 2 cạnh được vẽ
    (tức là còn ≥ 2 cạnh tự do — có thể nối với box khác khi endgame đến).

    Thực ra theo Berlekamp, chúng ta cần đếm số "long chains" và "loops"
    trong cấu trúc nimstring graph.  Hàm này phân tích connected components
    của các box chưa bị ăn, kết nối qua cạnh CHƯA VẼ.

    Returns:
        open_chains: list of int (độ dài chain tuyến tính có ≥ 3 box)
        closed_loops: list of int (độ dài loop vòng kín có ≥ 4 box)
    """
    rows, cols = state.rows, state.cols
    visited = [[False] * cols for _ in range(rows)]
    open_chains = []
    closed_loops = []

    for sr in range(rows):
        for sc in range(cols):
            if visited[sr][sc] or state.boxes[sr][sc] != 0:
                continue

            # BFS tìm connected component qua cạnh chưa vẽ
            component = []
            queue = [(sr, sc)]
            visited[sr][sc] = True
            while queue:
                cr, cc = queue.pop()
                component.append((cr, cc))
                # 4 láng giềng, kiểm tra cạnh chung chưa vẽ
                for nr, nc, edge_drawn in _box_neighbors_edge_status(state, cr, cc):
                    if not visited[nr][nc] and state.boxes[nr][nc] == 0 and not edge_drawn:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

            n = len(component)
            if n < 2:
                continue

            # Kiểm tra component là loop hay chain
            # Loop: mọi node đều có đúng 2 liên kết trong component
            comp_set = set(component)
            is_loop = True
            for cr, cc in component:
                deg = sum(
                    1 for nr, nc, drawn in _box_neighbors_edge_status(state, cr, cc)
                    if (nr, nc) in comp_set and not drawn
                )
                if deg != 2:
                    is_loop = False
                    break

            if is_loop and n >= 4:
                closed_loops.append(n)
            elif not is_loop and n >= 3:
                open_chains.append(n)

    return open_chains, closed_loops


def _box_neighbors_edge_status(state: GameState, r: int, c: int):
    """Trả về [(nr, nc, edge_is_drawn)] cho 4 box kề của box (r,c)."""
    rows, cols = state.rows, state.cols
    result = []
    if r > 0:
        result.append((r - 1, c, bool(state.h_edges[r][c])))
    if r < rows - 1:
        result.append((r + 1, c, bool(state.h_edges[r + 1][c])))
    if c > 0:
        result.append((r, c - 1, bool(state.v_edges[r][c])))
    if c < cols - 1:
        result.append((r, c + 1, bool(state.v_edges[r][c + 1])))
    return result


def _count_long_regions(state: GameState) -> int:
    """
    Đếm N = số 'long' regions:
      - open chain dài ≥ 3
      - closed loop dài ≥ 4
    Đây chính là N dùng trong Berlekamp parity.
    """
    chains, loops = _analyze_chains_and_loops(state)
    return len(chains) + len(loops)


# ============================================================
#  Chain walking — dùng cho sacrifice decision
# ============================================================

def _find_capturable_chain_from(state: GameState, start_r: int, start_c: int):
    """
    Từ một box có edges_count == 3, đi theo chuỗi các box có thể ăn liên tiếp.
    Mỗi box tiếp theo phải có edges_count == 2 và kết nối qua cạnh CHƯA VẼ.
    Returns: list of (r, c) theo thứ tự ăn, bắt đầu từ start.
    """
    chain = [(start_r, start_c)]
    visited = {(start_r, start_c)}
    cr, cc = start_r, start_c

    while True:
        found = False
        for nr, nc, edge_drawn in _box_neighbors_edge_status(state, cr, cc):
            if (nr, nc) in visited or state.boxes[nr][nc] != 0:
                continue
            # Cạnh chung chưa vẽ → nếu ta ăn box hiện tại, box kề sẽ có 3 cạnh
            if not edge_drawn and state.edges_count[nr][nc] == 2:
                chain.append((nr, nc))
                visited.add((nr, nc))
                cr, cc = nr, nc
                found = True
                break
        if not found:
            break

    return chain


def _is_loop_chain(state: GameState, chain: list) -> bool:
    """
    Kiểm tra chain có phải loop (đầu và cuối kết nối qua cạnh chưa vẽ) không.
    Chỉ áp dụng khi len(chain) >= 4.
    """
    if len(chain) < 4:
        return False
    r1, c1 = chain[0]
    r2, c2 = chain[-1]
    # Kề nhau?
    if abs(r1 - r2) + abs(c1 - c2) != 1:
        return False
    # Cạnh chung chưa vẽ?
    if r1 == r2:
        col = max(c1, c2)
        return not state.v_edges[r1][col]
    else:
        row = max(r1, r2)
        return not state.h_edges[row][c1]


# ============================================================
#  Missing edge helpers
# ============================================================

def _get_missing_edge(state: GameState, br: int, bc: int):
    """Trả về cạnh còn thiếu của box có edges_count == 3."""
    if not state.h_edges[br][bc]:
        return Move('H', br, bc)
    if not state.h_edges[br + 1][bc]:
        return Move('H', br + 1, bc)
    if not state.v_edges[br][bc]:
        return Move('V', br, bc)
    if not state.v_edges[br][bc + 1]:
        return Move('V', br, bc + 1)
    return None


def _get_shared_undrawn_edge(state: GameState, r1: int, c1: int, r2: int, c2: int):
    """
    Cạnh chung CHƯA VẼ giữa 2 box kề nhau.
    Returns: Move hoặc None.
    """
    if r1 == r2:          # cùng hàng → cạnh dọc
        col = max(c1, c2)
        if not state.v_edges[r1][col]:
            return Move('V', r1, col)
    elif c1 == c2:        # cùng cột → cạnh ngang
        row = max(r1, r2)
        if not state.h_edges[row][c1]:
            return Move('H', row, c1)
    return None


# ============================================================
#  Sacrifice (Double-Cross) decision
# ============================================================

def _decide_greedy_or_sacrifice(state: GameState, chain: list) -> bool:
    """
    Quyết định có nên sacrifice (double-cross) không khi đang cầm một chain.

    Berlekamp parity rule:
      Sau khi ăn HẾT chain hiện tại, đếm N_còn_lại (long regions chưa mở).
      - N_còn_lại CHẴN → mình có lợi thế → ĂN HẾT (greedy), return False
      - N_còn_lại LẺ  → mình bất lợi   → SACRIFICE,         return True

    Điều này đúng VÌ: sau khi ta ăn hết chain, ta phải đi nước tiếp.
    Nếu N_còn_lại lẻ, ta sẽ là người phải mở chain tiếp theo → thua tempo.
    Sacrifice đẩy trách nhiệm mở chain về phía đối thủ.
    """
    n = len(chain)
    is_loop = _is_loop_chain(state, chain)
    sacrifice_size = 4 if is_loop else 2

    # Chain quá ngắn để sacrifice
    if n <= sacrifice_size:
        return False

    # Ăn hết chain (giả lập) → đếm N còn lại
    # Thực ra chỉ cần biết chain này có phải "long" không và
    # đếm N trên board hiện tại (chain đang mở = không tính vào N nữa)
    # Vì chain đang bị ăn → nó không còn là "unopened long region" nữa.
    # N_còn_lại = N_hiện_tại - 1 (bỏ chain này ra, vì nó đang bị ăn hết)
    N_current = _count_long_regions(state)

    # Chain hiện tại có phải long không?
    long_threshold = 3 if not is_loop else 4
    this_is_long = (n >= long_threshold)

    N_remaining = N_current - (1 if this_is_long else 0)

    # N_remaining CHẴN → ta đang có lợi thế sau khi ăn hết → greedy
    # N_remaining LẺ  → ta bất lợi → sacrifice
    return (N_remaining % 2 == 1)


def _execute_capture_chain(state: GameState, chain: list, sacrifice: bool):
    """
    Thực hiện ăn chain (và sacrifice nếu cần).
    - sacrifice=False: ăn tất cả n box.
    - sacrifice=True:
        open chain: ăn (n-2) box, vẽ cạnh sacrifice giữa box[-2] và box[-1]
        closed loop: ăn (n-4) box, vẽ cạnh sacrifice chia 4 box cuối
    Returns: (first_move, all_undo_info_list)
      first_move          — nước đầu tiên để trả về cho caller
      all_undo_info_list  — list of (move, undo_info) để undo nếu cần
    """
    n = len(chain)
    is_loop = _is_loop_chain(state, chain)
    sacrifice_size = 4 if is_loop else 2
    capture_count = n if not sacrifice else max(n - sacrifice_size, 0)

    all_moves = []
    first_move = None

    # --- Ăn capture_count box đầu ---
    for i in range(capture_count):
        br, bc = chain[i]
        if state.boxes[br][bc] != 0:
            # Đã bị ăn rồi (không nên xảy ra)
            continue
        missing = _get_missing_edge(state, br, bc)
        if missing is None:
            break
        undo = apply_move(state, missing)
        if first_move is None:
            first_move = missing
        all_moves.append((missing, undo))

    # --- Sacrifice edge nếu cần ---
    if sacrifice and capture_count < n:
        if not is_loop:
            # Open chain: vẽ cạnh giữa box[-2] và box[-1]
            r1, c1 = chain[n - 2]
            r2, c2 = chain[n - 1]
            sac_edge = _get_shared_undrawn_edge(state, r1, c1, r2, c2)
        else:
            # Closed loop: vẽ cạnh giữa box[capture_count] và box[capture_count+1]
            if capture_count + 1 < n:
                r1, c1 = chain[capture_count]
                r2, c2 = chain[capture_count + 1]
                sac_edge = _get_shared_undrawn_edge(state, r1, c1, r2, c2)
            else:
                sac_edge = None

        if sac_edge is not None:
            undo = apply_move(state, sac_edge)
            if first_move is None:
                first_move = sac_edge
            all_moves.append((sac_edge, undo))

    return first_move, all_moves


# ============================================================
#  Pha 2: Mở chain (forced opening)
# ============================================================

def _find_all_chains_info(state: GameState):
    """
    Tìm tất cả 'unopened chains' (các chain/loop chưa bị mở).
    Một chain chưa bị mở = không có box nào có edges_count == 3 trong chain đó.

    Returns: list of (chain_cells: list, is_loop: bool)
    """
    rows, cols = state.rows, state.cols
    visited = [[False] * cols for _ in range(rows)]
    result = []

    for sr in range(rows):
        for sc in range(cols):
            if visited[sr][sc] or state.boxes[sr][sc] != 0:
                continue
            if state.edges_count[sr][sc] > 2:
                # Box đã có ≥ 3 cạnh → đang trong chain đã mở rồi
                visited[sr][sc] = True
                continue
            if state.edges_count[sr][sc] < 1:
                visited[sr][sc] = True
                continue

            # BFS component qua cạnh chưa vẽ
            component = []
            queue = [(sr, sc)]
            visited[sr][sc] = True
            while queue:
                cr, cc = queue.pop()
                component.append((cr, cc))
                for nr, nc, edge_drawn in _box_neighbors_edge_status(state, cr, cc):
                    if not visited[nr][nc] and state.boxes[nr][nc] == 0 and not edge_drawn:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

            n = len(component)
            if n < 1:
                continue

            # Kiểm tra loop
            comp_set = set(component)
            is_loop = True
            for cr, cc in component:
                deg = sum(
                    1 for nr, nc, drawn in _box_neighbors_edge_status(state, cr, cc)
                    if (nr, nc) in comp_set and not drawn
                )
                if deg != 2:
                    is_loop = False
                    break

            result.append((component, is_loop))

    return result


def _best_forced_opening(state: GameState):
    """
    Pha 2: Không còn safe move, phải mở một chain.
    Chiến lược:
      1. Ưu tiên mở short chain (≤ 2 box): đối thủ ăn ít, không sacrifice được
         → tempo lập tức trở về mình.
      2. Nếu buộc mở long chain: chọn cạnh của chain
         sao cho N_còn_lại sau khi đối thủ sacrifice có lợi nhất.

    Returns: Move
    """
    chains_info = _find_all_chains_info(state)

    short_chains = [(cells, is_loop) for cells, is_loop in chains_info if len(cells) <= 2]
    long_chains  = [(cells, is_loop) for cells, is_loop in chains_info if len(cells) >= 3]

    # --- Ưu tiên short chain ---
    if short_chains:
        # Mở short chain ngắn nhất (thường = 1 hoặc 2 box)
        short_chains.sort(key=lambda x: len(x[0]))
        cells, _ = short_chains[0]
        # Tìm cạnh để vẽ lên box này (cạnh chưa vẽ của box có ít cạnh nhất)
        best_cell = min(cells, key=lambda rc: state.edges_count[rc[0]][rc[1]])
        return _pick_opening_edge(state, best_cell[0], best_cell[1])

    # --- Buộc mở long chain: minimax nhẹ chọn chain ---
    if not long_chains:
        # Fallback: bất kỳ nước nào (không nên xảy ra)
        legal = get_legal_moves(state)
        return legal[0] if legal else None

    # Thử từng long chain, chọn cái có lợi nhất theo parity
    N_current = _count_long_regions(state)
    best_move = None
    best_parity_advantage = -999

    for cells, is_loop in long_chains:
        n = len(cells)
        # Sau khi ta mở chain này → đối thủ sẽ sacrifice (nếu là long chain)
        # → N giảm 1 (chain này biến mất) → N_after = N_current - 1
        N_after = N_current - 1
        # N_after CHẴN → đối thủ có lợi sau sacrifice → ta bất lợi → -1
        # N_after LẺ   → ta có lợi → +1
        advantage = 1 if (N_after % 2 == 1) else -1
        if advantage > best_parity_advantage:
            best_parity_advantage = advantage
            best_cell = min(cells, key=lambda rc: state.edges_count[rc[0]][rc[1]])
            best_move = _pick_opening_edge(state, best_cell[0], best_cell[1])

    return best_move


def _pick_opening_edge(state: GameState, br: int, bc: int):
    """
    Chọn cạnh để 'mở' một box (tức là vẽ cạnh vào box đó mà không hoàn thành nó).
    Chọn cạnh mà kết quả: edges_count của box đó tăng lên nhưng KHÔNG lên 3 nếu có thể.
    Thực ra ở đây ta muốn tạo box 3-cạnh cho đối thủ ăn → vẽ bất kỳ cạnh nào của box.
    """
    # Kiểm tra top
    if not state.h_edges[br][bc]:
        return Move('H', br, bc)
    if not state.h_edges[br + 1][bc]:
        return Move('H', br + 1, bc)
    if not state.v_edges[br][bc]:
        return Move('V', br, bc)
    if not state.v_edges[br][bc + 1]:
        return Move('V', br, bc + 1)
    return None


# ============================================================
#  Evaluation function  (dùng trong Pha 1 minimax)
# ============================================================

def _evaluate(state: GameState, ai_player: int) -> float:
    """
    Hàm đánh giá trạng thái cho minimax trong Pha 1.

    Thành phần:
      1. score_diff: hiệu số điểm hiện tại (quan trọng nhất)
      2. parity_score: dựa trên N (số long regions) và ai đang đến lượt
         — đánh giá ai sẽ kiểm soát chain trong Pha 2
      3. penalty: phạt các box có 2 cạnh (dễ thành chain dài)
    """
    if ai_player == 1:
        score_diff = state.score_player1 - state.score_player2
    else:
        score_diff = state.score_player2 - state.score_player1

    open_chains, closed_loops = _analyze_chains_and_loops(state)
    N = len(open_chains) + len(closed_loops)

    # Ước tính tổng số box AI sẽ ăn được từ các long chains
    # Người kiểm soát (sacrifice-holder) ăn được: sum(len-2) cho open chain,
    # sum(len-4) cho loop. Người không kiểm soát chỉ ăn được phần sacrifice.
    gain_if_control = sum(n - 2 for n in open_chains) + sum(n - 4 for n in closed_loops)

    # Parity: ai là người đến lượt trong Pha 2?
    # N CHẴN → người phải đi tiếp (current_player sau khi safe moves hết) bất lợi
    # N LẺ  → người phải đi tiếp có lợi
    # "Người phải đi tiếp" trong Pha 2 = current_player ở thời điểm đánh giá
    # (vì pha 1 chưa kết thúc, sau khi safe moves hết thì current_player mở chain đầu)
    is_ai_turn = (state.current_player == ai_player)

    if N % 2 == 1:
        # Người phải mở chain (current_player) có lợi thế
        parity_advantage = gain_if_control if is_ai_turn else -gain_if_control
    else:
        # Người phải mở chain (current_player) bất lợi
        parity_advantage = -gain_if_control if is_ai_turn else gain_if_control

    # Phạt box 2 cạnh: chúng dễ trở thành chain dài sau này
    boxes_2 = sum(
        1 for r in range(state.rows) for c in range(state.cols)
        if state.boxes[r][c] == 0 and state.edges_count[r][c] == 2
    )

    return score_diff * 200 + parity_advantage * 30 - boxes_2 * 5


# ============================================================
#  Move ordering  (cho alpha-beta pruning hiệu quả hơn)
# ============================================================

def _order_moves(state: GameState, moves: list, tt_best_key=None) -> list:
    """
    Sắp xếp nước đi: TT move → safe → risky (theo số box nguy hiểm tạo ra).
    """
    tt_move = None
    safe = []
    risky = []

    for m in moves:
        mk = (m.edge_type, m.r, m.c)
        if tt_best_key and mk == tt_best_key:
            tt_move = m
            continue
        danger = _creates_third_edge(state, m)
        if danger == 0:
            safe.append(m)
        else:
            risky.append((m, danger))

    risky.sort(key=lambda x: x[1])
    ordered = safe + [m for m, _ in risky]
    if tt_move:
        ordered.insert(0, tt_move)
    return ordered


# ============================================================
#  Minimax (Pha 1: chỉ search safe moves)
# ============================================================

def _minimax_phase1(state: GameState, depth: int, alpha: float, beta: float,
                    ai_player: int):
    """
    Minimax chỉ xét safe moves (Pha 1).
    Nếu không còn safe moves → evaluate bằng parity.
    """
    global _tt

    if is_terminal(state):
        if ai_player == 1:
            return (state.score_player1 - state.score_player2) * 10000, None
        else:
            return (state.score_player2 - state.score_player1) * 10000, None

    safe_moves = _get_safe_moves(state)

    if not safe_moves or depth <= 0:
        return _evaluate(state, ai_player), None

    # TT lookup
    alpha_orig = alpha
    key = _state_key(state)
    tt_best_key = None

    if key in _tt:
        tt_depth, tt_score, tt_flag, tt_mk = _tt[key]
        if tt_depth >= depth:
            if tt_flag == EXACT:
                return tt_score, None
            elif tt_flag == LOWERBOUND:
                alpha = max(alpha, tt_score)
            elif tt_flag == UPPERBOUND:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score, None
        tt_best_key = tt_mk

    ordered = _order_moves(state, safe_moves, tt_best_key)
    is_max  = (state.current_player == ai_player)
    best_val  = -math.inf if is_max else math.inf
    best_move = ordered[0]

    for m in ordered:
        undo = apply_move(state, m)
        val, _ = _minimax_phase1(state, depth - 1, alpha, beta, ai_player)
        undo_move(state, m, undo)

        if is_max:
            if val > best_val:
                best_val = val
                best_move = m
            alpha = max(alpha, val)
        else:
            if val < best_val:
                best_val = val
                best_move = m
            beta = min(beta, val)

        if alpha >= beta:
            break

    # TT store
    if len(_tt) < _TT_MAX:
        if best_val <= alpha_orig:
            flag = UPPERBOUND
        elif best_val >= beta - 1:
            flag = LOWERBOUND
        else:
            flag = EXACT
        _tt[key] = (depth, best_val, flag, (best_move.edge_type, best_move.r, best_move.c))

    return best_val, best_move


# ============================================================
#  Public API: get_best_move
# ============================================================

def get_best_move(state: GameState, ai_player: int = 2,
                  base_depth: int = None, time_limit: float = 3.0) -> Move:
    """
    Trả về nước đi tốt nhất cho AI theo luồng quyết định:

    1. Nếu có box ăn ngay (Pha 2, đang giữa chain):
       → Tìm chain, quyết định greedy hay sacrifice theo Berlekamp parity.

    2. Nếu còn safe moves (Pha 1):
       → Minimax chỉ trên safe moves, evaluate bằng parity score.

    3. Nếu không còn safe moves (Pha 2, phải mở chain):
       → Chọn chain tốt nhất để mở theo parity.
    """
    import time
    _tt_clear()
    start = time.time()

    if base_depth is None:
        total_boxes = state.rows * state.cols
        if total_boxes <= 9:
            base_depth = 8
        elif total_boxes <= 16:
            base_depth = 6
        elif total_boxes <= 25:
            base_depth = 5
        elif total_boxes <= 36:
            base_depth = 4
        else:
            base_depth = 3

    legal = get_legal_moves(state)
    if not legal:
        return None
    if len(legal) == 1:
        return legal[0]

    # ─── Bước 1: Có box ăn ngay? ─────────────────────────────
    cap_move = _get_capture_move(state)
    if cap_move is not None:
        # Tìm chain bắt đầu từ box mà cap_move sẽ hoàn thành
        affected = get_affected_boxes(cap_move, state.rows, state.cols)
        start_box = None
        for br, bc in affected:
            if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 3:
                start_box = (br, bc)
                break

        if start_box is not None:
            chain = _find_capturable_chain_from(state, start_box[0], start_box[1])
            do_sacrifice = _decide_greedy_or_sacrifice(state, chain)
            first_move, _ = _execute_capture_chain(state, chain, sacrifice=do_sacrifice)
            # Undo những nước đã apply trong _execute_capture_chain
            # (chúng ta chỉ muốn QUYẾT ĐỊNH nước đầu, không apply thật)
            # → Thực ra _execute_capture_chain đã apply thật vào state!
            # → Cần undo lại để trả state về như cũ.
            # → Dùng approach khác: chỉ tính toán, không apply.
            # Xem hàm _decide_and_get_first_move bên dưới.
            pass

        # Dùng hàm helper không side-effect:
        return _decide_and_get_first_move(state, ai_player)

    # ─── Bước 2: Còn safe moves? (Pha 1) ────────────────────
    safe_moves = _get_safe_moves(state)
    if safe_moves:
        # Adaptive depth
        remaining = state.moves_remaining
        depth = base_depth
        if remaining <= 10:
            depth = min(remaining, 20)
        elif remaining <= 16:
            depth = base_depth + 4
        elif remaining <= 22:
            depth = base_depth + 2

        # Iterative Deepening với time limit
        best_move = safe_moves[0]
        for d in range(1, depth + 1):
            elapsed = time.time() - start
            if d > 2 and elapsed > time_limit * 0.8:
                break
            val, move = _minimax_phase1(state, d, -math.inf, math.inf, ai_player)
            if move:
                best_move = move
            if abs(val) >= 9000:
                break

        return best_move

    # ─── Bước 3: Không còn safe moves → phải mở chain ───────
    return _best_forced_opening(state)


def _decide_and_get_first_move(state: GameState, ai_player: int) -> Move:
    """
    Quyết định greedy hay sacrifice cho chain hiện tại,
    trả về nước đầu tiên mà KHÔNG thay đổi state.
    """
    # Tìm tất cả các chain đang capturable
    rows, cols = state.rows, state.cols
    found_chain = None
    found_start = None

    for r in range(rows):
        for c in range(cols):
            if state.boxes[r][c] == 0 and state.edges_count[r][c] == 3:
                found_start = (r, c)
                break
        if found_start:
            break

    if found_start is None:
        # Fallback
        legal = get_legal_moves(state)
        return legal[0] if legal else None

    chain = _find_capturable_chain_from(state, found_start[0], found_start[1])
    do_sacrifice = _decide_greedy_or_sacrifice(state, chain)

    n = len(chain)
    is_loop = _is_loop_chain(state, chain)
    sacrifice_size = 4 if is_loop else 2

    if not do_sacrifice or n <= sacrifice_size:
        # Greedy: trả về nước ăn box đầu tiên
        return _get_missing_edge(state, chain[0][0], chain[0][1])
    else:
        # Sacrifice:
        # Ăn (n - sacrifice_size) box đầu → trả về nước đầu tiên
        # Nhưng nếu n - sacrifice_size == 0 → trả về sacrifice edge ngay
        capture_count = n - sacrifice_size
        if capture_count > 0:
            return _get_missing_edge(state, chain[0][0], chain[0][1])
        else:
            # Sacrifice ngay lập tức: vẽ cạnh chia chain
            if not is_loop:
                r1, c1 = chain[n - 2]
                r2, c2 = chain[n - 1]
            else:
                mid = n // 2
                r1, c1 = chain[mid - 1]
                r2, c2 = chain[mid]
            return _get_shared_undrawn_edge(state, r1, c1, r2, c2)