import json
import sys
import os

def patch_config(file_path, base_url):
    print(f"Patching {file_path} with baseUrl={base_url}")

    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        sys.exit(1)

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        if 'jupyter-config-data' not in data:
            data['jupyter-config-data'] = {}

        data['jupyter-config-data']['baseUrl'] = base_url

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        print("Successfully patched configuration.")

    except Exception as e:
        print(f"Error patching file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python patch_jupyterlite_config.py <path_to_jupyter_lite.json> <base_url>")
        sys.exit(1)

    patch_config(sys.argv[1], sys.argv[2])
