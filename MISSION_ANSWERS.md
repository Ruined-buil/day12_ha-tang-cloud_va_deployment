 **Student Name:** Thai Minh Kien  
> **Student ID:** 2A202600288
> **Date:** 17/4/2026

# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (Các lỗi thiết kế)
1. **Hardcoded Secrets (Lộ thông tin nhạy cảm)**: API Key và chuỗi kết nối Database được ghi trực tiếp trong mã nguồn (Dòng 17-18). Điều này cực kỳ nguy hiểm nếu code được đẩy lên các kho lưu trữ công khai như GitHub.
2. **Hardcoded Port & Host (Cố định Port và Host)**: App chỉ chạy trên `localhost` và port `8000` (Dòng 51-52). Trong môi trường Cloud (Railway/Render), ứng dụng phải lắng nghe trên port được cấp phát qua biến môi trường $PORT và binding vào địa chỉ `0.0.0.0`.
3. **Debug Mode & Hot Reload (Chế độ gỡ lỗi)**: `reload=True` vẫn được bật (Dòng 53). Chế độ này chỉ dùng cho phát triển local, trong production nó tiêu tốn tài nguyên và có thể làm lộ thông tin hệ thống khi xảy ra lỗi.
4. **Thiếu Health Check Endpoints (Thiếu kiểm tra trạng thái)**: Không có endpoint `/health` hoặc `/ready` (Dòng 42). Các nền tảng Cloud sẽ không biết container có đang chạy ổn định hay đã bị treo để khởi động lại.
5. **Logging bằng print() (Ghi log không chuẩn)**: Sử dụng lệnh `print()` thay vì thư viện logging chuyên nghiệp (Dòng 33). Nghiêm trọng hơn, ứng dụng còn **log cả secret API key** ra màn hình (Dòng 34).
6. **Không xử lý Graceful Shutdown (Tắt đột ngột)**: Ứng dụng không xử lý các tín hiệu như SIGTERM. Khi server bảo trì hoặc restart, nó sẽ ngắt ngay lập tức các yêu cầu đang xử lý của người dùng.
7. **Cấu hình ghi cứng (Hardcoded Config)**: Các thông số như `MAX_TOKENS`, `DEBUG` được gán cứng giá trị (Dòng 21-22) thay vì đọc từ biến môi trường để linh hoạt thay đổi.

### Exercise 1.3: Comparison table (Bảng so sánh)

| Tính năng | Bản phát triển (Develop) | Bản thực tế (Production) | Tại sao quan trọng? |
| :--- | :--- | :--- | :--- |
| **Cấu hình (Config)** | **Ghi cứng**: Các bí mật và cài đặt nằm ngay trong code. | **Biến môi trường**: Sử dụng file config để đọc từ Environment Variables. | Đảm bảo bảo mật (không lộ key lên Git) và linh hoạt khi chạy trên các server khác nhau. |
| **Kiểm tra trạng thái (Health Check)** | **Không có**: Không có cách nào để biết ứng dụng còn "sống" hay không. | **Có Endpoint**: Cung cấp `/health` và `/ready` để giám sát. | Giúp hệ thống tự động phục hồi (Self-healing); Cloud sẽ tự restart app nếu nó bị lỗi hoặc treo. |
| **Ghi log (Logging)** | **print()**: Chỉ là văn bản đơn giản, rất khó để tìm kiếm khi có hàng triệu dòng log. | **Structured JSON**: Log định dạng JSON có phân cấp (INFO/DEBUG). | Giúp dễ dàng tìm kiếm và phân tích lỗi trên các công cụ tập trung log (như Datadog, ELK). |
| **Tắt ứng dụng (Shutdown)** | **Đột ngột**: App dừng ngay lập tức, có thể làm hỏng dữ liệu hoặc ngắt kết nối dở dang. | **Graceful Shutdown**: Xử lý tín hiệu dừng, hoàn tất yêu cầu cuối trước khi tắt. | Đảm bảo trải nghiệm người dùng không bị gián đoạn và các kết nối cơ sở dữ liệu được đóng an toàn. |

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile basics (Cơ bản về Dockerfile)

1. **Base image là gì?**: `python:3.11`. Đây là ảnh nền chứa hệ điều hành Debian và môi trường Python 3.11 được cài đặt sẵn để ứng dụng có thể chạy được.
2. **Working directory là gì?**: `/app`. Đây là thư mục làm việc chính bên trong container. Mọi câu lệnh tiếp theo (như COPY, RUN, CMD) sẽ được thực thi tại thư mục này.
3. **Tại sao COPY requirements.txt trước?**: Để tận dụng **cơ chế Cache theo Layer của Docker**. Các thư viện (dependencies) thường ít thay đổi hơn mã nguồn. Việc cài đặt chúng trước giúp Docker không phải tải và cài lại thư viện mỗi khi bạn chỉ thay đổi một dòng code trong `app.py`, từ đó giúp tốc độ build image nhanh hơn rất nhiều.
4. **CMD vs ENTRYPOINT khác nhau thế nào?**:
   - **CMD**: Thiết lập lệnh mặc định cho container. Lệnh này **có thể bị ghi đè** dễ dàng khi chạy `docker run <image> <command_mới>`.
   - **ENTRYPOINT**: Thiết lập lệnh cố định không thể bị ghi đè một cách thông thường. Nó thường được dùng cho các ứng dụng đóng vai trò như một công cụ dòng lệnh.
   - Trong Dockerfile này, `CMD ["python", "app.py"]` cung cấp cách chạy ứng dụng mặc định nhưng vẫn cho phép linh hoạt thay đổi nếu cần (ví dụ: chạy shell để debug).