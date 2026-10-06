import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class LegacyTests(unittest.TestCase):
    def test_existing_analyzer_entry_exports_validated_18_records(self):
        with tempfile.TemporaryDirectory() as directory:
            result=subprocess.run([sys.executable,'-X','utf8','analysis/analyzer.py','--output',directory],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads((Path(directory)/'report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['sample_count'],18)
            self.assertEqual(report['source_counts'],{'illustrative':18})
            self.assertEqual(report['currency'],'CNY')
            self.assertTrue(report['warnings'])

if __name__=='__main__':unittest.main()
