import yaml
import os
import logging

class ConfigManager:
    def __init__(self, api_config_path="config/api_config.yaml", trading_config_path="config/trading_config.yaml"):
        self.api_config_path = api_config_path
        self.trading_config_path = trading_config_path
        self.api_config = self._load_yaml(self.api_config_path)
        self.trading_config = self._load_yaml(self.trading_config_path)

    def _load_yaml(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @property
    def is_real_mode(self):
        mode = self.api_config.get('kis', {}).get('mode', 'VIRTUAL').upper()
        return mode == 'REAL'

    @property
    def kis_creds(self):
        mode = 'real' if self.is_real_mode else 'virtual'
        return self.api_config.get('kis', {}).get(mode, {})

    @property
    def gemini_api_key(self):
        return self.api_config.get('ai', {}).get('gemini_api_key', '')

    @property
    def discord_webhooks(self):
        return self.api_config.get('discord', {})

    def get_strategy_params(self, strategy_name):
        return self.trading_config.get('strategies', {}).get(strategy_name, {})

    @property
    def risk_limits(self):
        return self.trading_config.get('risk_management', {})

    @property
    def system_config(self):
        return self.trading_config.get('system', {})

config_manager = ConfigManager()
