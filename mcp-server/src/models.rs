use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

pub const VALID_SERVICES: &[&str] = &["auth-service", "payments-api", "notification-worker"];
pub const VALID_SEVERITIES: &[&str] = &["INFO", "WARN", "ERROR", "FATAL"];
pub const VALID_TICKET_SEVERITIES: &[&str] = &["LOW", "MEDIUM", "HIGH", "CRITICAL"];

/// Structured error payload returned for invalid inputs or unknown resources
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StructuredError {
    pub error: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub valid_services: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub valid_severities: Option<Vec<String>>,
}

impl StructuredError {
    pub fn unknown_service(service: &str) -> Self {
        Self {
            error: "UNKNOWN_SERVICE".to_string(),
            message: format!("Unknown service: '{service}'"),
            valid_services: Some(VALID_SERVICES.iter().map(|s| (*s).to_string()).collect()),
            valid_severities: None,
        }
    }

    pub fn invalid_severity(sev: &str) -> Self {
        Self {
            error: "INVALID_SEVERITY".to_string(),
            message: format!("Invalid severity: '{sev}'"),
            valid_services: None,
            valid_severities: Some(VALID_SEVERITIES.iter().map(|s| (*s).to_string()).collect()),
        }
    }

    pub fn invalid_limit(msg: &str) -> Self {
        Self {
            error: "INVALID_LIMIT".to_string(),
            message: msg.to_string(),
            valid_services: None,
            valid_severities: None,
        }
    }

    pub fn invalid_window(msg: &str) -> Self {
        Self {
            error: "INVALID_WINDOW_HOURS".to_string(),
            message: msg.to_string(),
            valid_services: None,
            valid_severities: None,
        }
    }

    pub fn validation_error(field: &str, msg: &str) -> Self {
        Self {
            error: "VALIDATION_ERROR".to_string(),
            message: format!("Validation failed for field '{field}': {msg}"),
            valid_services: None,
            valid_severities: None,
        }
    }
}

/// Request parameters for search_logs
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct SearchLogsParams {
    /// Service name to filter logs for (e.g., auth-service, payments-api, notification-worker)
    pub service_name: String,
    /// Optional severity level: INFO, WARN, ERROR, FATAL
    #[serde(default)]
    pub severity: Option<String>,
    /// Maximum number of log entries to return (1-50, default 10)
    #[serde(default)]
    pub limit: Option<u32>,
}

/// Log entry representation
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LogEntry {
    pub timestamp: String,
    pub service: String,
    pub severity: String,
    pub message: String,
}

/// Request parameters for get_deployment_history
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct DeploymentHistoryParams {
    /// Service name to inspect deployments for
    pub service_name: String,
    /// Time window in hours to look back (1-168, default 24)
    #[serde(default)]
    pub window_hours: Option<u32>,
}

/// Deployment record representation
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DeploymentEntry {
    pub service: String,
    pub commit: String,
    pub timestamp: String,
    pub status: String,
    pub rolled_back: bool,
    pub message: String,
}

/// Request parameters for create_incident_ticket
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct CreateTicketParams {
    /// Concise title of the incident (1-200 characters)
    pub title: String,
    /// Severity level: LOW, MEDIUM, HIGH, CRITICAL
    pub severity: String,
    /// Detailed diagnostic summary and context (1-2000 characters)
    pub summary: String,
    /// Assigned engineer or team handle (1-100 characters)
    pub assignee: String,
}

/// Persistent Incident Ticket record
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct IncidentTicket {
    pub id: String,
    pub title: String,
    pub severity: String,
    pub summary: String,
    pub assignee: String,
    pub status: String,
    pub created_at: String,
}
