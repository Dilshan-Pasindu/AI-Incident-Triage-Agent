use std::fs;

use rmcp::{handler::server::wrapper::Parameters, model::ContentBlock};

use crate::{
    models::{CreateTicketParams, DeploymentHistoryParams, SearchLogsParams, StructuredError},
    server::OpsTelemetryServer,
    state::AppState,
};

fn get_content_text(res: &rmcp::model::CallToolResult) -> &str {
    match &res.content[0] {
        ContentBlock::Text(t) => &t.text,
        _ => panic!("Expected text content block"),
    }
}

fn setup_test_state() -> (AppState, tempfile::TempDir) {
    let tmp = tempfile::tempdir().expect("create tempdir");
    let base = tmp.path();

    // Copy or create test files
    let runbooks_dir = base.join("runbooks");
    fs::create_dir_all(&runbooks_dir).unwrap();

    fs::write(
        runbooks_dir.join("auth-service.md"),
        "# Auth Runbook\nTest content",
    )
    .unwrap();
    fs::write(
        runbooks_dir.join("payments-api.md"),
        "# Payments Runbook\nTest content",
    )
    .unwrap();
    fs::write(
        runbooks_dir.join("notification-worker.md"),
        "# Notification Runbook\nTest content",
    )
    .unwrap();

    fs::write(base.join("checklist.md"), "# Checklist\nTest criteria").unwrap();

    let logs = serde_json::json!([
        {
            "timestamp": "2026-11-20T10:00:00Z",
            "service": "payments-api",
            "severity": "ERROR",
            "message": "DB connection timeout after 5000ms"
        },
        {
            "timestamp": "2026-11-20T09:50:00Z",
            "service": "payments-api",
            "severity": "INFO",
            "message": "Transaction completed"
        },
        {
            "timestamp": "2026-11-20T09:40:00Z",
            "service": "auth-service",
            "severity": "WARN",
            "message": "Slow token verification"
        }
    ]);
    fs::write(
        base.join("logs.json"),
        serde_json::to_string_pretty(&logs).unwrap(),
    )
    .unwrap();

    let deps = serde_json::json!([
        {
            "service": "payments-api",
            "commit": "c4a9f12",
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "status": "success",
            "rolled_back": false,
            "message": "Recent deploy"
        },
        {
            "service": "payments-api",
            "commit": "old0001",
            "timestamp": (chrono::Utc::now() - chrono::Duration::hours(50)).to_rfc3339(),
            "status": "success",
            "rolled_back": false,
            "message": "Old deploy"
        }
    ]);
    fs::write(
        base.join("deployments.json"),
        serde_json::to_string_pretty(&deps).unwrap(),
    )
    .unwrap();

    let state = AppState::with_custom_dir(base.to_path_buf());
    (state, tmp)
}

#[tokio::test]
async fn test_unknown_service_validation() {
    let (state, _tmp) = setup_test_state();
    let server = OpsTelemetryServer::new(state);

    let res = server
        .search_logs(Parameters(SearchLogsParams {
            service_name: "billing-service".to_string(),
            severity: None,
            limit: None,
        }))
        .await
        .unwrap();

    assert_eq!(res.is_error, Some(true));
    let text = get_content_text(&res);
    let err: StructuredError = serde_json::from_str(text).unwrap();
    assert_eq!(err.error, "UNKNOWN_SERVICE");
    assert!(err.valid_services.is_some());
}

#[tokio::test]
async fn test_limit_bounds() {
    let (state, _tmp) = setup_test_state();
    let server = OpsTelemetryServer::new(state);

    // Limit 0 should fail
    let res0 = server
        .search_logs(Parameters(SearchLogsParams {
            service_name: "payments-api".to_string(),
            severity: None,
            limit: Some(0),
        }))
        .await
        .unwrap();
    assert_eq!(res0.is_error, Some(true));

    // Limit 51 should fail
    let res51 = server
        .search_logs(Parameters(SearchLogsParams {
            service_name: "payments-api".to_string(),
            severity: None,
            limit: Some(51),
        }))
        .await
        .unwrap();
    assert_eq!(res51.is_error, Some(true));

    // Limit 1 should succeed
    let res1 = server
        .search_logs(Parameters(SearchLogsParams {
            service_name: "payments-api".to_string(),
            severity: None,
            limit: Some(1),
        }))
        .await
        .unwrap();
    assert_eq!(res1.is_error, Some(false));
}

#[tokio::test]
async fn test_window_hours_bounds() {
    let (state, _tmp) = setup_test_state();
    let server = OpsTelemetryServer::new(state);

    // Window 0 should fail
    let res0 = server
        .get_deployment_history(Parameters(DeploymentHistoryParams {
            service_name: "payments-api".to_string(),
            window_hours: Some(0),
        }))
        .await
        .unwrap();
    assert_eq!(res0.is_error, Some(true));

    // Window 169 should fail
    let res169 = server
        .get_deployment_history(Parameters(DeploymentHistoryParams {
            service_name: "payments-api".to_string(),
            window_hours: Some(169),
        }))
        .await
        .unwrap();
    assert_eq!(res169.is_error, Some(true));

    // Window 24 should succeed and exclude deployment >24h ago
    let res24 = server
        .get_deployment_history(Parameters(DeploymentHistoryParams {
            service_name: "payments-api".to_string(),
            window_hours: Some(24),
        }))
        .await
        .unwrap();
    assert_eq!(res24.is_error, Some(false));
    let text = get_content_text(&res24);
    let deps: Vec<serde_json::Value> = serde_json::from_str(text).unwrap();
    assert_eq!(deps.len(), 1);
    assert_eq!(deps[0]["commit"], "c4a9f12");
}

