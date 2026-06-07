use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub id: String,
    pub timestamp: i64,
    pub session_id: String,
    pub capability_type: String,
    pub risk_level: String,
    pub confirmed_by_user: bool,
    pub result: String,
    pub error_message: Option<String>,
    pub duration_ms: u64,
}

pub struct AuditLogger;

impl AuditLogger {
    pub fn log(entry: AuditEntry) {
        log::info!("[AUDIT] {} | {} | risk={} | result={} | {}ms",
            entry.capability_type, entry.session_id, entry.risk_level, entry.result, entry.duration_ms);
    }
}
