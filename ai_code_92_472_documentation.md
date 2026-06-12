# Giải thích code `ai.py` từ dòng 92 đến 472

Tài liệu này giải thích nhóm hàm trong `ai.py` từ dòng 92 đến dòng 472. Đây là phần logic trung gian nằm giữa các hàm kiểm tra luật cơ bản và hàm chọn nước đi chính của AI. Nhiệm vụ của đoạn code này là đánh giá nước đi an toàn, nước đi rủi ro, nước đi bắt buộc, phát hiện chuỗi có thể bị ăn liên tiếp và xử lý chiến thuật hy sinh 2/4 ô cuối theo kiểu hard-hearted handout.

Lưu ý: số dòng có thể thay đổi nếu file `ai.py` được chỉnh sửa thêm. Nội dung dưới đây được viết theo logic hiện tại của code.

---

## 1. Vai trò chung của đoạn code

Trong Dots and Boxes, AI không thể chỉ tham ăn ô trước mắt. Nếu ăn hết một chuỗi vào sai thời điểm, AI có thể làm mất quyền kiểm soát và bị đối thủ ép mở chuỗi lớn hơn ở cuối ván. Vì vậy, đoạn code từ dòng 92 đến 472 đóng vai trò như một lớp chiến thuật trước khi Minimax đi sâu:

1. Đánh giá nước đi an toàn và khả năng ép đối thủ hết nước an toàn.
2. Ước lượng thiệt hại nếu buộc phải mở chuỗi.
3. Sắp xếp nước đi để Alpha-Beta cắt tỉa hiệu quả hơn.
4. Mô phỏng các nước ăn ô bắt buộc.
5. Phát hiện các chuỗi có thể ăn liên tiếp.
6. Tìm nước hy sinh 2 hoặc 4 ô cuối để giữ quyền kiểm soát chuỗi.

Nói ngắn gọn, phần này giúp AI không chỉ tối đa hóa điểm hiện tại, mà còn tối ưu quyền kiểm soát ở endgame.

---

## 2. Nhóm hàm đánh giá áp lực và sắp xếp nước đi

### 2.1. `_best_forced_opener_loss(state)`

Hàm này ước lượng thiệt hại nhỏ nhất nếu người chơi hiện tại bị buộc phải mở chuỗi.

Cách xử lý:

1. Duyệt toàn bộ nước đi hợp lệ.
2. Chỉ xét các nước có thể tạo box 3 cạnh bằng điều kiện `would_create_third_edge(state, move) > 0`.
3. Với mỗi nước như vậy, gọi `_estimate_opened_chain_loss(state, move)` để ước lượng chuỗi mà đối thủ có thể bắt đầu ăn.
4. Lấy giá trị nhỏ nhất trong các thiệt hại tìm được.
5. Nếu không có nước nào mở chuỗi, trả về `0`.

Mục đích:

- Cho AI biết nếu một người chơi hết nước an toàn thì người đó sẽ phải mở chuỗi lớn hay nhỏ.
- Hỗ trợ chiến thuật ép đối thủ vào thế phải mở chuỗi.

---

### 2.2. `_safe_pressure_score(state, move)`

Hàm này chấm điểm một nước đi an toàn theo mức độ tạo áp lực lên đối thủ.

Cách xử lý:

1. Lưu người chơi hiện tại vào `mover`.
2. Thử đánh nước `move` bằng `apply_move`.
3. Đếm số nước an toàn còn lại của đối thủ bằng `_count_safe_moves(state)`.
4. Nếu đối thủ không còn nước an toàn và cũng không có forcing move, hàm tính thêm `forced_opener_loss`.
5. Tính lợi thế chuỗi sau nước đi bằng `_evaluate_chains(state, mover)`.
6. Hoàn tác nước đi bằng `undo_move`.
7. Trả về bộ giá trị gồm:
   - số nước an toàn còn lại của đối thủ;
   - thiệt hại bị ép mở chuỗi, được đảo dấu để phục vụ sắp xếp;
   - lợi thế chain, cũng được đảo dấu để ưu tiên cấu trúc có lợi.

Mục đích:

- Không chỉ chọn nước “không mất ô”, mà chọn nước an toàn có khả năng dồn đối thủ vào thế khó.
- Đây là phần quan trọng để AI chơi theo control/parity thay vì chỉ tham điểm.

---

### 2.3. `_candidate_limit(state)`

Hàm này giới hạn số nước ứng viên được đưa vào tìm kiếm.

Cách xử lý:

