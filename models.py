import copy

class GameState:
    def __init__(self, rows, cols, h_edges, v_edges, boxes, edges_count, current_player, score_player1, score_player2, moves_remaining, last_move=None):
        self.rows = rows
        self.cols = cols
        self.h_edges = h_edges
        self.v_edges = v_edges
        self.boxes = boxes
        self.edges_count = edges_count
        self.current_player = current_player
        self.score_player1 = score_player1
        self.score_player2 = score_player2
        self.moves_remaining = moves_remaining
        self.last_move = last_move if last_move is not None else []

    def print_game_status(self):
        """Hiển thị trạng thái game dựa trên các thuộc tính của GameState"""
        print("\n" + "=" * 35)
        print(f" ĐIỂM SỐ:  Player 1: {self.score_player1}  |  Player 2: {self.score_player2}")
        print(f" LƯỢT CHƠI: {self.current_player}")
        print(f" CÒN LẠI: {self.moves_remaining} nước đi")
        print("=" * 35 + "\n")

        # Duyệt qua từng hàng chấm
        for i in range(self.rows + 1):
            # 1. Vẽ dòng chấm và các cạnh ngang (h_edges)
            row_str = "●"
            for j in range(self.cols):
                # Kiểm tra xem tại vị trí (i, j) cạnh ngang có được đánh chưa
                # Giả định h_edges[i][j] lưu giá trị khác None/trống nếu đã đánh
                edge = "---" if self.h_edges[i][j] != ' ' else "   "
                row_str += edge + "●"
            print(row_str)

            # 2. Vẽ dòng cạnh dọc (v_edges) và chủ sở hữu ô (boxes)
            if i < self.rows:
                v_row_str = ""
                for j in range(self.cols + 1):
                    # Vẽ cạnh dọc
                    v_edge = "|" if self.v_edges[i][j] != ' ' else " "
                    v_row_str += v_edge

                    # Vẽ chủ sở hữu ô vuông (giữa 2 cạnh dọc)
                    if j < self.cols:
                        # self.boxes[i][j] sẽ là 'X', 'O' hoặc ' '
                        v_row_str += f" {self.boxes[i][j]} "
                print(v_row_str)

        if self.last_move:
            print(f"\nNước đi cuối: {self.last_move}")
        print("=" * 35)

    def clone_state(self):
        """Tạo một bản sao sâu (deep copy) của trạng thái hiện tại"""
        return GameState(
            rows=self.rows,
            cols=self.cols,
            # Sử dụng deepcopy để sao chép mảng 2 chiều, tránh việc sửa bản sao làm hỏng bản gốc
            h_edges=copy.deepcopy(self.h_edges),
            v_edges=copy.deepcopy(self.v_edges),
            boxes=copy.deepcopy(self.boxes),
            edges_count=self.edges_count,
            current_player=self.current_player,
            score_player1=self.score_player1,
            score_player2=self.score_player2,
            moves_remaining=self.moves_remaining,
            last_move=copy.deepcopy(self.last_move)
        )
class Move:
    def __init__(self, edge_type, r, c):
        self.edge_type = edge_type # 'H' or 'V'
        self.r = r
        self.c = c


def create_initial_state(rows: int, columns: int):
    """
    Khởi tạo trạng thái ban đầu cho game Dots and Boxes.
    Trả về một dictionary chứa toàn bộ thông tin bàn cờ.
    """
    total_edges = (rows+1)*columns + rows*(columns+1)

    #1. Khởi tạo mảng cạnh ngang h_edges
    # Kích thước (rows+1) hàng, cols cạnh
    h_edges = []
    for i in range(rows+1):
        row_edges=[]
        for j in range(columns):
            row_edges.append(False)
        h_edges.append(row_edges)

    #2. Khởi tạo mảng cạnh dọc v_edges
    # Kích thước rows hàng, cols+1 cạnh
    v_edges=[]
    for i in range(rows):
        row_edges = []
        for j in range(columns+1):
            row_edges.append(False)
        v_edges.append(row_edges)

    #3. Khởi tạo mảng các ô vuông boxes
    # Kích thước rows hàng, cols cột
    # 0 chưa ai ăn, 1 người chơi 1 ăn, 2 người chơi 2 ăn
    boxes = []
    for i in range(rows):
        row_boxes = []
        for j in range(columns):
            row_boxes.append(0)
        boxes.append(row_boxes)

    #4. Khởi tạo mảng đếm số cạnh mỗi ô edges_count
    #Kích thước rows hàng, cols cột, giá trị từ 0->4
    edges_count=[]
    for i in range(rows):
        row_counts=[]
        for j in range(columns):
            row_counts.append(0)
        edges_count.append(row_counts)

    return GameState(
        rows=rows,
        cols=columns,
        h_edges=h_edges,
        v_edges=v_edges,
        boxes=boxes,
        edges_count=edges_count,
        current_player=1,
        score_player1=0,
        score_player2=0,
        moves_remaining=total_edges,
        last_move=[]
    )




# # --- Đoạn code test ---

if __name__ == "__main__":
#     # Test thử tạo một bàn cờ kích thước 2 hàng, 2 cột
    test_state = create_initial_state(2, 2)

    print("--- KHỞI TẠO STATE THÀNH CÔNG ---")
    print("Tổng số cạnh (moves_remaining):", test_state.moves_remaining)
    print("Mảng trạng thái các ô (boxes):", test_state.boxes)
    print("Lượt đi hiện tại:", test_state.current_player)
    test_state.print_game_status()
    test_clone = test_state.clone_state()
