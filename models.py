def create_initial_state(rows, cols):
    """
    Khởi tạo trạng thái ban đầu cho game Dots and Boxes.
    Trả về một dictionary chứa toàn bộ thông tin bàn cờ.
    Dinhthuy 12/4/2026
    """
    total_edges = (rows+1)*cols + rows*(cols+1)

    #1. Khởi tạo mảng cạnh ngang h_edges
    # Kích thước (rows+1) hàng, cols cạnh
    h_edges = []
    for i in range(rows+1):
        row_edges=[]
        for j in range(cols):
            row_edges.append(False)
        h_edges.append(row_edges)

    #2. Khởi tạo mảng cạnh dọc v_edges
    # Kích thước rows hàng, cols+1 cạnh
    v_edges=[]
    for i in range(rows):
        row_edges = []
        for j in range(cols+1):
            row_edges.append(False)
        v_edges.append(row_edges)

    #3. Khởi tạo mảng các ô vuông boxes
    # Kích thước rows hàng, cols cột
    # 0 chưa ai ăn, 1 người chơi 1 ăn, 2 người chơi 2 ăn
    boxes = []
    for i in range(rows):
        row_boxes = []
        for j in range(cols):
            row_boxes.append(0)
        boxes.append(row_boxes)

    #4. Khởi tạo mảng đếm số cạnh mỗi ô edges_count
    #Kích thước rows hàng, cols cột, giá trị từ 0->4
    edges_count=[]
    for i in range(rows):
        row_counts=[]
        for j in range(cols):
            row_counts.append(0)
        edges_count.append(row_counts)

    state = {
        'rows': rows,
        'cols': cols,
        'h_edges': h_edges,
        'v_edges': v_edges,
        'boxes': boxes,
        'edges_count': edges_count,
        'current_player': 1, #mặc định người 1 đi trước
        'score_player1': 0,
        'score_player2': 0,
        'moves_remaining': total_edges,
        'last_move': []  #Stack lưu lịch sử nước đi
    }

    return state

# # --- Đoạn code test ---
# if __name__ == "__main__":
#     # Test thử tạo một bàn cờ kích thước 2 hàng, 2 cột
#     test_state = create_initial_state(2, 2)
    
#     print("--- KHỞI TẠO STATE THÀNH CÔNG ---")
#     print("Tổng số cạnh (moves_remaining):", test_state['moves_remaining'])
#     print("Mảng trạng thái các ô (boxes):", test_state['boxes'])
#     print("Lượt đi hiện tại:", test_state['current_player'])