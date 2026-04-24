import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(BASE, 'templates')

def final_template_cleanup():
    files = {
        'admin.html': 'Quản lý từ vựng',
        'admin_questions.html': 'Quản lý câu hỏi',
        'admin_grammar.html': 'Quản lý ngữ pháp',
        'admin_accounts.html': 'Quản lý tài khoản'
    }
    
    for filename, title in files.items():
        path = os.path.join(TEMPLATES, filename)
        if not os.path.exists(path): continue
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Standardize Head
        head_match = re.search(r'<head>.*?</head>', content, flags=re.DOTALL)
        if head_match:
            new_head = f"""<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - LingoCards Admin</title>
    {{% include '_admin_styles.html' %}}
    {{% include '_head_fonts.html' %}}
</head>"""
            content = content.replace(head_match.group(0), new_head)
            
        # 2. Cleanup redundant style/class usage if any
        # (The shared CSS now handles most of it)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[Cleanup] Standardized head for {filename}')

if __name__ == '__main__':
    final_template_cleanup()
