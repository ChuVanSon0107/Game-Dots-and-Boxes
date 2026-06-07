"""
Không cần minimax — AI dùng 6 bước rule theo thứ tự ưu tiên:
  1. take_safe3s   — ăn box 3 cạnh an toàn (không mở chain)
  2. sides3 check  — nếu còn box 3 cạnh → sac() (double-cross)
  3. sides01       — tìm nước an toàn (không tạo ô 3 cạnh)
  4. singleton     — sacrifice 1 ô để thoát chain
  5. doubleton     — sacrifice 2 ô để thoát chain
  6. make_any_move — đi bất kỳ cạnh hợp lệ (fallback)
"""

import random
import copy
from models import GameState, Move, create_initial_state
from rules import apply_move, get_affected_boxes, is_terminal, switch_player


# ═══════════════════════════════════════════════════════════
#  HELPERS — đọc / ghi cạnh không qua apply_move
#  (dùng nội bộ để AI tự di chuyển mà không ảnh hưởng history)
# ═══════════════════════════════════════════════════════════

def _edge_drawn(state: GameState, move: Move) -> bool:
    """Kiểm tra cạnh đã được vẽ chưa."""
    if move.edge_type == 'H':
        return bool(state.h_edges[move.r][move.c])
    return bool(state.v_edges[move.r][move.c])


def _box_edge_count(state: GameState, r: int, c: int) -> int:
    """Trả về số cạnh đã vẽ của ô (r, c) — dùng edges_count sẵn có."""
    return state.edges_count[r][c]


def _is_box_free(state: GameState, r: int, c: int) -> bool:
    """Ô (r,c) chưa bị ai ăn."""
    return state.boxes[r][c] == 0


# ═══════════════════════════════════════════════════════════
#  BƯỚC 0 — take_safe3s
#  Ăn ngay box 3 cạnh nếu cạnh còn thiếu KHÔNG kề ô có 2 cạnh
# ═══════════════════════════════════════════════════════════

def _missing_edge_of_box(state: GameState, r: int, c: int) -> Move | None:
    """Tìm cạnh còn thiếu của ô (r,c) — dùng khi edges_count == 3."""
    if not state.h_edges[r][c]:
        return Move('H', r, c)
    if not state.h_edges[r + 1][c]:
        return Move('H', r + 1, c)
    if not state.v_edges[r][c]:
        return Move('V', r, c)
    if not state.v_edges[r][c + 1]:
        return Move('V', r, c + 1)
    return None


def _neighbor_box_count(state: GameState, move: Move) -> int:
    """
    Với cạnh `move`, trả về edges_count của ô láng giềng nằm
    phía bên kia cạnh (ô không phải ô đang xét).
    Dùng để kiểm tra 'không kề ô 2 cạnh'.
    """
    # Hàm này trả về danh sách các ô bị ảnh hưởng bởi cạnh,
    # nhưng ta cần ô KHÁC với ô đang có 3 cạnh.
    affected = get_affected_boxes(move, state.rows, state.cols)
    return [state.edges_count[br][bc] for br, bc in affected]


def take_safe3s(state: GameState, ai_player: int):
    """
    Lặp liên tục ăn box 3 cạnh an toàn cho đến khi không còn nữa.
    'An toàn' nghĩa là: cạnh còn thiếu không kề một ô khác có 2 cạnh
    (tránh vô tình mở chain tiếp theo cho đối thủ).
    """
    rows, cols = state.rows, state.cols
    changed = True
    while changed:
        changed = False
        for r in range(rows):
            for c in range(cols):
                if state.boxes[r][c] != 0:
                    continue
                if state.edges_count[r][c] != 3:
                    continue

                move = _missing_edge_of_box(state, r, c)
                if move is None:
                    continue

                # Lấy danh sách ô bị ảnh hưởng bởi cạnh này
                affected = get_affected_boxes(move, rows, cols)
                # Ô láng giềng = ô trong affected mà KHÔNG phải (r,c)
                neighbor_counts = [
                    state.edges_count[br][bc]
                    for br, bc in affected
                    if (br, bc) != (r, c) and state.boxes[br][bc] == 0
                ]
                # Chỉ ăn nếu không có ô láng giềng nào đang có 2 cạnh
                if all(cnt != 2 for cnt in neighbor_counts):
                    # Đảm bảo đúng lượt trước khi apply
                    state.current_player = ai_player
                    apply_move(state, move)
                    changed = True


