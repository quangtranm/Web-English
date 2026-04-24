import os
import re

template_dir = r"c:\Users\Hp\Desktop\Demo2\templates"

def process_shadows(filename):
    filepath = os.path.join(template_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace blue shadows rgba(37, 99, 235, ...) or rgba(14, 165, 233, ...) or rgba(56, 189, 248...)
    content = re.sub(r"rgba\(37,\s*99,\s*235,\s*([0-9\.]+)\)", r"rgba(109, 40, 217, \1)", content)
    content = re.sub(r"rgba\(14,\s*165,\s*233,\s*([0-9\.]+)\)", r"rgba(109, 40, 217, \1)", content)
    content = re.sub(r"rgba\(56,\s*189,\s*248,\s*([0-9\.]+)\)", r"rgba(109, 40, 217, \1)", content)
    content = re.sub(r"rgba\(139,\s*92,\s*246,\s*([0-9\.]+)\)", r"rgba(109, 40, 217, \1)", content)
    
    # We also might have `#f8fafc` instead of white, or `#7dd3fc` text.
    # In user_auth.html: `color: #7dd3fc;` -> `color: #6d28d9;`
    content = re.sub(r"color:\s*#7dd3fc;", "color: #6d28d9;", content)
    content = re.sub(r"color:\s*#38bdf8;", "color: #7c3aed;", content)
    
    # Clean up any leftover gradient for body from index.html that might have had hardcoded colors
    content = re.sub(
        r"background:\s*linear-gradient\(135deg,\s*#c4b5fd,\s*#8b5cf6\);",
        "background: linear-gradient(135deg, #a78bfa, #7c3aed);", 
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

files = [
    "about.html", "account.html", "admin.html", "admin_questions.html", 
    "index.html", "quiz_results.html", "quiz_take.html", "quiz_topics.html", "user_auth.html"
]

for f in files:
    process_shadows(f)

print("Shadows and leftovers patched.")
