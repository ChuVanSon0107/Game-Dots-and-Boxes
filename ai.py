import math
import time
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
_search_deadline = None
_search_timed_out = False



def _time_up():
    return _search_deadline is not None and time.perf_counter() >= _search_deadline

def _state_key(state: GameState):
    """Tạo hashable key từ trạng thái bàn cờ cho transposition table."""
    h = tuple(val for row in state.h_edges for val in row)
    v = tuple(val for row in state.v_edges for val in row)
    boxes = tuple(val for row in state.boxes for val in row)
    return (h, v, boxes, state.current_player, state.score_player1, state.score_player2)


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





def _count_safe_moves(state: GameState):
    count = 0
    for move in get_legal_moves(state):
        if would_create_third_edge(state, move) == 0:
            count += 1
    return count


def _best_forced_opener_loss(state: GameState):
    best_loss = math.inf
    for move in get_legal_moves(state):
        if would_create_third_edge(state, move) > 0:
            best_loss = min(best_loss, _estimate_opened_chain_loss(state, move))
    return 0 if best_loss == math.inf else best_loss


def _safe_pressure_score(state: GameState, move: Move):
    """Prefer safe moves that leave the opponent close to opening a chain."""
    mover = state.current_player
    undo_info = apply_move(state, move)

    opponent_safe_moves = _count_safe_moves(state)
    forced_opener_loss = 0
    if opponent_safe_moves == 0 and not get_forcing_moves(state):
        forced_opener_loss = _best_forced_opener_loss(state)

    chain_advantage = _evaluate_chains(state, mover)
    undo_move(state, move, undo_info)

    return (
        opponent_safe_moves,
        -forced_opener_loss,
        -chain_advantage,
    )

def _candidate_limit(state: GameState):
    """Keep alpha-beta practical on large boards after strategic filtering."""
    total_boxes = state.rows * state.cols
    if total_boxes <= 16:
        return 32
    if total_boxes <= 36:
        return 24
    return 18


def _move_center_distance(state: GameState, move: Move):
    if move.edge_type == 'H':
        mr, mc = move.r - 0.5, move.c + 0.5
    else:
        mr, mc = move.r + 0.5, move.c - 0.5
    return abs(mr - state.rows / 2) + abs(mc - state.cols / 2)


def _safe_move_score(state: GameState, move: Move):
    affected_counts = [
        state.edges_count[r][c]
        for r, c in get_affected_boxes(move, state.rows, state.cols)
        if state.boxes[r][c] == 0
    ]
    creates_two_edge_boxes = sum(1 for count in affected_counts if count == 1)
    touches_empty_boxes = sum(1 for count in affected_counts if count == 0)
    return _safe_pressure_score(state, move) + (
        creates_two_edge_boxes,
        len(affected_counts),
        -touches_empty_boxes,
        _move_center_distance(state, move),
        _move_key(move),
    )


def _estimate_opened_chain_loss(state: GameState, move: Move):
    """Estimate how many boxes the opponent can start collecting after opener."""
    undo_info = apply_move(state, move)
    chains = _find_capturable_chains(state)
    loss = max((len(chain) for chain in chains), default=0)
    undo_move(state, move, undo_info)
    return loss


def _post_move_chain_advantage(state: GameState, move: Move):
    mover = state.current_player
    undo_info = apply_move(state, move)
    advantage = _evaluate_chains(state, mover)
    undo_move(state, move, undo_info)
    return advantage


def _risky_move_score(state: GameState, move: Move):
    third_edges = would_create_third_edge(state, move)
    return (
        _estimate_opened_chain_loss(state, move),
        -_post_move_chain_advantage(state, move),
        third_edges,
        _move_center_distance(state, move),
        _move_key(move),
    )


def _dedupe_and_limit(moves, limit, preferred_key=None):
    seen = set()
    ordered = []
    preferred = None

    for move in moves:
        key = _move_key(move)
        if key in seen:
            continue
        seen.add(key)
        if preferred_key and key == preferred_key:
            preferred = move
        else:
            ordered.append(move)

    if preferred:
        ordered.insert(0, preferred)
    return ordered[:limit]
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