# ═══════════════════════════════════════════════════════════
#  BƯỚC 1 — sides3 / take_all3s / take_box
# ═══════════════════════════════════════════════════════════

def sides3(state: GameState):
    """Trả (True, r, c) nếu tồn tại ô chưa ăn có 3 cạnh, ngược lại (False, -1, -1)."""
    for r in range(state.rows):
        for c in range(state.cols):
            if state.boxes[r][c] == 0 and state.edges_count[r][c] == 3:
                return True, r, c
    return False, -1, -1


def take_box(state: GameState, r: int, c: int, ai_player: int):
    """Vẽ cạnh còn thiếu của ô (r,c) để hoàn thành nó."""
    move = _missing_edge_of_box(state, r, c)
    if move:
        state.current_player = ai_player
        apply_move(state, move)


def take_all3s(state: GameState, ai_player: int):
    """Ăn hết tất cả box 3 cạnh."""
    found, r, c = sides3(state)
    while found:
        take_box(state, r, c, ai_player)
        found, r, c = sides3(state)


# ═══════════════════════════════════════════════════════════
#  BƯỚC 2 — sides01: tìm nước an toàn
# ═══════════════════════════════════════════════════════════

def _is_safe_hedge(state: GameState, r: int, c: int) -> bool:
    """
    hedge[r][c] an toàn nếu chưa vẽ VÀ không tạo ô nào thành 3 cạnh.
    Tức là: mọi ô bị ảnh hưởng đều có < 2 cạnh hiện tại.
    """
    if state.h_edges[r][c]:
        return False
    # Ô phía trên (r-1, c)
    if r > 0 and state.boxes[r - 1][c] == 0 and state.edges_count[r - 1][c] >= 2:
        return False
    # Ô phía dưới (r, c)
    if r < state.rows and state.boxes[r][c] == 0 and state.edges_count[r][c] >= 2:
        return False
    return True


def _is_safe_vedge(state: GameState, r: int, c: int) -> bool:
    """vedge[r][c] an toàn tương tự."""
    if state.v_edges[r][c]:
        return False
    # Ô bên trái (r, c-1)
    if c > 0 and state.boxes[r][c - 1] == 0 and state.edges_count[r][c - 1] >= 2:
        return False
    # Ô bên phải (r, c)
    if c < state.cols and state.boxes[r][c] == 0 and state.edges_count[r][c] >= 2:
        return False
    return True


def sides01(state: GameState):
    """
    Tìm một cạnh an toàn, bắt đầu từ vị trí random để AI ít bị đoán.
    Trả (True, move) hoặc (False, None).
    """
    rows, cols = state.rows, state.cols

    # Tìm trong hedge, bắt đầu random
    si = random.randrange(rows + 1)
    sj = random.randrange(cols)
    i, j = si, sj
    while True:
        if _is_safe_hedge(state, i, j):
            return True, Move('H', i, j)
        j += 1
        if j == cols:
            j = 0
            i += 1
            if i > rows:
                i = 0
        if i == si and j == sj:
            break

    # Tìm trong vedge, bắt đầu random
    si = random.randrange(rows)
    sj = random.randrange(cols + 1)
    i, j = si, sj
    while True:
        if _is_safe_vedge(state, i, j):
            return True, Move('V', i, j)
        j += 1
        if j > cols:
            j = 0
            i += 1
            if i == rows:
                i = 0
        if i == si and j == sj:
            break

    return False, None