- Nếu bàn có tối đa 16 ô, giữ tối đa 32 nước.
- Nếu bàn có từ 17 đến 36 ô, giữ tối đa 24 nước.
- Nếu bàn lớn hơn, giữ tối đa 18 nước.

Mục đích:

- Giảm số nhánh mà Minimax phải xét.
- Giúp AI vẫn chạy được trên bàn lớn như 6x6, 7x7, 8x8 trong giới hạn thời gian.
- Đổi lại, AI phụ thuộc nhiều hơn vào chất lượng sắp xếp nước đi.

---

### 2.4. `_move_center_distance(state, move)`

Hàm này tính khoảng cách tương đối của một cạnh đến trung tâm bàn cờ.

Cách xử lý:

1. Nếu là cạnh ngang `H`, vị trí cạnh được xấp xỉ bằng `(move.r - 0.5, move.c + 0.5)`.
2. Nếu là cạnh dọc `V`, vị trí cạnh được xấp xỉ bằng `(move.r + 0.5, move.c - 0.5)`.
3. Tính khoảng cách Manhattan từ vị trí đó đến tâm bàn.

Mục đích:

- Là tiêu chí phụ khi sắp xếp nước đi.
- Nước gần trung tâm thường ảnh hưởng nhiều ô hơn, nên có giá trị chiến thuật tốt hơn ở đầu và giữa game.

---

### 2.5. `_safe_move_score(state, move)`

Hàm này tạo khóa sắp xếp cho các nước đi an toàn.

Cách xử lý:

1. Lấy các box bị ảnh hưởng bởi nước đi bằng `get_affected_boxes`.
2. Chỉ xét các box chưa bị chiếm.
3. Đếm số box đang có 1 cạnh, vì sau nước đi chúng sẽ thành box 2 cạnh.
4. Đếm số box đang có 0 cạnh.
5. Ghép kết quả từ `_safe_pressure_score` với các tiêu chí phụ:
   - số box 2 cạnh được tạo;
   - số box bị ảnh hưởng;
   - số box trống bị chạm vào;
   - khoảng cách đến trung tâm;
   - `_move_key(move)` để thứ tự ổn định.

Mục đích:

- Giúp `_order_moves` đưa nước an toàn tốt lên trước.
- Khi nước tốt được xét sớm, Alpha-Beta có thể cắt tỉa nhiều hơn.

---

### 2.6. `_estimate_opened_chain_loss(state, move)`

Hàm này ước lượng số ô có thể mất nếu đánh một nước mở chuỗi.

Cách xử lý:

1. Thử đánh `move`.
2. Gọi `_find_capturable_chains(state)` để tìm các chuỗi có thể ăn.
3. Lấy độ dài chuỗi lớn nhất làm thiệt hại ước lượng.
4. Hoàn tác nước đi.
5. Trả về giá trị `loss`.

Mục đích:

- Khi không còn nước an toàn, AI cần biết mở chuỗi nào ít thiệt hại nhất.
- Đây là thông tin chính cho việc sắp xếp các nước rủi ro.

---

### 2.7. `_post_move_chain_advantage(state, move)`

Hàm này đánh giá lợi thế chain sau khi thử đánh một nước.

Cách xử lý:

1. Lưu người chơi hiện tại vào `mover`.
2. Thử đánh `move`.
3. Gọi `_evaluate_chains(state, mover)`.
4. Hoàn tác nước đi.
5. Trả về điểm lợi thế.

Mục đích:

- Xem tác động dài hạn của nước đi lên cấu trúc chuỗi.
- Hỗ trợ so sánh các nước cùng rủi ro nhưng tạo thế endgame khác nhau.

---

### 2.8. `_risky_move_score(state, move)`

Hàm này tạo khóa sắp xếp cho các nước rủi ro, tức là các nước có thể tạo box 3 cạnh cho đối thủ.

Cách xử lý:

Hàm trả về một tuple gồm:

1. Thiệt hại mở chuỗi từ `_estimate_opened_chain_loss`.
2. Lợi thế chain sau nước đi từ `_post_move_chain_advantage`, được đảo dấu.
3. Số box 3 cạnh được tạo ra.
4. Khoảng cách đến trung tâm.
5. Khóa nước đi `_move_key(move)`.

Mục đích:

- Nếu buộc phải đi nước xấu, AI chọn nước xấu ít nhất.
- Hạn chế mở chuỗi dài hoặc tạo quá nhiều cơ hội ăn ô cho đối thủ.

