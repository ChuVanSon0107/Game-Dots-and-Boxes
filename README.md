# Game Dots and Boxes với AI

Đây là project xây dựng game **Dots and Boxes** bằng Python/Pygame, có giao diện trực quan và bot AI chơi đối kháng với người dùng. AI được thiết kế để chơi trên nhiều kích thước bàn cờ, đặc biệt tập trung vào các chiến thuật quan trọng của Dots and Boxes như safe move, chain control, parity và sacrifice/hard-hearted handout ở cuối ván.

## 1. Giới thiệu trò chơi

Dots and Boxes là trò chơi hai người trên một lưới các điểm. Mỗi lượt, người chơi vẽ một cạnh nối hai điểm liền kề. Nếu một người vẽ cạnh thứ tư để hoàn thành một ô vuông, người đó nhận điểm và được đi tiếp. Trò chơi kết thúc khi toàn bộ ô đã được chiếm; người có nhiều ô hơn là người thắng.

Luật chơi đơn giản nhưng chiến thuật khá sâu. Ở cuối ván, người chơi không chỉ cần ăn điểm ngay mà còn phải kiểm soát các chuỗi ô để ép đối thủ mở chuỗi bất lợi.

## 2. Tính năng chính

- Chơi Dots and Boxes với giao diện Pygame.
- Hỗ trợ chế độ người chơi đấu với AI.
- Bàn cờ có thể thay đổi kích thước trong code, mặc định hiện tại là `7x7`.
- Có hiệu ứng giao diện, âm thanh và nhiều theme hiển thị.
- AI sử dụng Minimax, Alpha-Beta Pruning, Transposition Table và Iterative Deepening.
- AI có logic xử lý chain, loop, parity và sacrifice trong endgame.
- AI chạy trên background thread để giao diện không bị đứng khi bot suy nghĩ.

## 3. Cấu trúc project

```text
Game-Dots-and-Boxes/
├── main.py
├── models.py
├── rules.py
├── ai.py
├── ui.py
├── assets/
│   └── sounds/
├── ai_logic_documentation.md
├── ai_execution_flow.md
└── README.md
```

Ý nghĩa các file chính:

| File | Vai trò |
|---|---|
| `main.py` | Entry point, tạo bàn cờ ban đầu và khởi chạy giao diện |
| `models.py` | Định nghĩa `GameState`, `Move` và hàm khởi tạo bàn cờ |
| `rules.py` | Xử lý luật chơi: kiểm tra move, apply move, undo move, terminal state |
| `ai.py` | Toàn bộ logic AI: tìm kiếm, heuristic, chain theory, sacrifice |
| `ui.py` | Giao diện Pygame, xử lý click chuột, render board, gọi AI |
| `assets/sounds/` | Âm thanh click, capture, win |
| `ai_logic_documentation.md` | Tài liệu giải thích logic AI chi tiết |
| `ai_execution_flow.md` | Tài liệu mô tả luồng chạy AI theo thứ tự thực thi |

## 4. Cài đặt và chạy project

### 4.1. Yêu cầu

- Python 3.10 trở lên.
- Thư viện `pygame`.

Nếu chưa có `pygame`, cài bằng:

```bash
pip install pygame
```

### 4.2. Chạy game

Tại thư mục project, chạy:

```bash
python main.py
```

Game sẽ mở cửa sổ Pygame. Người chơi tương tác bằng chuột để vẽ cạnh trên bàn cờ.

## 5. Thay đổi kích thước bàn cờ

Kích thước bàn cờ mặc định được khai báo trong `main.py`:

```python
board_size = 7
init_state = models.create_initial_state(board_size, board_size)
```

Muốn đổi sang bàn khác, ví dụ `4x4`, `6x6` hoặc `8x8`, sửa:

```python
board_size = 6
```

Sau đó chạy lại:

```bash
python main.py
```

## 6. Tổng quan logic AI

AI được gọi qua hàm:

```python
get_best_move(state, ai_player=2, base_depth=None, time_limit=4.0)
```

Luồng tổng quát:

