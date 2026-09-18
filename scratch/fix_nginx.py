with open('/etc/nginx/sites-available/ffmotors', 'r') as f:
    text = f.read()
text = text.replace('add_header Cache-Control " public no-transform;\n }', 'add_header Cache-Control "public, no-transform";\n    }')
with open('/etc/nginx/sites-available/ffmotors', 'w') as f:
    f.write(text)
