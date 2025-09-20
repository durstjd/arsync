# arsync - Enhanced rsync with YAML configuration

A Python script that provides enhanced rsync functionality with YAML configuration files, variable substitution, and parallel execution support.

## Features

- YAML-based configuration with variable substitution
- Support for multiple sync operations
- Parallel execution of multiple syncs
- SSH password prompting for remote connections
- Dry-run mode for testing
- Flexible command-line interface
- Bash completion support
- Easy installation with install scripts
- Global command-line access (`arsync` command)

## Installation

### Quick Install

```bash
cd arsync
./install.sh
```

### Manual Installation

1. Navigate to the arsync directory:
```bash
cd arsync
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable (on Unix-like systems):
```bash
chmod +x arsync.py
```

4. Copy the example configuration file:
```bash
cp arsync.conf.example ~/.config/arsync.conf
```

5. Add arsync to your PATH (optional):
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

## Configuration

The configuration file should be placed at `~/.config/arsync.conf`. An example configuration file (`arsync.conf.example`) is included in this directory:

```yaml
---
variables:
  - SOURCE_USERNAME = "admin"
  - SOURCE_BASE = "192.168.0.11"
  - DESTINATION_BASE = "/media/usb/repos"

config:
  rsync_flags: "-avPh"

sync:
  debian:
    src: "${SOURCE_BASE}:/data/debian"
    dest: "${DESTINATION_BASE}/debian"
  
  ubuntu:
    src: "${SOURCE_BASE}:/data/ubuntu"
    dest: "${DESTINATION_BASE}/ubuntu"
  
  local_backup:
    src: "/home/user/documents"
    dest: "/backup/documents"
```

## Usage

### Basic Commands

```bash
# Run all syncs defined in config
arsync

# Run specific sync operations
arsync debian
arsync debian ubuntu

# List available sync operations
arsync --list

# Dry run (show what would be done)
arsync --dry-run

# Run syncs sequentially instead of parallel
arsync --no-parallel

# Use custom config file
arsync --config /path/to/config.conf

# Refresh bash completion (after installation)
arsync refresh
```

### Command Line Options

- `sync_names`: Specific sync names to run (default: run all)
- `--config, -c`: Path to configuration file (default: ~/.config/arsync.conf)
- `--list, -l`: List available sync operations
- `--no-parallel`: Run syncs sequentially instead of in parallel
- `--dry-run, -n`: Show what would be done without actually running rsync
- `refresh`: Refresh bash completion (after installation)

## Configuration Format

### Variables Section
Define variables that can be used throughout the configuration:
```yaml
variables:
  - VAR_NAME = "value"
  - ANOTHER_VAR = "another_value"
```

### Config Section
Global configuration options:
```yaml
config:
  rsync_flags: "-avPh"  # Default rsync flags
```

### Sync Section
Define individual sync operations:
```yaml
sync:
  sync_name:
    src: "source_path_or_remote"
    dest: "destination_path"
```

Variables can be used in `src` and `dest` paths using `${VAR_NAME}` syntax.

**Path Handling:**
- Tilde (`~`) is automatically expanded to your home directory
- Relative paths are resolved to absolute paths
- Remote paths (containing `:`) are left unchanged

**Important:** In YAML config files, use quotes around paths containing `~`:
```yaml
# Correct
src: "~/test/test.txt"
dest: "~/.test.txt"

# Incorrect (will be treated as literal ~)
src: ~/test/test.txt
dest: ~/.test.txt
```

## Bash Completion

After installation, arsync includes bash completion support that provides:

- Auto-completion of sync names from your configuration
- Auto-completion of command-line options
- Auto-completion of config file paths
- **Persistent completion**: Completion works across all terminal sessions
- **Automatic updates**: Completion stays up-to-date with your configuration changes

The completion script is installed to `~/.bash_completion.d/arsync` and automatically loaded by your shell. You can manually refresh with:

```bash
arsync refresh
```

## Examples

### Local to Local Sync
```yaml
sync:
  documents:
    src: "/home/user/documents"
    dest: "/backup/documents"
```

### Remote to Local Sync
```yaml
sync:
  remote_data:
    src: "user@server.com:/data"
    dest: "/local/backup"
```

### Using Variables
```yaml
variables:
  - SERVER = "192.168.1.100"
  - BACKUP_DIR = "/backup"

sync:
  server_data:
    src: "${SERVER}:/var/data"
    dest: "${BACKUP_DIR}/server_data"
```

## Requirements

- Python 3.6+
- PyYAML
- rsync (must be available in PATH)
- sshpass (for SSH password authentication, if needed)

## Notes

- The script will prompt for SSH passwords if no SSH key is found for remote connections
- All sync operations run in parallel by default (unless `--no-parallel` is used)
- Variable substitution supports the format `${VARIABLE_NAME}`
- The script returns appropriate exit codes for success/failure

## Troubleshooting

### arsync command not found

If you get "arsync: command not found" after installation:

1. **Check if the wrapper script exists:**
   ```bash
   ls -la ~/.local/bin/arsync
   ```

2. **Check your PATH:**
   ```bash
   echo $PATH | grep -o "$HOME/.local/bin"
   ```

3. **Reload your shell configuration:**
   ```bash
   source ~/.bashrc
   # or restart your terminal
   ```

4. **Test the wrapper script directly:**
   ```bash
   ~/.local/bin/arsync --help
   ```

5. **If PATH is missing, add it manually:**
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```
