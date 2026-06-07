use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload")]
pub enum Capability {
    #[serde(rename = "file.read")]
    FileRead { path: String },
    #[serde(rename = "file.write")]
    FileWrite { path: String, content: String },
    #[serde(rename = "file.delete")]
    FileDelete { path: String, recursive: bool },
    #[serde(rename = "file.list")]
    FileList { path: String, pattern: Option<String> },
    #[serde(rename = "file.move")]
    FileMove { from: String, to: String },
    #[serde(rename = "file.copy")]
    FileCopy { from: String, to: String },
    #[serde(rename = "file.search")]
    FileSearch { query: String, scope: String },
    #[serde(rename = "app.launch")]
    AppLaunch { app_id: String, args: Option<Vec<String>> },
    #[serde(rename = "app.close")]
    AppClose { app_id: String, pid: Option<u32> },
    #[serde(rename = "app.list")]
    AppList,
    #[serde(rename = "system.info")]
    SystemInfo,
    #[serde(rename = "system.lock")]
    SystemLock,
    #[serde(rename = "system.shutdown")]
    SystemShutdown { delay: Option<u32> },
    // UI 自动化
    #[serde(rename = "ui.click")]
    UIClick { x: i32, y: i32 },
    #[serde(rename = "ui.type")]
    UIType { text: String },
    #[serde(rename = "ui.screenshot")]
    UIScreenshot { region: Option<ScreenRegion> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenRegion {
    pub x: i32,
    pub y: i32,
    pub w: u32,
    pub h: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityRequest {
    pub id: String,
    pub capability: Capability,
    pub context: CapabilityContext,
    pub policy: Option<PolicyRequest>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityContext {
    pub os: String,
    pub user: String,
    pub session_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyRequest {
    pub require_confirmation: bool,
    pub risk_score: f64,
    pub audit: bool,
    pub rollback: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityResult {
    pub id: String,
    pub success: bool,
    pub data: Option<serde_json::Value>,
    pub error: Option<String>,
    /// 当操作需要用户确认时，此字段包含确认信息
    #[serde(skip_serializing_if = "Option::is_none")]
    pub needs_confirmation: Option<ConfirmationInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfirmationInfo {
    pub message: String,
    pub risk_level: String,
    pub capability_type: String,
}
