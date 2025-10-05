# ChatBrain

ChatBrain là mô hình trợ lý hội thoại tiếng Việt dựa trên FastAPI, kết hợp NLU BM25 và embeddings (tuỳ chọn).

## Yêu cầu hệ thống

* Python 3.11
* pip

## Cài đặt

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r chatbrain/requirements.txt
```

## Khởi chạy API

```bash
uvicorn chatbrain.app:app --reload
```

Sau khi máy chủ chạy, cần nạp kịch bản:

```bash
curl -X POST http://localhost:8000/load-scripts \
  -H "Content-Type: application/json" \
  -d '{"folder": "knowledge_base/scripts"}'
```

Gửi tin nhắn thử:

```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "Tôi muốn kích hoạt VNeID"}'
```

## Tích hợp Facebook Messenger

1. Cài đặt phụ thuộc:
   ```bash
   pip install -r chatbrain/requirements.txt
   ```
2. Chạy máy chủ FastAPI:
   ```bash
   uvicorn chatbrain.app:app --reload
   ```
3. Mở đường hầm công khai, ví dụ với ngrok:
   ```bash
   ngrok http 8000
   ```
   Sau đó đặt biến môi trường `PUBLIC_BASE_URL` trùng với URL do ngrok cung cấp.
4. Thiết lập biến môi trường (có thể dựa trên `.env.example`):
   * `FB_PAGE_ACCESS_TOKEN`
   * `FB_VERIFY_TOKEN` (mặc định `cap-demo-token`)
   * `USE_MEDIA=true` nếu muốn gửi ảnh đi kèm.
5. Cấu hình webhook trong Facebook App/Page:
   * Callback URL: `<PUBLIC_BASE_URL>/webhook/facebook`
   * Verify token: giá trị `FB_VERIFY_TOKEN`
6. Nạp kịch bản có sẵn (chỉ đọc YAML hiện tại):
   ```bash
   curl -X POST http://localhost:8000/load-scripts \
     -H "Content-Type: application/json" \
     -d '{"folder": "knowledge_base/scripts"}'
   ```
7. Gửi tin nhắn từ trang Facebook để kiểm thử. Hệ thống sẽ tự động phản hồi, hiển thị quick replies từ `ui.buttons` và (khi `USE_MEDIA=true`) gửi từng ảnh trong `ui.media`.

## CLI quản lý

```bash
python -m chatbrain.cli.menu
```

Menu hỗ trợ reload kịch bản, xem danh sách intents, xem stack và mô phỏng hội thoại.

## Kiểm thử

```bash
USE_EMBEDDING=false USE_SQLITE_LOG=false pytest chatbrain/tests -q
```

## Biến môi trường chính

| Biến | Mặc định | Mô tả |
| --- | --- | --- |
| `USE_EMBEDDING` | `false` | Bật/tắt embeddings sentence-transformers |
| `CONF_THRESHOLD` | `0.55` | Ngưỡng tự tin NLU |
| `MAX_DEPTH` | `2` | Độ sâu tối đa stack context |
| `USE_SQLITE_LOG` | `false` | Bật ghi log SQLite |
| `SQLITE_PATH` | `chatbrain_logs.db` | Đường dẫn file SQLite |

## Cấu trúc dữ liệu

Các kịch bản YAML đặt trong `knowledge_base/scripts/` với schema mô tả intents, bước và UI.
