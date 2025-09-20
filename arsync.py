#!/usr/bin/env python3
"""
arsync - Enhanced rsync with YAML configuration and variable substitution
"""

import os
import sys
import yaml
import argparse
import subprocess
import threading
import getpass
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ArsyncConfig:
    """Handles configuration loading and variable substitution"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.expanduser("~/.config/arsync.conf")
        
        self.config_path = config_path
        self.config = {}
        self.variables = {}
        self.load_config()
    
    def load_config(self):
        """Load and parse the YAML configuration file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Extract variables
            if 'variables' in self.config:
                for var_def in self.config['variables']:
                    if isinstance(var_def, str) and '=' in var_def:
                        key, value = var_def.split('=', 1)
                        self.variables[key.strip()] = value.strip().strip('"\'')
            
            # Validate required sections
            if 'sync' not in self.config:
                raise ValueError("Config file must contain a 'sync' section")
                
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
    
    def substitute_variables(self, text: str) -> str:
        """Substitute variables in the format ${VAR_NAME} with their values"""
        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.variables:
                return self.variables[var_name]
            else:
                print(f"Warning: Variable ${var_name} not defined")
                return match.group(0)  # Return original if not found
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, text)
    
    def get_sync_config(self, sync_name: str) -> Dict:
        """Get configuration for a specific sync operation"""
        if sync_name not in self.config['sync']:
            available_syncs = list(self.config['sync'].keys())
            raise ValueError(f"Sync '{sync_name}' not found. Available syncs: {', '.join(available_syncs)}")
        
        sync_config = self.config['sync'][sync_name].copy()
        
        # Expand paths first (handle ~ and relative paths)
        if 'src' in sync_config and ':' not in sync_config['src']:
            src_path = sync_config['src']
            # Handle tilde expansion
            if src_path.startswith('~/'):
                src_path = os.path.expanduser(src_path)
            elif src_path.startswith('/') and '/~/' in src_path:
                # Fix paths like /home/user/~/path -> /home/user/path
                src_path = src_path.replace('/~/', '/')
            sync_config['src'] = os.path.abspath(src_path)
        if 'dest' in sync_config and ':' not in sync_config['dest']:
            dest_path = sync_config['dest']
            # Handle tilde expansion
            if dest_path.startswith('~/'):
                dest_path = os.path.expanduser(dest_path)
            elif dest_path.startswith('/') and '/~/' in dest_path:
                # Fix paths like /home/user/~/path -> /home/user/path
                dest_path = dest_path.replace('/~/', '/')
            sync_config['dest'] = os.path.abspath(dest_path)
        
        # Substitute variables in src and dest (after path expansion)
        if 'src' in sync_config:
            sync_config['src'] = self.substitute_variables(sync_config['src'])
        if 'dest' in sync_config:
            sync_config['dest'] = self.substitute_variables(sync_config['dest'])
        
        return sync_config
    
    def get_rsync_flags(self) -> str:
        """Get rsync flags from config, with default fallback"""
        return self.config.get('config', {}).get('rsync_flags', '-avPh')
    
    def list_syncs(self) -> List[str]:
        """List all available sync operations"""
        return list(self.config['sync'].keys())


