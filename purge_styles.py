import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(BASE, 'templates')

def purge_redundant_styles():
    admin_files = ['admin_questions.html', 'admin_grammar.html', 'admin_accounts.html']
    
    for filename in admin_files:
        path = os.path.join(TEMPLATES, filename)
        if not os.path.exists(path): continue
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Remove @supports block and body animations that might hide the page
        content = re.sub(r'@supports not \(view-transition-name: none\)\s*{.*?}', '', content, flags=re.DOTALL)
        content = re.sub(r'body\s*{[^}]*animation:[^}]*}', '', content, flags=re.DOTALL)
        
        # 2. Remove redundant sidebar/topbar/btn styles that are now in _admin_styles.html
        redundant_patterns = [
            r'/\* ═══════ SIDEBAR ═══════ \*/.*?/\*',
            r'\.sidebar.*?{.*?}',
            r'\.sidebar-.*?{.*?}',
            r'\.top-bar.*?{.*?}',
            r'\.topbar.*?{.*?}',
            r'\.btn.*?{.*?}',
            r'\.logout-link.*?{.*?}',
            r'\.main-container.*?{.*?}',
            r'\.main\s*{.*?}'
        ]
        
        # Clean up common Sidebar styles that are usually at the top
        content = re.sub(r'/\* ═══════ SIDEBAR ═══════ \*/.*?(\n\s*\n)', '\n', content, flags=re.DOTALL)
        
        # 3. Fix potential body visibility issues
        content = re.sub(r'body\s*{[^}]*opacity:[^}]*}', '', content, flags=re.DOTALL)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[Purge] Cleaned up {filename}')

if __name__ == '__main__':
    purge_redundant_styles()
