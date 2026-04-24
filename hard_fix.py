import os

def fix_file(filename, title):
    path = os.path.join('templates', filename)
    if not os.path.exists(path): return
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    body_start = content.find('<body')
    if body_start == -1: return
    
    new_head = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - LingoCards Admin</title>
    {{% include '_admin_styles.html' %}}
    {{% include '_head_fonts.html' %}}
    <style>
        .content-scroll {{ flex: 1; overflow-y: auto; padding: 1.5rem 1.75rem; }}
        .card-panel {{ background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-md); padding: 1.5rem; margin-bottom: 1.25rem; box-shadow: var(--shadow-sm); }}
        .panel-title {{ font-size: 1rem; font-weight: 800; margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.6rem; }}
        
        /* Modal & UI */
        .modal-backdrop {{ position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: none; align-items: center; justify-content: center; z-index: 1000; }}
        .modal-backdrop.active {{ display: flex; }}
        .modal {{ background: white; border-radius: 16px; width: 90%; max-width: 600px; padding: 2rem; }}
    </style>
</head>
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_head + content[body_start:])
    print(f'Fixed {filename}')

fix_file('admin_questions.html', 'Quản lý câu hỏi')
fix_file('admin_grammar.html', 'Quản lý ngữ pháp')
fix_file('admin_accounts.html', 'Quản lý tài khoản')
