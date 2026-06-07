use serde_json::{json, Value};

pub async fn read(path: &str) -> Result<Value, String> {
    tokio::fs::read_to_string(path).await
        .map(|c| json!({"content": c}))
        .map_err(|e| format!("读取文件失败: {}", e))
}

pub async fn write(path: &str, content: &str) -> Result<Value, String> {
    tokio::fs::write(path, content).await
        .map(|_| json!({"success": true}))
        .map_err(|e| format!("写入文件失败: {}", e))
}

pub async fn delete(path: &str, _recursive: bool) -> Result<Value, String> {
    super::super::safety::SafetyHooks::check_delete_path(path)?;
    trash::delete(path).map(|_| json!({"deleted": path})).map_err(|e| format!("删除文件失败: {}", e))
}

pub async fn list(path: &str, _pattern: Option<&str>) -> Result<Value, String> {
    let mut entries = Vec::new();
    let mut dir = tokio::fs::read_dir(path).await.map_err(|e| format!("读取目录失败: {}", e))?;
    while let Some(entry) = dir.next_entry().await.map_err(|e| e.to_string())? {
        let meta = entry.metadata().await.map_err(|e| e.to_string())?;
        entries.push(json!({"name": entry.file_name().to_string_lossy(), "path": entry.path().to_string_lossy(), "is_dir": meta.is_dir(), "size": meta.len()}));
    }
    Ok(json!({"entries": entries}))
}
