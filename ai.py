import math
from models import GameState, Move
from rules import get_affected_boxes, apply_move, undo_move, is_terminal


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
#  Heuristic evaluation function
# ============================================================

def evaluate(state: GameState, ai_player: int):
    """
    Hàm đánh giá trạng thái bàn cờ cho thuật toán Minimax.

    Chiến lược đánh giá:
    1. Hiệu số điểm hiện tại (quan trọng nhất)
    2. Số ô đang có 3 cạnh mà lượt hiện tại có thể ăn
    3. Phạt nếu tạo ra ô 3 cạnh cho đối thủ
    4. Chain analysis: đánh giá chuỗi ô liên tiếp có thể ăn
    """
    opponent = 3 - ai_player

    # --- 1. Hiệu số điểm trực tiếp (trọng số cao nhất) ---
    if ai_player == 1:
        score_diff = state.score_player1 - state.score_player2
    else:
        score_diff = state.score_player2 - state.score_player1

    # --- 2. Đếm số ô 3 cạnh (capturable) và ô 2 cạnh (risky) ---
    capturable_for_current = 0  # Ô 3 cạnh mà người đi hiện tại có thể ăn
    boxes_with_2_edges = 0      # Ô đang có 2 cạnh (nguy hiểm tiềm tàng)
    boxes_with_1_edge = 0       # Ô đang có 1 cạnh
    boxes_with_0_edges = 0      # Ô chưa có cạnh nào

    for r in range(state.rows):
        for c in range(state.cols):
            if state.boxes[r][c] == 0:  # Ô chưa bị ai ăn
                ec = state.edges_count[r][c]
                if ec == 3:
                    capturable_for_current += 1
                elif ec == 2:
                    boxes_with_2_edges += 1
                elif ec == 1:
                    boxes_with_1_edge += 1
                elif ec == 0:
                    boxes_with_0_edges += 1

    # Nếu lượt hiện tại là AI → ô 3 cạnh có lợi cho AI
    # Nếu lượt hiện tại là đối thủ → ô 3 cạnh có lợi cho đối thủ
    if state.current_player == ai_player:
        capturable_score = capturable_for_current * 5
    else:
        capturable_score = -capturable_for_current * 5

    # --- 3. Chain analysis (đánh giá chuỗi) ---
    chain_score = _evaluate_chains(state, ai_player)

    # --- 4. Tổng hợp ---
    total_boxes = state.rows * state.cols
    score = (
        score_diff * 100          # Hiệu số điểm là yếu tố chính
        + capturable_score * 10   # Ô 3 cạnh
        + chain_score * 8         # Phân tích chuỗi
        - boxes_with_2_edges * 2  # Ô 2 cạnh: tiềm ẩn nguy hiểm
    )

    return score


def _evaluate_chains(state: GameState, ai_player: int):
    """
    Phân tích chuỗi (chain) trong Dots and Boxes.
    
    Chain = chuỗi các ô liên tiếp có 2 cạnh mà khi ăn 1 ô sẽ
    tạo cơ hội ăn tiếp ô kế. Trong endgame, người nắm quyền
    kiểm soát chain cuối cùng thường thắng.
    
    Returns: điểm chain (dương = có lợi cho AI)
    """
    rows, cols = state.rows, state.cols
    visited = [[False] * cols for _ in range(rows)]
    chains = []  # list of chain lengths

    for r in range(rows):
        for c in range(cols):
            if state.boxes[r][c] == 0 and state.edges_count[r][c] >= 2 and not visited[r][c]:
                # BFS/DFS tìm chain
                chain_len = 0
                chain_has_3 = False
                stack = [(r, c)]

                while stack:
                    cr, cc = stack.pop()
                    if visited[cr][cc]:
                        continue
                    if state.boxes[cr][cc] != 0:
                        continue
                    ec = state.edges_count[cr][cc]
                    if ec < 2:
                        continue

                    visited[cr][cc] = True
                    chain_len += 1
                    if ec == 3:
                        chain_has_3 = True

                    # Tìm ô kề mà chia sẻ cạnh chưa được vẽ
                    neighbors = _get_open_neighbors(state, cr, cc)
                    for nr, nc in neighbors:
                        if not visited[nr][nc] and state.boxes[nr][nc] == 0 and state.edges_count[nr][nc] >= 2:
                            stack.append((nr, nc))

                if chain_len > 0:
                    chains.append((chain_len, chain_has_3))

    # Đánh giá: trong endgame, người chơi muốn số lượng chain dài là chẵn
    # (để đối thủ phải "mở" chain trước)
    score = 0
    long_chains = sum(1 for length, _ in chains if length >= 3)

    # Nếu AI đang đi và số chain dài là chẵn → AI có lợi thế
    # (đối thủ phải sacrifice chain trước)
    if state.current_player == ai_player:
        if long_chains % 2 == 0:
            score += long_chains * 3
        else:
            score -= long_chains * 3
    else:
        if long_chains % 2 == 1:
            score += long_chains * 3
        else:
            score -= long_chains * 3

    return score


