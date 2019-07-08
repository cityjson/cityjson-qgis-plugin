import pytest

from core.settings import save_defaults, load_settings

class TestSettings:
    """A class to test handling of settings for the plugin"""

    def test_load_defaults(self):
        """Tests if the default settings are loaded correctly"""
        save_defaults()
        colors = load_settings()

        assert len(colors) == 5
