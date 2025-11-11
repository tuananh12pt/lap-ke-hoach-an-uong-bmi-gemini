import math

def lbs_to_kg(lbs: float) -> float:
    return lbs * 0.45359237


def inches_to_cm(inches: float) -> float:
    return inches * 2.54


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    if height_cm <= 0:
        raise ValueError('height must be > 0')
    height_m = height_cm / 100.0
    return weight_kg / (height_m * height_m)


def estimate_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    # Mifflin-St Jeor
    if sex.lower().startswith('m'):
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def activity_multiplier(level: str) -> float:
    mapping = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very': 1.9,
    }
    return mapping.get(level, 1.2)


def estimate_tdee(weight_kg: float, height_cm: float, age: int, sex: str, activity: str) -> float:
    bmr = estimate_bmr(weight_kg, height_cm, age, sex)
    return bmr * activity_multiplier(activity)


def target_calories_by_goal(tdee: float, bmi: float, goal: str) -> float:
    # If goal is 'auto', infer from BMI
    if goal == 'auto':
        if bmi >= 25:
            goal = 'lose'
        elif bmi < 18.5:
            goal = 'gain'
        else:
            goal = 'maintain'

    if goal == 'lose':
        return tdee - 500  # simple deficit
    elif goal == 'gain':
        return tdee + 300
    else:
        return tdee


def build_prompt(bmi: float, tdee: float, target_cal: float, diet: str = 'none', goal: str = 'auto', activity: str = 'sedentary') -> str:
    diet_text = '' if diet in (None, '', 'none') else f"Ưu tiên/không ăn: {diet}."
    prompt = (
        f"Hãy tạo kế hoạch ăn 7 ngày theo phong cách ẩm thực Việt Nam, mỗi ngày khoảng {int(target_cal)} kcal. "
        f"Bao gồm 3 bữa chính và 1-2 bữa phụ, phân bố macro (protein/carbs/fat) sơ bộ. "
        f"Người dùng có BMI {bmi:.1f}, TDEE ~{int(tdee)} kcal, mục tiêu: {goal}, mức hoạt động: {activity}. {diet_text} "
        f"Ghi rõ khẩu phần theo đơn vị Việt Nam (ví dụ: chén cơm, miếng, lát, bát canh). Cho công thức ngắn gọn dễ nấu.\n\n"
    )

    # Request structured output with clear sections
    prompt += (
        "Định dạng kết quả theo các phần sau:\n\n"
        "## KẾ HOẠCH ĂN 7 NGÀY\n"
        "[Liệt kê từng ngày với format: Ngày X: Bữa sáng | Bữa trưa | Bữa phụ | Bữa tối | Ước tính kcal]\n\n"
        "## DANH SÁCH MUA SẮM\n"
        "[Liệt kê tất cả nguyên liệu cần mua cho 7 ngày, ước lượng khối lượng (kg/gram), phân loại theo nhóm: rau củ, thịt cá, hạt ngũ cốc, gia vị...]\n\n"
    )

    # Request exercise plan based on BMI and goal
    prompt += (
        "## KẾ HOẠCH LUYỆN TẬP 7 NGÀY\n"
        f"[Đề xuất kế hoạch luyện tập chi tiết cho 7 ngày, phù hợp với BMI {bmi:.1f} và mục tiêu {goal}:\n"
        "- Nếu mục tiêu giảm cân: ưu tiên cardio (đi bộ nhanh, chạy bộ nhẹ, đạp xe), kết hợp sức bền, thời gian và cường độ cụ thể\n"
        "- Nếu mục tiêu tăng cân: ưu tiên bài tập sức mạnh (tạ, bodyweight), ít cardio, thời gian nghỉ ngơi\n"
        "- Nếu duy trì: kết hợp cardio + sức mạnh + yoga/giãn cơ cân bằng\n"
        "Ghi rõ: loại bài tập, thời gian/số lượng, mức độ (nhẹ/vừa/nặng), lưu ý an toàn]\n\n"
    )

    # Request BMI analysis
    prompt += (
        "## PHÂN TÍCH BMI VÀ CẢNH BÁO SỨC KHỎE\n"
        f"[Phân tích chỉ số BMI {bmi:.1f}:\n"
        "- Nếu BMI < 18.5: cảnh báo gầy, liệt kê rủi ro (suy dinh dưỡng, giảm miễn dịch, loãng xương), khuyến nghị khám bác sĩ nếu < 16\n"
        "- Nếu 18.5 ≤ BMI < 25: nhận xét bình thường, khuyến nghị duy trì\n"
        "- Nếu 25 ≤ BMI < 30: cảnh báo thừa cân, rủi ro tim mạch/chuyển hóa, khuyến nghị giảm cân an toàn\n"
        "- Nếu BMI ≥ 30: cảnh báo béo phì, rủi ro cao (tiểu đường, huyết áp, tim mạch), khuyến nghị tham vấn bác sĩ chuyên khoa\n"
        "Đưa lời khuyên cụ thể và an toàn về chế độ ăn + vận động phù hợp với tình trạng BMI]\n"
    )

    return prompt
