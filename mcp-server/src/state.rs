use std::{
    fs::{self, File, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    sync::Arc,
};

use anyhow::{Context, Result};
use chrono::Utc;
use fs2::FileExt;
use tokio::sync::Mutex;

use crate::models::{
    DeploymentEntry, IncidentTicket, LogEntry, StructuredError, VALID_SERVICES,
    VALID_TICKET_SEVERITIES,
};

#[derive(Clone)]
pub struct AppState {
    data_dir: PathBuf,
    ticket_mutex: Arc<Mutex<()>>,
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}

impl AppState {
    pub fn new() -> Self {
        let data_dir = Self::resolve_data_dir();
        tracing::info!("Initialized AppState with data_dir: {:?}", data_dir);
        Self {
            data_dir,
            ticket_mutex: Arc::new(Mutex::new(())),
        }
    }

    pub fn with_custom_dir(data_dir: PathBuf) -> Self {
        Self {
            data_dir,
            ticket_mutex: Arc::new(Mutex::new(())),
        }
    }

    /// Resolve the data directory from OPS_DATA_DIR env var or sensible project defaults
    pub fn resolve_data_dir() -> PathBuf {
        if let Ok(val) = std::env::var("OPS_DATA_DIR") {
            let p = PathBuf::from(val);
            if p.is_absolute() && p.exists() {
                return p;
            }
            if let Ok(canonical) = p.canonicalize() {
                return canonical;
            }
        }

        // Try candidate locations relative to cwd or exe
        let candidates = [
            PathBuf::from("../mock_data"),
            PathBuf::from("mock_data"),
            PathBuf::from("../../mock_data"),
        ];

        for c in &candidates {
            if c.exists() {
                if let Ok(can) = c.canonicalize() {
                    return can;
                }
                return c.clone();
            }
        }

        // Fallback to relative path
        PathBuf::from("../mock_data")
    }

    pub fn data_dir(&self) -> &Path {
        &self.data_dir
    }

    /// Read logs.json safely
    pub fn read_logs(&self) -> Result<Vec<LogEntry>> {
        let p = self.data_dir.join("logs.json");
        let content = fs::read_to_string(&p)
            .with_context(|| format!("Failed to read logs file at {:?}", p))?;
        let entries: Vec<LogEntry> = serde_json::from_str(&content)
            .with_context(|| format!("Failed to parse logs JSON from {:?}", p))?;
        Ok(entries)
    }

    /// Read deployments.json safely
    pub fn read_deployments(&self) -> Result<Vec<DeploymentEntry>> {
        let p = self.data_dir.join("deployments.json");
        let content = fs::read_to_string(&p)
            .with_context(|| format!("Failed to read deployments file at {:?}", p))?;
        let entries: Vec<DeploymentEntry> = serde_json::from_str(&content)
            .with_context(|| format!("Failed to parse deployments JSON from {:?}", p))?;
        Ok(entries)
    }

    /// Read runbook markdown for an approved service.
    /// Strictly verifies service against fixed allowlist before path construction.
    pub fn read_runbook(&self, service: &str) -> Result<String, StructuredError> {
        if !VALID_SERVICES.contains(&service) {
            return Err(StructuredError::unknown_service(service));
        }

        let p = self.data_dir.join("runbooks").join(format!("{service}.md"));
        fs::read_to_string(&p).map_err(|e| StructuredError {
            error: "RUNBOOK_READ_ERROR".to_string(),
            message: format!("Failed to read runbook for {service}: {e}"),
            valid_services: None,
            valid_severities: None,
        })
    }

    /// Read release checklist markdown safely
    pub fn read_checklist(&self) -> Result<String, StructuredError> {
        let p = self.data_dir.join("checklist.md");
        fs::read_to_string(&p).map_err(|e| StructuredError {
            error: "CHECKLIST_READ_ERROR".to_string(),
            message: format!("Failed to read checklist at {:?}: {e}", p),
            valid_services: None,
            valid_severities: None,
        })
    }

    /// Concurrency-safe ticket creation with in-process Mutex and OS advisory file lock.
    /// Protects the entire read-allocate-write cycle as one atomic critical section.
    pub async fn create_ticket(
        &self,
        title: String,
        severity: String,
        summary: String,
        assignee: String,
    ) -> Result<IncidentTicket, StructuredError> {
        // Validate inputs
        let trimmed_title = title.trim();
        if trimmed_title.is_empty() {
            return Err(StructuredError::validation_error(
                "title",
                "Title must not be empty",
            ));
        }
        if trimmed_title.len() > 200 {
            return Err(StructuredError::validation_error(
                "title",
                "Title exceeds maximum length of 200 characters",
            ));
        }

        let trimmed_summary = summary.trim();
        if trimmed_summary.is_empty() {
            return Err(StructuredError::validation_error(
                "summary",
                "Summary must not be empty",
            ));
        }
        if trimmed_summary.len() > 2000 {
            return Err(StructuredError::validation_error(
                "summary",
                "Summary exceeds maximum length of 2000 characters",
            ));
        }

        let trimmed_assignee = assignee.trim();
        if trimmed_assignee.is_empty() {
            return Err(StructuredError::validation_error(
                "assignee",
                "Assignee must not be empty",
            ));
        }
        if trimmed_assignee.len() > 100 {
            return Err(StructuredError::validation_error(
                "assignee",
                "Assignee exceeds maximum length of 100 characters",
            ));
        }

        let upper_severity = severity.trim().to_uppercase();
        if !VALID_TICKET_SEVERITIES.contains(&upper_severity.as_str()) {
            return Err(StructuredError {
                error: "INVALID_SEVERITY".to_string(),
                message: format!("Invalid ticket severity: '{severity}'"),
                valid_services: None,
                valid_severities: Some(
                    VALID_TICKET_SEVERITIES
                        .iter()
                        .map(|s| (*s).to_string())
                        .collect(),
                ),
            });
        }

        // 1. Acquire in-process async mutex
        let _guard = self.ticket_mutex.lock().await;

        let data_dir = self.data_dir.clone();
        let title = trimmed_title.to_string();
        let severity = upper_severity;
        let summary = trimmed_summary.to_string();
        let assignee = trimmed_assignee.to_string();

        // 2. Execute blocking file locking and atomic write in tokio spawn_blocking
        tokio::task::spawn_blocking(move || {
            let lock_path = data_dir.join("tickets.lock");
            let tickets_path = data_dir.join("tickets.json");

            // Open lock file
            let lock_file = OpenOptions::new()
                .read(true)
                .write(true)
                .create(true)
                .truncate(false)
                .open(&lock_path)
                .map_err(|e| StructuredError {
                    error: "LOCK_ERROR".to_string(),
                    message: format!("Failed to open lock file at {:?}: {e}", lock_path),
                    valid_services: None,
                    valid_severities: None,
                })?;

            // 3. Acquire OS advisory lock
            lock_file.lock_exclusive().map_err(|e| StructuredError {
                error: "LOCK_ACQUISITION_FAILED".to_string(),
                message: format!("Failed to acquire advisory lock: {e}"),
                valid_services: None,
                valid_severities: None,
            })?;

            // Read existing tickets
            let mut tickets: Vec<IncidentTicket> = if tickets_path.exists() {
                let content = fs::read_to_string(&tickets_path).map_err(|e| StructuredError {
                    error: "READ_TICKETS_FAILED".to_string(),
                    message: format!("Failed to read existing tickets: {e}"),
                    valid_services: None,
                    valid_severities: None,
                })?;
                if content.trim().is_empty() {
                    Vec::new()
                } else {
                    serde_json::from_str(&content).unwrap_or_default()
                }
            } else {
                Vec::new()
            };

            // 5. Determine next incrementing ID
            let mut max_id: u32 = 1000;
            for t in &tickets {
                if let Some(num_str) = t.id.strip_prefix("INC-") {
                    if let Ok(num) = num_str.parse::<u32>() {
                        if num > max_id {
                            max_id = num;
                        }
                    }
                }
            }
            let next_id = format!("INC-{}", max_id + 1);

            let new_ticket = IncidentTicket {
                id: next_id,
                title,
                severity,
                summary,
                assignee,
                status: "OPEN".to_string(),
                created_at: Utc::now().to_rfc3339(),
            };

            tickets.push(new_ticket.clone());

            // 6. Write to temporary file in the same directory
            let pid = std::process::id();
            let nonce = Utc::now().timestamp_nanos_opt().unwrap_or(0);
            let tmp_path = data_dir.join(format!("tickets.tmp.{pid}.{nonce}"));

            let mut tmp_file = OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&tmp_path)
                .map_err(|e| StructuredError {
                    error: "TMP_FILE_ERROR".to_string(),
                    message: format!("Failed to create temporary file at {:?}: {e}", tmp_path),
                    valid_services: None,
                    valid_severities: None,
                })?;

            let serialized = serde_json::to_string_pretty(&tickets).map_err(|e| {
                let _ = fs::remove_file(&tmp_path);
                StructuredError {
                    error: "SERIALIZATION_ERROR".to_string(),
                    message: format!("Failed to serialize tickets: {e}"),
                    valid_services: None,
                    valid_severities: None,
                }
            })?;

            tmp_file.write_all(serialized.as_bytes()).map_err(|e| {
                let _ = fs::remove_file(&tmp_path);
                StructuredError {
                    error: "WRITE_ERROR".to_string(),
                    message: format!("Failed to write tickets to tmp file: {e}"),
                    valid_services: None,
                    valid_severities: None,
                }
            })?;

            // 7. Flush and fsync temporary file
            tmp_file.sync_all().map_err(|e| {
                let _ = fs::remove_file(&tmp_path);
                StructuredError {
                    error: "FSYNC_ERROR".to_string(),
                    message: format!("Failed to fsync temporary file: {e}"),
                    valid_services: None,
                    valid_severities: None,
                }
            })?;
            drop(tmp_file);

            // 8. Atomically rename over tickets.json
            fs::rename(&tmp_path, &tickets_path).map_err(|e| {
                let _ = fs::remove_file(&tmp_path);
                StructuredError {
                    error: "RENAME_ERROR".to_string(),
                    message: format!("Failed to atomically rename tickets file: {e}"),
                    valid_services: None,
                    valid_severities: None,
                }
            })?;

            // 9. Sync parent directory if supported
            if let Ok(dir_file) = File::open(&data_dir) {
                let _ = dir_file.sync_all();
            }

            // 10. Unlock advisory lock
            let _ = lock_file.unlock();

            Ok(new_ticket)
        })
        .await
        .map_err(|e| StructuredError {
            error: "TASK_JOIN_ERROR".to_string(),
            message: format!("Task execution failed: {e}"),
            valid_services: None,
            valid_severities: None,
        })?
    }
}
