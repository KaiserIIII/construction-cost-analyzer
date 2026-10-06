"""Small, deterministic macro-free Open XML report writer (stdlib only)."""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
import io
import math
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

MAIN='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PACKAGE='http://schemas.openxmlformats.org/package/2006/relationships'
ET.register_namespace('',MAIN)
ET.register_namespace('r',REL)


def clean_text(value):
    """Keep XML 1.0 legal Unicode; JSON companions retain original input text."""
    return ''.join(c for c in str(value) if ord(c) in (9,10,13) or 32<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff)


def column(index):
    result=''
    while index:
        index,rem=divmod(index-1,26);result=chr(65+rem)+result
    return result


@dataclass(frozen=True)
class Formula:
    expression: str
    cached: float


@dataclass(frozen=True)
class Cell:
    value: object
    style: int=0


@dataclass
class Sheet:
    name: str
    rows: list
    headers: list=field(default_factory=lambda:[4])
    filter_end: int=0


def deterministic_zip(members):
    stream=io.BytesIO()
    with ZipFile(stream,'w',compression=ZIP_DEFLATED) as archive:
        for name,content in members.items():
            info=ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=ZIP_DEFLATED
            info.external_attr=0o600<<16
            archive.writestr(info,content.encode('utf-8') if isinstance(content,str) else content)
    return stream.getvalue()


def xml_bytes(root):
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def tag(name):return '{'+MAIN+'}'+name


def styles():
    root=ET.Element(tag('styleSheet'))
    formats=ET.SubElement(root,tag('numFmts'),count='4')
    for identifier,code in [(164,'#,##0.######;(#,##0.######);0'),(165,'#,##0.00;(#,##0.00);0.00'),(166,'0.00%;(0.00%);0.00%'),(167,'yyyy-mm-dd')]:
        ET.SubElement(formats,tag('numFmt'),numFmtId=str(identifier),formatCode=code)
    fonts=ET.SubElement(root,tag('fonts'),count='4')
    for size,color,bold in [(10,'FF243746',False),(10,'FFFFFFFF',True),(14,'FF243746',True),(10,'FF526572',False)]:
        font=ET.SubElement(fonts,tag('font'));ET.SubElement(font,tag('sz'),val=str(size));ET.SubElement(font,tag('name'),val='Arial');ET.SubElement(font,tag('color'),rgb=color)
        if bold:ET.SubElement(font,tag('b'))
    fills=ET.SubElement(root,tag('fills'),count='3')
    for pattern,color in [('none',None),('gray125',None),('solid','FF243746')]:
        fill=ET.SubElement(fills,tag('fill'));p=ET.SubElement(fill,tag('patternFill'),patternType=pattern)
        if color:ET.SubElement(p,tag('fgColor'),rgb=color);ET.SubElement(p,tag('bgColor'),indexed='64')
    borders=ET.SubElement(root,tag('borders'),count='1');b=ET.SubElement(borders,tag('border'))
    for part in ('left','right','top','bottom','diagonal'):ET.SubElement(b,tag(part))
    base=ET.SubElement(root,tag('cellStyleXfs'),count='1');ET.SubElement(base,tag('xf'),numFmtId='0',fontId='0',fillId='0',borderId='0')
    xfs=ET.SubElement(root,tag('cellXfs'),count='9')
    for num,font,fill,align,wrap in [(0,0,0,'left',True),(0,1,2,'center',True),(164,0,0,'right',False),(165,0,0,'right',False),(166,0,0,'right',False),(167,0,0,'right',False),(0,2,0,'left',False),(0,3,0,'left',True),(165,0,0,'right',False)]:
        xf=ET.SubElement(xfs,tag('xf'),numFmtId=str(num),fontId=str(font),fillId=str(fill),borderId='0',xfId='0',applyNumberFormat='1',applyAlignment='1')
        ET.SubElement(xf,tag('alignment'),horizontal=align,vertical='center',wrapText='1' if wrap else '0')
    cs=ET.SubElement(root,tag('cellStyles'),count='1');ET.SubElement(cs,tag('cellStyle'),name='Normal',xfId='0',builtinId='0')
    return xml_bytes(root)


