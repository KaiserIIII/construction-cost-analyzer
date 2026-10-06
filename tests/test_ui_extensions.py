import shutil
import json
import subprocess
import unittest
from pathlib import Path


class ExportControlsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node required for UI utility checks')
    def test_omitted_schedule_defaults_survive_ui_roundtrip(self):
        from cost_analyzer.development import development
        from tests.test_development import fixture
        file=Path(__file__).resolve().parents[1]/'cost_analyzer/static/app.js'
        for override in ({'prep_months':0},{'duration_months':1}):
            data=fixture();data.pop('prep_months');data.pop('prep_spend_pct')
            data['options'][0]['settings']=override
            expected=development(data)['options'][0]
            script="const ui=require(process.argv[1]);const n=ui.normalizedInputs('development',JSON.parse(process.argv[2]));const overrides=new Map(n.options.map(o=>[o.name,o.settings||{}]));delete n.options;console.log(JSON.stringify(ui.developmentPayload(n,overrides)));"
            run=subprocess.run([shutil.which('node'),'-e',script,str(file),json.dumps(data)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            actual=development(json.loads(run.stdout))['options'][0]
            self.assertEqual(actual,expected)

    @unittest.skipUnless(shutil.which('node'),'Node required for UI utility checks')
    def test_native_grids_overrides_metadata_and_attachment_request(self):
        script=r"""
const assert=require('node:assert/strict'),ui=require(process.argv[1]);
const units=[{name:'House',count:1,area_m2:80,base_rate:100,sale_price:20000,source_ref:'',area_source_ref:''}];
const options=[{name:'A',units,settings:{marketing_pct:0,duration_months:8}}];
const input=ui.normalizedInputs('development',{options,cost_changes_pct:[10,0,-10],report_reference:'QS-1',estimate_date:'2026-10-06'});
assert.deepEqual(input.options,options);assert.deepEqual(input.cost_changes_pct,[-10,0,10]);
assert.deepEqual(ui.parseSensitivityRange('-20,-10,0,10,20','cost_changes_pct'),[-20,-10,0,10,20]);
assert.equal(ui.parseSensitivityRange('','cost_changes_pct'),undefined);
for(const bad of ['1,2','0,0','0,,10','0,101','0,NaN'])assert.throws(()=>ui.parseSensitivityRange(bad,'cost_changes_pct'));
const payload=ui.developmentPayload({csv:input.csv,cost_changes_pct:'-10,0,10',value_changes_pct:'',report_reference:'QS-1'},new Map([['A',{marketing_pct:0,duration_months:8}]]));
assert.deepEqual(payload.options,options);assert.deepEqual(payload.cost_changes_pct,[-10,0,10]);
assert.equal('value_changes_pct' in payload,false);
assert.throws(()=>ui.developmentPayload({csv:input.csv},new Map([['B',{marketing_pct:0}]])),/refresh|刷新/i);
assert.throws(()=>ui.normalizedInputs('development',{options:[{name:'A',units,settings:{wrong:0}}]}),/wrong/);
assert.throws(()=>ui.normalizedInputs('development',{options,estimate_date:'2026-02-30'}),/estimate_date/);
assert.deepEqual(ui.reportExportRequest('development','xlsx',{inputs:payload,stale:false},'en'),{tool:'development',format:'xlsx',inputs:payload,language:'en'});
assert.throws(()=>ui.reportExportRequest('development','zip',{inputs:payload,stale:true},'en'),/stale|重新/i);
"""
        file=Path(__file__).resolve().parents[1]/'cost_analyzer/static/app.js'
        run=subprocess.run([shutil.which('node'),'-e',script,str(file)],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)


if __name__=='__main__':unittest.main()
