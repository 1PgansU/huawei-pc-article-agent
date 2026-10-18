import zipfile
import os
import sys

src = r'c:\Users\phobi\Desktop\华为赛题\handoff-完整方案包.zip'
dst = r'c:\Users\phobi\Desktop\华为赛题\handoff-extracted'
os.makedirs(dst, exist_ok=True)

with zipfile.ZipFile(src, 'r') as z:
    for info in z.infolist():
        try:
            # Use cp437 -> utf-8 fallback
            name = info.filename
            try:
                name = name.encode('cp437').decode('utf-8')
            except Exception:
                pass
            print('Extracting:', name, info.file_size)
            target = os.path.join(dst, name)
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(info) as src_f, open(target, 'wb') as out_f:
                    out_f.write(src_f.read())
        except Exception as e:
            print('ERROR with', info.filename, ':', e)
            sys.stdout.flush()

print('Done.')