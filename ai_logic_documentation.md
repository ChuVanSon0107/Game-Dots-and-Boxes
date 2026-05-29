# Tài Liệu Mô Tả Logic AI Bot - Dots and Boxes

## 1. Tổng quan (Overview)

AI Bot cho trò chơi Dots and Boxes được xây dựng dựa trên thuật toán tìm kiếm gốc **Minimax** kết hợp với kỹ thuật cắt tỉa **Alpha-Beta (Alpha-Beta Pruning)**.

Bên cạnh thuật toán tìm kiếm cơ bản, trò chơi Dots and Boxes (đặc biệt là giai đoạn cuối game) đòi hỏi tư duy chiến thuật cao. Do đó, Bot được tích hợp các lý thuyết chuyên sâu của trò chơi như **Nimstring Theory**, phân tích chẵn/lẻ (**Parity**), chiến thuật **Double-Cross**, cùng các kỹ thuật tối ưu hóa hiệu suất như **Transposition Table** và **Iterative Deepening**.

## 2. Thuật toán cốt lõi (Core Algorithm)

### 2.1. Minimax & Alpha-Beta Pruning (`minimax`)

Thuật toán duyệt cây trò chơi, giả định rằng cả Bot và đối thủ đều chơi những nước đi tối ưu nhất:

- **Max Node:** Lượt của Bot, cố gắng chọn nước đi mang lại điểm đánh giá cao nhất.
- **Min Node:** Lượt của Người, Bot giả định người chơi sẽ chọn nước đi làm điểm số của Bot thấp nhất.
- **Cắt tỉa Alpha-Beta:** Bỏ qua việc duyệt các nhánh nước đi chắc chắn mang lại kết quả tồi tệ hơn những nước đi đã tìm thấy trước đó. Điều này giúp AI tiết kiệm tài nguyên và tìm kiếm sâu hơn.

### 2.2. Iterative Deepening & Time Management (`get_best_move`)

AI không tìm kiếm thẳng đến một độ sâu cố định. Nó sử dụng vòng lặp duyệt từ độ sâu 1, 2, 3... cho đến độ sâu tối đa, nhưng sẽ dừng lại nếu vượt quá giới hạn thời gian (`time_limit`).

- **Lợi ích:** Đảm bảo Bot luôn có sẵn một nước đi tốt nhất trong thời gian quy định, tránh tình trạng "đơ" game do tính toán quá lâu.

### 2.3. Tự động điều chỉnh độ sâu (Adaptive Depth) (`_get_adaptive_depth`)

Khi trò chơi đi về cuối (càng ít cạnh chưa vẽ), không gian trạng thái nhỏ dần. Hàm này tự động tăng mạnh độ sâu tìm kiếm, giúp Bot tính toán chính xác tuyệt đối các nước đi cuối cùng.

## 3. Các chiến thuật chuyên sâu (Advanced Strategies)

Một bot Dots and Boxes giỏi không chỉ biết "ăn ô khi có thể", mà phải biết giăng bẫy và ép đối thủ.

### 3.1. Phân tích chuỗi và vòng khép kín (`_analyze_chains_and_loops`)

Bàn cờ được phân tích thành các khu vực:

- **Open Chain (Chuỗi mở):** Một hàng các ô liên tiếp mà nếu đối thủ buộc phải đi vào, họ sẽ cho ta ăn một loạt ô.
- **Closed Loop (Vòng kín):** Một vòng các ô liên tiếp.

### 3.2. Nước đi ép buộc (Forcing Moves) & Double-Cross (`get_forcing_moves`)

Khi Bot có cơ hội ăn một chuỗi dài (ví dụ: 6 ô), thay vì ăn hết cả 6 ô và phải đánh nước tiếp theo mở đường cho đối thủ ăn chuỗi khác, Bot sử dụng chiến thuật **Double-Cross**:

- Nó sẽ ăn 4 ô đầu.
- Sau đó cố tình hy sinh (sacrifice) 2 ô cuối bằng cách vẽ một cạnh chia cắt chúng.
- Đối thủ bị "ép" phải ăn 2 ô này, và do luật chơi, đối thủ phải đi tiếp nước kế tiếp, vô tình mở ra một chuỗi khác cho Bot ăn.

### 3.3. Định lý Nimstring & Quy tắc chẵn lẻ (`_evaluate_chains`)

Giai đoạn Endgame được quyết định bởi ai là người kiểm soát các chuỗi.

- Bot đếm số lượng các chuỗi trên bàn cờ.
- Nếu số lượng chuỗi là **số chẵn** (Parity), người nào đang giữ lượt sẽ có khả năng "Control" bàn cờ, ép đối thủ phải liên tục cho mình ăn các chuỗi lớn. Thuật toán tính toán chính xác điểm số thu được và mất đi khi thực hiện các pha hy sinh (sacrifice) giữa các chuỗi này.

## 4. Hàm Đánh giá Heuristic (`evaluate`)

Khi chưa thể duyệt tới cuối game, Bot sẽ dùng hàm Heuristic để chấm điểm trạng thái bàn cờ hiện tại. Điểm tổng hợp được tính dựa trên các trọng số:

1.  **Chênh lệch điểm thực tế:** Điểm của Bot trừ đi điểm của Người (Trọng số lớn: `x100`).
2.  **Cơ hội ăn ô (Capturable):** Số lượng ô đang có đúng 3 cạnh (chuẩn bị ăn được).
3.  **Kiểm soát chuỗi (Chain Control):** Dựa trên `_evaluate_chains`. Đặc biệt, **trọng số này tự động thay đổi (Adaptive Weights)**:
    - Giữa game: Quan tâm đến việc ăn ô thực tế hơn.
    - Cuối game: Trọng số kiểm soát chuỗi cực lớn (`x15`), ép Bot chuyển đổi sang lối chơi chiến thuật "hy sinh ô nhỏ, đoạt chuỗi to".
4.  **Hạn chế ô nguy hiểm (2 cạnh):** Trừ điểm heuristic (`- boxes_2 * 3`) đối với mỗi ô có 2 cạnh trên bàn cờ. Điều này giúp Bot tự động ưu tiên các "nước đi an toàn", tránh việc làm cạn kiệt không gian an toàn quá sớm và hạn chế rủi ro rơi vào thế bị động (Zugzwang) - buộc phải biếu không điểm cho đối thủ.

## 5. Tối ưu hóa hiệu năng (Performance Optimizations)

### 5.1. Bảng băm trạng thái (Transposition Table - TT)

- **Vấn đề:** Trong game, cùng một trạng thái bàn cờ có thể đạt được bằng nhiều trình tự đi nét khác nhau.
- **Giải pháp:** Bot sử dụng `_tt` (dictionary) để lưu trữ kết quả của các trạng thái đã đánh giá. Hàm `_state_key` băm trạng thái hiện tại thành một tuple. Nếu trạng thái này đã từng được tính toán với độ sâu tương đương hoặc sâu hơn, Bot sẽ tái sử dụng kết quả ngay lập tức, tiết kiệm tài nguyên khổng lồ.

### 5.2. Sắp xếp thứ tự nước đi (Move Ordering) (`_order_moves`)

Thuật toán Alpha-Beta hiệu quả nhất khi nó duyệt các nước đi "tốt" trước. Bot phân loại nước đi như sau:

1.  Nước đi tốt nhất được lưu trong Transposition Table từ các vòng lặp trước (Iterative Deepening).
2.  Nước đi "An toàn" (Safe moves): Không biến ô nào thành 3 cạnh.
3.  Nước đi "Rủi ro" (Risky moves): Sắp xếp theo mức độ ít tạo ra lợi thế cho đối thủ nhất.