---

### 2.9. `_dedupe_and_limit(moves, limit, preferred_key=None)`

Hàm này loại nước đi trùng lặp và giới hạn danh sách ứng viên.

Cách xử lý:

1. Duyệt danh sách `moves`.
2. Dùng `_move_key(move)` để phát hiện nước trùng.
3. Nếu một nước trùng với `preferred_key`, lưu lại để đưa lên đầu.
4. Thêm các nước không trùng vào danh sách `ordered`.
5. Nếu có nước ưu tiên, chèn nó vào vị trí đầu tiên.
6. Trả về tối đa `limit` nước.

Mục đích:

- Tránh để Minimax xét lại cùng một nước.
- Cho phép ưu tiên nước tốt đã biết từ Transposition Table hoặc vòng Iterative Deepening trước đó.

---

## 3. Nhóm hàm xử lý nước bắt buộc và forcing move

### 3.1. `_greedy_capture_moves(state)`

Hàm này lấy danh sách các nước có thể ăn ô ngay lập tức.

Cách xử lý:

1. Duyệt toàn bộ nước hợp lệ.
2. Giữ lại nước có `would_complete_box(state, move) > 0`.
3. Sắp xếp để nước ăn được nhiều ô hơn đứng trước.
4. Nếu số ô ăn được bằng nhau, dùng `_move_key(move)` để thứ tự ổn định.

Mục đích:

- Cung cấp danh sách capture move cho các hàm mô phỏng.
- Capture move ở đây là nước hoàn thành ít nhất một box ngay tại thời điểm đánh.

---

### 3.2. `_play_greedy_forced_captures(state)`

Hàm này mô phỏng việc liên tục ăn các ô đang có thể ăn ngay.

Cách xử lý:

1. Tạo `undo_stack` rỗng.
2. Lặp liên tục:
   - lấy capture move bằng `_greedy_capture_moves`;
   - nếu không còn capture thì dừng;
   - chọn nước capture đầu tiên;
   - đánh thử bằng `apply_move`;
   - lưu `(move, undo_info)` vào `undo_stack`.
3. Trả về `undo_stack`.

Mục đích:

- Xem nhanh trạng thái sau khi các nước ăn ô bắt buộc đã được giải quyết.
- Dùng trong việc so sánh giữa ăn hết chuỗi và hy sinh.

---

### 3.3. `_undo_forced_capture_stack(state, undo_stack)`

Hàm này hoàn tác toàn bộ các nước đã được `_play_greedy_forced_captures` đánh thử.

Cách xử lý:

1. Duyệt `undo_stack` theo thứ tự ngược.
2. Gọi `undo_move` cho từng nước.

Mục đích:

- Đảm bảo các mô phỏng không làm thay đổi `GameState` gốc.
- Đây là cơ chế bắt buộc vì các hàm đánh giá liên tục thử và hoàn tác nước đi.

---

### 3.4. `_terminal_score(state, ai_player)`

Hàm này chấm điểm rất lớn cho trạng thái kết thúc.

Cách xử lý:

- Nếu AI là player 1, trả về `(score_player1 - score_player2) * 10000`.
- Nếu AI là player 2, trả về `(score_player2 - score_player1) * 10000`.

Mục đích:

- Đảm bảo thắng/thua thật sự quan trọng hơn heuristic trung gian.
- Khi Minimax nhìn thấy trạng thái kết thúc, nó sẽ ưu tiên kết quả thắng rõ ràng.

---

### 3.5. `_control_after_forced_resolution(state, ai_player)`

Hàm này đánh giá quyền kiểm soát sau khi các capture bắt buộc đã được xử lý.

Cách xử lý:

1. Nếu game đã kết thúc, trả về `_terminal_score`.
2. Đếm số nước an toàn còn lại.
3. Nếu không còn nước an toàn:
   - tính `opener_loss`;
   - nếu đến lượt đối thủ, cộng điểm vì đối thủ bị ép mở chuỗi;
   - nếu đến lượt AI, trừ điểm vì AI bị ép mở chuỗi.
4. Nếu còn các vùng chain/loop:
   - gọi `_analyze_chains_and_loops(state)`;
   - tính số vùng bằng `len(open_chains) + len(closed_loops)`;
   - tính `control_bias = _evaluate_chains(state, ai_player) * 8`;
   - tính `turn_bias = 45 * region_count`;
   - nếu đến lượt AI, trừ `turn_bias`;
   - nếu đến lượt đối thủ, cộng `turn_bias`.

