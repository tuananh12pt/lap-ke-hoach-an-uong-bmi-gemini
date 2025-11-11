<h2 align="center">
    <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
    🎓 Faculty of Information Technology (DaiNam University)
    </a>
</h2>
<h2 align="center">
   NETWORK PROGRAMMING
</h2>
<div align="center">
    <p align="center">
        <img src="docs/aiotlab_logo.png" alt="AIoTLab Logo" width="170"/>
        <img src="docs/fitdnu_logo.png" alt="AIoTLab Logo" width="180"/>
        <img src="docs/dnu_logo.png" alt="DaiNam University Logo" width="200"/>
    </p>

[![AIoTLab](https://img.shields.io/badge/AIoTLab-green?style=for-the-badge)](https://www.facebook.com/DNUAIoTLab)
[![Faculty of Information Technology](https://img.shields.io/badge/Faculty%20of%20Information%20Technology-blue?style=for-the-badge)](https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin)
[![DaiNam University](https://img.shields.io/badge/DaiNam%20University-orange?style=for-the-badge)](https://dainam.edu.vn)

</div>


# Meal Planner by BMI (Flask + Google Gemini API)

Ứng dụng Flask tính BMI, ước lượng nhu cầu calo, và tạo kế hoạch ăn uống + luyện tập 7 ngày bằng Google Gemini AI.

## Tính năng
- ✅ Tính BMI & TDEE (Total Daily Energy Expenditure)
- ✅ Kế hoạch ăn uống 7 ngày theo ẩm thực Việt Nam
- ✅ Gợi ý luyện tập phù hợp (đi bộ, yoga, cardio theo BMI)
- ✅ Phân tích và cảnh báo BMI (quá thấp/quá cao)
- ✅ Tích hợp Google Gemini API để sinh kế hoạch thông minh
- ✅ Giao diện web hiện đại, responsive với bảng đẹp
- ✅ **Hiển thị dạng bảng chuyên nghiệp** với hiệu ứng hover & click
- ✅ **Sao chép bảng** vào clipboard
- ✅ **Xuất CSV** để mở bằng Excel
- ✅ **Thu gọn/Mở rộng** bảng linh hoạt
- ✅ **In ấn & Tải PDF** trực tiếp
- ✅ Mock fallback khi không có API key

## Các chức năng tương tác với bảng

### 1. **Highlight Row (Click để chọn)**
- Click vào bất kỳ hàng nào trong bảng để làm nổi bật
- Giúp dễ dàng theo dõi kế hoạch theo từng ngày

### 2. **Copy to Clipboard (Sao chép)**
- Nút "Sao chép" trong toolbar hoặc phía dưới
- Sao chép toàn bộ bảng để paste vào Word, Email, etc.

### 3. **Export to CSV (Xuất Excel)**
- Tải xuống file CSV với encoding UTF-8
- Mở bằng Excel để chỉnh sửa hoặc lưu trữ

### 4. **Toggle View (Thu gọn/Mở rộng)**
- Thu gọn bảng để xem tổng quan nhanh
- Mở rộng để xem chi tiết đầy đủ

### 5. **Print & PDF**
- In trực tiếp hoặc lưu thành PDF
- Layout được tối ưu cho in ấn

## Cài đặt nhanh

### 1. Clone và tạo virtualenv
```powershell
cd "C:\Users\GIAP OS\BMI"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Cài dependencies
```powershell
pip install -r requirements.txt
```

### 3. Cấu hình Gemini API Key

#### Lấy API Key miễn phí
1. Truy cập: https://makersuite.google.com/app/apikey
2. Đăng nhập Google
3. Nhấn **"Create API Key"**
4. Copy key

#### Tạo file .env
```powershell
copy .env.example .env
```

Mở `.env` và paste API key:
```env
GEMINI_API_KEY=AIzaSy...your-actual-key-here
```

### 4. Chạy app
```powershell
$env:FLASK_APP='app.app'
$env:FLASK_ENV='development'
flask run
```

Mở trình duyệt: http://127.0.0.1:5000

## Cách hoạt động

1. Người dùng nhập: cân nặng, chiều cao, tuổi, giới tính, mức hoạt động, mục tiêu
2. Server tính BMI và TDEE, xác định target calories
3. Tạo prompt chi tiết gửi tới **Google Gemini API**:
   - Yêu cầu kế hoạch ăn 7 ngày (khẩu phần Việt Nam)
   - Gợi ý luyện tập phù hợp
   - Phân tích BMI + cảnh báo sức khỏe
4. Gemini trả về plan → server parse thành HTML table an toàn
5. Hiển thị plan + shopping list + exercise + BMI analysis

## Mock Mode (không cần API key)
- Nếu không đặt `GEMINI_API_KEY`, app sẽ dùng mock thông minh:
  - Tạo plan 7 ngày dựa trên BMI/target calories
  - Điều chỉnh khẩu phần theo BMI (thấp → tăng, cao → giảm)
  - Gợi ý luyện tập theo mục tiêu
  - Cảnh báo BMI bất thường

## Cấu trúc project
```
BMI/
├── app/
│   ├── __init__.py
│   ├── app.py              # Flask routes
│   ├── utils.py            # BMI/TDEE calculation, prompt builder
│   ├── gemini_client.py    # Google Gemini API client
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html      # Form nhập liệu
│   │   └── plan.html       # Hiển thị kế hoạch
│   └── static/
│       └── style.css       # Custom styles
├── tests/
│   └── test_utils.py       # Unit tests
├── requirements.txt
├── .env.example
└── README.md
```

## API Details

### Google Gemini API
- Model: `gemini-pro`
- SDK: `google-generativeai`
- Rate limit: 60 requests/minute (free tier)
- Docs: https://ai.google.dev/docs

### Prompt structure
```
Hãy tạo kế hoạch ăn 7 ngày theo phong cách ẩm thực Việt Nam...
BMI: X.X, TDEE: YYYY kcal, mục tiêu: [giảm/tăng/duy trì]...
Đề xuất kế hoạch luyện tập nhẹ...
Phân tích chỉ số BMI và cảnh báo nếu cần...
```

## Tests
```powershell
pytest -q
```

## Troubleshooting

### Lỗi: "API key not valid"
- Kiểm tra key đã copy đúng vào `.env`
- Đảm bảo không có khoảng trắng thừa
- Key phải bắt đầu bằng `AIza...`

### App trả về mock thay vì gọi API
- Kiểm tra `GEMINI_API_KEY` đã set trong `.env`
- Restart Flask sau khi thay đổi `.env`
- Xem terminal log: sẽ có message `[GeminiClient] Configured with...`

### Response quá ngắn/không đủ 7 ngày
- Gemini đôi khi truncate. Tăng token limit trong `gemini_client.py` (sửa `max_output_tokens`)

## License
MIT

## Credits
- Flask web framework
- Google Gemini API
- Bootstrap 5 + Bootstrap Icons
