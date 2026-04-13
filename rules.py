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