def worksheet(sheet):
    root=ET.Element(tag('worksheet'));ncols=max((len(r) for r in sheet.rows),default=1)
    ET.SubElement(root,tag('dimension'),ref=f'A1:{column(ncols)}{len(sheet.rows)}')
    views=ET.SubElement(root,tag('sheetViews'));view=ET.SubElement(views,tag('sheetView'),workbookViewId='0',showGridLines='0')
    header=sheet.headers[0]
    ET.SubElement(view,tag('pane'),xSplit='1',ySplit=str(header),topLeftCell=f'B{header+1}',activePane='bottomRight',state='frozen')
    ET.SubElement(root,tag('sheetFormatPr'),defaultRowHeight='18')
    cols=ET.SubElement(root,tag('cols'));widths=[]
    for j in range(ncols):
        values=[r[j] for r in sheet.rows[header-1:] if len(r)>j]
        lengths=[max(map(len,clean_text(v.value if isinstance(v,Cell) else v).split('\n'))) for v in values if not isinstance(v,Formula)]
        width=min(42,max(14,max(lengths,default=12)+2))
        widths.append(width)
        ET.SubElement(cols,tag('col'),min=str(j+1),max=str(j+1),width=str(width),customWidth='1')
    data=ET.SubElement(root,tag('sheetData'))
    for i,values in enumerate(sheet.rows,1):
        height=42 if i in sheet.headers else 28 if i==2 else 54 if i==3 else 24
        if i>=4:
            lines=1
            for j,v in enumerate(values):
                if isinstance(v,Cell):v=v.value
                if not isinstance(v,str):continue
                wrapped=sum(max(1,math.ceil(sum(2 if ord(c)>255 else 1 for c in part)/max(8,widths[j]-2))) for part in clean_text(v).split('\n'))
                lines=max(lines,wrapped)
            height=max(height,min(180,lines*15+6))
        row=ET.SubElement(data,tag('row'),r=str(i),ht=str(height),customHeight='1')
        for j,value in enumerate(values,1):
            style=0
            if isinstance(value,Cell):style=value.style;value=value.value
            if i in sheet.headers:style=1
            if value is None:continue
            attrs={'r':f'{column(j)}{i}','s':str(style)}
            if isinstance(value,Formula):
                cell=ET.SubElement(row,tag('c'),attrs);ET.SubElement(cell,tag('f')).text=value.expression;ET.SubElement(cell,tag('v')).text=str(value.cached)
            elif isinstance(value,bool):
                cell=ET.SubElement(row,tag('c'),{**attrs,'t':'b'});ET.SubElement(cell,tag('v')).text='1' if value else '0'
            elif isinstance(value,(int,float,Decimal)):
                if not math.isfinite(value):raise ValueError('Report numeric values must be finite')
                cell=ET.SubElement(row,tag('c'),attrs);ET.SubElement(cell,tag('v')).text=str(value)
            elif isinstance(value,(datetime,date)):
                d=value.date() if isinstance(value,datetime) else value
                base=date(1899,12,30) if d>=date(1900,3,1) else date(1899,12,31)
                cell=ET.SubElement(row,tag('c'),{**attrs,'s':'5'});ET.SubElement(cell,tag('v')).text=str((d-base).days)
            else:
                cell=ET.SubElement(row,tag('c'),{**attrs,'t':'inlineStr'});inline=ET.SubElement(cell,tag('is'));ET.SubElement(inline,tag('t'),{'{http://www.w3.org/XML/1998/namespace}space':'preserve'}).text=clean_text(value)
    if sheet.filter_end>=header:ET.SubElement(root,tag('autoFilter'),ref=f'A{header}:{column(ncols)}{sheet.filter_end}')
    if ncols>1:
        merges=ET.SubElement(root,tag('mergeCells'),count='2')
        for r in (2,3):ET.SubElement(merges,tag('mergeCell'),ref=f'A{r}:{column(ncols)}{r}')
    if sheet.name=='Checks' and len(sheet.rows)>4:
        cf=ET.SubElement(root,tag('conditionalFormatting'),sqref=f'E5:E{len(sheet.rows)}')
        rule=ET.SubElement(cf,tag('cfRule'),type='expression',priority='1',dxfId='0');ET.SubElement(rule,tag('formula')).text='ABS(E5)>F5'
    ET.SubElement(root,tag('printOptions'),horizontalCentered='0')
    ET.SubElement(root,tag('pageMargins'),left='0.25',right='0.25',top='0.4',bottom='0.4',header='0.2',footer='0.2')
    ET.SubElement(root,tag('pageSetup'),paperSize='9',orientation='landscape' if ncols>6 else 'portrait',fitToWidth='1',fitToHeight='0')
    # fitToPage is an explicit worksheet property, separate from pageSetup.
    props=ET.Element(tag('sheetPr'));ET.SubElement(props,tag('pageSetUpPr'),fitToPage='1');root.insert(0,props)
    return xml_bytes(root)


