use ops_telemetry_mcp::{server::OpsTelemetryServer, state::AppState};
use rmcp::ServiceExt;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // NON-NEGOTIABLE RULE 1: Stdio safety
    // The Rust stdio MCP server must NEVER write to stdout except via MCP JSON-RPC transport!
    // Direct tracing logs exclusively to stderr.
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .init();

    tracing::info!("Starting ops-telemetry-mcp server over stdio...");

    let state = AppState::new();
    let server = OpsTelemetryServer::new(state);

    let service = server.serve(rmcp::transport::stdio()).await?;
    service.waiting().await?;

    Ok(())
}
