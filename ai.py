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
                    # Box kề chia sẻ cạnh chưa vẽ VÀ có >= 2 cạnh
                    if not shared_drawn and state.edges_count[nr][nc] >= 2:
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


def _get_exit_edge(state, r, c, shared_edge):
    """Tìm cạnh còn thiếu của box (r,c) mà không phải là shared_edge."""
    edges = []
    if not state.h_edges[r][c]: edges.append(Move('H', r, c))
    if not state.h_edges[r + 1][c]: edges.append(Move('H', r + 1, c))
    if not state.v_edges[r][c]: edges.append(Move('V', r, c))
    if not state.v_edges[r][c + 1]: edges.append(Move('V', r, c + 1))
    
    for e in edges:
        if e.edge_type != shared_edge.edge_type or e.r != shared_edge.r or e.c != shared_edge.c:
            return e
    return None


# ============================================================
#  Forcing Moves: Greedy Capture + Double-Cross
# ============================================================

def get_forcing_moves(state: GameState):
    """
    Sinh các nước đi ép buộc (ăn box) và sacrifice (double-cross) 
    nếu chuỗi đang ở critical point.
    """
    chains = _find_capturable_chains(state)
    if not chains:
        return []

    chain = chains[0]
    n = len(chain)
    first_box = chain[0]
    last_box = chain[-1]
    is_closed = (state.edges_count[last_box[0]][last_box[1]] == 3) and (n > 1)
    
    moves = []
    missing = _get_missing_edge(state, first_box[0], first_box[1])
    if missing:
        moves.append(missing)
        
    if is_closed:
        if n == 4:
            sac_a = chain[1]
            sac_b = chain[2]
            sac_move = _get_shared_edge(state, sac_a[0], sac_a[1], sac_b[0], sac_b[1])
            if sac_move and not _is_edge_drawn(state, sac_move):
                moves.append(sac_move)
    else:
        if n == 2:
            sac_a = chain[0]
            sac_b = chain[1]
            shared = _get_shared_edge(state, sac_a[0], sac_a[1], sac_b[0], sac_b[1])
            if shared:
                sac_move = _get_exit_edge(state, sac_b[0], sac_b[1], shared)
                if sac_move and not _is_edge_drawn(state, sac_move):
                    moves.append(sac_move)
                    
    return moves


def _is_edge_drawn(state, move):
    """Kiểm tra cạnh đã được vẽ chưa."""
    if move.edge_type == 'H':
        return state.h_edges[move.r][move.c]
    return state.v_edges[move.r][move.c]


# ============================================================
#  Heuristic evaluation
# ============================================================

def _count_double_edge_pairs(state: GameState):
    """
    Đếm số cặp ô 2 cạnh kề nhau (cùng hàng hoặc cùng cột)
    qua cạnh chưa vẽ. Đây là dấu hiệu cực kỳ nguy hiểm: 
    ai đi vào 1 ô sẽ cho đối thủ ăn ô kia.
    """
    count = 0
    for r in range(state.rows):
        for c in range(state.cols):
            if state.boxes[r][c] != 0 or state.edges_count[r][c] != 2:
                continue
            # Check phải
            if (c + 1 < state.cols and state.boxes[r][c + 1] == 0 
                    and state.edges_count[r][c + 1] == 2):
                if not state.v_edges[r][c + 1]:
                    count += 1
            # Check dưới
            if (r + 1 < state.rows and state.boxes[r + 1][c] == 0 
                    and state.edges_count[r + 1][c] == 2):
                if not state.h_edges[r + 1][c]:
                    count += 1
    return count