# ═══════════════════════════════════════════════════════════
#  BƯỚC 3 — singleton: sacrifice 1 ô
# ═══════════════════════════════════════════════════════════

def singleton(state: GameState):
    """
    Tìm cạnh sao cho chỉ sacrifice đúng 1 ô (ô 2 cạnh có ≥2 lối ra ngoài chain).
    Trả (True, move) hoặc (False, None).
    """
    rows, cols = state.rows, state.cols

    for r in range(rows):
        for c in range(cols):
            if state.boxes[r][c] != 0 or state.edges_count[r][c] != 2:
                continue

            numb = 0  # số lối thoát ra ngoài chain

            # Cạnh trên: hedge[r][c]
            if not state.h_edges[r][c]:
                if r == 0 or state.edges_count[r - 1][c] < 2 or state.boxes[r-1][c] != 0:
                    numb += 1

            # Cạnh trái: vedge[r][c]
            if not state.v_edges[r][c]:
                if c == 0 or state.edges_count[r][c - 1] < 2 or state.boxes[r][c-1] != 0:
                    numb += 1
                if numb > 1:
                    return True, Move('V', r, c)

            # Cạnh phải: vedge[r][c+1]
            if not state.v_edges[r][c + 1]:
                if c + 1 == cols or state.edges_count[r][c + 1] < 2 or state.boxes[r][c+1] != 0:
                    numb += 1
                if numb > 1:
                    return True, Move('V', r, c + 1)

            # Cạnh dưới: hedge[r+1][c]
            if not state.h_edges[r + 1][c]:
                if r + 1 == rows or state.edges_count[r + 1][c] < 2 or state.boxes[r+1][c] != 0:
                    numb += 1
                if numb > 1:
                    return True, Move('H', r + 1, c)

    return False, None


# ═══════════════════════════════════════════════════════════
#  BƯỚC 4 — doubleton: sacrifice 2 ô
# ═══════════════════════════════════════════════════════════

def _ldub(state: GameState, r: int, c: int) -> bool:
    """Box (r,c)=2 cạnh, vedge[r][c+1] chưa vẽ; cạnh còn lại dẫn ra ngoài?"""
    if not state.v_edges[r][c]:
        if c == 0 or state.edges_count[r][c - 1] < 2 or state.boxes[r][c-1] != 0:
            return True
    elif not state.h_edges[r][c]:
        if r == 0 or state.edges_count[r - 1][c] < 2 or state.boxes[r-1][c] != 0:
            return True
    elif r == state.rows - 1 or state.edges_count[r + 1][c] < 2 or state.boxes[r+1][c] != 0:
        return True
    return False


def _rdub(state: GameState, r: int, c: int) -> bool:
    if not state.v_edges[r][c + 1]:
        if c + 1 == state.cols or state.edges_count[r][c + 1] < 2 or state.boxes[r][c+1] != 0:
            return True
    elif not state.h_edges[r][c]:
        if r == 0 or state.edges_count[r - 1][c] < 2 or state.boxes[r-1][c] != 0:
            return True
    elif r + 1 == state.rows or state.edges_count[r + 1][c] < 2 or state.boxes[r+1][c] != 0:
        return True
    return False


def _udub(state: GameState, r: int, c: int) -> bool:
    if not state.h_edges[r][c]:
        if r == 0 or state.edges_count[r - 1][c] < 2 or state.boxes[r-1][c] != 0:
            return True
    elif not state.v_edges[r][c]:
        if c == 0 or state.edges_count[r][c - 1] < 2 or state.boxes[r][c-1] != 0:
            return True
    elif c == state.cols - 1 or state.edges_count[r][c + 1] < 2 or state.boxes[r][c+1] != 0:
        return True
    return False


