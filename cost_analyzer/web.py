"""Loopback browser workspace, sharing the same engine as the CLI."""
import csv
import io
import json
import socket
from decimal import DecimalException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .engine import early_estimate, takeoff, unit_rate, price_boq, appraise
from .development import development
from .benchmarks import benchmark, read_boq_csv, generate_scenarios, scenario_csv
from .examples import example
from .downloads import DownloadStore
from . import reporting

ROOT=Path(__file__).resolve().parents[1]
STATIC=Path(__file__).resolve().parent/'static'
MAX_BODY=5_000_000
EXPORT_TOOLS={'early','takeoff','rate','boq','benchmark','appraise','development'}
EXPORT_TYPES={'json':'application/json; charset=utf-8','csv':'text/csv; charset=utf-8',
    'html':'text/html; charset=utf-8','xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','zip':'application/zip'}


def prepare_source(data):
    """Save editable inputs through the same bounded attachment service."""
    if not isinstance(data,dict) or set(data)!={'filename','content'}:raise ValueError('Source requires filename and content')
    name,content=data['filename'],data['content']
    allowed={tool+'-inputs.json' for tool in EXPORT_TOOLS}|{'development-housing.csv'}
    if not isinstance(name,str) or name not in allowed:raise ValueError('Unknown source filename')
    if not isinstance(content,str):raise ValueError('Source content must be text')
    if name.endswith('.json'):
        value=json.loads(content,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON number')))
        if not isinstance(value,dict):raise ValueError('Input JSON must be an object')
        return json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8'),name,EXPORT_TYPES['json']
    rows=list(csv.reader(io.StringIO(content.lstrip('\ufeff'))))
    fields=['option','name','count','area_m2','base_rate','sale_price','source_ref','area_source_ref']
    if not rows or rows[0]!=fields or any(len(row)!=len(fields) for row in rows):raise ValueError('Invalid housing CSV structure')
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\r\n')
    writer.writerows([[reporting.csv_safe(value) for value in row] for row in rows])
    return stream.getvalue().encode('utf-8-sig'),name,EXPORT_TYPES['csv']


def prepare_export(data):
    if not isinstance(data,dict) or set(data)!={'tool','format','inputs','language'}:
        raise ValueError('Export requires tool, format, inputs and language')
    tool,kind,language=data['tool'],data['format'],data['language']
    if not isinstance(tool,str) or tool not in EXPORT_TOOLS:raise ValueError('Unknown export tool')
    if not isinstance(kind,str) or kind not in EXPORT_TYPES:raise ValueError('Unknown export format')
    if not isinstance(language,str) or language not in {'zh','en','bilingual'}:raise ValueError('Unknown report language')
    result=dispatch('/api/'+tool,data['inputs'])
    result['inputs']=json.loads(json.dumps(data['inputs'],ensure_ascii=False,allow_nan=False))
    if kind=='json':body=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')
    elif kind=='csv':body=('\ufeff'+reporting.report_csv(result)).encode('utf-8')
    elif kind=='html':body=reporting.report_html(result,language).encode('utf-8')
    elif kind=='xlsx':body=reporting.report_xlsx(result,language)
    else:body=reporting.report_bundle(result,language)
    return body,'estimate.'+kind,EXPORT_TYPES[kind]


def dispatch(path,data):
    if not isinstance(data,dict):raise ValueError('Request JSON must be an object')
    functions={'/api/early':early_estimate,'/api/takeoff':takeoff,'/api/rate':unit_rate,'/api/appraise':appraise,'/api/development':development}
    if path in functions:return functions[path](data)
    if path=='/api/boq':
        project=data.get('project',{})
        if not isinstance(project,dict):raise ValueError('project: use an object')
        return price_boq(read_boq_csv(data.get('csv','')),project)
    if path=='/api/benchmark':return benchmark(data.get('csv',''),data.get('filters'),data.get('target_index',100),data.get('target_location_index',100))
    raise KeyError(path)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(10)

    def log_message(self,*args):
        pass

    def reply(self,status,body,content_type='application/json; charset=utf-8',filename=None):
        if isinstance(body,(dict,list)):body=json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8')
        if isinstance(body,str):body=body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(body)

    def valid_host(self):
        host=self.headers.get('Host','').lower()
        port=self.server.server_port
        allowed={f'127.0.0.1:{port}',f'localhost:{port}'}
        origin=self.headers.get('Origin')
        if host not in allowed or (origin is not None and origin not in {f'http://{value}' for value in allowed}):
            self.reply(403,{'error':'Local origin required / 仅允许本地访问'});return False
        return True

    def do_GET(self):
        if not self.valid_host():return
        path=urlsplit(self.path).path
        if path.startswith('/download/'):
            attachment=self.server.downloads.get(path[len('/download/'):])
            if attachment:
                body,filename,content_type=attachment;self.reply(200,body,content_type,filename)
            else:self.reply(404,{'error':'Download expired or not found; prepare the report again'})
            return
        if path=='/api/example':self.reply(200,example());return
        if path=='/api/dataset':
            content_path=ROOT/'data'/'synthetic_projects.csv'
            content=content_path.read_text(encoding='utf-8') if content_path.exists() else scenario_csv(generate_scenarios())
            rows=list(csv.DictReader(io.StringIO(content)))
            self.reply(200,{'csv':content,'metadata':{'sample_count':len(rows),'source_type':'synthetic'}});return
        if path=='/api/indices':
            directory=ROOT/'data'/'indices'
            try:
                rows=list(csv.DictReader(io.StringIO((directory/'ons_construction_opi.csv').read_text(encoding='utf-8'))))
                metadata=json.loads((directory/'ons_construction_opi.metadata.json').read_text(encoding='utf-8'))
                self.reply(200,{'rows':rows,'metadata':metadata})
            except FileNotFoundError:self.reply(404,{'error':'Index snapshot not installed'})
            return
        routes={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'}
        if path in routes and (STATIC/routes[path]).exists():
            content_type={'.html':'text/html','.js':'text/javascript','.css':'text/css'}[Path(routes[path]).suffix]
            self.reply(200,(STATIC/routes[path]).read_bytes(),content_type+'; charset=utf-8');return
        self.reply(404,{'error':'Route not found'})

    def do_POST(self):
        if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
            self.reply(415,{'error':'Use application/json'});return
        try:
            length=int(self.headers.get('Content-Length','0'))
        except ValueError:
            self.reply(400,{'error':'Invalid content length'});return
        if not 0<length<=MAX_BODY:
            self.reply(413,{'error':'Request body must be under 5 MB'});return
        try:
            content=self.rfile.read(length)
            if len(content)!=length:raise ValueError('Incomplete request body')
            if not self.valid_host():return
            data=json.loads(content.decode('utf-8'),parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON number')))
            path=urlsplit(self.path).path
            if path in ('/api/export','/api/source'):
                body,filename,content_type=(prepare_export if path=='/api/export' else prepare_source)(data)
                token=self.server.downloads.put(body,filename,content_type)
                self.reply(200,{'url':'/download/'+token,'filename':filename,'expires_in':self.server.downloads.ttl})
                return
            result=dispatch(path,data)
            self.reply(200,result)
        except KeyError:self.reply(404,{'error':'Route not found'})
        except (ValueError,TypeError,AttributeError,DecimalException,OverflowError,RecursionError) as exc:
            self.reply(400,{'error':'Invalid input / 输入无效: '+str(exc)[:400]})
        except (socket.timeout,ConnectionError):
            self.close_connection=True


def create_server(port=8765):
    if isinstance(port,bool) or not isinstance(port,int) or not 0<=port<=65535:
        raise ValueError('port: integer from 0 to 65535')
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.downloads=DownloadStore()
    server.daemon_threads=True
    return server