def evaluate(state: GameState, ai_player: int):
    """Hàm đánh giá trạng thái cho Minimax."""
    if ai_player == 1:
        score_diff = state.score_player1 - state.score_player2
    else:
        score_diff = state.score_player2 - state.score_player1

    capturable = 0
    boxes_2 = 0
    boxes_safe = 0

    for r in range(state.rows):
        for c in range(state.cols):
            if state.boxes[r][c] == 0:
                ec = state.edges_count[r][c]
                if ec == 3:
                    capturable += 1
                elif ec == 2:
                    boxes_2 += 1
                else:
                    boxes_safe += 1

    if state.current_player == ai_player:
        cap_score = capturable * 50
    else:
        cap_score = -capturable * 50

    chain_score = _evaluate_chains(state, ai_player)

    # Tự động điều chỉnh trọng số Nimstring dựa trên giai đoạn game
    if boxes_safe > 2:
        chain_weight = 15   # Giữa game: Ưu tiên ăn hộp thực tế
    elif boxes_safe > 0:
        chain_weight = 75   # Sắp vào Endgame: Bắt đầu cân nhắc Parity
    else:
        chain_weight = 225  # Endgame thực sự: Áp dụng mạnh mẽ Chain Theory

    # Phạt nặng cặp ô 2 cạnh kề nhau (double-edge pairs)
    double_edge_pairs = _count_double_edge_pairs(state)

    return (score_diff * 100 + cap_score + chain_score * chain_weight 
            - boxes_2 * 20 - double_edge_pairs * 30)


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
    Đánh giá chain/loop control dựa trên Nimstring theory chuẩn xác.
    Tính toán chính xác số điểm (net score) dự kiến mà mỗi bên sẽ nhận được
    khi toàn bộ các chuỗi/loop được giải quyết bằng chiến thuật double-cross.
    """
    open_chains, closed_loops = _analyze_chains_and_loops(state)

    regions = []
    for ch in open_chains:
        regions.append({'len': ch, 'sac': 2})
    for lp in closed_loops:
        regions.append({'len': lp, 'sac': 4})

    if not regions:
        return 0

    # Nạn nhân (victim) sẽ ép ta (controller) ăn các chuỗi có net-gain ít nhất trước.
    # Do đó, chuỗi cuối cùng (được ăn trọn, không phải sacrifice) sẽ là chuỗi ngon nhất.
    regions.sort(key=lambda x: x['len'] - x['sac'])

    total_regions = len(regions)

    # Quy tắc Parity:
    # Khi số lượng region CHẴN, người đang có lượt (current_player) sẽ có cơ hội
    # bám sát nước đi của đối thủ (mirror) và giành quyền điều khiển (controller).
    current_player_controls = (total_regions % 2 == 0)

    controller_points = 0
    victim_points = 0

    for i, reg in enumerate(regions):
        if i == total_regions - 1:
            # Chuỗi cuối cùng: Không cần sacrifice nữa, Controller ăn trọn toàn bộ
            controller_points += reg['len']
        else:
            # Áp dụng chiến thuật Double-cross ép buộc
            controller_points += max(0, reg['len'] - reg['sac'])
            victim_points += min(reg['len'], reg['sac'])

    net_chain_score = controller_points - victim_points

    if state.current_player == ai_player:
        # AI đang đi
        ai_chain_diff = net_chain_score if current_player_controls else -net_chain_score
    else:
        # Đối thủ đang đi
        ai_chain_diff = -net_chain_score if current_player_controls else net_chain_score

    # Nhân trọng số 15. Vì trong hàm evaluate() đang có đoạn `chain_score * 15`
    # Mỗi box lợi thế ở đây sẽ đóng góp: 1 * 15 * 15 = 225 điểm heuristic 
    # (vượt trội hơn hẳn so với cap_score thông thường)
    return ai_chain_diff


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
#  Minimax + Alpha-Beta + TT
# ============================================================

def minimax(state: GameState, depth: int, alpha: float, beta: float,
            ai_player: int):
    global _tt

    if is_terminal(state):
        if ai_player == 1:
            diff = state.score_player1 - state.score_player2
        else:
            diff = state.score_player2 - state.score_player1
        return diff * 10000, None

    forcing_moves = get_forcing_moves(state)

    if depth <= 0 and not forcing_moves:
        return evaluate(state, ai_player), None

    # TT lookup
    alpha_orig = alpha
    beta_orig = beta
    key = _state_key(state)
    tt_best_key = None

    if key in _tt:
        tt_depth, tt_score, tt_flag, tt_mk = _tt[key]
        if tt_depth >= depth:
            if tt_flag == EXACT:
                return tt_score, _key_to_move(tt_mk)
            elif tt_flag == LOWERBOUND:
                alpha = max(alpha, tt_score)
            elif tt_flag == UPPERBOUND:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score, _key_to_move(tt_mk)
        tt_best_key = tt_mk

    is_max = (state.current_player == ai_player)

    if forcing_moves:
        ordered = forcing_moves
    else:
        legal_moves = get_legal_moves(state)
        if not legal_moves:
            return evaluate(state, ai_player), None
        ordered = _order_moves(state, legal_moves, tt_best_key)

    best_move = ordered[0]

    # Alpha-Beta search
    if is_max:
        best_val = -math.inf
        for move in ordered:
            undo_info = apply_move(state, move)
            next_depth = depth if undo_info['previous_player'] == state.current_player else depth - 1
            val, _ = minimax(state, next_depth, alpha, beta, ai_player)
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
            next_depth = depth if undo_info['previous_player'] == state.current_player else depth - 1
            val, _ = minimax(state, next_depth, alpha, beta, ai_player)
            undo_move(state, move, undo_info)
            if val < best_val:
                best_val = val
                best_move = move
            beta = min(beta, val)
            if alpha >= beta:
                break

    # TT store
    if len(_tt) < _tt_max:
        flag = EXACT
        if best_val <= alpha_orig:
            flag = UPPERBOUND
        elif best_val >= beta_orig:
            flag = LOWERBOUND
        _tt[key] = (depth, best_val, flag, _move_key(best_move))

    return best_val, best_move


# ============================================================
#  Adaptive depth
# ============================================================

def _get_adaptive_depth(state: GameState, base_depth: int):
    """Tự động tăng depth khi game gần kết thúc."""
    remaining = state.moves_remaining
    if remaining <= 10:
        return min(remaining, 22)
    elif remaining <= 16:
        return base_depth + 6
    elif remaining <= 22:
        return base_depth + 4
    elif remaining <= 30:
        return base_depth + 2
    elif remaining <= 40:
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

    # # Tự động điều chỉnh time_limit theo giai đoạn game
    # if time_limit is None:
    #     total_moves = state.moves_remaining
    #     total_boxes = state.rows * state.cols
    #     if total_boxes <= 9:
    #         time_limit = 2.0        # Bàn nhỏ: đủ nhanh
    #     elif total_moves <= 12:
    #         time_limit = 5.0        # Sát endgame: cho nhiều thời gian để tính chính xác
    #     elif total_moves <= 25:
    #         time_limit = 3.5        # Gần endgame
    #     elif total_moves <= 40:
    #         time_limit = 2.5        # Chuyển tiếp mid→late
    #     elif total_moves <= 60:
    #         time_limit = 2.0        # Midgame
    #     else:
    #         time_limit = 1.5        # Đầu game: nhiều nước, không cần nghĩ sâu

    if base_depth is None:
        total_boxes = state.rows * state.cols
        if total_boxes <= 9:
            base_depth = 10
        elif total_boxes <= 16:
            base_depth = 8
        elif total_boxes <= 25:
            base_depth = 6
        elif total_boxes <= 49:
            base_depth = 4
        else:
            base_depth = 2

    _tt.clear()

    forcing = get_forcing_moves(state)
    if forcing:
        if len(forcing) == 1:
            return forcing[0]
        legal_moves = forcing
    else:
        legal_moves = get_legal_moves(state)
        
    if not legal_moves:
        return None
        
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