class ArsyncRunner:
    """Handles rsync execution and parallel operations"""
    
    def __init__(self, config: ArsyncConfig):
        self.config = config
        self.threads = []
        self.results = {}
    
    def is_remote_path(self, path: str) -> bool:
        """Check if a path is remote (contains ':')"""
        return ':' in path
    
    def get_ssh_password(self, host: str) -> str:
        """Prompt for SSH password if needed"""
        return getpass.getpass(f"Enter SSH password for {host}: ")
    
    def build_rsync_command(self, sync_config: Dict, sync_name: str, dry_run: bool = False) -> List[str]:
        """Build the rsync command for a sync operation"""
        src = sync_config['src']
        dest = sync_config['dest']
        flags = self.config.get_rsync_flags()
        
        # Check if we need SSH password
        if self.is_remote_path(src):
            host = src.split(':')[0]
            # Check if SSH key exists
            ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")
            if not os.path.exists(ssh_key_path) and not dry_run:
                password = self.get_ssh_password(host)
                # Use sshpass for password authentication
                cmd = ['sshpass', '-p', password, 'rsync', flags, src, dest]
            else:
                cmd = ['rsync', flags, src, dest]
        else:
            cmd = ['rsync', flags, src, dest]
        
        return cmd
    
    def run_sync(self, sync_name: str) -> Tuple[bool, str]:
        """Run a single sync operation"""
        try:
            sync_config = self.config.get_sync_config(sync_name)
            cmd = self.build_rsync_command(sync_config, sync_name)
            
            print(f"Running sync '{sync_name}': {' '.join(cmd)}")
            
            # Run rsync
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return True, result.stdout
            
        except subprocess.CalledProcessError as e:
            error_msg = f"rsync failed: {e.stderr}"
            return False, error_msg
        except Exception as e:
            error_msg = f"Error running sync '{sync_name}': {str(e)}"
            return False, error_msg
    
    def run_sync_parallel(self, sync_names: List[str]) -> Dict[str, Tuple[bool, str]]:
        """Run multiple sync operations in parallel"""
        results = {}
        
        def sync_worker(sync_name: str):
            success, output = self.run_sync(sync_name)
            results[sync_name] = (success, output)
        
        # Start all sync operations
        threads = []
        for sync_name in sync_names:
            thread = threading.Thread(target=sync_worker, args=(sync_name,))
            thread.start()
            threads.append(thread)
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        return results
    
    def run_syncs(self, sync_names: List[str], parallel: bool = True) -> Dict[str, Tuple[bool, str]]:
        """Run sync operations, either in parallel or sequentially"""
        if parallel and len(sync_names) > 1:
            return self.run_sync_parallel(sync_names)
        else:
            results = {}
            for sync_name in sync_names:
                success, output = self.run_sync(sync_name)
                results[sync_name] = (success, output)
            return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Enhanced rsync with YAML configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  arsync                    # Run all syncs
  arsync debian            # Run only 'debian' sync
  arsync debian ubuntu     # Run multiple syncs
  arsync --list            # List available syncs
  arsync --config /path/to/config.conf  # Use custom config file
  arsync refresh           # Refresh bash completion
        """
    )
    
    parser.add_argument(
        'sync_names',
        nargs='*',
        help='Specific sync names to run, or "refresh" to update bash completion (default: run all)'
    )
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file (default: ~/.config/arsync.conf)'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available sync operations'
    )
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Run syncs sequentially instead of in parallel'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be done without actually running rsync'
    )
    
    args = parser.parse_args()
    
    try:
        # Handle refresh command
        if args.sync_names and args.sync_names[0] == 'refresh':
            print("Refreshing bash completion...")
            # This is handled by the wrapper script, but we can provide feedback
            print("Bash completion refreshed.")
            return 0
        
        # Load configuration
        config = ArsyncConfig(args.config)
        
        # List syncs if requested
        if args.list:
            syncs = config.list_syncs()
            print("Available sync operations:")
            for sync in syncs:
                print(f"  - {sync}")
            return 0
        
        # Determine which syncs to run
        if args.sync_names:
            sync_names = args.sync_names
        else:
            sync_names = config.list_syncs()
        
        if not sync_names:
            print("No sync operations defined in configuration")
            return 1
        
        # Dry run mode
        if args.dry_run:
            print("Dry run mode - would execute the following:")
            for sync_name in sync_names:
                try:
                    sync_config = config.get_sync_config(sync_name)
                    cmd = ArsyncRunner(config).build_rsync_command(sync_config, sync_name, dry_run=True)
                    print(f"  {sync_name}: {' '.join(cmd)}")
                except Exception as e:
                    print(f"  {sync_name}: ERROR - {e}", file=sys.stderr)
            return 0
        
        # Run syncs
        runner = ArsyncRunner(config)
        results = runner.run_syncs(sync_names, parallel=not args.no_parallel)
        
        # Report results
        success_count = 0
        for sync_name, (success, output) in results.items():
            if success:
                print(f"✓ {sync_name}: Success")
                success_count += 1
            else:
                print(f"✗ {sync_name}: Failed - {output}")
        
        print(f"\nCompleted: {success_count}/{len(results)} syncs successful")
        return 0 if success_count == len(results) else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