#[tokio::test]
async fn test_path_traversal_blocked_in_resources() {
    let (state, _tmp) = setup_test_state();
    let server = OpsTelemetryServer::new(state);

    // Attempt path traversal via resource URI
    let traversal_uris = [
        "service://runbooks/../../etc/passwd",
        "service://runbooks/../payments-api",
        "service://runbooks/unknown-service",
        "service://runbooks/auth-service/evil",
    ];

    for uri in traversal_uris {
        let err = server.handle_read_resource(uri);
        assert!(err.is_err(), "Expected error for URI: {}", uri);
    }

    // Valid resource URIs must succeed
    let valid_runbook = server.handle_read_resource("service://runbooks/payments-api");
    assert!(valid_runbook.is_ok());

    let valid_checklist = server.handle_read_resource("config://release-checklist");
    assert!(valid_checklist.is_ok());
}

#[tokio::test]
async fn test_empty_and_oversized_ticket_fields() {
    let (state, _tmp) = setup_test_state();
    let server = OpsTelemetryServer::new(state);

    // Empty title
    let res = server
        .create_incident_ticket(Parameters(CreateTicketParams {
            title: "   ".to_string(),
            severity: "HIGH".to_string(),
            summary: "Valid summary".to_string(),
            assignee: "alice".to_string(),
        }))
        .await
        .unwrap();
    assert_eq!(res.is_error, Some(true));

    // Oversized title (>200)
    let res = server
        .create_incident_ticket(Parameters(CreateTicketParams {
            title: "A".repeat(201),
            severity: "HIGH".to_string(),
            summary: "Valid summary".to_string(),
            assignee: "alice".to_string(),
        }))
        .await
        .unwrap();
    assert_eq!(res.is_error, Some(true));

    // Invalid severity
    let res = server
        .create_incident_ticket(Parameters(CreateTicketParams {
            title: "Valid title".to_string(),
            severity: "ULTRA_CRITICAL".to_string(),
            summary: "Valid summary".to_string(),
            assignee: "alice".to_string(),
        }))
        .await
        .unwrap();
    assert_eq!(res.is_error, Some(true));
}

#[tokio::test]
async fn test_ticket_id_sequential_increment() {
    let (state, _tmp) = setup_test_state();
    let server = OpsTelemetryServer::new(state);

    let t1 = server
        .create_incident_ticket(Parameters(CreateTicketParams {
            title: "First incident".to_string(),
            severity: "HIGH".to_string(),
            summary: "Summary 1".to_string(),
            assignee: "alice".to_string(),
        }))
        .await
        .unwrap();
    assert_eq!(t1.is_error, Some(false));
    let t1_val: serde_json::Value = serde_json::from_str(get_content_text(&t1)).unwrap();
    assert_eq!(t1_val["id"], "INC-1001");

    let t2 = server
        .create_incident_ticket(Parameters(CreateTicketParams {
            title: "Second incident".to_string(),
            severity: "CRITICAL".to_string(),
            summary: "Summary 2".to_string(),
            assignee: "bob".to_string(),
        }))
        .await
        .unwrap();
    assert_eq!(t2.is_error, Some(false));
    let t2_val: serde_json::Value = serde_json::from_str(get_content_text(&t2)).unwrap();
    assert_eq!(t2_val["id"], "INC-1002");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn test_parallel_ticket_concurrency() {
    let (state, _tmp) = setup_test_state();

    const NUM_TICKETS: usize = 20;
    let mut handles = Vec::new();

    for i in 0..NUM_TICKETS {
        let st = state.clone();
        let handle = tokio::spawn(async move {
            st.create_ticket(
                format!("Concurrent incident {i}"),
                "HIGH".to_string(),
                format!("Automated diagnostic summary {i}"),
                format!("engineer_{i}"),
            )
            .await
        });
        handles.push(handle);
    }

    let mut created_ids = Vec::new();
    for h in handles {
        let ticket = h.await.unwrap().expect("ticket creation must succeed");
        created_ids.push(ticket.id);
    }

    // Verify all NUM_TICKETS unique
    created_ids.sort();
    let unique_count = created_ids
        .iter()
        .collect::<std::collections::BTreeSet<_>>()
        .len();
    assert_eq!(unique_count, NUM_TICKETS);

    // Verify file content matches
    let tickets_file = state.data_dir().join("tickets.json");
    let content = fs::read_to_string(tickets_file).unwrap();
    let persisted: Vec<serde_json::Value> = serde_json::from_str(&content).unwrap();
    assert_eq!(persisted.len(), NUM_TICKETS);
}
