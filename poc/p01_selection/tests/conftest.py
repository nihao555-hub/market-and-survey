import sys
from pathlib import Path

# 让测试可直接 import modules.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