def _get_open_neighbors(state: GameState, r: int, c: int):
    """
    Tìm các ô kề với ô (r, c) mà chia sẻ một cạnh CHƯA được vẽ.
    Hai ô kề nhau nếu chúng chia sẻ 1 cạnh chung chưa bị vẽ → 
    nếu vẽ cạnh đó sẽ tạo liên kết chain.
    """
    neighbors = []
    rows, cols = state.rows, state.cols

    # Trên: ô (r-1, c) – chia sẻ cạnh ngang h_edges[r][c]
    if r > 0 and not state.h_edges[r][c]:
        neighbors.append((r - 1, c))

    # Dưới: ô (r+1, c) – chia sẻ cạnh ngang h_edges[r+1][c]
    if r < rows - 1 and not state.h_edges[r + 1][c]:
        neighbors.append((r + 1, c))

    # Trái: ô (r, c-1) – chia sẻ cạnh dọc v_edges[r][c]
    if c > 0 and not state.v_edges[r][c]:
        neighbors.append((r, c - 1))

    # Phải: ô (r, c+1) – chia sẻ cạnh dọc v_edges[r][c+1]
    if c < cols - 1 and not state.v_edges[r][c + 1]:
        neighbors.append((r, c + 1))

    return neighbors


# ============================================================
#  Move ordering (sắp xếp nước đi để alpha-beta cắt tỉa tốt hơn)
# ============================================================

def _order_moves(state: GameState, moves: list):
    """
    Sắp xếp nước đi theo thứ tự ưu tiên để alpha-beta pruning
    cắt tỉa hiệu quả hơn.

    Thứ tự ưu tiên:
    1. Nước ăn box ngay (completing moves) → thử trước
    2. Nước an toàn (không tạo ô 3 cạnh) → thử sau
    3. Nước nguy hiểm (tạo ô 3 cạnh cho đối thủ) → thử cuối
    """
    completing = []      # Ăn box ngay
    safe = []            # An toàn
    risky = []           # Tạo ô 3 cạnh cho đối thủ

    for move in moves:
        boxes_completed = would_complete_box(state, move)
        third_edges = would_create_third_edge(state, move)

        if boxes_completed > 0:
            # Ưu tiên ăn nhiều box hơn
            completing.append((move, boxes_completed))
        elif third_edges == 0:
            safe.append(move)
        else:
            # Bớt ưu tiên nước tạo nhiều ô 3 cạnh
            risky.append((move, third_edges))

    # Sắp xếp completing giảm dần theo số box ăn được
    completing.sort(key=lambda x: x[1], reverse=True)
    # Sắp xếp risky tăng dần theo số ô 3 tạo ra (ít nguy hiểm hơn trước)
    risky.sort(key=lambda x: x[1])

    ordered = [m for m, _ in completing] + safe + [m for m, _ in risky]
    return ordered


# ============================================================
#  Minimax + Alpha-Beta Pruning
# ============================================================