def _ddub(state: GameState, r: int, c: int) -> bool:
    if not state.h_edges[r + 1][c]:
        if r + 1 == state.rows or state.edges_count[r + 1][c] < 2 or state.boxes[r+1][c] != 0:
            return True
    elif not state.v_edges[r][c]:
        if c == 0 or state.edges_count[r][c - 1] < 2 or state.boxes[r][c-1] != 0:
            return True
    elif c == state.cols - 1 or state.edges_count[r][c + 1] < 2 or state.boxes[r][c+1] != 0:
        return True
    return False


def doubleton(state: GameState):
    """
    Tìm cạnh sacrifice đúng 2 ô liền kề.
    Trả (True, move) hoặc (False, None).
    """
    rows, cols = state.rows, state.cols

    # Hai ô nằm ngang: (r,c) và (r,c+1) chia nhau vedge[r][c+1]
    for r in range(rows):
        for c in range(cols - 1):
            if (state.boxes[r][c] == 0 and state.edges_count[r][c] == 2 and
                    state.boxes[r][c + 1] == 0 and state.edges_count[r][c + 1] == 2 and
                    not state.v_edges[r][c + 1]):
                if _ldub(state, r, c) and _rdub(state, r, c + 1):
                    return True, Move('V', r, c + 1)

    # Hai ô nằm dọc: (r,c) và (r+1,c) chia nhau hedge[r+1][c]
    for c in range(cols):
        for r in range(rows - 1):
            if (state.boxes[r][c] == 0 and state.edges_count[r][c] == 2 and
                    state.boxes[r + 1][c] == 0 and state.edges_count[r + 1][c] == 2 and
                    not state.h_edges[r + 1][c]):
                if _udub(state, r, c) and _ddub(state, r + 1, c):
                    return True, Move('H', r + 1, c)

    return False, None


# ═══════════════════════════════════════════════════════════
#  BƯỚC đặc biệt — sac: Double-cross sacrifice
#  Khi còn box 3 cạnh nhưng không có nước an toàn
# ═══════════════════════════════════════════════════════════

class _ChainWalker:
    """
    Đếm độ dài chain và thực hiện đi theo chain,
    chừa lại 2 ô cuối cho đối thủ (double-cross).
    """

    def __init__(self, state: GameState, ai_player: int):
        self.state = state
        self.ai_player = ai_player
        self.count = 0
        self.loop = False

    # ----------------------------------------------------------
    # incount: đi vào chain, đếm số ô
    # k=0 lần đầu, k=1 skip trái, k=2 skip trên, k=3 skip phải, k=4 skip dưới
    # ----------------------------------------------------------
    def incount(self, k: int, r: int, c: int):
        s = self.state
        rows, cols = s.rows, s.cols
        self.count += 1

        # Trái: vedge[r][c] chưa vẽ → sang (r, c-1)
        if k != 1 and not s.v_edges[r][c]:
            if c > 0:
                nb = s.edges_count[r][c - 1]
                if s.boxes[r][c - 1] == 0:
                    if nb > 2:
                        self.count += 1
                        self.loop = True
                    elif nb > 1:
                        self.incount(3, r, c - 1)

        # Trên: hedge[r][c] chưa vẽ → sang (r-1, c)
        elif k != 2 and not s.h_edges[r][c]:
            if r > 0:
                nb = s.edges_count[r - 1][c]
                if s.boxes[r - 1][c] == 0:
                    if nb > 2:
                        self.count += 1
                        self.loop = True
                    elif nb > 1:
                        self.incount(4, r - 1, c)

        # Phải: vedge[r][c+1] chưa vẽ → sang (r, c+1)
        elif k != 3 and not s.v_edges[r][c + 1]:
            if c < cols - 1:
                nb = s.edges_count[r][c + 1]
                if s.boxes[r][c + 1] == 0:
                    if nb > 2:
                        self.count += 1
                        self.loop = True
                    elif nb > 1:
                        self.incount(1, r, c + 1)

        # Dưới: hedge[r+1][c] chưa vẽ → sang (r+1, c)
        elif k != 4 and not s.h_edges[r + 1][c]:
            if r < rows - 1:
                nb = s.edges_count[r + 1][c]
                if s.boxes[r + 1][c] == 0:
                    if nb > 2:
                        self.count += 1
                        self.loop = True
                    elif nb > 1:
                        self.incount(2, r + 1, c)

    # ----------------------------------------------------------
    # outcount: đi theo chain, ăn tất cả TRỪ 2 ô cuối
    # ----------------------------------------------------------
    def outcount(self, k: int, r: int, c: int):
        s = self.state
        rows, cols = s.rows, s.cols
        if self.count <= 0:
            return

        if k != 1 and not s.v_edges[r][c]:
            if self.count != 2:
                s.current_player = self.ai_player
                apply_move(s, Move('V', r, c))
            self.count -= 1
            self.outcount(3, r, c - 1)

        elif k != 2 and not s.h_edges[r][c]:
            if self.count != 2:
                s.current_player = self.ai_player
                apply_move(s, Move('H', r, c))
            self.count -= 1
            self.outcount(4, r - 1, c)

        elif k != 3 and not s.v_edges[r][c + 1]:
            if self.count != 2:
                s.current_player = self.ai_player
                apply_move(s, Move('V', r, c + 1))
            self.count -= 1
            self.outcount(1, r, c + 1)

        elif k != 4 and not s.h_edges[r + 1][c]:
            if self.count != 2:
                s.current_player = self.ai_player
                apply_move(s, Move('H', r + 1, c))
            self.count -= 1
            self.outcount(2, r + 1, c)


