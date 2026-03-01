//! Unit tests for worker management demonstrating async rstest patterns.

#[cfg(test)]
mod tests {
    use rstest::*;
    use std::path::PathBuf;
    use std::sync::Arc;
    use tempfile::TempDir;

    use crate::process::MockClaudeProcess;
    use crate::worker::Worker;

    // ─── fixtures ────────────────────────────────────────────────

    /// Fixture: temporary worktree directory.
    #[fixture]
    fn worktree_dir() -> (TempDir, PathBuf) {
        let dir = TempDir::new().unwrap();
        let path = dir.path().to_path_buf();
        (dir, path)
    }

    /// Fixture: a no-op mock process factory.
    #[fixture]
    fn mock_process() -> MockClaudeProcess {
        MockClaudeProcess::new()
    }

    /// Fixture: worker with ID 1 and worktree path.
    #[fixture]
    fn test_worker(
        worktree_dir: (TempDir, PathBuf),
        mock_process: MockClaudeProcess,
    ) -> (TempDir, Worker) {
        let (guard, path) = worktree_dir;
        let worker = Worker::new(1, path, Arc::new(mock_process));
        (guard, worker)
    }

    // ─── basic worker tests ──────────────────────────────────────

    #[rstest]
    fn worker_has_valid_worktree_path(test_worker: (TempDir, Worker)) {
        let (_guard, worker) = test_worker;
        assert!(worker.worktree_path.exists());
    }

    #[rstest]
    #[case(1)]
    #[case(2)]
    #[case(5)]
    fn worker_id_matches(
        #[case] id: u32,
        worktree_dir: (TempDir, PathBuf),
        mock_process: MockClaudeProcess,
    ) {
        let (_guard, path) = worktree_dir;
        let worker = Worker::new(id, path, Arc::new(mock_process));
        assert_eq!(worker.id, id);
    }

    #[rstest]
    fn worker_exposes_process_factory(test_worker: (TempDir, Worker)) {
        let (_guard, worker) = test_worker;
        // Verify process_factory() returns without panic
        let _factory = worker.process_factory();
    }

    // ─── async test example (for when spawn logic is implemented) ─

    #[rstest]
    #[tokio::test]
    async fn worker_spawn_placeholder() {
        // Placeholder for async worker spawn test.
        // Will use tokio::test + rstest fixture injection.
        tokio::time::sleep(std::time::Duration::from_millis(1)).await;
        assert!(true, "async test infrastructure works");
    }
}
