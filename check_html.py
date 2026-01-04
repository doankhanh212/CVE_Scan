with open('web/templates/settings.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check lines around button areas
print("=== Lines 50-65 (toggleApiKey area) ===")
for i in range(49, min(65, len(lines))):
    line_num = i + 1
    print(f"{line_num:3d}: {lines[i]}", end='')

print("\n\n=== Lines 100-115 (browseDb area) ===")
for i in range(99, min(115, len(lines))):
    line_num = i + 1
    print(f"{line_num:3d}: {lines[i]}", end='')

# Check if all button tags are closed
print("\n\n=== Button Tag Validation ===")
import re
button_opens = re.findall(r'<button[^>]*id="([^"]*)"[^>]*>', ''.join(lines))
button_closes = len(re.findall(r'</button>', ''.join(lines)))
print(f"Opened buttons: {len(button_opens)} - {button_opens}")
print(f"Closed buttons: {button_closes}")
if len(button_opens) == button_closes:
    print("✓ All buttons properly closed")
else:
    print("✗ Button count mismatch!")