def _take_all_but(state: GameState, excl_r: int, excl_c: int, ai_player: int):
    """Ăn hết box 3 cạnh ngoại trừ ô (excl_r, excl_c)."""
    for r in range(state.rows):
        for c in range(state.cols):
            if (state.boxes[r][c] == 0 and state.edges_count[r][c] == 3
                    and (r != excl_r or c != excl_c)):
                take_box(state, r, c, ai_player)


def sac(state: GameState, u: int, v: int, ai_player: int):
    """
    Double-cross sacrifice từ box (u,v).
    - Đếm độ dài chain (incount).
    - Nếu open chain: ăn hết các box 3 cạnh khác trước.
    - Nếu chain đủ để kết thúc game → ăn hết luôn.
    - Ngược lại: ăn trừ 2 ô cuối rồi dừng (sacrifice cho đối thủ).
    - Nếu loop: sacrifice thêm 2 (tổng 4).
    """
    walker = _ChainWalker(state, ai_player)
    walker.incount(0, u, v)

    if not walker.loop:
        _take_all_but(state, u, v, ai_player)

    total_after = walker.count + state.score_player1 + state.score_player2
    if total_after == state.rows * state.cols:
        take_all3s(state, ai_player)
        return

    if walker.loop:
        walker.count -= 2  # Loop: chừa thêm 2 ô nữa

    walker.outcount(0, u, v)


# ═══════════════════════════════════════════════════════════
#  BƯỚC 6 — make_any_move: fallback
# ═══════════════════════════════════════════════════════════

def make_any_move(state: GameState, ai_player: int):
    """Đi cạnh hợp lệ đầu tiên tìm được — chỉ dùng khi hết mọi lựa chọn."""
    rows, cols = state.rows, state.cols
    for r in range(rows + 1):
        for c in range(cols):
            if not state.h_edges[r][c]:
                state.current_player = ai_player
                apply_move(state, Move('H', r, c))
                return
    for r in range(rows):
        for c in range(cols + 1):
            if not state.v_edges[r][c]:
                state.current_player = ai_player
                apply_move(state, Move('V', r, c))
                return


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT — make_move (tương đương makemove() trong JS)
# ═══════════════════════════════════════════════════════════

