from models import GameState, Move
from rules import get_affected_boxes


def would_create_third_edge(state: GameState, move: Move):
    """
    Kiểm tra nước đi này có làm tạo ra box 3 cạnh cho đối thủ không (Trả về số cạnh 3 tạo ra). 
    """
    created = 0
    affected = get_affected_boxes(move, state.rows, state.cols)

    for br, bc in affected:
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 2:
            created += 1

    return created


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
    kiểm tra nước đi có ăn box ngay không (Trả về số box hoàn thành)
    """
    completed = 0
    affected = get_affected_boxes(move, state.rows, state.cols)

    for br, bc in affected:
        if state.boxes[br][bc] == 0 and state.edges_count[br][bc] == 3:
            completed += 1

    return  completed

def get_safe_moves(state: GameState):
    """
    Tìm nước đi an toàn: Lọc từ danh sách nước đi hợp lệ những nước KHÔNG tạo ra cạnh 3.
    """
    moves = []
    
    # Chỉ duyệt qua những nước đi chắc chắn hợp lệ (chưa bị vẽ)
    legal_moves = get_legal_moves(state)
    
    for move in legal_moves:
        # Nếu nước đi này không vô tình tạo ra ô 3 cạnh cho đối thủ ăn
        if would_create_third_edge(state, move) == 0:
            moves.append(move)

    return moves