```text
get_best_move()
    -> khởi tạo deadline 4 giây
    -> chọn base_depth theo kích thước bàn
    -> tìm forcing moves
        -> nếu có: sắp xếp bằng _order_forcing_moves()
        -> nếu không: lọc/sắp xếp bằng _order_moves()
    -> chạy iterative deepening
    -> gọi minimax + alpha-beta
    -> trả về best_move
```

Các ý tưởng chính:

- **Safe move**: ưu tiên nước không tạo ô 3 cạnh cho đối thủ.
- **Risky move**: chỉ xét khi không còn safe move, chọn nước mở chuỗi ít thiệt hại nhất.
- **Forcing move**: xử lý các tình huống có ô 3 cạnh hoặc chuỗi đang mở.
- **Sacrifice / hard-hearted handout**: khi có lợi, AI hy sinh 2 hoặc 4 ô cuối để ép đối thủ mở chuỗi tiếp theo.
- **Transposition Table**: cache trạng thái đã tính để giảm số lần tìm kiếm lặp.
- **Deadline nội bộ**: đảm bảo AI trả nước trong giới hạn thời gian, mặc định `4.0` giây.

## 7. Chiến thuật sacrifice của AI

Một điểm quan trọng của Dots and Boxes là không phải lúc nào ăn hết chuỗi cũng tốt. Nếu AI ăn hết một chuỗi nhưng vẫn giữ lượt và hết nước an toàn, AI có thể bị buộc phải mở chuỗi lớn hơn cho đối thủ.

Vì vậy AI hiện tại so sánh trực tiếp hai hướng:

- **Greedy capture**: ăn hết các ô có thể ăn.
- **Sacrifice / handout**: nhường lại 2 ô cuối với open chain hoặc 4 ô cuối với loop/closed structure.

AI dùng `_resolved_forcing_score()` để mô phỏng các capture bắt buộc sau mỗi lựa chọn, rồi đánh giá bên nào bị buộc mở chuỗi tiếp theo. Nhờ đó AI có thể hy sinh khi sacrifice giữ được quyền kiểm soát, nhưng vẫn ăn hết nếu đó là chuỗi cuối cùng.

## 8. Tài liệu chi tiết

Nếu cần hiểu sâu về AI, đọc thêm:

- [ai_logic_documentation.md](./ai_logic_documentation.md): giải thích các thành phần logic AI, heuristic, chain theory và sacrifice.
- [ai_execution_flow.md](./ai_execution_flow.md): mô tả thứ tự chạy từ UI đến `get_best_move()`, `minimax()` và trả kết quả.

Hai file này phù hợp để dùng khi thuyết trình hoặc khi thành viên khác muốn bảo trì/chỉnh sửa AI.

## 9. Ghi chú phát triển

- Project hiện không phải solver tuyệt đối cho mọi kích thước bàn.
- Sức mạnh AI phụ thuộc vào giới hạn thời gian, độ sâu tìm kiếm và heuristic.
- Trên bàn lớn, candidate pruning và chain heuristic quan trọng hơn việc tăng depth quá cao.
- Khi chỉnh AI, cần kiểm tra `get_best_move()` không làm thay đổi state đầu vào, vì UI chỉ nên apply move thật sau khi AI trả kết quả.

## 10. Thành phần kỹ thuật chính

| Nhóm kỹ thuật | Mục đích |
|---|---|
| Minimax | Mô phỏng lựa chọn tối ưu của AI và đối thủ |
| Alpha-Beta Pruning | Cắt bỏ nhánh không cần xét |
| Iterative Deepening | Tìm kiếm tăng dần độ sâu trong giới hạn thời gian |
| Transposition Table | Cache trạng thái để tránh tính lại |
| Move Ordering | Tăng hiệu quả cắt tỉa và ưu tiên move quan trọng |
| Chain/Loop Analysis | Đánh giá cấu trúc endgame |
| Sacrifice Control | Quyết định khi nào nên hy sinh để giữ quyền kiểm soát |

## 11. Tóm tắt

Project là một game Dots and Boxes hoàn chỉnh với AI chiến thuật. Điểm nổi bật của AI là không chỉ biết ăn ô trước mắt, mà còn biết tránh mở chuỗi, dồn đối thủ hết safe move và hy sinh đúng lúc để giữ quyền kiểm soát endgame.