def make_move(state: GameState, ai_player: int = 2):
    """
    AI thực hiện một lượt đi hoàn chỉnh theo thứ tự ưu tiên:

      Bước 0: Ăn ngay các box 3 cạnh an toàn (take_safe3s)
      Bước 1: Nếu còn box 3 cạnh:
                - Có nước an toàn? → ăn hết 3s, rồi đi nước an toàn đó
                - Không?           → sac() (double-cross)
      Bước 2: Nếu không còn box 3 cạnh:
                - Có nước an toàn? → đi
                - Có singleton?    → sacrifice 1 ô
                - Có doubleton?    → sacrifice 2 ô
                - Còn lại          → make_any_move
    """
    # Bước 0: Ăn safe 3s trước
    take_safe3s(state, ai_player)

    if is_terminal(state):
        return

    found3, u, v = sides3(state)

    if found3:
        # Còn box 3 cạnh
        found_safe, safe_move = sides01(state)
        if found_safe:
            # Ăn hết 3s → rồi đi nước an toàn đã tìm
            take_all3s(state, ai_player)
            if not is_terminal(state):
                state.current_player = ai_player
                apply_move(state, safe_move)
        else:
            # Không có nước an toàn → double-cross sacrifice
            sac(state, u, v, ai_player)
    else:
        # Không còn box 3 cạnh
        found_safe, safe_move = sides01(state)
        if found_safe:
            state.current_player = ai_player
            apply_move(state, safe_move)
            return

        found_s, s_move = singleton(state)
        if found_s:
            state.current_player = ai_player
            apply_move(state, s_move)
            return

        found_d, d_move = doubleton(state)
        if found_d:
            state.current_player = ai_player
            apply_move(state, d_move)
            return

        make_any_move(state, ai_player)


# ─────────────────────────────────────────────────────────
#  get_legal_moves — trả về tất cả nước hợp lệ
#  Dùng làm fallback trong ui._ai_compute_worker khi AI lỗi
# ─────────────────────────────────────────────────────────
 
def get_legal_moves(state: GameState) -> list[Move]:
    """Trả về danh sách tất cả nước đi hợp lệ từ trạng thái hiện tại."""
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
 
 
# ─────────────────────────────────────────────────────────
#  get_best_move — hàm chính ui.py gọi
# ─────────────────────────────────────────────────────────
 
def get_best_move(state: GameState, ai_player: int = 2) -> Move | None:
    """
    Tính nước đi tốt nhất cho AI dựa trên chiến lược rule-based (js_ai).
 
    Quy trình:
      1. Deepcopy state để không ảnh hưởng state thật.
      2. Gọi js_ai.make_move() trên bản sao — hàm này có thể apply nhiều nước.
      3. Lấy nước ĐẦU TIÊN từ last_move (index = len_before).
      4. Trả về Move đó để ui.py apply lên state thật.
 
    Trả về None nếu không có nước hợp lệ (ván đã kết thúc).
    """
    # Không còn nước nào → kết thúc
    if state.moves_remaining <= 0:
        return None
 
    # Snapshot số nước đã đi trước khi gọi AI
    len_before = len(state.last_move)
 
    # Deepcopy để AI tính toán độc lập, không mutate state thật
    state_copy = copy.deepcopy(state)
 
    # Đảm bảo bản sao đang là lượt của AI
    state_copy.current_player = ai_player
 
    # Chạy AI rule-based trên bản sao
    make_move(state_copy, ai_player=ai_player)
 
    # Lấy nước đầu tiên AI đã thực hiện
    if len(state_copy.last_move) > len_before:
        first_move = state_copy.last_move[len_before]
        return Move(first_move.edge_type, first_move.r, first_move.c)
 
    # Fallback: AI không tìm được nước → lấy nước hợp lệ đầu tiên
    legal = get_legal_moves(state)
    return legal[0] if legal else None
 
