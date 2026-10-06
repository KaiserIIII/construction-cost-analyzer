"""Contract and safety checks for the dependency-free browser workspace."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "cost_analyzer" / "static"


class BrowserAssetsTests(unittest.TestCase):
    def test_browser_entry_has_accessible_tool_navigation_and_local_assets(self):
        path = STATIC / "index.html"
        self.assertTrue(path.exists(), "The browser workspace must have an entry page")
        html = path.read_text(encoding="utf-8")
        self.assertIn('lang="zh-CN"', html)
        self.assertIn('role="tablist"', html)
        for tool in ["early", "takeoff", "boq", "benchmark", "appraise", "development"]:
            self.assertIn(f'id="panel-{tool}"', html)
            self.assertIn(f'aria-controls="panel-{tool}"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('src="/app.js"', html)
        self.assertIn('href="/styles.css"', html)
        self.assertNotIn('https://', html)

    def test_dynamic_ui_does_not_interpolate_imported_csv_as_html(self):
        path = STATIC / "app.js"
        self.assertTrue(path.exists(), "The forms and result renderer must exist")
        js = path.read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertNotIn("insertAdjacentHTML", js)
        self.assertIn("textContent", js)
        self.assertIn("file.text()", js)

    def test_responsive_and_print_report_styles_exist(self):
        path = STATIC / "styles.css"
        self.assertTrue(path.exists(), "The responsive workspace stylesheet must exist")
        css = path.read_text(encoding="utf-8")
        self.assertIn("@media print", css)
        self.assertIn("@media (max-width:", css)
        self.assertIn(":focus-visible", css)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for browser utility checks")
    def test_translations_api_forms_and_csv_export_protection(self):
        path = STATIC / "app.js"
        self.assertTrue(path.exists(), "The browser application module must exist")
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
assert.deepEqual(Object.keys(ui.copy.zh).sort(), Object.keys(ui.copy.en).sort());
for (const language of ['zh', 'en']) {
  for (const [key, value] of Object.entries(ui.copy[language])) {
    assert.equal(typeof value, 'string', key);
    assert.ok(value.trim(), key);
  }
}
assert.deepEqual(ui.apiPaths, {
  early:'/api/early', takeoff:'/api/takeoff', rate:'/api/rate',
  boq:'/api/boq', benchmark:'/api/benchmark', appraise:'/api/appraise',
  development:'/api/development'
});
assert.equal(ui.csvCell('=HYPERLINK("bad")'), '"\'=HYPERLINK(""bad"")"');
assert.equal(ui.csvCell('  +SUM(1,2)'), '"\'  +SUM(1,2)"');
assert.equal(ui.csvCell('@formula'), "'@formula");
assert.equal(ui.csvCell(-125), '-125');
assert.equal(ui.csvCell('Wall, brick'), '"Wall, brick"');
assert.equal(ui.csvCell('plain'), 'plain');
assert.deepEqual(ui.parseCashflows('-100000, 30000\n40000'), [-100000,30000,40000]);
assert.throws(() => ui.parseCashflows('-100, no'), /cashflow/i);
assert.throws(() => ui.parseCashflows(''), /cashflow/i);
assert.throws(() => ui.parseCashflows('-100,,200'), /cashflow/i);
const fields = ui.formFields;
assert.ok(fields.early.includes('rate_includes_preliminaries'));
assert.ok(fields.early.includes('rate_includes_ohp'));
assert.ok(fields.takeoff.includes('wall_thickness'));
assert.ok(fields.rate.includes('crew_output_per_hour'));
assert.ok(fields.boq.includes('csv'));
assert.ok(fields.benchmark.includes('source_type'));
assert.ok(fields.appraise.includes('profit_basis'));
assert.deepEqual(ui.restoreIndexSource({base_index:100,target_index:120}), null);
assert.deepEqual(ui.restoreIndexSource({index_source:{series:'ONS'}}), {series:'ONS'});
assert.equal(ui.rateInclusions({markup_pct:10}).included_ohp, true);
assert.equal(ui.rateInclusions({markup_pct:0}).included_ohp, false);
const quote = String.fromCharCode(34);
const parsed = ui.parseCSV('a,b\r\n'+quote+'first, name'+quote+','+quote+'line\nwith '+quote+quote+'quote'+quote+quote+quote+'\r\n');
assert.deepEqual(parsed, [['a','b'],['first, name','line\nwith "quote"']]);
assert.throws(() => ui.parseCSV('a,b\n"unterminated'), /CSV/);
assert.equal(ui.normalizedInputs('early',{area_m2:100,base_rate:100}).target_index,100);
assert.equal(ui.normalizedInputs('early',{area_m2:100,base_rate:100}).preliminaries_pct,0);
assert.deepEqual(ui.normalizedInputs('rate',{crew_hourly_cost:48}).materials,[]);
console.log('Browser utilities verified');
"""
        result = subprocess.run([shutil.which("node"), "-e", script, str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Browser utilities verified", result.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for browser utility checks")
    def test_housing_csv_preserves_groups_sources_and_precision(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
assert.equal(typeof ui.parseDevelopmentCSV, 'function');
assert.equal(typeof ui.developmentOptionsCSV, 'function');
const csv = '\ufeffoption,name,count,area_m2,base_rate,sale_price,source_ref,area_source_ref\r\n' +
  'Plan A,"Flat, one",2,71.123456789,0.333333333,100,"quote\nline",drawing-1\r\n' +
  'Plan B,<img src=x onerror=bad()>,1,80,1,125,quote-2,drawing-2\r\n' +
  'Plan A,House,3,90,2,250,quote-3,drawing-3\r\n';
const options = ui.parseDevelopmentCSV(csv);
assert.deepEqual(options, [
  {name:'Plan A',units:[
    {name:'Flat, one',count:2,area_m2:71.123456789,base_rate:0.333333333,sale_price:100,source_ref:'quote\nline',area_source_ref:'drawing-1'},
    {name:'House',count:3,area_m2:90,base_rate:2,sale_price:250,source_ref:'quote-3',area_source_ref:'drawing-3'}]},
  {name:'Plan B',units:[{name:'<img src=x onerror=bad()>',count:1,area_m2:80,base_rate:1,sale_price:125,source_ref:'quote-2',area_source_ref:'drawing-2'}]}
]);
assert.deepEqual(ui.parseDevelopmentCSV(ui.developmentOptionsCSV(options)), options);
assert.deepEqual(ui.parseDevelopmentCSV(ui.developmentOptionsCSV([{name:'__proto__',units:options[1].units}])), [{name:'__proto__',units:options[1].units}]);
const malicious = [{name:'=SUM(1,2)',units:[{...options[1].units[0],name:'@formula',source_ref:'\t=bad'}]}];
const protectedCsv = ui.developmentOptionsCSV(malicious);
assert.ok(protectedCsv.includes("'=SUM(1,2)"));
assert.ok(protectedCsv.includes("'@formula"));
const header = 'option,name,count,area_m2,base_rate,sale_price,source_ref,area_source_ref\n';
const precise = ui.parseDevelopmentCSV(header+'A,B,1,1.00000000000000001,9007199254740993,3,x,y')[0].units[0];
assert.equal(precise.area_m2, '1.00000000000000001');
assert.equal(precise.base_rate, '9007199254740993');
assert.throws(() => ui.parseDevelopmentCSV(header+'A,B,1.00000000000000001,20,2,3,x,y'), /count/);
for (const invalid of ['', header, 'option,name\nA,B', header+'A,B,1,20,2,3,x', header+'A,B,1,20,2,3,x,y,extra', header+'A,B,1.5,20,2,3,x,y', header+'A,B,0,20,2,3,x,y', header+'A,B,1,0,2,3,x,y', header+'A,B,1,20,-2,3,x,y', header+'A,B,1,20,2,Infinity,x,y', header+'A,B,1,20,,3,x,y', header+',B,1,20,2,3,x,y']) {
  assert.throws(() => ui.parseDevelopmentCSV(invalid), /CSV|housing|option|row/i, invalid);
}
assert.throws(() => ui.developmentOptionsCSV([{name:'A',units:'invalid'}]), /units|option/i);
"""
        result = subprocess.run([shutil.which("node"), "-e", script, str(STATIC / "app.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for browser utility checks")
    def test_development_payload_is_flat_and_partial_load_resets_previous_allowances(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
assert.equal(typeof ui.developmentPayload, 'function');
const options = [{name:'Option 1',units:[{name:'Unit',count:1,area_m2:80,base_rate:2,sale_price:200,source_ref:'quote',area_source_ref:'plan'}]}];
const defaults = ui.normalizedInputs('development', {options});
assert.equal(defaults.duration_months, 5);
assert.equal(defaults.prep_months, 1);
assert.equal(defaults.prep_spend_pct, 10);
assert.equal(defaults.hurdle_pct, 10);
assert.equal(defaults.sensitivity_pct, 10);
assert.equal(defaults.base_index, 100);
assert.equal(defaults.target_index, 100);
assert.equal(defaults.fees_pct, 0);
assert.equal(defaults.loan_share_pct, 0);
assert.equal(defaults.risk_design_pct, 0);
assert.equal(defaults.rate_includes_preliminaries, false);
assert.equal(defaults.rate_includes_ohp, false);
const first = ui.normalizedInputs('development', {options,loan_share_pct:50,fees_pct:10,rate_includes_ohp:true});
first.options[0].units[0].source_ref='changed';
assert.equal(options[0].units[0].source_ref, 'quote');
const loaded = ui.normalizedInputs('development', {options,source_ref:'new source'});
assert.equal(loaded.loan_share_pct, 0);
assert.equal(loaded.fees_pct, 0);
assert.equal(loaded.rate_includes_ohp, false);
const payload = ui.developmentPayload({currency:'GBP',loan_share_pct:'50',fees_pct:'10',rate_includes_preliminaries:true,csv:ui.developmentOptionsCSV(options)});
assert.equal(payload.loan_share_pct, '50');
assert.equal(payload.fees_pct, '10');
assert.equal(payload.rate_includes_preliminaries, true);
assert.deepEqual(payload.options, options);
assert.equal('csv' in payload, false);
assert.equal('settings' in payload, false);
assert.equal('project' in payload, false);
assert.throws(() => ui.normalizedInputs('development',{options:'invalid'}), /options/i);
"""
        result = subprocess.run([shutil.which("node"), "-e", script, str(STATIC / "app.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for browser utility checks")
    def test_development_csv_exports_every_nested_row_and_the_source_snapshot(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
assert.equal(typeof ui.resultCSV, 'function');
const inputs = {source_ref:'=SOURCE()', options:[{name:'A',units:[{name:'unit',source_ref:'quote',area_source_ref:'plan'}]}]};
const result = {project_name:'Test',currency:'GBP',option_count:2,viable_count:0,recommended_option:null,warnings:['No viable option'],
 options:[{name:'A',total:123.123456789,profit:-1,breakdown:[{label:'land_cost',base:10,percent:0,amount:10}],housing:[{name:'unit',count:1,source_ref:'quote'}],cashflows:[{month:0,loan_balance:10,equity_cashflow:-10}],sensitivity:[{cost_change_pct:-10,value_change_pct:10,profit:2}]},
 {name:'B',total:200,profit:-2,breakdown:[{label:'total',amount:200}],housing:[{name:'two',count:2,area_source_ref:'drawing-2'}],cashflows:[{month:1,loan_balance:0,equity_cashflow:250,loan_repayment:25}],sensitivity:[{cost_change_pct:10,value_change_pct:-10,profit:-3}]}]};
const rows = ui.parseCSV(ui.resultCSV(result,inputs).replace(/^\ufeff/,''));
assert.ok(rows.some(row => row[0]==='options' && row[1]==='0' && row[2]==='name' && row[3]==='A'));
assert.ok(rows.some(row => row[0]==='options' && row[1]==='0' && row[2]==='total' && row[3]==='123.123456789'));
assert.ok(rows.some(row => row[0]==='options' && row[1]==='1' && row[2]==='cashflows[0].loan_repayment' && row[3]==='25'));
assert.ok(rows.some(row => row[0]==='options' && row[1]==='1' && row[2]==='housing[0].area_source_ref' && row[3]==='drawing-2'));
assert.ok(rows.some(row => row[0]==='options' && row[1]==='0' && row[2]==='breakdown[0].label' && row[3]==='land_cost'));
assert.ok(rows.some(row => row[0]==='options' && row[1]==='1' && row[2]==='sensitivity[0].profit' && row[3]==='-3'));
assert.ok(rows.some(row => row[0]==='result' && row[2]==='warnings[0]' && row[3]==='No viable option'));
assert.deepEqual(JSON.parse(rows.find(row => row[0]==='inputs_json')[1]), inputs);
"""
        result = subprocess.run([shutil.which("node"), "-e", script, str(STATIC / "app.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for browser utility checks")
    def test_development_presentation_distinguishes_money_precision_and_no_viable_recommendation(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
assert.equal(typeof ui.developmentRecommendation, 'function');
assert.equal(typeof ui.formatDevelopmentValue, 'function');
assert.equal(ui.developmentRecommendation({viable_count:0,recommended_option:'Least loss'}), null);
assert.equal(ui.developmentRecommendation({viable_count:1,recommended_option:'A'}), 'A');
assert.equal(ui.developmentRecommendation({viable_count:1,recommended_option:null}), null);
assert.equal(ui.formatDevelopmentValue(12.123456789,'total','en-GB'), '12.12');
assert.equal(ui.formatDevelopmentValue(12,'loan_balance','en-GB'), '12.00');
assert.equal(ui.formatDevelopmentValue(12.123456789,'adjusted_rate','en-GB'), '12.123457');
assert.equal(ui.formatDevelopmentValue(12.123456789,'gifa_m2','en-GB'), '12.123457');
assert.equal(ui.formatDevelopmentValue(10.123456789,'return_on_cost_pct','en-GB'), '10.123457');
assert.equal(ui.formatDevelopmentValue(false,'meets_hurdle','en-GB'), 'No');
assert.equal(ui.formatDevelopmentValue(true,'meets_hurdle','zh-CN'), '是');
assert.equal(ui.formatDevelopmentValue(null,'budget_irr_annual_pct','en-GB'), 'Not applicable / not reached');
const original = 12.123456789;
ui.formatDevelopmentValue(original,'total','en-GB');
assert.equal(original, 12.123456789);
const loaded = ui.normalizedInputs('development',{options:[{name:'=Exact name',units:[{name:'@Exact housing',count:1,area_m2:20,base_rate:2,sale_price:50,source_ref:'=source',area_source_ref:'plan'}]}]});
assert.equal(ui.parseDevelopmentCSV(loaded.csv)[0].name, '=Exact name');
assert.equal(ui.parseDevelopmentCSV(loaded.csv)[0].units[0].source_ref, '=source');
assert.equal(ui.normalizedInputs('development',{}).marketing_pct, 0);
const spaced = [{name:'  Option A ',units:[{name:' House ',count:1,area_m2:20,base_rate:2,sale_price:50,source_ref:'  quote  ',area_source_ref:' drawing ' }]}];
assert.deepEqual(ui.parseDevelopmentCSV(ui.normalizedInputs('development',{options:spaced}).csv), spaced);
const short = ui.normalizedInputs('development',{duration_months:1});
assert.equal(short.prep_months, 0);
assert.equal(short.prep_spend_pct, 0);
assert.equal(ui.normalizedInputs('development',{prep_months:0}).prep_spend_pct, 0);
"""
        result = subprocess.run([shutil.which("node"), "-e", script, str(STATIC / "app.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for browser utility checks")
    def test_development_native_inputs_reject_unknown_settings_and_nested_fields(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const unit = {name:'House',count:1,area_m2:80,base_rate:2,sale_price:200,source_ref:'quote',area_source_ref:'plan'};
const options = [{name:'A',units:[unit]}];
assert.throws(() => ui.normalizedInputs('development',{options,overhead_profit_pct:10}), /overhead_profit_pct/);
assert.throws(() => ui.normalizedInputs('development',{options,csv:'ignored CSV'}), /csv/);
assert.throws(() => ui.normalizedInputs('development',{options,settings:{fees_pct:10}}), /settings/);
assert.throws(() => ui.normalizedInputs('development',{options:[{name:'A',units:[unit],total:999}]}), /total/);
assert.throws(() => ui.normalizedInputs('development',{options:[{name:'A',units:[{...unit,base_rates:20}]}]}), /base_rates/);
assert.throws(() => ui.normalizedInputs('development',{options:[{name:1,units:[unit]}]}), /name/);
for (const key of ['name','source_ref','area_source_ref']) {
  assert.throws(() => ui.normalizedInputs('development',{options:[{name:'A',units:[{...unit,[key]:{value:'bad'}}]}]}), new RegExp(key));
}
const csv=ui.developmentOptionsCSV(options);
assert.throws(() => ui.developmentPayload({csv,overhead_profit_pct:'10'}), /overhead_profit_pct/);
assert.throws(() => ui.developmentPayload({csv,options}), /options/);
assert.throws(() => ui.developmentOptionsCSV([{name:'A',units:[{...unit,rate:20}]}]), /rate/);
assert.throws(() => ui.normalizedInputs('development',null), /object/);
assert.throws(() => ui.normalizedInputs('development',[]), /object/);
"""
        result = subprocess.run([shutil.which("node"), "-e", script, str(STATIC / "app.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for browser utility checks")
    def test_development_native_type_validation_and_assumptions_survive_save_load(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const unit = {name:'House',count:'1',area_m2:'80.123456789',base_rate:'2',sale_price:'200',source_ref:' quote ',area_source_ref:' plan '};
const options = [{name:'A',units:[unit]}];
for (const key of ['project_name','currency','source_ref','index_source_ref','assumptions','start_date','price_date']) {
  for (const invalid of [null,10,true,{},[]]) {
    assert.throws(() => ui.normalizedInputs('development',{options,[key]:invalid}), new RegExp(key));
  }
  assert.equal(ui.normalizedInputs('development',{options,[key]:''})[key], '');
}
for (const key of ['start_date','price_date']) {
  for (const invalid of ['tomorrow','2026-02-30','2026-13-01','2026-1-01','0000-01-01']) {
    assert.throws(() => ui.normalizedInputs('development',{options,[key]:invalid}), new RegExp(key));
  }
  assert.equal(ui.normalizedInputs('development',{options,[key]:'2028-02-29'})[key], '2028-02-29');
}
for (const key of ['site_area_m2','fees_pct','loan_share_pct','duration_months']) {
  for (const invalid of [null,true,[],{},'','bad','Infinity','NaN',Infinity,NaN]) {
    assert.throws(() => ui.normalizedInputs('development',{options,[key]:invalid}), new RegExp(key));
  }
  assert.equal(ui.normalizedInputs('development',{options,[key]:'12.123456789'})[key], '12.123456789');
  assert.equal(ui.normalizedInputs('development',{options,[key]:12.123456789})[key], 12.123456789);
}
assert.equal(ui.normalizedInputs('development',{options,fees_pct:'  +.0000123456789 '}).fees_pct, '0.0000123456789');
assert.equal(ui.normalizedInputs('development',{options,loan_share_pct:' +50. '}).loan_share_pct, '50');
for (const key of ['count','area_m2','base_rate','sale_price']) {
  for (const invalid of [null,true,[],{},'','bad','Infinity',Infinity]) {
    assert.throws(() => ui.normalizedInputs('development',{options:[{name:'A',units:[{...unit,[key]:invalid}]}]}), new RegExp(key));
  }
}
for (const key of ['rate_includes_preliminaries','rate_includes_ohp']) {
  for (const value of [true,'true','yes','1',' TRUE ']) assert.equal(ui.normalizedInputs('development',{options,[key]:value})[key], true);
  for (const value of [false,'false','no','0',' FALSE ']) assert.equal(ui.normalizedInputs('development',{options,[key]:value})[key], false);
  for (const invalid of [0,1,2,null,'',[],{},'perhaps']) assert.throws(() => ui.normalizedInputs('development',{options,[key]:invalid}), new RegExp(key));
}
const assumptions='Housing mix from study drawing.\nCosts exclude tax; source remains provisional.';
const loaded=ui.normalizedInputs('development',{options,assumptions,source_ref:' quote source ',index_source_ref:' index source ',rate_includes_ohp:'yes'});
assert.equal(loaded.assumptions, assumptions);
assert.equal(ui.normalizedInputs('development',{}).assumptions, '');
assert.ok(ui.formFields.development.includes('assumptions'));
assert.equal(typeof ui.copy.zh.assumptions, 'string');
assert.equal(typeof ui.copy.en.assumptions, 'string');
const {options:loadedOptions,...form}=loaded;
const payload=ui.developmentPayload(form);
assert.equal(payload.assumptions, assumptions);
assert.equal(payload.source_ref, ' quote source ');
assert.equal(payload.index_source_ref, ' index source ');
assert.equal(payload.rate_includes_ohp, true);
assert.equal(payload.options[0].units[0].source_ref, ' quote ');
assert.equal(payload.options[0].units[0].area_m2, 80.123456789);
const reloaded=ui.normalizedInputs('development',JSON.parse(JSON.stringify(payload)));
assert.equal(reloaded.assumptions, assumptions);
assert.equal(reloaded.csv, loaded.csv);
const exportRows=ui.parseCSV(ui.resultCSV({options:[]},payload).replace(/^\ufeff/,''));
assert.equal(JSON.parse(exportRows.find(row=>row[0]==='inputs_json')[1]).assumptions, assumptions);
"""
        result = subprocess.run([shutil.which("node"), "-e", script, str(STATIC / "app.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
