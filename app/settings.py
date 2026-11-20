import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = ROOT / 'sample_data'
DB = Path(os.getenv('WORKBENCH_DB', str(ROOT/'state/ledger.sqlite3')))
TITLE = '泵站工况板'
SLUG = 'pump-curve'
KEY = '工况单'
FIELDS = ('泵组曲线', '管线曲线')
ROLE = '供水泵房运行分析员'
UNIT = '立方米/时'
RULE_VERSION = 'pump-curve-1.0'
SIGNATURE = '泵与管线交点'
TABS = {'intake': '实测导入', 'contract': '测点字段', 'quality': '异常工况', 'domain': '并联工况', 'reconcile': '工况对读', 'runs': '泵站批次', 'review': '值班复核'}
