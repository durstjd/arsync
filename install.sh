#!/bin/bash
# arsync install script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARSYNC_DIR="$SCRIPT_DIR"

echo -e "${BLUE}Installing arsync...${NC}"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo -e "${RED}Error: pip is required but not installed.${NC}"
    exit 1
fi

# Determine pip command
PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
cd "$ARSYNC_DIR"
$PIP_CMD install -r requirements.txt

# Create ~/.local/bin if it doesn't exist
mkdir -p "$HOME/.local/bin"

# Create arsync wrapper script
echo -e "${YELLOW}Creating arsync wrapper script...${NC}"
cat > "$HOME/.local/bin/arsync" << 'EOF'
#!/bin/bash
# arsync wrapper script

# Set the arsync directory to the installation location
ARSYNC_DIR="ARSYNC_DIR_PLACEHOLDER"

# Check if arsync.py exists
if [ ! -f "$ARSYNC_DIR/arsync.py" ]; then
    echo "Error: arsync.py not found at $ARSYNC_DIR. Please reinstall arsync."
    exit 1
fi

# Handle refresh command
if [ "$1" = "refresh" ]; then
    echo "Refreshing bash completion..."
    if [ -f "$HOME/.bash_completion.d/arsync" ]; then
        source "$HOME/.bash_completion.d/arsync"
        echo "Bash completion refreshed."
    else
        echo "Warning: Completion script not found."
    fi
    exit 0
fi

# Run arsync.py with all arguments (don't change directory)
python3 "$ARSYNC_DIR/arsync.py" "$@"
EOF

# Replace the placeholder with the actual directory
sed -i "s|ARSYNC_DIR_PLACEHOLDER|$ARSYNC_DIR|g" "$HOME/.local/bin/arsync"

# Make the wrapper script executable
chmod +x "$HOME/.local/bin/arsync"

# Create bash completion script
echo -e "${YELLOW}Creating bash completion script...${NC}"

# Create completion directory if it doesn't exist
mkdir -p "$HOME/.bash_completion.d"

# Create completion script in standard location
cat > "$HOME/.bash_completion.d/arsync" << 'EOF'
# arsync bash completion

_arsync_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # Get sync names from config file (refreshed on every run)
    local sync_names=""
    if [ -f "$HOME/.config/arsync.conf" ]; then
        sync_names=$(python3 -c "
import yaml
import sys
try:
    with open('$HOME/.config/arsync.conf', 'r') as f:
        config = yaml.safe_load(f)
    if 'sync' in config:
        print(' '.join(config['sync'].keys()))
except:
    pass
" 2>/dev/null)
    fi
    
    # Define options
    opts="--help --version --list --dry-run --no-parallel --config refresh $sync_names"
    
    case "${prev}" in
        --config|-c)
            COMPREPLY=( $(compgen -f -- "${cur}") )
            return 0
            ;;
        arsync)
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
    esac
    
    # Complete sync names and options
    COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
    return 0
}

complete -F _arsync_completion arsync
EOF

# Add arsync to PATH if not already there
echo -e "${YELLOW}Adding arsync to PATH...${NC}"
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo -e "${GREEN}Added $HOME/.local/bin to PATH in ~/.bashrc${NC}"
    echo -e "${YELLOW}Please run 'source ~/.bashrc' or restart your terminal to use arsync.${NC}"
else
    echo -e "${GREEN}$HOME/.local/bin is already in PATH${NC}"
fi

# Verify the wrapper script was created correctly
if [ -f "$HOME/.local/bin/arsync" ]; then
    echo -e "${GREEN}Wrapper script created at $HOME/.local/bin/arsync${NC}"
    echo -e "${BLUE}You can test it with: $HOME/.local/bin/arsync --help${NC}"
else
    echo -e "${RED}Error: Wrapper script not created${NC}"
fi

# Add bash completion sourcing if not already there
echo -e "${YELLOW}Setting up bash completion...${NC}"
if [ -f "$HOME/.bashrc" ] && ! grep -q "bash_completion.d" "$HOME/.bashrc"; then
    echo '' >> "$HOME/.bashrc"
    echo '# Load bash completion scripts' >> "$HOME/.bashrc"
    echo 'if [ -d "$HOME/.bash_completion.d" ]; then' >> "$HOME/.bashrc"
    echo '    for file in "$HOME/.bash_completion.d"/*; do' >> "$HOME/.bashrc"
    echo '        [ -f "$file" ] && source "$file"' >> "$HOME/.bashrc"
    echo '    done' >> "$HOME/.bashrc"
    echo 'fi' >> "$HOME/.bashrc"
    echo -e "${GREEN}Added bash completion loading to ~/.bashrc${NC}"
fi

# Source the completion script
if [ -f "$HOME/.bash_completion.d/arsync" ]; then
    source "$HOME/.bash_completion.d/arsync"
    echo -e "${GREEN}Bash completion loaded.${NC}"
fi

# Create example config if it doesn't exist
if [ ! -f "$HOME/.config/arsync.conf" ]; then
    echo -e "${YELLOW}Creating example configuration...${NC}"
    mkdir -p "$HOME/.config"
    cp "$ARSYNC_DIR/arsync.conf.example" "$HOME/.config/arsync.conf"
    echo -e "${GREEN}Example configuration created at $HOME/.config/arsync.conf${NC}"
    echo -e "${YELLOW}Please edit the configuration file to match your setup.${NC}"
fi

echo -e "${GREEN}Installation complete!${NC}"
echo -e "${BLUE}Usage:${NC}"
echo "  arsync                    # Run all syncs"
echo "  arsync sync_name          # Run specific sync"
echo "  arsync --list             # List available syncs"
echo "  arsync --dry-run          # Show what would be done"
echo "  arsync refresh            # Refresh bash completion"
echo ""
echo -e "${YELLOW}Note: If this is your first time installing, please run 'source ~/.bashrc' or restart your terminal.${NC}"