def minimax(state: GameState, depth: int, alpha: float, beta: float,
            maximizing: bool, ai_player: int):
    """
    Thuật toán Minimax với Alpha-Beta Pruning.

    Tham số:
    - state: trạng thái bàn cờ hiện tại
    - depth: độ sâu tìm kiếm còn lại
    - alpha: giá trị alpha (best score cho maximizer đã tìm được)
    - beta: giá trị beta (best score cho minimizer đã tìm được)
    - maximizing: True nếu lượt hiện tại là MAX (AI muốn tối đa hóa)
    - ai_player: số hiệu người chơi AI (1 hoặc 2)

    Returns:
        (score, best_move)
    """
    # --- Base case: trạng thái kết thúc hoặc hết depth ---
    if is_terminal(state):
        # Game kết thúc → tính điểm cuối cùng
        if ai_player == 1:
            final_diff = state.score_player1 - state.score_player2
        else:
            final_diff = state.score_player2 - state.score_player1

        # Nhân trọng số lớn để ưu tiên thắng/thua rõ ràng
        return final_diff * 10000, None

    if depth == 0:
        return evaluate(state, ai_player), None

    # --- Sinh và sắp xếp nước đi ---
    legal_moves = get_legal_moves(state)
    if not legal_moves:
        return evaluate(state, ai_player), None

    ordered_moves = _order_moves(state, legal_moves)

    best_move = ordered_moves[0]

    if maximizing:
        max_eval = -math.inf

        for move in ordered_moves:
            # Thực hiện nước đi
            undo_info = apply_move(state, move)

            # Kiểm tra: nếu ăn được box → vẫn là lượt AI (maximizing)
            # Nếu không ăn box → lượt đối thủ (minimizing)
            boxes_captured = len(undo_info['completed_boxes'])

            if boxes_captured > 0:
                # AI ăn box → được đi tiếp (vẫn maximizing)
                # Không giảm depth vì đây là extra turn
                eval_score, _ = minimax(state, depth, alpha, beta,
                                        True, ai_player)
            else:
                # Chuyển lượt → đối thủ minimizing
                eval_score, _ = minimax(state, depth - 1, alpha, beta,
                                        False, ai_player)

            # Hoàn tác
            undo_move(state, move, undo_info)

            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move

            # Alpha-Beta Pruning
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Beta cut-off

        return max_eval, best_move

    else:
        min_eval = math.inf

        for move in ordered_moves:
            undo_info = apply_move(state, move)
            boxes_captured = len(undo_info['completed_boxes'])

            if boxes_captured > 0:
                # Đối thủ ăn box → được đi tiếp (vẫn minimizing)
                eval_score, _ = minimax(state, depth, alpha, beta,
                                        False, ai_player)
            else:
                # Chuyển lượt → AI maximizing
                eval_score, _ = minimax(state, depth - 1, alpha, beta,
                                        True, ai_player)

            undo_move(state, move, undo_info)

            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move

            # Alpha-Beta Pruning
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha cut-off

        return min_eval, best_move


# ============================================================
#  Adaptive depth (điều chỉnh độ sâu theo giai đoạn game)
# ============================================================

def _get_adaptive_depth(state: GameState, base_depth: int):
    """
    Tự động tăng depth khi game gần kết thúc (ít nước đi còn lại).
    Giúp AI chơi chính xác hơn trong endgame.
    """
    remaining = state.moves_remaining
    total_edges = (state.rows + 1) * state.cols + state.rows * (state.cols + 1)

    if remaining <= 8:
        # Endgame: tìm kiếm sâu tối đa
        return min(remaining, 20)
    elif remaining <= 14:
        return base_depth + 4
    elif remaining <= 20:
        return base_depth + 2
    elif remaining <= total_edges * 0.4:
        return base_depth + 1
    else:
        return base_depth


# ============================================================
#  Public API – Gọi từ main/ui
# ============================================================

def get_best_move(state: GameState, ai_player: int = 2, base_depth: int = 5):
    """
    Tìm nước đi tốt nhất cho AI bằng Minimax + Alpha-Beta Pruning.

    Tham số:
    - state: trạng thái bàn cờ hiện tại
    - ai_player: số hiệu người chơi AI (mặc định = 2)
    - base_depth: độ sâu tìm kiếm cơ bản (mặc định = 5)

    Returns:
        Move – nước đi tốt nhất tìm được
    """
    # 1. Greedy check: nếu có nước ăn box ngay → ăn ngay (không cần search)
    legal_moves = get_legal_moves(state)

    if not legal_moves:
        return None

    # Ăn box ngay nếu có thể (luôn là nước tốt trong Dots and Boxes)
    for move in legal_moves:
        if would_complete_box(state, move) > 0:
            return move

    # 2. Nếu chỉ còn 1 nước → đi luôn
    if len(legal_moves) == 1:
        return legal_moves[0]

    # 3. Minimax với adaptive depth
    depth = _get_adaptive_depth(state, base_depth)

    maximizing = (state.current_player == ai_player)
    score, best_move = minimax(state, depth, -math.inf, math.inf,
                               maximizing, ai_player)

    return best_move
