"""
Config Viewer
Hiển thị tất cả cấu hình
"""

import yaml
import json
import os

def print_config(filepath):
    """Print config file nội dung"""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return
    
    with open(filepath, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"\n📄 {filepath}")
    print("─" * 70)
    print(json.dumps(config, indent=2, ensure_ascii=False))

def main():
    print("=" * 70)
    print("CONFIGURATION VIEWER")
    print("=" * 70)
    
    configs = [
        'config/camera_config.yaml',
        'config/ai_config.yaml',
        'config/system_config.yaml',
    ]
    
    for config_path in configs:
        print_config(config_path)
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