def _component_touched_by_move(state: GameState, move: Move, component):
    component_set = set(component)
    return any(box in component_set for box in get_affected_boxes(move, state.rows, state.cols))


def _capturable_boxes_after_move(state: GameState, move: Move, component):
    component_set = set(component)
    undo_info = apply_move(state, move)
    capturable = set()
    for chain in _find_capturable_chains(state):
        for box in chain:
            if box in component_set:
                capturable.add(box)
    undo_move(state, move, undo_info)
    return capturable


def _get_sacrifice_moves(state: GameState, chain):
    """
    Find hard-hearted handout moves for a capturable component.

    Open chains hand out the last 2 boxes. Opened loops / closed chains
    hand out the last 4 boxes. A sacrifice move must not score now; it
    should make the remaining component capturable for the opponent.
    """
    n = len(chain)
    if n < 2:
        return []

    three_edge_boxes = sum(
        1 for r, c in chain
        if state.boxes[r][c] == 0 and state.edges_count[r][c] == 3
    )
    handout_size = 4 if three_edge_boxes >= 2 else 2
    if n != handout_size:
        return []

    candidates = []
    for move in get_legal_moves(state):
        if would_complete_box(state, move) > 0:
            continue
        if not _component_touched_by_move(state, move, chain):
            continue

        capturable = _capturable_boxes_after_move(state, move, chain)
        if len(capturable) >= handout_size:
            candidates.append(move)

    candidates.sort(key=lambda move: (
        -len(_capturable_boxes_after_move(state, move, chain)),
        would_create_third_edge(state, move),
        _move_key(move),
    ))
    return candidates

# ============================================================
#  Forcing Moves: Greedy Capture + Double-Cross
# ============================================================

def get_forcing_moves(state: GameState):
    """
    Sinh cac nuoc di ep buoc (an box) va sacrifice (double-cross)
    neu chuoi dang o critical point.
    """
    chains = _find_capturable_chains(state)
    moves = []
    seen = set()

    def add_move(move):
        if move is None or _is_edge_drawn(state, move):
            return
        key = _move_key(move)
        if key not in seen:
            seen.add(key)
            moves.append(move)

    for chain in chains:
        if not chain:
            continue

        first_box = chain[0]
        add_move(_get_missing_edge(state, first_box[0], first_box[1]))

        for sacrifice_move in _get_sacrifice_moves(state, chain):
            add_move(sacrifice_move)

    # Fallback: never miss an immediately capturable box if the chain walk
    # above was blocked by an unusual component shape.
    for r in range(state.rows):
        for c in range(state.cols):
            if state.boxes[r][c] == 0 and state.edges_count[r][c] == 3:
                add_move(_get_missing_edge(state, r, c))

    return moves

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
        chain_weight = 1   # Giữa game: Ưu tiên ăn hộp thực tế
    elif boxes_safe > 0:
        chain_weight = 5   # Sắp vào Endgame: Bắt đầu cân nhắc Parity
    else:
        chain_weight = 15  # Endgame thực sự: Áp dụng mạnh mẽ Chain Theory

    mobility_score = 0
    if capturable == 0:
        legal_moves = get_legal_moves(state)
        safe_count = 0
        best_opener_loss = math.inf
        for move in legal_moves:
            if would_create_third_edge(state, move) == 0:
                safe_count += 1
            else:
                best_opener_loss = min(best_opener_loss, _estimate_opened_chain_loss(state, move))

        if safe_count > 0:
            mobility_score = safe_count * (2 if state.current_player == ai_player else -2)
        elif legal_moves and best_opener_loss < math.inf:
            # No safe moves means the side to move must open a chain. That is
            # usually good for the other side, especially on large boards.
            swing = best_opener_loss * 60
            mobility_score = -swing if state.current_player == ai_player else swing

    return score_diff * 100 + cap_score + chain_score * chain_weight + mobility_score - boxes_2 * 3


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
    return ai_chain_diff * 15


# ============================================================
#  Move ordering
# ============================================================

