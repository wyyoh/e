from common import *
import openpyxl
from zipfile import ZipFile
from xml.etree import ElementTree as ET

def main():
    d=inputs()
    for k in ['types','nodes']:print(k,json.dumps(d[k],ensure_ascii=False,indent=2))
    print('box',list(d['boxes'].values())[:3])
    raw=ROOT/'data/raw'
    for path in raw.glob('*.xlsx'):
        w=openpyxl.load_workbook(path,read_only=True,data_only=True)
        print(path.name)
        for s in w:
            print(s.title,list(s.values)[:35])
        w.close()
    with ZipFile(next(raw.glob('*.docx'))) as z:
        x=ET.fromstring(z.read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    ps=[''.join(p.itertext()) for p in x.findall('.//w:p',ns)]
    text='\n'.join(ps)
    (ROOT/'data/problem_text.txt').write_text(text,encoding='utf-8')
    print(text)
if __name__=='__main__':main()