Mục đích:

- Đánh giá ai đang nắm quyền buộc người còn lại mở chuỗi.
- Đây là phần giúp AI hiểu rằng hy sinh một ít ô có thể đáng giá nếu sau đó đối thủ phải mở chuỗi lớn.

---

### 3.6. `_resolved_forcing_score(state, move, ai_player)`

Hàm này chấm điểm cục bộ cho một forcing move, đặc biệt ở tình huống cần so sánh giữa ăn tiếp và hy sinh.

Cách xử lý:

1. Kiểm tra `move` có phải sacrifice move không bằng `_is_sacrifice_move`.
2. Thử đánh `move`.
3. Gọi `_play_greedy_forced_captures` để mô phỏng việc ăn các ô bắt buộc ngay sau đó.
4. Tính điểm bằng `evaluate(state, ai_player) + _control_after_forced_resolution(state, ai_player)`.
5. Nếu `move` là sacrifice và game chưa kết thúc:
   - cộng `120` nếu sau đó đến lượt đối thủ;
   - trừ `120` nếu sau đó đến lượt AI.
6. Hoàn tác toàn bộ các capture đã mô phỏng.
7. Hoàn tác nước `move`.
8. Trả về điểm.

Mục đích:

- Đây là điểm trung tâm của logic hy sinh trong đoạn code này.
- Hàm giúp AI không mặc định ăn hết chuỗi, mà đánh giá xem hard-hearted handout có giữ được control tốt hơn không.

---

### 3.7. `_order_forcing_moves(state, moves, ai_player)`

Hàm này sắp xếp các forcing move theo điểm đã mô phỏng.

Cách xử lý:

1. Xác định node hiện tại là lượt AI hay lượt đối thủ bằng `state.current_player == ai_player`.
2. Tính `_resolved_forcing_score` cho từng nước.
3. Sắp xếp theo:
   - điểm resolved score;
   - số ô ăn được ngay;
   - `_move_key`.
4. Nếu là lượt AI, nước có điểm cao được xét trước.
5. Nếu là lượt đối thủ, thứ tự được đảo theo logic Minimax.

Mục đích:

- Đưa nước forcing quan trọng lên đầu.
- Giúp Alpha-Beta nhanh chóng gặp nhánh tốt/xấu rõ ràng và cắt tỉa hiệu quả hơn.

---

## 4. Nhóm hàm phát hiện chain và cạnh liên quan

### 4.1. `_find_capturable_chains(state)`

Hàm này tìm các chuỗi box có thể bị ăn liên tiếp.

Cách xử lý:

1. Duyệt toàn bộ box trên bàn.
2. Bỏ qua box đã visited hoặc đã bị chiếm.
3. Chỉ bắt đầu chain từ box có đúng 3 cạnh.
4. Từ box 3 cạnh đó, đi sang box kề bên nếu:
   - hai box chia sẻ một cạnh chưa vẽ;
   - box kề bên chưa bị chiếm;
   - box kề bên có từ 2 cạnh trở lên.
5. Lặp đến khi không tìm được box tiếp theo.
6. Thêm chain tìm được vào danh sách kết quả.

Mục đích:

- Mô phỏng thứ tự ăn chuỗi: ăn box đầu có 3 cạnh, rồi các box kế tiếp dần trở thành có thể ăn.
- Cung cấp dữ liệu cho các hàm ước lượng thiệt hại, forcing score và sacrifice.

---

### 4.2. `_get_box_neighbors_with_edge(state, r, c)`

Hàm này trả về các box kề cạnh với box `(r, c)` kèm trạng thái cạnh chung.

Cách xử lý:

- Nếu có box phía trên, trả về cạnh chung `h_edges[r][c]`.
- Nếu có box phía dưới, trả về cạnh chung `h_edges[r + 1][c]`.
- Nếu có box bên trái, trả về cạnh chung `v_edges[r][c]`.
- Nếu có box bên phải, trả về cạnh chung `v_edges[r][c + 1]`.

Mục đích:

- Giúp `_find_capturable_chains` biết box nào nối tiếp trong chuỗi.
- Biến `shared_edge_drawn` cho biết cạnh chung đã được vẽ hay chưa.

---

### 4.3. `_get_missing_edge(state, box_r, box_c)`

Hàm này tìm cạnh còn thiếu của một box.

Cách xử lý:

1. Kiểm tra cạnh trên.
2. Kiểm tra cạnh dưới.
3. Kiểm tra cạnh trái.
4. Kiểm tra cạnh phải.
5. Trả về `Move` đầu tiên tương ứng với cạnh chưa được vẽ.
6. Nếu không có cạnh thiếu, trả về `None`.

Mục đích:

- Xác định nước nào sẽ hoàn thành box 3 cạnh.
- Hỗ trợ các logic ăn ô và phân tích chain.

---

### 4.4. `_get_shared_edge(state, r1, c1, r2, c2)`

Hàm này tìm cạnh chung chưa vẽ giữa hai box kề nhau.

Cách xử lý:

- Nếu hai box cùng hàng, cạnh chung là cạnh dọc `V`.
- Nếu hai box cùng cột, cạnh chung là cạnh ngang `H`.
- Chỉ trả về `Move` nếu cạnh chung chưa được vẽ.
- Nếu cạnh chung đã vẽ hoặc hai box không hợp lệ, trả về `None`.

Mục đích:

- Xác định cạnh nối giữa hai box trong một chain/component.
- Hỗ trợ các logic cần phân biệt cạnh chung và cạnh ngoài chuỗi.

---

### 4.5. `_get_exit_edge(state, r, c, shared_edge)`

Hàm này tìm một cạnh còn thiếu của box `(r, c)` nhưng không phải cạnh chung đã truyền vào.

Cách xử lý:

1. Liệt kê toàn bộ cạnh chưa vẽ của box.
2. Bỏ qua cạnh trùng với `shared_edge`.
3. Trả về cạnh còn thiếu khác đầu tiên.
4. Nếu không có, trả về `None`.

Mục đích:

- Phân biệt cạnh nối trong chuỗi và cạnh thoát ra ngoài chuỗi.
- Hỗ trợ các xử lý liên quan đến cấu trúc chain/component.

---

## 5. Nhóm hàm sacrifice / hard-hearted handout

### 5.1. `_component_touched_by_move(state, move, component)`

Hàm này kiểm tra một nước đi có chạm vào component/chain đang xét hay không.

Cách xử lý:

1. Chuyển `component` thành set.
2. Lấy các box bị ảnh hưởng bởi `move`.
3. Nếu có ít nhất một box thuộc component, trả về `True`.
4. Ngược lại trả về `False`.

Mục đích:

- Khi tìm sacrifice move, chỉ xét các nước liên quan trực tiếp đến chain đang phân tích.
- Tránh chọn nhầm một nước ở vùng khác của bàn cờ.

---

### 5.2. `_capturable_boxes_after_move(state, move, component)`

Hàm này xem sau khi thử đánh một nước, trong component đang xét có bao nhiêu box trở thành có thể ăn.

Cách xử lý:

1. Thử đánh `move`.
2. Gọi `_find_capturable_chains(state)`.
3. Duyệt các box trong các chain tìm được.
4. Nếu box thuộc component đang xét, thêm vào tập `capturable`.
5. Hoàn tác nước đi.
6. Trả về tập `capturable`.

Mục đích:

- Kiểm tra một nước sacrifice có để lại đúng số ô cần hy sinh hay không.
- Đây là bước xác nhận thực tế sau mô phỏng, thay vì chỉ đoán theo hình dạng.

---

### 5.3. `_handout_size_for_component(state, component)`

Hàm này quyết định nên hy sinh 2 hay 4 ô trong component đang xét.

Cách xử lý:

1. Đếm số box trong component đang có đúng 3 cạnh.
2. Nếu có từ 2 box 3 cạnh trở lên, trả về `4`.
3. Nếu không, trả về `2`.

Mục đích:

- Áp dụng nguyên tắc hard-hearted handout:
  - open chain thường để lại 2 ô cuối;
  - loop/closed structure thường để lại 4 ô cuối.
- Đây chính là logic sacrifice 2/4 ô cuối trong code hiện tại.

---

### 5.4. `_get_sacrifice_moves(state, chain)`

Hàm này tìm các nước có thể hy sinh đúng cách trong một chain/component.

Cách xử lý:

1. Lấy độ dài chain là `n`.
2. Nếu chain có ít hơn 2 ô, không xét hy sinh.
3. Tính `handout_size` bằng `_handout_size_for_component`.
4. Nếu chain ngắn hơn `handout_size`, không xét hy sinh.
5. Duyệt toàn bộ nước hợp lệ.
6. Bỏ qua nước ăn ô ngay lập tức vì sacrifice ở đây là nước không ghi điểm ngay.
7. Bỏ qua nước không chạm vào component.
8. Thử nước đi đó và đếm số box trong component có thể bị ăn sau nước đi.
9. Nếu số box có thể bị ăn đúng bằng `handout_size`, thêm nước đó vào danh sách ứng viên.
10. Sắp xếp ứng viên theo:
    - số box capturable tạo ra;
    - số box 3 cạnh được tạo;
    - `_move_key`.
