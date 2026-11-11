"""Build the current requirement reading page from its sole Markdown source."""
from pathlib import Path
import hashlib
import sys
import markdown
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'docs/governance'))
from paths import root_links_to_relative
SOURCE = ROOT / 'docs/requirements/REQUIREMENTS.md'
TARGET = SOURCE.with_suffix('.html')
ASSETS = SOURCE.parent / 'assets'
text = SOURCE.read_text(encoding='utf-8')
body = BeautifulSoup(markdown.markdown(text, extensions=['tables', 'fenced_code', 'sane_lists']), 'html.parser')
page = BeautifulSoup((ASSETS / 'reader.tmpl').read_text(encoding='utf-8'), 'html.parser')
page.style.string = (ASSETS / 'reader.css').read_text(encoding='utf-8')
toc, select = page.select_one('nav.toc'), page.select_one('#jump')
for i, heading in enumerate(body.find_all('h2'), 1):
    heading['id'] = f'section-{i:02d}'
    link = page.new_tag('a', href='#' + heading['id']); link.string = heading.get_text(); toc.append(link)
    option = page.new_tag('option', value='#' + heading['id']); option.string = heading.get_text(); select.append(option)
for table in list(body.find_all('table')):
    table.wrap(body.new_tag('div', attrs={'class': 'table-scroll', 'tabindex': '0', 'role': 'region', 'aria-label': '需求表格，可横向滚动'}))
main = page.select_one('main')
for node in list(body.contents):main.append(node)
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
page.find('meta', attrs={'name': 'source-sha256'})['content'] = source_hash
script = page.new_tag('script'); script.string = (ASSETS / 'reader.js').read_text(encoding='utf-8'); page.body.append(script)
document = root_links_to_relative(str(page), TARGET)
TARGET.write_bytes(document.encode('utf-8'))
assert len(main.find_all('h2')) == 16
print('Built REQUIREMENTS.html: 16 source sections; no remote runtime.')
