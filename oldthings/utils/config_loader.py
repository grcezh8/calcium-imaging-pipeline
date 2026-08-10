# utils/config_loader.py
#
# PURPOSE: Load both config files cleanly so every script
#          can access paths and parameters without hardcoding anything.
#
# Usage in any script:
#   from utils.config_loader import load_config
#   cfg = load_config()
#   data_dir = cfg['data_dir']        # from local_config.yaml (machine-specific)
#   fps = cfg['minian']['frame_rate'] # from params.yaml (shared)

import yaml
import os

def load_config():
    """
    Merge local_config.yaml (machine-specific paths) and
    configs/params.yaml (shared settings) into one dictionary.
    
    local_config.yaml is never on GitHub — each machine has its own.
    params.yaml is on GitHub — shared across machines.
    """
    
    # Find repo root (assumes this file is in utils/ subfolder)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load shared params
    params_path = os.path.join(repo_root, 'configs', 'params.yaml')
    if not os.path.exists(params_path):
        raise FileNotFoundError(
            f'Could not find configs/params.yaml at {params_path}\n'
            'Make sure you are running scripts from the repo root.'
        )
    
    with open(params_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load local machine config
    local_path = os.path.join(repo_root, 'local_config.yaml')
    if not os.path.exists(local_path):
        raise FileNotFoundError(
            f'Could not find local_config.yaml at {local_path}\n'
            'This file is machine-specific and not on GitHub.\n'
            'Create it manually — see the README for the template.'
        )
    
    with open(local_path, 'r') as f:
        local = yaml.safe_load(f)
    
    # Merge: local config values sit at the top level
    # so cfg['data_dir'] works directly
    config.update(local)
    
    return config