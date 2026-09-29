
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Praxis modules for static analysis
# We need to add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    # Direct import attempt since discovery was missing STAR
    try:
        from pylabrobot.legacy.liquid_handling.backends.hamilton.STAR_backend import STAR
        print(f"\nSuccessfully imported STAR from backend module.")
        
        if hasattr(STAR, 'capabilities_config') and STAR.capabilities_config:
            print("\n--- CAPABILITIES CONFIG (Direct Import) ---")
            print(json.dumps(STAR.capabilities_config.model_dump(), indent=2))
        else:
            print("STAR class imported but has no capabilities_config.")
            
    except ImportError as e:
        print(f"Could not directly import STAR: {e}")
    except Exception as e:
        print(f"Error inspecting STAR: {e}")
        
except ImportError as e:
    print(f"Import Error (ensure you are running from project root with uv run): {e}")
except Exception as e:
    print(f"Error: {e}")
