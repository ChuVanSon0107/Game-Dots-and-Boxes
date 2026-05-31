# Tài Liệu Luồng Chạy Logic Của AI Bot - Dots and Boxes

Tài liệu này mô tả chi tiết quá trình thực thi tuần tự (Execution Flow) của AI Bot mỗi khi đến lượt nó đi, từ lúc giao diện (UI) kích hoạt cho đến khi nước đi được thực hiện trên bàn cờ.

## 1. Khởi tạo và Gọi AI (UI Layer)

Khi trò chơi chuyển sang lượt của AI, quá trình được xử lý tại hàm `_handle_ai_turn()` trong tệp `ui.py`:

- **Kiểm tra trạng thái:** Xác nhận đúng lượt của AI và trò chơi chưa kết thúc (còn nét để vẽ).
- **Tránh đóng băng giao diện (Non-blocking UI):** Nếu tính toán trực tiếp trên luồng chính (Main Thread), giao diện sẽ bị "đơ". Do đó, một bản sao độc lập của trạng thái bàn cờ (`copy.deepcopy(self.GameState)`) được tạo ra.
- **Khởi chạy Background Thread:** Gọi luồng phụ `_ai_compute_worker` để tính toán ngầm. Giao diện lúc này sẽ chạy hiệu ứng chữ _"Bot is thinking..."_.

## 2. Tiền xử lý và Thiết lập (AI Entry Point)

Trên luồng phụ, hàm `ai.get_best_move()` được kích hoạt, bắt đầu chuỗi logic AI:

- **Xóa bộ nhớ đệm (Transposition Table):** Gọi `_tt.clear()` để làm trống bảng băm, tránh các tính toán sai lệch từ những lượt trước bị lẫn vào.
- **Xác định Nước đi Ép buộc (Forcing Moves):** Hàm `get_forcing_moves()` quét bàn cờ tìm các chuỗi có thể ăn ngay (Capturable) hoặc các nước hy sinh tạo bẫy (Double-Cross).
  - _Short-circuit:_ Nếu chỉ có duy nhất 1 nước đi ép buộc, AI trả về luôn nước đi này mà không cần tính toán sâu để tiết kiệm tối đa thời gian.
- **Xác định Độ sâu Thích ứng (Adaptive Depth):** Gọi `_get_adaptive_depth()` để đặt giới hạn `max_depth`. Bàn cờ càng ít nét vẽ (càng về cuối game), độ sâu tối đa càng được tăng lên (có thể lên tới 22) để AI nhìn thấy kết cục sớm nhất.

## 3. Vòng lặp Tìm kiếm (Iterative Deepening & Time Management)

AI không tìm thẳng tới `max_depth` mà sử dụng vòng lặp duyệt từ độ sâu $d = 1$ đến `max_depth`:

- Bắt đầu ghi nhận thời gian (Timer).
- Ở mỗi mức độ sâu $d$, AI gọi hàm lõi `minimax(...)` để tiến hành tìm kiếm.
- **Cắt thời gian (Time Cut-off):** Nếu dự đoán thời gian vòng lặp tiếp theo sẽ vượt quá giới hạn cho phép (mặc định 3.0 giây), AI sẽ bẻ gãy vòng lặp (`break`) và chấp nhận kết quả tốt nhất ở vòng lặp hiện tại.
- **Chiến thắng/Thua cuộc chắc chắn:** Nếu hàm `minimax` trả về điểm số cực kỳ lớn (ví dụ `abs(score) >= 9000`), tức là AI đã nhìn thấy đường thắng chắc (hoặc thua tuyệt đối), vòng lặp cũng dừng lại sớm.

## 4. Quá trình Duyệt cây (Minimax & Alpha-Beta)

Khi luồng chạy đi vào hàm đệ quy `minimax()`, quá trình diễn ra như sau:

1. **Kiểm tra kết thúc game:** Nếu hết nét để vẽ (`is_terminal`), trả về điểm chênh lệch thực tế nhân với hệ số rất lớn (10000).
2. **Kiểm tra Điều kiện Dừng Heuristic:** Nếu độ sâu $depth \le 0$ và không còn nước đi ép buộc nào, gọi hàm đánh giá `evaluate()`.
3. **Tra cứu Bộ nhớ Đệm (TT Lookup):** Mã hóa trạng thái bàn cờ thành một `key`. Nếu `key` này đã có trong bảng băm `_tt` với độ sâu $\ge depth$, tái sử dụng ngay kết quả tính toán trước đó để cắt tỉa (pruning).
4. **Sinh và Sắp xếp Nước đi (Move Ordering):** Gọi `_order_moves()` để sắp xếp thứ tự danh sách các nét vẽ:
   - _Ưu tiên 1:_ Nước đi tốt nhất từng được lưu trong `_tt` ở các độ sâu nông hơn.
   - _Ưu tiên 2:_ Nước đi "An toàn" (không vô tình tạo ô có 3 cạnh cho đối thủ ăn).
   - _Ưu tiên 3:_ Các nước đi rủi ro (Risky).
     _(Việc thử nước đi tốt trước giúp thuật toán Alpha-Beta cắt tỉa được nhiều nhánh vô ích nhất có thể)._
5. **Duyệt qua từng Nước đi:**
   - Thực hiện nước đi ảo lên bàn cờ (`apply_move`).
   - **Xử lý luật đặc biệt của Dots & Boxes:** Nếu nước đi ăn được ô, người chơi đó được đi tiếp. Nhờ vậy, **độ sâu ($depth$) không bị giảm**. Chỉ khi phải chuyển lượt cho đối thủ, $depth$ mới bị trừ đi 1.
   - Gọi đệ quy `minimax()` xuống tầng dưới.
   - Hoàn tác nước đi (`undo_move`) để trả lại trạng thái cũ cho nhánh duyệt tiếp theo.
   - Áp dụng logic của thuật toán Alpha-Beta Pruning: Cập nhật $alpha$ và $beta$. Nếu nhận thấy nhánh hiện tại chắc chắn tồi hơn một nhánh đã tìm thấy ($alpha \ge beta$), bẻ gãy vòng lặp ngay lập tức.
6. **Lưu Bộ nhớ Đệm:** Lưu giá trị tốt nhất và nét vẽ tương ứng vào `_tt` trước khi trả kết quả về tầng trên.

## 5. Chấm điểm Trạng thái (Hàm `evaluate`)

Khi quá trình duyệt chạm tới giới hạn độ sâu (node lá), hàm `evaluate()` đóng vai trò "chuyên gia" ước tính lợi thế của bàn cờ:

- **Tính điểm chênh lệch (Score Diff):** Lấy số điểm hiện tại của người chơi đang xét trừ đi đối thủ.
- **Đếm ô cơ hội:** Cộng một lượng điểm lớn cho những ô sắp ăn được (đã có 3 nét).
- **Phạt ô nguy hiểm:** Trừ điểm cho các ô đang có 2 nét, vì nếu vẽ thêm vào đây sẽ dâng tặng điểm cho đối thủ.
- **Phân tích lý thuyết Chuỗi (Nimstring Theory):**
  - Quét bàn cờ qua `_evaluate_chains()` để tìm các Open Chains và Closed Loops.
  - Sử dụng luật Parity (Chẵn/lẻ) để xác định xem bên nào nắm quyền kiểm soát chuỗi (Controller) và dự tính số điểm thực nhận sau các pha Double-Cross.
- **Trọng số linh hoạt:** Tùy thuộc vào số lượng không gian (ô trống) trên bàn cờ, AI sẽ tự động thay đổi trọng số. Khúc giữa game (Midgame), nó ưu tiên ăn điểm ngay lập tức. Về cuối game (Endgame), trọng số kiểm soát chuỗi được nhân lên gấp 15 lần, bắt buộc AI đánh theo chiến thuật hy sinh.

## 6. Trả về kết quả và Thực thi (Back to UI)

- Hàm `minimax` trả ngược nước đi tối ưu nhất qua từng độ sâu, và cuối cùng `get_best_move` thu được một đối tượng `Move`.
- Luồng phụ kết thúc, lưu đối tượng `Move` này vào biến `ai_move_pending`.
- Trên luồng chính (Main Thread), vòng lặp của game phát hiện `ai_move_pending` đã có giá trị.
- UI sẽ thực hiện một khoảng thời gian trễ nhân tạo (`ai_delay_ms` = 300ms) để người chơi kịp quan sát nhịp độ game, không bị giật mình.
- Cuối cùng, UI gọi `_apply_move_with_effects()`, tiến hành vẽ nét thật lên màn hình, cập nhật điểm, làm rung hình đại diện và phát âm thanh. Lượt chơi được chuyển về tay bạn hoặc AI tiếp tục chơi nếu vừa ăn được điểm.
