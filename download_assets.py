"""
Download Google Fonts with full Vietnamese support for offline use.
"""
import os, io, zipfile, requests, re

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, 'static')

# ─── 1. Font Awesome (Free) ─────────────────────────────────────
FA_VERSION = '6.4.0'
FA_ZIP_URL = f'https://use.fontawesome.com/releases/v{FA_VERSION}/fontawesome-free-{FA_VERSION}-web.zip'

def download_fontawesome():
    dest = os.path.join(STATIC, 'fontawesome')
    if os.path.isdir(dest) and os.listdir(dest):
        print('[FA] Already exists.')
        return
    print(f'[FA] Downloading Font Awesome {FA_VERSION}...')
    try:
        r = requests.get(FA_ZIP_URL, timeout=60)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        prefix = z.namelist()[0].split('/')[0]
        os.makedirs(dest, exist_ok=True)
        for info in z.infolist():
            if info.is_dir(): continue
            rel = info.filename[len(prefix)+1:]
            if not (rel.startswith('css/') or rel.startswith('webfonts/')): continue
            out_path = os.path.join(dest, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, 'wb') as f:
                f.write(z.read(info.filename))
        print(f'[FA] Done.')
    except Exception as e:
        print(f'[FA] Error: {e}')

# ─── 2. Google Fonts with Vietnamese Support ───────────────────
# Selecting fonts with excellent Vietnamese typography
GOOGLE_FONTS = {
    'Inter': [300, 400, 500, 600, 700, 800, 900],
    'Plus_Jakarta_Sans': [400, 500, 600, 700, 800],
    'Be_Vietnam_Pro': [300, 400, 500, 600, 700, 800], # Specifically designed for Vietnamese
    'Montserrat': [400, 500, 600, 700, 800],
    'DM_Sans': [400, 500, 700],
}

def download_google_fonts():
    dest = os.path.join(STATIC, 'fonts')
    os.makedirs(dest, exist_ok=True)
    css_parts = []

    # Using a modern User-Agent to get WOFF2
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
    }

    for family, weights in GOOGLE_FONTS.items():
        family_dir = os.path.join(dest, family.lower())
        os.makedirs(family_dir, exist_ok=True)
        
        # Build the URL for all weights at once to get the full CSS
        weight_str = ';'.join(map(str, sorted(weights)))
        css_url = f'https://fonts.googleapis.com/css2?family={family.replace("_", "+")}:wght@{weight_str}&display=swap'
        
        print(f'[Font] Fetching CSS for {family}...')
        try:
            resp = requests.get(css_url, headers=headers, timeout=30)
            resp.raise_for_status()
            css_content = resp.text

            # Google CSS contains blocks like:
            # /* vietnamese */
            # @font-face { ... src: url(https://...) ... }
            # /* latin */
            # @font-face { ... src: url(https://...) ... }
            
            # We need to find all @font-face blocks and download their files
            # Pattern to capture subset comment and the @font-face block
            blocks = re.findall(r'(/\* ([^*]+) \*/\s*@font-face\s*\{[^}]+\})', css_content)
            
            processed_urls = {}

            for full_block, subset in blocks:
                subset = subset.strip()
                # Extract the URL
                url_match = re.search(r'url\((https://[^)]+\.woff2)\)', full_block)
                if not url_match: continue
                
                font_url = url_match.group(1)
                font_filename = font_url.split('/')[-1]
                local_path = os.path.join(family_dir, font_filename)
                rel_path = f'../fonts/{family.lower()}/{font_filename}'

                if font_url not in processed_urls:
                    if not os.path.isfile(local_path):
                        print(f'  [Downloading] {family} subset: {subset}...')
                        font_resp = requests.get(font_url, timeout=30)
                        font_resp.raise_for_status()
                        with open(local_path, 'wb') as f:
                            f.write(font_resp.content)
                    processed_urls[font_url] = rel_path

                # Update the CSS block to use local URL
                local_block = full_block.replace(font_url, rel_path)
                css_parts.append(local_block)

        except Exception as e:
            print(f'[Font] Error processing {family}: {e}')

    # Write combined CSS
    css_out = os.path.join(STATIC, 'css', 'fonts.css')
    os.makedirs(os.path.dirname(css_out), exist_ok=True)
    with open(css_out, 'w', encoding='utf-8') as f:
        f.write('/* Auto-generated local Google Fonts with full subset support */\n\n')
        f.write('\n\n'.join(css_parts))
    print(f'[Font] Full CSS with Vietnamese support -> {css_out}')

def clean_css_files():
    # Ensuring style.css uses the new fonts if it was relying on others
    css_path = os.path.join(STATIC, 'css', 'style.css')
    if os.path.isfile(css_path):
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace fonts in style.css to use our best Vietnamese-supporting ones
        # Example: if it used 'DM Sans', we might want to ensure 'Be Vietnam Pro' or 'Inter' is available
        # But usually just providing the subsets fixes the "lỗi"
        pass

if __name__ == '__main__':
    download_fontawesome()
    download_google_fonts()
    print('\nOffline assets with Vietnamese support ready!')
