import os
import re

template_dir = r"c:\Users\Hp\Desktop\Demo2\templates"

light_theme = {
    "--bg-dark": "#fafbfc",
    "--bg-card": "#ffffff",
    "--bg-sidebar": "#ffffff",
    "--panel": "#ffffff",
    "--panel-border": "#e5e7eb",
    "--accent-blue": "#7c3aed",
    "--accent-strong": "#6d28d9",
    "--accent-green": "#059669",
    "--accent-red": "#dc2626",
    "--danger": "#dc2626",
    "--text-main": "#111827",
    "--text": "#111827",
    "--text-muted": "#4b5563",
    "--muted": "#4b5563",
    "--border-color": "#e5e7eb",
    "--panel-bg": "#ffffff",
    "--blue": "#7c3aed",
    "--green": "#059669",
    "--gold": "#f59e0b"
}

def process_file(filename):
    filepath = os.path.join(template_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace variable definitions
    for var, val in light_theme.items():
        content = re.sub(rf"({var}:\s*)[^;]+;", rf"\1{val};", content)
    
    # Replace background in body
    # Specifically for user_auth
    content = re.sub(
        r"background:\s*radial-gradient[^;]+linear-gradient[^;]+;", 
        "background: linear-gradient(135deg, #fafbfc 0%, #f3f4f6 100%);",
        content, flags=re.DOTALL
    )
    # Other files body background
    content = re.sub(
        r"background:\s*linear-gradient\(135deg,\s*#f5f3ff\s*0%,\s*#ede9fe\s*[0-9]+%,\s*#f0fdf4\s*100%\);",
        "background: linear-gradient(135deg, #fafbfc 0%, #f3f4f6 100%);",
        content
    )
    # Other files body background (about.html has 50%)
    content = re.sub(
        r"background:\s*linear-gradient\(135deg,\s*#f5f3ff\s*0%,\s*#ede9fe\s*50%,\s*#f0fdf4\s*100%\);",
        "background: linear-gradient(135deg, #fafbfc 0%, #f3f4f6 100%);",
        content
    )
    
    # Replace color gradients for specific things in user_auth
    content = re.sub(
        r"background:\s*linear-gradient\(180deg,\s*rgba\(14, 165, 233, 0\.1\),\s*rgba\(37, 99, 235, 0\.05\)\),\s*rgba\(255, 255, 255, 0\.02\);",
        "background: linear-gradient(135deg, rgba(237, 233, 254, 0.4) 0%, rgba(245, 243, 255, 0.6) 100%);",
        content
    )
    
    # Replace auth-shell background and colors
    content = re.sub(
        r"\.auth-shell\s*\{[^}]*background:\s*rgba\(255, 255, 255, 0\.04\);[^}]*\}",
        ".auth-shell { width: 100%; max-width: 1120px; display: grid; grid-template-columns: 1.08fr 0.92fr; background: #ffffff; border-radius: 28px; overflow: hidden; box-shadow: 0 20px 48px rgba(0, 0, 0, 0.15); }",
        content
    )
    
    # Fix dark cards in user_auth
    content = re.sub(r"background:\s*rgba\(255, 255, 255, 0\.04\);", "background: #f9fafb;", content)
    content = re.sub(r"border:\s*1px solid rgba\(255, 255, 255, 0\.08\);", "border: 1px solid #e5e7eb;", content)
    content = re.sub(r"background:\s*rgba\(0, 0, 0, 0\.2\);", "background: #ffffff;", content)
    content = re.sub(r"color:\s*#cbd5e1;", "color: #111827;", content) # form labels

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Processed {filename}")

files = [
    "about.html", "account.html", "admin.html", "admin_questions.html", 
    "index.html", "quiz_results.html", "quiz_take.html", "quiz_topics.html", "user_auth.html"
]

for f in files:
    process_file(f)