def workbook_bytes(sheets):
    content=ET.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
    ET.SubElement(content,'Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
    ET.SubElement(content,'Default',Extension='xml',ContentType='application/xml')
    for part,kind in [('workbook','sheet.main'),('styles','styles')]:ET.SubElement(content,'Override',PartName=f'/xl/{part}.xml',ContentType=f'application/vnd.openxmlformats-officedocument.spreadsheetml.{kind}+xml')
    root=ET.Element(tag('workbook'));group=ET.SubElement(root,tag('sheets'))
    rels=ET.Element('Relationships',xmlns=PACKAGE)
    defined=ET.SubElement(root,tag('definedNames'))
    for i,sheet in enumerate(sheets,1):
        ET.SubElement(group,tag('sheet'),name=sheet.name,sheetId=str(i),attrib={'{'+REL+'}id':f'rId{i}'})
        ET.SubElement(rels,'Relationship',Id=f'rId{i}',Type=REL+'/worksheet',Target=f'worksheets/sheet{i}.xml')
        ET.SubElement(content,'Override',PartName=f'/xl/worksheets/sheet{i}.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml')
        ET.SubElement(defined,tag('definedName'),name='_xlnm.Print_Titles',localSheetId=str(i-1)).text=f"'{sheet.name}'!$1:${sheet.headers[0]}"
        ET.SubElement(defined,tag('definedName'),name='_xlnm.Print_Area',localSheetId=str(i-1)).text=f"'{sheet.name}'!$A$1:${column(max(map(len,sheet.rows)))}${len(sheet.rows)}"
    ET.SubElement(rels,'Relationship',Id=f'rId{len(sheets)+1}',Type=REL+'/styles',Target='styles.xml')
    ET.SubElement(root,tag('calcPr'),calcId='191029',fullCalcOnLoad='1')
    package=ET.Element('Relationships',xmlns=PACKAGE);ET.SubElement(package,'Relationship',Id='rId1',Type=REL+'/officeDocument',Target='xl/workbook.xml')
    style_tree=ET.fromstring(styles());dxfs=ET.SubElement(style_tree,tag('dxfs'),count='1');dxf=ET.SubElement(dxfs,tag('dxf'));font=ET.SubElement(dxf,tag('font'));ET.SubElement(font,tag('b'));ET.SubElement(font,tag('color'),rgb='FF9C0006');fill=ET.SubElement(dxf,tag('fill'));p=ET.SubElement(fill,tag('patternFill'),patternType='solid');ET.SubElement(p,tag('fgColor'),rgb='FFFFC7CE')
    members={'[Content_Types].xml':xml_bytes(content),'_rels/.rels':xml_bytes(package),'xl/workbook.xml':xml_bytes(root),'xl/_rels/workbook.xml.rels':xml_bytes(rels),'xl/styles.xml':xml_bytes(style_tree)}
    for i,sheet in enumerate(sheets,1):members[f'xl/worksheets/sheet{i}.xml']=worksheet(sheet)
    return deterministic_zip(members)
