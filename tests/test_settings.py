# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

from core.settings import save_defaults, load_settings


class TestSettings:
    """A class to test handling of settings for the plugin"""

    def test_load_defaults(self):
        """Tests if the default settings are loaded correctly"""
        save_defaults()
        settings = load_settings()

        assert len(settings["semantic_colors"]) == 5
