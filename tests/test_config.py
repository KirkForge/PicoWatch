"""PicoWatch Config tests."""

from picowatch.config import DEFAULT_THRESHOLD_BLOCK, DEFAULT_THRESHOLD_WARN, PicoWatchConfig


class TestConfig:
    def test_defaults(self) -> None:
        """Default config values are correct."""
        config = PicoWatchConfig()
        assert config.threshold_block == DEFAULT_THRESHOLD_BLOCK
        assert config.threshold_warn == DEFAULT_THRESHOLD_WARN
        assert config.max_prompt_size == 1_000_000
        assert config.port == 8766
        assert config.admin_port == 9091

    def test_from_env(self) -> None:
        """Config loads from environment variables."""
        import os

        os.environ["PICOWATCH_THRESHOLD_BLOCK"] = "0.8"
        os.environ["PICOWATCH_PORT"] = "9999"
        try:
            config = PicoWatchConfig.from_env()
            assert config.threshold_block == 0.8
            assert config.port == 9999
        finally:
            del os.environ["PICOWATCH_THRESHOLD_BLOCK"]
            del os.environ["PICOWATCH_PORT"]
