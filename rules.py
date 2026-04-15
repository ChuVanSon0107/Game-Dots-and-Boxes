from models import Move, GameState

def create_move(edge_type: str, r: int, c: int):
    return Move(edge_type=edge_type, r=r, c=c)


def is_valid_move(state: GameState, move: Move):
    if move.edge_type not in ('H', 'V'):
        return False
    
    # cạnh ngang
    if move.edge_type == 'H':
        if not (0 <= move.r <= state.rows and 0 <= move.c < state.cols):
            return False
        return not state.h_edges[move.r][move.c]
    
    # cạnh dọc
    else:
        if not (0 <= move.r < state.rows and 0 <= move.c <= state.cols):
            return False
        return not state.v_edges[move.r][move.c]
    

def get_affected_boxes(move: Move, rows: int, cols: int):
    affected = []

    # cạnh ngang
    if move.edge_type == 'H':
        if move.r > 0:
            affected.append((move.r - 1, move.c))

        if move.r < rows:
            affected.append((move.r, move.c))
    
    # cạnh dọc
    else:
        if move.c > 0:
            affected.append((move.r, move.c - 1))
        
        if move.c < cols:
            affected.append((move.r, move.c))

    return affected


def is_box_closed(state: GameState, box_r: int, box_c: int):
    top = state.h_edges[box_r][box_c]
    bottom = state.h_edges[box_r + 1][box_c]
    left = state.v_edges[box_r][box_c]
    right = state.v_edges[box_r][box_c + 1]

    return top and bottom and left and right

def apply_move(state: GameState, move: Move):
    """
    Thực thi một nước đi lên trạng thái bàn cờ hiện tại.
    Trả về undo_info (dict) để có thể hoàn tác sau này.
    """
    # Khởi tạo gói thông tin phục vụ cho việc undo sau này
    undo_info = {
        'previous_player': state.current_player,
        'completed_boxes': [],
        'score_change_1': 0,
        'score_change_2': 0
    }

    # 1. Đánh dấu cạnh đã được vẽ
    if move.edge_type == 'H':
        state.h_edges[move.r][move.c] = True
    else:
        state.v_edges[move.r][move.c] = True

    state.moves_remaining -= 1
    boxes_closed_this_turn = 0

    # 2. Cập nhật các ô vuông bị ảnh hưởng
    affected = get_affected_boxes(move, state.rows, state.cols)
    for r, c in affected:
        state.edges_count[r][c] += 1
        
        # Nếu ô vuông đã đủ 4 cạnh
        if state.edges_count[r][c] == 4:
            state.boxes[r][c] = state.current_player
            undo_info['completed_boxes'].append((r, c))
            boxes_closed_this_turn += 1

    # 3. Cập nhật điểm và lượt chơi
    if boxes_closed_this_turn > 0:
        if state.current_player == 1:
            state.score_player1 += boxes_closed_this_turn
            undo_info['score_change_1'] = boxes_closed_this_turn
        else:
            state.score_player2 += boxes_closed_this_turn
            undo_info['score_change_2'] = boxes_closed_this_turn
        # Điểm mấu chốt: Ăn được ô thì KHÔNG đổi lượt (được đi tiếp)
    else:
        # Chuyển lượt: 1 -> 2, 2 -> 1
        state.current_player = 3 - state.current_player

    # 4. Lưu lại lịch sử nước đi
    state.last_move.append(move)

    return undo_info


def undo_move(state: GameState, move: Move, undo_info: dict):
    """
    Hoàn tác một nước đi dựa trên thông tin từ undo_info.
    """
    # 1. Xóa cạnh vừa vẽ
    if move.edge_type == 'H':
        state.h_edges[move.r][move.c] = False
    else:
        state.v_edges[move.r][move.c] = False

    state.moves_remaining += 1

    # 2. Phục hồi mảng đếm cạnh
    affected = get_affected_boxes(move, state.rows, state.cols)
    for r, c in affected:
        state.edges_count[r][c] -= 1

    # 3. Xóa quyền sở hữu của các ô vừa bị ăn
    for r, c in undo_info.get('completed_boxes', []):
        state.boxes[r][c] = 0

    # 4. Phục hồi điểm số
    state.score_player1 -= undo_info.get('score_change_1', 0)
    state.score_player2 -= undo_info.get('score_change_2', 0)

    # 5. Phục hồi lượt chơi cũ
    state.current_player = undo_info['previous_player']

    # 6. Lấy nước đi ra khỏi lịch sử
    if state.last_move:
        state.last_move.pop()

def is_terminal(state: GameState):
    if state.moves_remaining > 0:
        return False
    return True

def switch_player(state: GameState):
    if state.current_player == 1:
        state.current_player = 2
    else:
        state.current_player = 1

def get_winner(state: GameState):
    if state.score_player1 > state.score_player2:
        return 1
    elif state.score_player1 < state.score_player2:
        return 2
    return 0