11. Trả về danh sách sacrifice move.

Mục đích:

- Tìm nước không ăn điểm ngay nhưng để lại đúng 2 hoặc 4 ô cho đối thủ.
- Nếu đúng thời điểm, đối thủ phải ăn các ô nhỏ đó rồi bị buộc mở chuỗi lớn hơn cho AI.
- Đây là cơ chế giúp AI tránh ăn hết chuỗi và đánh mất quyền kiểm soát.

---

### 5.5. `_is_sacrifice_move(state, move)`

Hàm này kiểm tra một nước cụ thể có phải sacrifice move hay không.

Cách xử lý:

1. Nếu nước đó ăn ô ngay lập tức, trả về `False`.
2. Tìm các chain có thể ăn bằng `_find_capturable_chains`.
3. Với mỗi chain, lấy danh sách sacrifice candidate bằng `_get_sacrifice_moves`.
4. So sánh `_move_key(move)` với từng candidate.
5. Nếu trùng, trả về `True`.
6. Nếu không trùng candidate nào, trả về `False`.

Mục đích:

- Gắn nhãn cho nước hy sinh để `_resolved_forcing_score` cộng/trừ điểm control phù hợp.
- Giúp AI nhận ra nước hy sinh ngay cả khi nước đó không ghi điểm tại thời điểm đánh.

---

## 6. Capture move khác forcing move như thế nào?

Trong đoạn code này:

- Capture move là nước hoàn thành ít nhất một box ngay lập tức, kiểm tra bằng `would_complete_box(state, move) > 0`.
- Forcing move là nhóm nước có tác động chiến thuật bắt buộc. Nó có thể là capture move, nhưng cũng có thể là sacrifice move. Forcing move được đánh giá theo việc sau nước đó ai bị ép ăn, ai bị ép mở chuỗi và ai giữ quyền kiểm soát.

Vì vậy, capture move là một trường hợp cụ thể, còn forcing move là khái niệm rộng hơn.

---

## 7. Vì sao các hàm dùng `apply_move` và `undo_move` liên tục?

Nhiều hàm trong đoạn 92-472 không đánh thật, mà chỉ thử đánh để xem trạng thái sau đó như thế nào. Mẫu xử lý chung là:

```python
undo_info = apply_move(state, move)
# phân tích trạng thái sau nước đi
undo_move(state, move, undo_info)
```

Lý do:

- Minimax cần thử rất nhiều nhánh nên việc copy bàn cờ quá nhiều sẽ tốn thời gian.
- `apply_move` cập nhật trạng thái nhanh.
- `undo_move` đưa bàn cờ quay lại chính xác trạng thái cũ.
- Nếu thiếu bước hoàn tác, các hàm đánh giá sau đó sẽ đọc sai trạng thái.

---

## 8. Luồng xử lý chính của phần 92-472

```text
Danh sách nước hợp lệ
        |
        v
Phân loại và đánh giá nước đi
        |
        +--> Nước an toàn
        |       dùng _safe_move_score
        |       ưu tiên ép đối thủ hết safe move
        |
        +--> Nước rủi ro
        |       dùng _risky_move_score
        |       chọn nước mở chuỗi ít thiệt hại
        |
        +--> Nước forcing
                dùng _resolved_forcing_score
                so sánh ăn tham và sacrifice
                xét control sau khi resolve capture

Các nước đã sắp xếp được đưa vào Minimax + Alpha-Beta.
```

---

## 9. Tóm tắt cho thuyết trình

Đoạn code từ dòng 92 đến 472 là lớp chiến thuật quan trọng của AI. Nó giúp AI đánh giá nước đi an toàn, nước đi rủi ro, nước ăn ô bắt buộc và nước hy sinh. Điểm đáng chú ý nhất là logic hard-hearted handout: AI phát hiện chain/component có thể bị ăn, xác định nên để lại 2 hay 4 ô, sau đó thử các nước không ghi điểm ngay để xem có tạo đúng số ô hy sinh hay không. Nhờ vậy, AI không chỉ tham ăn điểm trước mắt mà còn cố gắng giữ quyền kiểm soát chuỗi ở cuối ván.
