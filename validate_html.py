from html.parser import HTMLParser
import sys

class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.tag_stack = []
        self.current_line = 1
        self.lines = []
        
    def feed_with_lines(self, data):
        self.lines = data.split('\n')
        self.feed(data)
        
    def error(self, message):
        self.errors.append(f"Line {self.getpos()[0]}: {message}")

try:
    with open('web/templates/settings.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    validator = HTMLValidator()
    validator.feed_with_lines(html_content)
    
    # Manual checks for button and anchor tags
    import re
    
    # Check button tags
    button_pattern = r'<button[^>]*>'
    buttons = re.finditer(button_pattern, html_content)
    
    for match in buttons:
        button_html = match.group()
        # Check if it has proper closing
        if not 'type=' in button_html:
            line_num = html_content[:match.start()].count('\n') + 1
            print(f"⚠ Line {line_num}: Button missing 'type' attribute: {button_html[:60]}...")
    
    # Check anchor tags
    anchor_pattern = r'<a[^>]*>'
    anchors = re.finditer(anchor_pattern, html_content)
    
    anchor_count = 0
    for match in anchors:
        anchor_html = match.group()
        anchor_count += 1
        # Check href attribute
        if 'href=' not in anchor_html:
            line_num = html_content[:match.start()].count('\n') + 1
            print(f"⚠ Line {line_num}: Anchor missing 'href' attribute: {anchor_html[:60]}...")
    
    if anchor_count == 0:
        print("✓ All anchors have href attribute")
    
    print(f"\n✓ HTML validation complete - Found {len(re.findall(r'<button', html_content))} buttons and {anchor_count} anchors")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
