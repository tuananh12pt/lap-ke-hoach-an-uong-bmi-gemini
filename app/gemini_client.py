import os
import requests
import re
import random
import json
import html
from typing import Optional

# Try to import Google Generative AI SDK for real Gemini integration
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiClient:
    def __init__(self, api_key: str = None, api_url: str = None):
        self.api_key = api_key
        self.api_url = api_url or 'https://api.example.com/v1/generate'
        self.use_genai_sdk = False
        
        # If API key is set and SDK is available, configure it
        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.use_genai_sdk = True
                print("[GeminiClient] Configured with Google Generative AI SDK")
            except Exception as e:
                print(f"[GeminiClient] Could not configure genai SDK: {e}")
                self.use_genai_sdk = False

    def generate(self, prompt: str) -> str:
        # If no API key configured, return mock
        if not self.api_key:
            return self._mock_response(prompt)

        # If SDK is available and configured, use it (preferred)
        if self.use_genai_sdk and GENAI_AVAILABLE:
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                if response and response.text:
                    # Format the response into safe HTML
                    return self._format_response(response.text)
                else:
                    # Fallback to mock if no text returned
                    return self._mock_response(prompt)
            except Exception as e:
                print(f"[GeminiClient] Error calling Gemini API: {e}")
                # Fallback to mock on error
                return self._mock_response(prompt)

        # If api_url looks like Google Generative API, try to call using key or service account
        if self.api_url and 'googleapis.com' in self.api_url:
            # Prefer using API key in query string, else attempt Bearer via service account
            try:
                # If api_key looks like an API key (no dots), use it as query param
                if self.api_key and isinstance(self.api_key, str) and '.' not in self.api_key:
                    url = f"{self.api_url}?key={self.api_key}"
                    payload = {'prompt': prompt}
                    resp = requests.post(url, json=payload, timeout=20)
                else:
                    # Try to obtain an OAuth2 token via google-auth if available
                    try:
                        from google.oauth2 import service_account
                        from google.auth.transport.requests import AuthorizedSession
                        # If GEMINI_API_KEY is a path to a service account JSON, use it
                        creds = service_account.Credentials.from_service_account_file(self.api_key, scopes=["https://www.googleapis.com/auth/cloud-platform"]) if os.path.exists(self.api_key) else None
                        if creds:
                            authed_session = AuthorizedSession(creds)
                            resp = authed_session.post(self.api_url, json={'prompt': prompt}, timeout=20)
                        else:
                            # fallback to basic POST with Bearer token header
                            headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
                            resp = requests.post(self.api_url, json={'prompt': prompt}, headers=headers, timeout=20)
                    except Exception:
                        # fallback
                        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
                        resp = requests.post(self.api_url, json={'prompt': prompt}, headers=headers, timeout=20)

                resp.raise_for_status()
                data = resp.json()
            except Exception:
                # On any failure to call Google endpoint, fallback to mock
                return self._mock_response(prompt)

        else:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            payload = { 'prompt': prompt, 'max_tokens': 800 }
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        # Try to extract a text response from common fields
        text = None
        # Google/other LLMs may return different shapes
        if isinstance(data, dict):
            # common variants
            if 'text' in data:
                text = data['text']
            elif 'output' in data and isinstance(data['output'], str):
                text = data['output']
            elif 'candidates' in data and len(data['candidates']) > 0:
                # candidate could be dict with 'content' or 'text'
                c = data['candidates'][0]
                if isinstance(c, dict):
                    text = c.get('content') or c.get('text')
                else:
                    text = str(c)
            elif 'choices' in data and len(data['choices']) > 0:
                ch = data['choices'][0]
                if isinstance(ch, dict):
                    # some APIs nest message->content
                    text = ch.get('text') or ch.get('message') or ch.get('content')
                    if isinstance(text, dict):
                        # message object
                        text = text.get('content') or text.get('text')
                else:
                    text = str(ch)
            else:
                # last resort: stringify
                text = json.dumps(data)
        else:
            text = str(data)

        # Format the text into safe HTML (try structured parse)
        return self._format_response(text)

    def _format_response(self, text: str) -> str:
        """Try to parse model text into a safe HTML table.
        - If text contains JSON with 'days', use it.
        - Else try to split by 'Ngày' or 'Day' markers.
        - If text has ## section markers (structured output), parse sections.
        - Fallback: escape and return as preformatted text.
        """
        if not text:
            return ''

        # Check if text has structured sections with ## headers
        if '##' in text:
            return self._parse_structured_sections(text)

        # If text looks like JSON, try to parse
        stripped = text.strip()
        try:
            # Find JSON object in text
            json_start = stripped.find('{')
            json_end = stripped.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                candidate = stripped[json_start:json_end+1]
                obj = json.loads(candidate)
                if isinstance(obj, dict) and 'days' in obj and isinstance(obj['days'], list):
                    return self._render_days_to_table(obj['days'])
        except Exception:
            pass

        # Try to detect day-separated plain text (Vietnamese or English)
        # Split by lines containing 'Ngày' or 'Day'
        lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
        day_indices = [i for i,l in enumerate(lines) if re.match(r'^(Ngày|Day)\s*\d+', l, re.I)]
        if day_indices:
            days = []
            # Collect text blocks per day
            for idx, start in enumerate(day_indices):
                end = day_indices[idx+1] if idx+1 < len(day_indices) else len(lines)
                block = '\n'.join(lines[start:end])
                # heuristic: split meals by '-' or ':'
                meal_lines = re.split(r'\n|-\s*', block)
                # first token contains day label
                day_label = meal_lines[0]
                # remaining tokens are meals; try to map to breakfast/lunch/snack/dinner
                meals = [m.strip() for m in meal_lines[1:] if m.strip()][:4]
                # pad meals
                while len(meals) < 4:
                    meals.append('')
                days.append({'label': day_label, 'breakfast': meals[0], 'lunch': meals[1], 'snack': meals[2], 'dinner': meals[3]})
            return self._render_days_to_table(days)

        # fallback: escape and wrap in pre
        return '<pre class="plan-output">' + html.escape(text) + '</pre>'

    def _parse_structured_sections(self, text: str) -> str:
        """Parse text with ## section markers into HTML.
        Expected sections: KẾ HOẠCH ĂN, DANH SÁCH MUA SẮM, KẾ HOẠCH LUYỆN TẬP, PHÂN TÍCH BMI
        """
        sections = {}
        current_section = None
        current_content = []

        for line in text.splitlines():
            stripped = line.strip()
            # Detect section header
            if stripped.startswith('##'):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                # Start new section
                current_section = stripped.replace('##', '').strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content)

        # Build HTML from sections
        html_parts = ['<div class="gemini-response">']

        # 1. BMI analysis section (FIRST - moved to top for visibility)
        bmi_section = None
        for key in sections:
            if 'PHÂN TÍCH BMI' in key.upper() or 'BMI ANALYSIS' in key.upper() or 'CẢNH BÁO' in key.upper():
                bmi_section = sections[key]
                break
        
        if bmi_section:
            # Determine warning level from content
            warning_class = 'text-muted'
            icon_class = 'bi-info-circle-fill'
            if any(w in bmi_section.lower() for w in ['béo phì', 'rất thấp', 'nghiêm trọng', 'obese', 'severe']):
                warning_class = 'text-danger'
                icon_class = 'bi-exclamation-octagon-fill'
            elif any(w in bmi_section.lower() for w in ['thừa cân', 'gầy', 'overweight', 'underweight', 'cảnh báo']):
                warning_class = 'text-warning'
                icon_class = 'bi-exclamation-triangle-fill'
            else:
                warning_class = 'text-success'
                icon_class = 'bi-check-circle-fill'
            
            html_parts.append(f'<div class="alert alert-{warning_class.replace("text-", "")} border-start border-4 mb-4">')
            html_parts.append(f'<h5 class="alert-heading"><i class="bi {icon_class} me-2"></i>Phân tích BMI & Cảnh báo sức khỏe</h5>')
            html_parts.append(self._format_paragraph_content(bmi_section))
            html_parts.append('</div>')

        # 2. Meal plan section
        meal_section = None
        for key in sections:
            if 'KẾ HOẠCH ĂN' in key.upper() or 'MEAL PLAN' in key.upper():
                meal_section = sections[key]
                break
        
        if meal_section:
            html_parts.append('<h4 class="text-primary mt-3"><i class="bi bi-calendar-week me-2"></i>Kế hoạch ăn 7 ngày</h4>')
            # Try to parse days into table
            table_html = self._parse_meal_days_to_table(meal_section)
            html_parts.append(table_html)

        # 3. Shopping list section
        shopping_section = None
        for key in sections:
            if 'DANH SÁCH MUA SẮM' in key.upper() or 'SHOPPING' in key.upper():
                shopping_section = sections[key]
                break
        
        if shopping_section:
            html_parts.append('<h5 class="text-success mt-4"><i class="bi bi-cart-fill me-2"></i>Danh sách mua sắm</h5>')
            html_parts.append('<div class="shopping-list">')
            html_parts.append(self._format_list_content(shopping_section))
            html_parts.append('</div>')

        # 3. Exercise plan section
        exercise_section = None
        for key in sections:
            if 'LUYỆN TẬP' in key.upper() or 'EXERCISE' in key.upper():
                exercise_section = sections[key]
                break
        
        if exercise_section:
            html_parts.append('<h5 class="text-info mt-4"><i class="bi bi-heart-pulse-fill me-2"></i>Kế hoạch luyện tập</h5>')
            html_parts.append('<div class="exercise-plan">')
            html_parts.append(self._format_list_content(exercise_section))
            html_parts.append('</div>')

        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def _parse_meal_days_to_table(self, content: str) -> str:
        """Parse meal plan content into HTML table."""
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        
        table = [
            '<div class="table-responsive">',
            '<table class="table table-bordered table-hover align-middle">',
            '<thead><tr><th style="width: 10%;">Ngày</th><th style="width: 20%;">🌅 Bữa sáng</th><th style="width: 25%;">☀️ Bữa trưa</th><th style="width: 20%;">🍎 Bữa phụ</th><th style="width: 20%;">🌙 Bữa tối</th><th style="width: 5%;">Kcal</th></tr></thead>',
            '<tbody>'
        ]
        
        # Try to parse each line as: Ngày X: meal1 | meal2 | meal3 | meal4 | kcal
        for line in lines:
            match = re.match(r'(Ngày\s*\d+)[:\s]+(.*)', line, re.I)
            if match:
                day_label = html.escape(match.group(1))
                rest = match.group(2)
                # Split by | or similar delimiter
                parts = [p.strip() for p in re.split(r'[|]', rest)]
                # Expect: breakfast, lunch, snack, dinner, kcal
                while len(parts) < 5:
                    parts.append('')
                breakfast, lunch, snack, dinner, kcal = parts[:5]
                
                # Format each meal with line breaks for better readability
                breakfast_fmt = html.escape(breakfast).replace(',', '<br>')
                lunch_fmt = html.escape(lunch).replace(',', '<br>')
                snack_fmt = html.escape(snack).replace(',', '<br>')
                dinner_fmt = html.escape(dinner).replace(',', '<br>')
                
                table.append(f'<tr><td>{day_label}</td><td>{breakfast_fmt}</td><td>{lunch_fmt}</td><td>{snack_fmt}</td><td>{dinner_fmt}</td><td><span class="badge bg-success">{html.escape(kcal)}</span></td></tr>')
        
        table.append('</tbody></table>')
        table.append('</div>')
        return '\n'.join(table)

    def _format_list_content(self, content: str) -> str:
        """Format list content (shopping/exercise) with proper grouping and styling."""
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        html_parts = ['<div class="row g-3">']
        
        current_group = None
        group_items = []
        
        for line in lines:
            # Check if line is a group header (bold text with ** or starting with capital letter followed by :)
            if line.startswith('**') and line.endswith('**'):
                # Save previous group
                if current_group and group_items:
                    html_parts.append(self._render_list_group(current_group, group_items))
                    group_items = []
                current_group = line.strip('*').strip(':')
            elif re.match(r'^([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ][^:]+):\s*$', line):
                # Save previous group
                if current_group and group_items:
                    html_parts.append(self._render_list_group(current_group, group_items))
                    group_items = []
                current_group = line.strip(':')
            else:
                # Remove markdown list markers
                item = re.sub(r'^[-*•]\s*', '', line)
                if item:
                    group_items.append(item)
        
        # Save last group
        if current_group and group_items:
            html_parts.append(self._render_list_group(current_group, group_items))
        
        # If no groups found, render as simple list
        if not current_group:
            html_parts = ['<ul class="list-group">']
            for line in lines:
                item = re.sub(r'^[-*•]\s*', '', line)
                if item:
                    html_parts.append(f'<li class="list-group-item"><i class="bi bi-check-circle-fill text-success me-2"></i>{html.escape(item)}</li>')
            html_parts.append('</ul>')
        else:
            html_parts.append('</div>')
        
        return '\n'.join(html_parts)

    def _render_list_group(self, title: str, items: list) -> str:
        """Render a list group as a card."""
        html = ['<div class="col-md-6">']
        html.append('<div class="card shadow-sm h-100">')
        html.append(f'<div class="card-header bg-primary text-white"><strong>{html.escape(title)}</strong></div>')
        html.append('<ul class="list-group list-group-flush">')
        for item in items:
            html.append(f'<li class="list-group-item"><i class="bi bi-check-circle text-success me-2"></i>{html.escape(item)}</li>')
        html.append('</ul>')
        html.append('</div>')
        html.append('</div>')
        return '\n'.join(html)

    def _format_paragraph_content(self, content: str) -> str:
        """Format paragraph content with proper spacing."""
        paragraphs = [p.strip() for p in content.strip().split('\n\n') if p.strip()]
        html_parts = []
        for para in paragraphs:
            # Replace single newlines with <br>, escape
            para = '<br>'.join(html.escape(line) for line in para.splitlines() if line.strip())
            html_parts.append(f'<p>{para}</p>')
        return '\n'.join(html_parts)

    def _render_days_to_table(self, days) -> str:
        # days: list of dicts with keys label, breakfast, lunch, snack, dinner (or simple strings)
        parts = ['<table class="table table-sm table-bordered">', '<thead class="table-light"><tr><th>Ngày</th><th>Bữa sáng</th><th>Bữa trưa</th><th>Bữa phụ</th><th>Bữa tối</th></tr></thead>', '<tbody>']
        for d in days:
            if isinstance(d, dict):
                label = html.escape(str(d.get('label','')))
                b = html.escape(str(d.get('breakfast','')))
                l = html.escape(str(d.get('lunch','')))
                s = html.escape(str(d.get('snack','')))
                di = html.escape(str(d.get('dinner','')))
            else:
                # if element is a simple string, put it under 'Bữa sáng'
                label = html.escape(str(d))
                b = l = s = di = ''
            parts.append(f'<tr><td>{label}</td><td>{b}</td><td>{l}</td><td>{s}</td><td>{di}</td></tr>')
        parts.append('</tbody></table>')
        return '\n'.join(parts)

    def _mock_response(self, prompt: str) -> str:
        # Dynamic 7-day mock: parse target kcal and diet from the prompt when possible
        # Return structured text with ## sections (mimicking real Gemini output format)
        # Extract target kcal (e.g., '2000 kcal')
        match = re.search(r"(\d{3,4})\s*kcal", prompt)
        try:
            target_kcal = int(match.group(1)) if match else 2000
        except Exception:
            target_kcal = 2000

        # detect simple diet keywords
        prompt_lower = prompt.lower()
        is_vegetarian = any(k in prompt_lower for k in ['chay', 'vegetarian', 'vegan'])
        # extract BMI if present
        bmi_match = re.search(r"bmi\s*[:=]?\s*(\d{1,2}(?:\.\d+)?)", prompt_lower)
        try:
            bmi_val = float(bmi_match.group(1)) if bmi_match else None
        except Exception:
            bmi_val = None

        # seed random with target so same inputs yield same plan
        random.seed(target_kcal)

        # Build structured response (plain text with ## headers, like Gemini would return)
        response_parts = []

        # 1. BMI Analysis first
        response_parts.append("## PHÂN TÍCH BMI VÀ CẢNH BÁO SỨC KHỎE\n")
        if bmi_val is None:
            response_parts.append("Không có thông tin BMI rõ ràng để phân tích.\n")
        else:
            if bmi_val < 16:
                response_parts.append(f"**BMI hiện tại: {bmi_val:.1f} - Gầy mức độ nghiêm trọng**\n\n")
                response_parts.append("⚠️ **Cảnh báo nghiêm trọng**: BMI dưới 16 cho thấy tình trạng suy dinh dưỡng nặng.\n\n")
                response_parts.append("**Rủi ro sức khỏe:**\n- Suy giảm miễn dịch nghiêm trọng\n- Loãng xương, dễ gãy xương\n- Rối loạn nội tiết, kinh nguyệt (nữ)\n- Suy tim, rối loạn nhịp tim\n\n")
                response_parts.append("**Khuyến nghị:** Cần khám bác sĩ chuyên khoa dinh dưỡng NGAY. Tăng calo từ từ dưới sự giám sát y tế.\n")
            elif bmi_val < 18.5:
                response_parts.append(f"**BMI hiện tại: {bmi_val:.1f} - Thiếu cân**\n\n")
                response_parts.append("**Rủi ro sức khỏe:**\n- Thiếu hụt dinh dưỡng, vitamin\n- Giảm khả năng miễn dịch\n- Mệt mỏi, chóng mặt\n\n")
                response_parts.append("**Khuyến nghị:** Tăng khẩu phần ăn, ưu tiên thực phẩm giàu năng lượng (hạt, bơ, sữa, thịt nạc). Ăn 5-6 bữa nhỏ/ngày.\n")
            elif bmi_val >= 30:
                response_parts.append(f"**BMI hiện tại: {bmi_val:.1f} - Béo phì**\n\n")
                response_parts.append("⚠️ **Cảnh báo cao**: BMI ≥ 30 tăng nguy cơ các bệnh mạn tính.\n\n")
                response_parts.append("**Rủi ro sức khỏe:**\n- Bệnh tim mạch, đột quỵ\n- Tiểu đường type 2\n- Huyết áp cao\n- Khó thở khi ngủ\n- Thoái hóa khớp\n\n")
                response_parts.append("**Khuyến nghị:** Tham vấn bác sĩ chuyên khoa tim mạch và nội tiết. Giảm cân từ từ (0.5-1kg/tuần), kết hợp vận động có cường độ.\n")
            elif bmi_val >= 25:
                response_parts.append(f"**BMI hiện tại: {bmi_val:.1f} - Thừa cân**\n\n")
                response_parts.append("**Rủi ro sức khỏe:**\n- Tăng nguy cơ tim mạch\n- Rối loạn chuyển hóa\n- Viêm khớp do tăng tải trọng\n\n")
                response_parts.append("**Khuyến nghị:** Giảm calo vừa phải (300-500 kcal/ngày), tăng hoạt động thể chất. Ưu tiên rau xanh, protein nạc, giảm carb tinh chế.\n")
            else:
                response_parts.append(f"**BMI hiện tại: {bmi_val:.1f} - Bình thường**\n\n")
                response_parts.append("✅ Chỉ số BMI trong ngưỡng khỏe mạnh. Hãy duy trì chế độ ăn cân bằng và hoạt động thể chất đều đặn.\n\n")
                response_parts.append("**Khuyến nghị:** Tiếp tục chế độ ăn đa dạng, 30 phút vận động/ngày, ngủ đủ giấc.\n")

        # 2. Meal plan
        response_parts.append("\n## KẾ HOẠCH ĂN 7 NGÀY\n\n")
        
        # Define meal pools (Vietnamese-style). If vegetarian, remove meat dishes.
        breakfasts = [
            '1 bát phở gà nhỏ + 1 quả chuối',
            '1 bát bún riêu nhỏ',
            '1 chén cháo yến mạch + 1 quả chuối',
            '1 bánh mì ốp la (1 quả trứng) + rau',
            '1 chén yến mạch + sữa',
            '1 bánh cuốn nhỏ + ít nước chấm'
        ]

        lunches = [
            '1 chén cơm + 100g ức gà xào rau',
            '1 chén cơm + 100g cá nướng + rau luộc',
            '1 phở gà nhỏ (ít dầu)',
            '1 chén cơm + đậu hũ xào + rau',
            '1 chén cơm + salad cá ngừ',
            '1 chén cơm + thịt bò xào rau'
        ]

        snacks = [
            '1 hộp sữa chua', '1 quả táo + ít hạt', '1 nắm hạt điều', '1 ly sinh tố bơ nhỏ', '1 quả chuối'
        ]

        dinners = [
            '1 chén cơm + 120g cá kho + canh rau',
            '1 chén cơm + 120g gà áp chảo + canh',
            '1 chén cơm + đậu hũ xào + rau',
            '1 chén cơm + cá nướng + rau',
            '1 phần mỳ Ý nhỏ (ít sốt) + salad',
            '1 chén cơm + cá quay + rau'
        ]

        if is_vegetarian:
            # Replace lunches/dinners with vegetarian options
            lunches = [l.replace('ức gà', 'đậu hũ').replace('cá', 'đậu hũ').replace('thịt bò', 'rau') for l in lunches]
            dinners = [d.replace('cá', 'đậu hũ').replace('gà', 'đậu hũ').replace('thịt', 'rau') for d in dinners]

        # Adjust pools by BMI: overweight -> smaller carb portions and more protein/veg;
        # underweight -> include more energy-dense options
        if bmi_val is not None:
            if bmi_val >= 25:
                # reduce rice portions wording, prefer grilled/steamed, add salads
                lunches = [s.replace('1 chén cơm', '1/2 chén cơm').replace('gà', 'ức gà').replace('cá', 'cá nướng') for s in lunches]
                dinners = [s.replace('1 chén cơm', '1/2 chén cơm') for s in dinners]
                breakfasts = [s.replace('1 chén cháo', '1 bát cháo nhỏ').replace('bánh mì', 'bánh mì nguyên cám nhỏ') for s in breakfasts]
            elif bmi_val < 18.5:
                # increase portions slightly, add energy-dense foods
                lunches = [s.replace('1 chén cơm', '1.5 chén cơm').replace('100g', '150g') for s in lunches]
                dinners = [s.replace('1 chén cơm', '1.5 chén cơm') for s in dinners]
                breakfasts = [s + ' + 1 ly sữa' if 'sữa' not in s else s for s in breakfasts]

        # Build 7-day plan
        for i in range(7):
            b = random.choice(breakfasts)
            l = random.choice(lunches)
            s = random.choice(snacks)
            d = random.choice(dinners)
            # approximate base kcal per day
            base_kcal = 400 + 600 + 150 + 800
            scale = target_kcal / base_kcal if base_kcal > 0 else 1.0
            approx_kcal = int(base_kcal * scale)
            response_parts.append(f"Ngày {i+1}: {b} | {l} | {s} | {d} | ~{approx_kcal} kcal\n")

        # 3. Shopping list
        response_parts.append("\n## DANH SÁCH MUA SẮM\n\n")
        response_parts.append("**Nhóm tinh bột:**\n- Gạo/cơm: 2-3 kg\n- Bún/phở khô: 500g\n- Yến mạch: 500g\n- Bánh mì nguyên cám: 1 ổ\n\n")
        
        if not is_vegetarian:
            response_parts.append("**Nhóm protein động vật:**\n- Ức gà: 700g\n- Cá (hồi/rô phi): 800g\n- Trứng: 1 vỉ (10 quả)\n\n")
        
        response_parts.append("**Nhóm protein thực vật:**\n- Đậu hũ: 500g\n- Hạt điều: 200g\n- Sữa chua: 7 hộp\n\n")
        response_parts.append("**Rau củ:**\n- Rau xanh hỗn hợp: 1.5kg\n- Chuối: 7 quả\n- Táo: 3 quả\n- Bơ: 2 quả\n\n")
        response_parts.append("**Gia vị & khác:**\n- Dầu ăn, muối, tiêu, tương ớt\n- Nước mắm, tỏi, hành\n")

        # 4. Exercise plan
        response_parts.append("\n## KẾ HOẠCH LUYỆN TẬP 7 NGÀY\n\n")
        if bmi_val is None or (18.5 <= bmi_val < 25):
            response_parts.append("**Mục tiêu: Duy trì sức khỏe**\n\n")
            response_parts.append("- Ngày 1: Đi bộ nhanh 30 phút (5-6 km/h)\n")
            response_parts.append("- Ngày 2: Yoga 25 phút (tư thế cơ bản)\n")
            response_parts.append("- Ngày 3: Chạy bộ nhẹ 20 phút + giãn cơ 10 phút\n")
            response_parts.append("- Ngày 4: Nghỉ ngơi hoặc đi bộ nhẹ 15 phút\n")
            response_parts.append("- Ngày 5: Tập sức mạnh (tạ nhẹ/bodyweight) 30 phút\n")
            response_parts.append("- Ngày 6: Đi bộ 30 phút + yoga 15 phút\n")
            response_parts.append("- Ngày 7: Nghỉ ngơi tích cực (giãn cơ nhẹ)\n")
        elif bmi_val and bmi_val >= 25:
            response_parts.append("**Mục tiêu: Giảm cân an toàn**\n\n")
            response_parts.append("- Ngày 1: Đi bộ nhanh 40 phút (nhịp tim 60-70% max)\n")
            response_parts.append("- Ngày 2: Đạp xe hoặc bơi 30 phút\n")
            response_parts.append("- Ngày 3: Đi bộ nhanh 35 phút + tạ nhẹ 15 phút\n")
            response_parts.append("- Ngày 4: Yoga hoặc giãn cơ 30 phút\n")
            response_parts.append("- Ngày 5: Cardio nhẹ (đi bộ/xe đạp) 45 phút\n")
            response_parts.append("- Ngày 6: Bài tập sức bền (squat, plank) 25 phút\n")
            response_parts.append("- Ngày 7: Nghỉ ngơi hoặc đi bộ nhẹ 20 phút\n")
            response_parts.append("\n**Lưu ý:** Bắt đầu từ từ, tăng cường độ dần. Uống đủ nước. Nếu có đau khớp/tim đập nhanh bất thường, dừng và khám bác sĩ.\n")
        else:  # underweight
            response_parts.append("**Mục tiêu: Tăng cân lành mạnh**\n\n")
            response_parts.append("- Ngày 1: Tập tạ nhẹ (nhóm cơ lớn) 30 phút\n")
            response_parts.append("- Ngày 2: Đi bộ nhẹ 20 phút (không cardio mạnh)\n")
            response_parts.append("- Ngày 3: Nghỉ ngơi, ưu tiên phục hồi\n")
            response_parts.append("- Ngày 4: Tập sức mạnh (bodyweight) 25 phút\n")
            response_parts.append("- Ngày 5: Yoga nhẹ 20 phút\n")
            response_parts.append("- Ngày 6: Tập tạ nhẹ 30 phút\n")
            response_parts.append("- Ngày 7: Nghỉ ngơi hoàn toàn\n")
            response_parts.append("\n**Lưu ý:** Tránh cardio mạnh (tiêu hao calo). Ưu tiên tăng cơ bắp. Ngủ đủ 8-9 giờ/đêm.\n")

        return ''.join(response_parts)
        # Dynamic 7-day mock: parse target kcal and diet from the prompt when possible
        # so different inputs produce different plans.
        # Extract target kcal (e.g., '2000 kcal')
        match = re.search(r"(\d{3,4})\s*kcal", prompt)
        try:
            target_kcal = int(match.group(1)) if match else 2000
        except Exception:
            target_kcal = 2000

        # detect simple diet keywords and BMI
        prompt_lower = prompt.lower()
        is_vegetarian = any(k in prompt_lower for k in ['chay', 'vegetarian', 'vegan'])
        # extract BMI if present
        bmi_match = re.search(r"bmi\s*[:=]?\s*(\d{1,2}(?:\.\d+)?)", prompt_lower)
        try:
            bmi_val = float(bmi_match.group(1)) if bmi_match else None
        except Exception:
            bmi_val = None

        # seed random with target so same inputs yield same plan
        random.seed(target_kcal)

        # Full 7-day mock as an HTML table so the UI can render it nicely when no API key set
        table = [
            '<table class="table table-sm table-bordered">',
            '<thead class="table-light"><tr><th>Ngày</th><th>Bữa sáng</th><th>Bữa trưa</th><th>Bữa phụ</th><th>Bữa tối</th><th>Khoảng kcal</th></tr></thead>',
            '<tbody>'
        ]
    # Define meal pools (Vietnamese-style). If vegetarian, remove meat dishes.
        breakfasts = [
            '1 bát phở gà nhỏ + 1 quả chuối',
            '1 bát bún riêu nhỏ',
            '1 chén cháo yến mạch + 1 quả chuối',
            '1 bánh mì ốp la (1 quả trứng) + rau',
            '1 chén yến mạch + sữa',
            '1 bánh cuốn nhỏ + ít nước chấm'
        ]

        lunches = [
            '1 chén cơm + 100g ức gà xào rau',
            '1 chén cơm + 100g cá nướng + rau luộc',
            '1 phở gà nhỏ (ít dầu)',
            '1 chén cơm + đậu hũ xào + rau',
            '1 chén cơm + salad cá ngừ',
            '1 chén cơm + thịt bò xào rau'
        ]

        snacks = [
            '1 hộp sữa chua', '1 quả táo + ít hạt', '1 nắm hạt điều', '1 ly sinh tố bơ nhỏ', '1 quả chuối'
        ]

        dinners = [
            '1 chén cơm + 120g cá kho + canh rau',
            '1 chén cơm + 120g gà áp chảo + canh',
            '1 chén cơm + đậu hũ xào + rau',
            '1 chén cơm + cá nướng + rau',
            '1 phần mỳ Ý nhỏ (ít sốt) + salad',
            '1 chén cơm + cá quay + rau'
        ]

        if is_vegetarian:
            # Replace lunches/dinners with vegetarian options
            lunches = [l.replace('ức gà', 'đậu hũ').replace('cá', 'đậu hũ').replace('thịt bò', 'rau') for l in lunches]
            dinners = [d.replace('cá', 'đậu hũ').replace('gà', 'đậu hũ').replace('thịt', 'rau') for d in dinners]

        # Adjust pools by BMI: overweight -> smaller carb portions and more protein/veg;
        # underweight -> include more energy-dense options
        if bmi_val is not None:
            if bmi_val >= 25:
                # reduce rice portions wording, prefer grilled/steamed, add salads
                lunches = [s.replace('1 chén cơm', '1/2 chén cơm').replace('gà', 'ức gà').replace('cá', 'cá nướng') for s in lunches]
                dinners = [s.replace('1 chén cơm', '1/2 chén cơm') for s in dinners]
                breakfasts = [s.replace('1 chén cháo', '1 bát cháo nhỏ').replace('bánh mì', 'bánh mì nguyên cám nhỏ') for s in breakfasts]
            elif bmi_val < 18.5:
                # increase portions slightly, add energy-dense foods
                lunches = [s.replace('1 chén cơm', '1.5 chén cơm').replace('100g', '150g') for s in lunches]
                dinners = [s.replace('1 chén cơm', '1.5 chén cơm') for s in dinners]
                breakfasts = [s + ' + 1 ly sữa' if 'sữa' not in s else s for s in breakfasts]

        # Build 7-day plan by sampling without replacement where possible
        days = []
        for i in range(7):
            b = random.choice(breakfasts)
            l = random.choice(lunches)
            s = random.choice(snacks)
            d = random.choice(dinners)
            # approximate base kcal per day (rough heuristic)
            base_kcal = 400 + 600 + 150 + 800  # breakfast + lunch + snack + dinner
            # scale to target_kcal
            scale = target_kcal / base_kcal if base_kcal > 0 else 1.0
            approx_kcal = int(base_kcal * scale)
            days.append((i+1, b, l, s, d, f'~{approx_kcal}'))

        for d in days:
            table.append(f'<tr><td>Ngày {d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td><td>{d[5]}</td></tr>')

        table.append('</tbody></table>')

        shopping = '<h5>Danh sách mua sắm gợi ý</h5><ul>'
        shopping_items = [
            'gạo/ cơm', 'bún/ phở', 'yến mạch', 'chuối', 'trứng', 'ức gà',
            'cá', 'đậu hũ', 'rau xanh', 'sữa chua', 'hạt', 'khoai lang', 'dầu ăn', 'gia vị'
        ]
        if is_vegetarian:
            # prefer plant items
            shopping_items = [it for it in shopping_items if it not in ('ức gà','cá')]
        for it in shopping_items:
            shopping += f'<li>{it}</li>'
        shopping += '</ul>'

        note = '<p class="text-muted">Lưu ý: Đây là kế hoạch mẫu. Điều chỉnh khẩu phần theo nhu cầu calo mục tiêu.</p>'

        # Simple exercise suggestions based on BMI & goal
        exercise = ''
        if bmi_val is None:
            exercise = '<p>Gợi ý luyện tập nhẹ: đi bộ 20-30 phút mỗi ngày, yoga 2 lần/tuần.</p>'
        else:
            if bmi_val >= 25:
                exercise = '<h5>Gợi ý luyện tập (giảm cân)</h5><ul><li>Đi bộ nhanh 30-45 phút, 5 lần/tuần</li><li>Yoga/giãn cơ 2-3 lần/tuần</li><li>Bài tập sức bền nhẹ (tạ nhẹ) 2 lần/tuần</li></ul>'
            elif bmi_val < 18.5:
                exercise = '<h5>Gợi ý luyện tập (tăng cân)</h5><ul><li>Bài tập sức mạnh nhẹ (tạ, bodyweight) 3 lần/tuần</li><li>Đi bộ ngắn 20 phút để duy trì sức khỏe</li><li>Tăng cường phục hồi và ngủ đủ giấc</li></ul>'
            else:
                exercise = '<h5>Gợi ý luyện tập (duy trì)</h5><ul><li>Cardio nhẹ: chạy bộ/đi bộ 30 phút, 3-4 lần/tuần</li><li>Yoga/giãn cơ 2 lần/tuần</li><li>Thực hiện bài tập sức mạnh 2 lần/tuần</li></ul>'

        # Add BMI analysis/warnings
        analysis = ''
        if bmi_val is None:
            analysis = '<p>Không có thông tin BMI rõ ràng để phân tích.</p>'
        else:
            if bmi_val < 16:
                analysis = '<h5 class="text-danger">Cảnh báo: BMI rất thấp (gầy mức độ nghiêm trọng)</h5><p>Nguy cơ suy dinh dưỡng nặng, giảm miễn dịch, loãng xương. Khuyến nghị: khám bác sĩ/điều dưỡng, tăng calo an toàn, theo dõi y tế.</p>'
            elif bmi_val < 18.5:
                analysis = '<h5 class="text-warning">Cảnh báo: BMI thấp</h5><p>Nguy cơ thiếu hụt dinh dưỡng, mệt mỏi. Khuyến nghị: tăng khẩu phần, ưu tiên thực phẩm giàu năng lượng và protein.</p>'
            elif bmi_val >= 30:
                analysis = '<h5 class="text-danger">Cảnh báo: Béo phì (BMI cao)</h5><p>Nguy cơ cao bệnh tim mạch, tiểu đường type 2, huyết áp. Khuyến nghị: tham vấn bác sĩ chuyên khoa và giảm dần calo an toàn; kết hợp vận động.</p>'
            elif bmi_val >= 25:
                analysis = '<h5 class="text-warning">Cảnh báo: Thừa cân</h5><p>Tăng nguy cơ tim mạch và chuyển hóa. Khuyến nghị: giảm calo vừa phải, tăng hoạt động thể chất.</p>'
            else:
                analysis = '<p>BMI trong ngưỡng bình thường. Duy trì chế độ ăn cân bằng và hoạt động thể chất đều đặn.</p>'

        content = '<div>' + '\n'.join(table) + shopping + exercise + note + '</div>'
        # Return combined HTML with analysis separated (client._format_response expects a text string)
        # We'll return content + a marker + analysis so _format_response can display both when using mock.
        return content + '\n\n<!--BMI_ANALYSIS_START-->' + analysis + '<!--BMI_ANALYSIS_END-->'
