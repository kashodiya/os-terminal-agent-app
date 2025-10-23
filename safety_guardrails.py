"""
Safety Guardrails for OS Terminal Agent CLI
Provides multiple layers of protection against harmful commands and operations.
"""

import re
import os
import platform
import json
from typing import List, Dict, Tuple, Optional
from pathlib import Path

class SafetyGuardrails:
    """Comprehensive safety system for CLI command execution."""
    
    def __init__(self, safe_mode: bool = True, config_file: str = 'safety_config.json'):
        self.safe_mode = safe_mode
        self.is_windows = platform.system().lower() == 'windows'
        self.config = self._load_config(config_file)
        
        # Load configuration
        self.protected_paths = self._get_protected_paths()
        self.dangerous_commands = self._get_dangerous_commands()
        self.protected_extensions = set(self.config.get('protected_extensions', ['.exe', '.dll', '.sys']))
        self.safe_commands = set(self.config.get('safe_commands', []))
        self.destructive_flags = self.config.get('destructive_flags', [])
        
    def _get_protected_paths(self) -> List[str]:
        """Get list of critical system paths to protect."""
        config_paths = self.config.get('protected_paths', {})
        if self.is_windows:
            paths = config_paths.get('windows', [])
            # Add environment-based paths
            paths.extend([
                os.environ.get('SYSTEMROOT', 'C:\\Windows'),
                os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
            ])
            return paths
        else:
            return config_paths.get('unix', [])
    
    def _get_dangerous_commands(self) -> Dict[str, str]:
        """Get dictionary of dangerous commands from config."""
        config_commands = self.config.get('dangerous_commands', {})
        commands = {}
        
        # Combine all risk levels into a single dictionary with descriptions
        for risk_level, cmd_list in config_commands.items():
            for cmd in cmd_list:
                commands[cmd.split()[0]] = f"{risk_level.replace('_', ' ').title()} risk command"
        
        return commands
    
    def assess_command_risk(self, command: str) -> Tuple[str, str, List[str]]:
        """
        Assess the risk level of a command.
        
        Returns:
            Tuple of (risk_level, reason, warnings)
            risk_level: 'safe', 'low', 'medium', 'high', 'critical'
        """
        command = command.strip().lower()
        warnings = []
        
        # Check for dangerous command patterns
        first_word = command.split()[0] if command.split() else ''
        
        # Critical risk patterns from config
        critical_commands = self.config.get('dangerous_commands', {}).get('critical', [])
        if any(pattern in command for pattern in critical_commands):
            return 'critical', 'Destructive system operation detected', ['SYSTEM DESTRUCTION RISK']
        
        # High risk commands
        if first_word in self.dangerous_commands:
            risk_desc = self.dangerous_commands[first_word]
            warnings.append(f'Dangerous command: {risk_desc}')
            
            # Check for additional high-risk patterns
            if any(pattern in command for pattern in self.destructive_flags):
                warnings.append('Recursive/forced operation detected')
                return 'high', f'High-risk {risk_desc} with destructive flags', warnings
            
            return 'medium', f'Potentially dangerous: {risk_desc}', warnings
        
        # Check for protected paths
        for path in self.protected_paths:
            if path.lower() in command:
                warnings.append(f'Operation on protected system path: {path}')
                return 'high', 'System directory access detected', warnings
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'>\s*nul',  # Output redirection to null
            r'2>&1',     # Error redirection
            r'\|\s*del', # Piped deletion
            r'&\s*del',  # Chained deletion
            r'&&\s*del', # Conditional deletion
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, command):
                warnings.append(f'Suspicious pattern detected: {pattern}')
                return 'medium', 'Suspicious command pattern', warnings
        
        # Safe commands from config
        if first_word in self.safe_commands:
            return 'safe', 'Read-only operation', []
        
        return 'low', 'Standard command', []
    
    def is_path_protected(self, path: str) -> bool:
        """Check if a path is in protected directories."""
        try:
            abs_path = os.path.abspath(path)
            for protected in self.protected_paths:
                if abs_path.startswith(os.path.abspath(protected)):
                    return True
        except:
            pass
        return False
    
    def _load_config(self, config_file: str) -> Dict:
        """Load safety configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_config()
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {config_file}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration if config file is missing."""
        return {
            'safety_settings': {'default_mode': 'safe'},
            'protected_paths': {'windows': [], 'unix': []},
            'dangerous_commands': {'critical': [], 'high_risk': [], 'medium_risk': []},
            'safe_commands': ['dir', 'ls', 'pwd'],
            'destructive_flags': ['-rf', '/s /q'],
            'protected_extensions': ['.exe', '.dll']
        }
    
    def validate_command(self, command: str, working_dir: str = None) -> Dict[str, any]:
        """
        Validate a command before execution.
        
        Returns:
            Dictionary with validation results and recommendations
        """
        risk_level, reason, warnings = self.assess_command_risk(command)
        
        result = {
            'allowed': True,
            'risk_level': risk_level,
            'reason': reason,
            'warnings': warnings,
            'requires_confirmation': False,
            'blocked_reason': None
        }
        
        # Block critical risk commands in safe mode
        if self.safe_mode and risk_level == 'critical':
            result['allowed'] = False
            result['blocked_reason'] = 'Command blocked due to critical risk level'
            return result
        
        # Require confirmation for high/medium risk commands
        if risk_level in ['high', 'medium']:
            result['requires_confirmation'] = True
        
        # Additional validation for working directory
        if working_dir and self.is_path_protected(working_dir):
            result['warnings'].append(f'Working directory is in protected system path: {working_dir}')
            if self.safe_mode:
                result['requires_confirmation'] = True
        
        return result
    
    def get_safe_alternatives(self, command: str) -> List[str]:
        """Suggest safer alternatives for dangerous commands."""
        command_lower = command.lower().strip()
        first_word = command_lower.split()[0] if command_lower.split() else ''
        
        alternatives = {
            'del': ['dir (to list files first)', 'move to recycle bin instead'],
            'rm': ['ls -la (to list files first)', 'mv to backup location'],
            'format': ['chkdsk (to check disk)', 'backup data first'],
            'shutdown': ['Use GUI shutdown', 'Schedule shutdown with delay'],
            'reg': ['Export registry backup first', 'Use Registry Editor GUI'],
            'chmod': ['ls -la (to check current permissions)', 'Use specific permission values'],
            'sudo': ['Use specific sudo command', 'Check if really needed']
        }
        
        return alternatives.get(first_word, ['Review command carefully', 'Consider read-only alternatives'])
    
    def create_backup_recommendation(self, command: str) -> Optional[str]:
        """Recommend backup strategy for potentially destructive commands."""
        destructive_patterns = ['del', 'rm', 'format', 'rmdir', 'rd']
        
        for pattern in destructive_patterns:
            if pattern in command.lower():
                if self.is_windows:
                    return "Consider creating a system restore point: 'rstrui.exe'"
                else:
                    return "Consider creating a backup: 'rsync -av /source/ /backup/'"
        
        return None