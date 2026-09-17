import pathlib
p = pathlib.Path('database.py')
text = p.read_text(encoding='utf-8')
text = text.replace(r"\'Europe/London\'", "'Europe/London'")
p.write_text(text, encoding='utf-8')
