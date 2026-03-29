import os
import re

dir_path = 'c:/Users/saksh/Desktop/Odoo/frontend'
img_tag = '<img src="assetslogo.jpeg" alt="FlowFund Logo" style="width: 100%; height: 100%; object-fit: cover; border-radius: inherit;">'
span_img_tag = '<img src="assetslogo.jpeg" alt="FlowFund Logo" style="width: 28px; height: 28px; object-fit: cover; border-radius: 6px;">'

for filename in os.listdir(dir_path):
    if not filename.endswith('.html'):
        continue
    
    file_path = os.path.join(dir_path, filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if filename == 'login.html':
        content = re.sub(r'<img src="assetslogo\.JPEG" alt="Logo">', img_tag, content)
        content = content.replace('💸', img_tag)
    else:
        content = content.replace('<span style="font-size:1.5rem;">💸</span>', f'<span style="display:flex; align-items:center;">{span_img_tag}</span>')
        content = content.replace('💸', img_tag)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Replacements complete.")
