use serde::Deserialize;

/// Ralph configuration loaded from ralph.toml.
#[derive(Debug, Deserialize, Default)]
pub struct RalphConfig {
    pub max_workers: Option<u32>,
}
