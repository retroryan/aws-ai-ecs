#!/bin/bash

# Enhanced Logging Module
# Provides file-based logging functionality that extends common.sh logging
# Used by deploy-services.sh and other scripts that need detailed logging

# Ensure common.sh is sourced (it should be sourced by the calling script)
if [ -z "$COMMON_SOURCED" ]; then
    echo "Error: common.sh must be sourced before enhanced_logging.sh"
    exit 1
fi

# Mark this module as sourced
export ENHANCED_LOGGING_SOURCED=true

# =====================================================================
# Enhanced Logging Configuration
# =====================================================================

# Default log directory and file setup
setup_log_file() {
    local script_name="${1:-deployment}"
    local log_dir="${2:-${SCRIPT_DIR}/logs}"
    
    # Create logs directory if it doesn't exist
    mkdir -p "$log_dir"
    
    # Generate log file with timestamp
    LOG_FILE="${log_dir}/${script_name}_$(date +%Y%m%d_%H%M%S).log"
    
    # Export for use by other functions
    export LOG_FILE
    export LOG_DIR="$log_dir"
    
    # Initialize log file
    echo "================================================================================" >> "$LOG_FILE"
    echo "Log started at: $(date)" >> "$LOG_FILE"
    echo "Script: $script_name" >> "$LOG_FILE"
    echo "Working directory: $(pwd)" >> "$LOG_FILE"
    echo "User: $(whoami)" >> "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
    
    echo "Log file initialized: $LOG_FILE"
}

# =====================================================================
# Enhanced Logging Functions
# =====================================================================

# Write directly to log file with timestamp
log_to_file() {
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ -n "$LOG_FILE" ]; then
        echo "[$timestamp] $message" >> "$LOG_FILE"
    fi
}

# Enhanced log function with both console and file output
# This extends the basic logging from common.sh
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Log to file with timestamp and level
    if [ -n "$LOG_FILE" ]; then
        echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    fi
    
    # Log to console with colors (using common.sh color definitions)
    case $level in
        INFO)
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        STEP)
            echo -e "${BLUE}[STEP]${NC} $message"
            ;;
        DEBUG)
            echo -e "${NC}[DEBUG]${NC} $message"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Enhanced wrapper functions that use the file-based log function
# These override the basic functions from common.sh when enhanced logging is enabled
log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_step() {
    log "STEP" "$@"
}

log_debug() {
    log "DEBUG" "$@"
}

# =====================================================================
# Utility Functions
# =====================================================================

# Function to capture command output to both console and log
log_command() {
    local command="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    log_info "Executing: $command"
    
    if [ -n "$LOG_FILE" ]; then
        echo "[$timestamp] [COMMAND] $command" >> "$LOG_FILE"
        echo "[$timestamp] [OUTPUT] BEGIN" >> "$LOG_FILE"
        
        # Execute command and capture output
        local output
        local exit_code
        output=$($command 2>&1)
        exit_code=$?
        
        # Log the output
        echo "$output" >> "$LOG_FILE"
        echo "[$timestamp] [OUTPUT] END (exit code: $exit_code)" >> "$LOG_FILE"
        
        # Also display to console
        if [ $exit_code -eq 0 ]; then
            log_info "Command completed successfully"
        else
            log_error "Command failed with exit code: $exit_code"
            echo "$output"
        fi
        
        return $exit_code
    else
        # Fallback to direct execution if no log file
        $command
    fi
}

# Function to log deployment section headers
log_deployment_section() {
    local section_title="$1"
    local separator="================================================================================"
    
    echo "$separator"
    log_step "$section_title"
    echo "$separator"
    
    if [ -n "$LOG_FILE" ]; then
        echo "$separator" >> "$LOG_FILE"
        log_to_file "[SECTION] $section_title"
        echo "$separator" >> "$LOG_FILE"
    fi
}

# Function to finalize log file
finalize_log() {
    local status="${1:-completed}"
    
    if [ -n "$LOG_FILE" ]; then
        echo "================================================================================" >> "$LOG_FILE"
        log_to_file "Log ended at: $(date) - Status: $status"
        echo "================================================================================" >> "$LOG_FILE"
        
        log_info "Detailed log saved to: $LOG_FILE"
    fi
}