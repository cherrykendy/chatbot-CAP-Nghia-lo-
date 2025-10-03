# Bước 1: Chọn một image Python làm nền tảng
FROM python:3.10-slim

# Bước 2: Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Bước 3: Sao chép file requirements vào trước để tận dụng cache
COPY requirements.txt .

# Bước 4: Cài đặt tất cả các thư viện Python cần thiết
RUN pip install --no-cache-dir -r requirements.txt

# Bước 5: Sao chép toàn bộ mã nguồn của dự án vào container
COPY . .

# Bước 6: Lệnh để khởi chạy ứng dụng khi container bắt đầu
# !!! THAY THẾ "app.py" BẰNG TÊN FILE PYTHON CHÍNH CỦA BẠN !!!
CMD ["python", "app.py"] 
