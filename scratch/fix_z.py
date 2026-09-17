import pathlib
p = pathlib.Path('app.py')
text = p.read_text(encoding='utf-8')
text = text.replace(".isoformat() + 'Z'", ".isoformat()")
p.write_text(text, encoding='utf-8')
