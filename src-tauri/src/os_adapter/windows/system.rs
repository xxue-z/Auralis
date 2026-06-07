use serde_json::{json, Value};
use std::process::Command;

pub async fn info() -> Result<Value, String> {
    let output = Command::new("powershell")
        .args(["-Command", "$os = Get-CimInstance Win32_OperatingSystem; @{os=$os.Caption; version=$os.Version; hostname=$env:COMPUTERNAME; arch=$env:PROCESSOR_ARCHITECTURE} | ConvertTo-Json"])
        .output().map_err(|e| format!("获取系统信息失败: {}", e))?;
    serde_json::from_str(&String::from_utf8_lossy(&output.stdout)).map_err(|e| format!("解析失败: {}", e))
}

pub async fn lock() -> Result<Value, String> {
    Command::new("rundll32.exe").args(["user32.dll,LockWorkStation"]).output()
        .map(|_| json!({"locked": true}))
        .map_err(|e| format!("锁定系统失败: {}", e))
}
