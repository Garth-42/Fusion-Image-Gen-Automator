from pathlib import Path
import sys

ADDIN_ROOT = Path(__file__).resolve().parents[1] / "addin" / "FusionManualSceneManager"
sys.path.insert(0, str(ADDIN_ROOT))
