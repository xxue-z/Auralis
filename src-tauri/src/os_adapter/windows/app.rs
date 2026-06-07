use serde_json::{json, Value};
use std::process::Command;

pub async fn launch(app_id: &str, _args: Option<&[String]>) -> Result<Value, String> {
    Command::new("cmd").args(["/C", "start", "", app_id]).spawn()
        .map(|child| json!({"pid": child.id()}))
        .map_err(|e| format!("启动应用失败: {}", e))
}

pub async fn close(app_id: &str, pid: Option<u32>) -> Result<Value, String> {
    let output = if let Some(pid) = pid {
        Command::new("taskkill").args(["/PID", &pid.to_string(), "/F"]).output()
    } else {
        Command::new("taskkill").args(["/IM", app_id, "/F"]).output()
    };
    output.map(|o| json!({"success": o.status.success()})).map_err(|e| format!("关闭应用失败: {}", e))
}

pub async fn list() -> Result<Value, String> {
    let output = Command::new("powershell")
        .args(["-Command", "Get-Process | Select-Object Id, ProcessName, MainWindowTitle | ConvertTo-Json"])
        .output().map_err(|e| format!("获取进程列表失败: {}", e))?;
    Ok(json!({"processes": String::from_utf8_lossy(&output.stdout)}))
}
