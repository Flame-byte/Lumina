"""
Configuration Management Module

Responsible for reading and writing YAML configuration files
"""
import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path


class ConfigManager:
    """Configuration manager"""

    def __init__(self, config_dir: str = None):
        """
        Initialize configuration manager

        Args:
            config_dir: Configuration directory, defaults to config/ directory
        """
        if config_dir is None:
            # Get the parent directory of the current file (project root)
            self.config_dir = Path(__file__).parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)

        # Configuration file paths
        self.llm_config_path = self.config_dir / "llm_config.yaml"
        self.agent_config_path = self.config_dir / "agent_config.yaml"

        # Configuration cache
        self._llm_config: Optional[Dict[str, Any]] = None
        self._agent_config: Optional[Dict[str, Any]] = None

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file"""
        if not path.exists():
            raise FileNotFoundError(f"Configuration file does not exist: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _save_yaml(self, path: Path, data: Dict[str, Any]) -> None:
        """Save YAML file"""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)

    def get_llm_config(self, section: str = None) -> Any:
        """
        Get LLM configuration

        Args:
            section: Configuration section, such as 'default', 'planner', 'executor'
                     Returns full configuration if not provided

        Returns:
            Configuration dictionary or configuration value
        """
        if self._llm_config is None:
            self._llm_config = self._load_yaml(self.llm_config_path)

        if section:
            return self._llm_config.get(section, {})
        return self._llm_config

    def get_agent_config(self, section: str = None) -> Any:
        """
        Get Agent configuration

        Args:
            section: Configuration section, such as 'session', 'planner', 'executor', 'tools'
                     Returns full configuration if not provided

        Returns:
            Configuration dictionary or configuration value
        """
        if self._agent_config is None:
            self._agent_config = self._load_yaml(self.agent_config_path)

        if section:
            return self._agent_config.get(section, {})
        return self._agent_config

    def update_llm_config(self, section: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update LLM configuration

        Args:
            section: Configuration section, such as 'default', 'planner', 'executor'
            updates: Configuration items to update

        Returns:
            Updated configuration
        """
        if self._llm_config is None:
            self._llm_config = self._load_yaml(self.llm_config_path)

        if section not in self._llm_config:
            self._llm_config[section] = {}

        # Update configuration
        self._llm_config[section].update(updates)

        # Save to file
        self._save_yaml(self.llm_config_path, self._llm_config)

        return self._llm_config[section]

    def update_agent_config(self, section: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update Agent configuration

        Args:
            section: Configuration section, such as 'session', 'planner', 'executor', 'tools'
            updates: Configuration items to update

        Returns:
            Updated configuration
        """
        if self._agent_config is None:
            self._agent_config = self._load_yaml(self.agent_config_path)

        if section not in self._agent_config:
            self._agent_config[section] = {}

        # Update configuration
        self._agent_config[section].update(updates)

        # Save to file
        self._save_yaml(self.agent_config_path, self._agent_config)

        return self._agent_config[section]

    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration

        Returns:
            Complete dictionary containing llm and agent configurations
        """
        return {
            "llm": self.get_llm_config(),
            "agent": self.get_agent_config()
        }

    def clear_cache(self) -> None:
        """Clear configuration cache, force reload"""
        self._llm_config = None
        self._agent_config = None


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
