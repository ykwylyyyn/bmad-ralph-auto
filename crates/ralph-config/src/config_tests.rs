//! Unit tests for ralph-config demonstrating rstest patterns.

#[cfg(test)]
mod tests {
    use rstest::*;
    use tempfile::TempDir;
    use std::path::PathBuf;
    use crate::config::RalphConfig;

    // ─── rstest fixtures ───────────────────────────────────────────

    /// Fixture: temporary directory with ralph.toml inside.
    #[fixture]
    fn config_dir() -> (TempDir, PathBuf) {
        let dir = TempDir::new().unwrap();
        let path = dir.path().to_path_buf();
        (dir, path)
    }

    /// Fixture: default valid TOML config string.
    #[fixture]
    fn valid_toml() -> String {
        r#"max_workers = 5"#.to_string()
    }

    // ─── basic tests ──────────────────────────────────────────────

    #[rstest]
    fn default_config_has_no_max_workers() {
        let config = RalphConfig::default();
        assert_eq!(config.max_workers, None);
    }

    #[rstest]
    fn parse_valid_toml(valid_toml: String) {
        let config: RalphConfig = toml::from_str(&valid_toml).unwrap();
        assert_eq!(config.max_workers, Some(5));
    }

    // ─── parametrized tests ───────────────────────────────────────

    #[rstest]
    #[case("max_workers = 1", Some(1))]
    #[case("max_workers = 5", Some(5))]
    #[case("", None)]
    fn parse_max_workers(#[case] input: &str, #[case] expected: Option<u32>) {
        let config: RalphConfig = toml::from_str(input).unwrap();
        assert_eq!(config.max_workers, expected);
    }

    // ─── file-based fixture test ──────────────────────────────────

    #[rstest]
    fn load_config_from_file(config_dir: (TempDir, PathBuf), valid_toml: String) {
        let (_guard, path) = config_dir;
        let config_path = path.join("ralph.toml");
        std::fs::write(&config_path, &valid_toml).unwrap();

        let content = std::fs::read_to_string(&config_path).unwrap();
        let config: RalphConfig = toml::from_str(&content).unwrap();
        assert_eq!(config.max_workers, Some(5));
    }
}
