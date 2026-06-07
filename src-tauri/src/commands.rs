use crate::os_adapter::capability::CapabilityRequest;
use crate::os_adapter::router::OSAdapterRouter;

#[tauri::command]
pub fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to Auralis.", name)
}

/// 执行 OS 操作能力
/// 前端传入 JSON 格式的 CapabilityRequest，返回 CapabilityResult
#[tauri::command]
pub async fn execute_capability(request: serde_json::Value) -> Result<serde_json::Value, String> {
    let req: CapabilityRequest = serde_json::from_value(request)
        .map_err(|e| format!("请求解析失败: {}", e))?;
    let result = OSAdapterRouter::execute(req).await;
    serde_json::to_value(result).map_err(|e| format!("结果序列化失败: {}", e))
}
