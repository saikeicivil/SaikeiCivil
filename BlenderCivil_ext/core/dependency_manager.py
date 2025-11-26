# ==============================================================================
# BlenderCivil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Dependency Manager
Handles checking and installing required dependencies for BlenderCivil
"""

import subprocess
import sys
from typing import Dict, List, Tuple
from .logging_config import get_logger

logger = get_logger(__name__)

class DependencyManager:
    """Manages addon dependencies - checking and installation"""
    
    # Define required dependencies
    DEPENDENCIES = {
        'ifcopenshell': {
            'package': 'ifcopenshell',
            'min_version': '0.8.0',
            'display_name': 'IfcOpenShell',
            'description': 'Required for native IFC operations',
        }
    }
    
    @classmethod
    def check_dependency(cls, dep_key: str) -> Tuple[bool, str]:
        """
        Check if a specific dependency is available.
        
        Args:
            dep_key: Key of the dependency to check
            
        Returns:
            (is_available, version_or_error)
        """
        if dep_key not in cls.DEPENDENCIES:
            return False, f"Unknown dependency: {dep_key}"
        
        dep_info = cls.DEPENDENCIES[dep_key]
        package_name = dep_info['package']
        
        try:
            module = __import__(package_name)
            
            # Try to get version
            version = "unknown"
            if hasattr(module, '__version__'):
                version = module.__version__
            elif hasattr(module, 'version'):
                version = module.version
                
            return True, version
            
        except ImportError:
            return False, "Not installed"
    
    @classmethod
    def check_all_dependencies(cls) -> Dict[str, Tuple[bool, str]]:
        """
        Check all dependencies.
        
        Returns:
            Dict mapping dependency key to (is_available, version_or_error)
        """
        results = {}
        for dep_key in cls.DEPENDENCIES.keys():
            results[dep_key] = cls.check_dependency(dep_key)
        return results
    
    @classmethod
    def has_missing_dependencies(cls) -> bool:
        """Check if any dependencies are missing"""
        results = cls.check_all_dependencies()
        return any(not available for available, _ in results.values())
    
    @classmethod
    def get_missing_dependencies(cls) -> List[str]:
        """Get list of missing dependency keys"""
        results = cls.check_all_dependencies()
        return [key for key, (available, _) in results.items() if not available]
    
    @classmethod
    def install_dependency(cls, dep_key: str) -> Tuple[bool, str]:
        """
        Install a specific dependency using pip.
        
        Args:
            dep_key: Key of the dependency to install
            
        Returns:
            (success, message)
        """
        if dep_key not in cls.DEPENDENCIES:
            return False, f"Unknown dependency: {dep_key}"
        
        dep_info = cls.DEPENDENCIES[dep_key]
        package_name = dep_info['package']
        
        logger.info("Installing %s...", dep_info['display_name'])
        logger.info("Package: %s", package_name)

        try:
            # Get Python executable from Blender
            python_exe = sys.executable
            logger.info("Python: %s", python_exe)

            # Install using pip with --break-system-packages flag
            # This is needed for Blender's Python environment
            cmd = [
                python_exe,
                '-m', 'pip',
                'install',
                package_name,
                '--break-system-packages'
            ]

            logger.info("Command: %s", ' '.join(cmd))
            
            # Run installation with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("Installation successful!")
                return True, f"Successfully installed {dep_info['display_name']}"
            else:
                error_msg = result.stderr or result.stdout
                logger.error("Installation failed!")
                logger.error("Error: %s", error_msg[:200])
                return False, f"Installation failed: {error_msg[:200]}"
                
        except subprocess.TimeoutExpired:
            return False, "Installation timeout (>2 minutes)"
        except Exception as e:
            return False, f"Installation error: {str(e)}"
    
    @classmethod
    def install_all_dependencies(cls) -> Tuple[bool, str]:
        """
        Install all missing dependencies.
        
        Returns:
            (all_success, message)
        """
        missing = cls.get_missing_dependencies()
        
        if not missing:
            return True, "All dependencies already installed"

        logger.info("=" * 60)
        logger.info("Installing %s dependencies...", len(missing))
        logger.info("=" * 60)
        
        all_success = True
        messages = []
        
        for dep_key in missing:
            success, message = cls.install_dependency(dep_key)
            messages.append(f"  • {cls.DEPENDENCIES[dep_key]['display_name']}: {message}")
            
            if not success:
                all_success = False
        
        result_message = "\n".join(messages)

        if all_success:
            logger.info("All dependencies installed successfully!")
            return True, result_message
        else:
            logger.warning("Some installations failed")
            return False, result_message
    
    @classmethod
    def get_status_report(cls) -> str:
        """Get a formatted status report of all dependencies"""
        results = cls.check_all_dependencies()
        
        lines = ["Dependency Status:"]
        lines.append("-" * 40)
        
        for dep_key, (available, version) in results.items():
            dep_info = cls.DEPENDENCIES[dep_key]
            status = "[+]" if available else "[-]"
            version_str = f"({version})" if available else ""
            lines.append(f"{status} {dep_info['display_name']} {version_str}")
            
        return "\n".join(lines)
