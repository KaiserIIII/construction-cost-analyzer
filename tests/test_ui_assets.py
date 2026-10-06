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
        for tool in ["early", "takeoff", "boq", "benchmark", "appraise"]:
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
  boq:'/api/boq', benchmark:'/api/benchmark', appraise:'/api/appraise'
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


if __name__ == "__main__":
    unittest.main()
