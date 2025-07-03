import os
from bs4 import BeautifulSoup

# Directories
mn_dir = '../data/tipitaka/mn'
out_dir = '../data/texts/tripitaka/mn'

# Ensure output directory exists
os.makedirs(out_dir, exist_ok=True)

# Iterate through all files in mn_dir
for filename in os.listdir(mn_dir):
    if filename.endswith('.html'):
        in_path = os.path.join(mn_dir, filename)
        out_path = os.path.join(out_dir, os.path.splitext(filename)[0] + '.txt')
        with open(in_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            chapter_div = soup.find('div', class_='chapter')
            if chapter_div:
                text = chapter_div.get_text(separator='\n', strip=True)
                with open(out_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(text)
            else:
                # If no chapter div, write a note or skip
                with open(out_path, 'w', encoding='utf-8') as out_f:
                    out_f.write('[No <div class="chapter"> found]') 