def _order_moves(state, moves, tt_best_key=None):
    """Order and prune moves using Dots-and-Boxes strategy phases."""
    limit = _candidate_limit(state)

    captures = [move for move in moves if would_complete_box(state, move) > 0]
    if captures:
        captures.sort(key=lambda move: (-would_complete_box(state, move), _risky_move_score(state, move)))
        return _dedupe_and_limit(captures, max(limit, len(captures)), tt_best_key)

    safe = [move for move in moves if would_create_third_edge(state, move) == 0]
    if safe:
        safe.sort(key=lambda move: _safe_move_score(state, move))
        return _dedupe_and_limit(safe, limit, tt_best_key)

    risky = list(moves)
    risky.sort(key=lambda move: _risky_move_score(state, move))
    return _dedupe_and_limit(risky, limit, tt_best_key)

# ============================================================
#  Minimax + Alpha-Beta + TT
# ============================================================

def minimax(state: GameState, depth: int, alpha: float, beta: float,
            ai_player: int):
    global _tt, _search_timed_out

    if _time_up():
        _search_timed_out = True
        return evaluate(state, ai_player), None

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
            if _time_up():
                _search_timed_out = True
                break
            undo_info = apply_move(state, move)
            next_depth = depth if undo_info['previous_player'] == state.current_player else depth - 1
            val, _ = minimax(state, next_depth, alpha, beta, ai_player)
            undo_move(state, move, undo_info)
            if _search_timed_out:
                break
            if val > best_val:
                best_val = val
                best_move = move
            alpha = max(alpha, val)
            if alpha >= beta:
                break
    else:
        best_val = math.inf
        for move in ordered:
            if _time_up():
                _search_timed_out = True
                break
            undo_info = apply_move(state, move)
            next_depth = depth if undo_info['previous_player'] == state.current_player else depth - 1
            val, _ = minimax(state, next_depth, alpha, beta, ai_player)
            undo_move(state, move, undo_info)
            if _search_timed_out:
                break
            if val < best_val:
                best_val = val
                best_move = move
            beta = min(beta, val)
            if alpha >= beta:
                break

    if best_val in (-math.inf, math.inf):
        return evaluate(state, ai_player), None

    # TT store
    if not _search_timed_out and len(_tt) < _tt_max:
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
        return base_depth + 4
    elif remaining <= 22:
        return base_depth + 3
    elif remaining <= 30:
        return base_depth + 2
    else:
        return base_depth + 1


# ============================================================
#  Public API
# ============================================================

def get_best_move(state: GameState, ai_player: int = 2, base_depth: int = None,
                   time_limit: float = 8.0):
    """
    Tìm nước đi tốt nhất cho AI bằng Minimax + Alpha-Beta Pruning
    với Double-Cross strategy.
    """
    global _tt, _search_deadline, _search_timed_out
    start_time = time.perf_counter()
    _search_deadline = start_time + time_limit
    _search_timed_out = False

    if base_depth is None:
        total_boxes = state.rows * state.cols
        if total_boxes <= 9:
            base_depth = 25
        elif total_boxes <= 16:
            base_depth = 23
        elif total_boxes <= 25:
            base_depth = 21
        elif total_boxes <= 36:
            base_depth = 19
        else:
            base_depth = 17

    _tt.clear()

    forcing = get_forcing_moves(state)
    if forcing:
        legal_moves = forcing
    else:
        legal_moves = _order_moves(state, get_legal_moves(state))

    if not legal_moves:
        _search_deadline = None
        return None

    if len(legal_moves) == 1:
        _search_deadline = None
        return legal_moves[0]

    # Iterative Deepening với time limit
    max_depth = _get_adaptive_depth(state, base_depth)
    best_move = legal_moves[0]
    last_iter_time = 0

    for d in range(1, max_depth + 1):
        elapsed = time.perf_counter() - start_time
        estimated_next = max(last_iter_time * 5, 0.02)
        if d > 1 and (elapsed + estimated_next) > time_limit:
            break

        iter_start = time.perf_counter()
        _search_timed_out = False
        score, move = minimax(state, d, -math.inf, math.inf, ai_player)
        last_iter_time = time.perf_counter() - iter_start

        if _search_timed_out:
            break

        if move:
            best_move = move

        if abs(score) >= 9000:
            break

    _search_deadline = None
    return best_move
