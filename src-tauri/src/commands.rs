use crate::os_adapter::capability::CapabilityRequest;
use crate::os_adapter::router::OSAdapterRouter;
use serde::Serialize;
use std::path::Path;
use tauri::{AppHandle, Emitter, Manager};
use zip::ZipArchive;

#[derive(Serialize, Clone)]
pub struct ExtractProgress {
    pub current: usize,
    pub total: usize,
    pub file: String,
}

#[derive(Serialize)]
pub struct ExtractModelResult {
    pub model_id: String,
    pub model_name: String,
    pub model_dir: String,
    pub model_json_path: String,
}

/// 提取 Live2D 模型压缩包到数据目录，递归查找 .model3.json / .model.json
/// zip_data 直接传入 Uint8Array（Tauri IPC 二进制传输）
#[tauri::command]
pub async fn extract_model_zip(
    app: AppHandle,
    zip_data: Vec<u8>,
) -> Result<ExtractModelResult, String> {
    let models_dir = app.path().app_data_dir()
        .map_err(|e| format!("获取数据目录失败: {}", e))?
        .join("models");

    std::fs::create_dir_all(&models_dir)
        .map_err(|e| format!("创建 models 目录失败: {}", e))?;

    let mut archive = ZipArchive::new(std::io::Cursor::new(zip_data))
        .map_err(|e| format!("ZIP 解析失败: {}", e))?;

    let total = archive.len();
    log::info!("ZIP 包含 {} 个条目", total);

    let mut model_json_path: Option<String> = None;
    let mut all_files: Vec<(String, Vec<u8>)> = Vec::new();

    for i in 0..total {
        let mut entry = archive.by_index(i)
            .map_err(|e| format!("读取 ZIP 条目失败: {}", e))?;

        let name = entry.name().to_string();
        let is_dir = entry.is_dir();

        // 发送进度事件
        let _ = app.emit("import-progress", ExtractProgress {
            current: i + 1,
            total,
            file: name.clone(),
        });

        log::debug!("ZIP 条目 #{}: dir={}, name='{}'", i, is_dir, name);

        if is_dir { continue; }

        let lower = name.to_lowercase();
        if lower.ends_with(".model3.json") || lower.ends_with(".model.json") {
            log::info!("找到模型文件: {}", name);
            model_json_path = Some(name.clone());
        }

        let mut buf = Vec::new();
        if entry.size() > 0 {
            std::io::Read::read_to_end(&mut entry, &mut buf)
                .map_err(|e| format!("读取文件失败 ({}): {}", name, e))?;
        }
        all_files.push((name, buf));
    }

    let model_json = model_json_path
        .ok_or("ZIP 中未找到 Live2D 模型文件（.model3.json 或 .model.json）")?;

    // 模型 JSON 所在目录作为模型根目录
    let model_dir = Path::new(&model_json).parent().unwrap_or(Path::new(""));
    let dir_name = model_dir
        .file_name()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| {
            model_json.rsplit_once('/')
                .map(|(d, _)| d.split('/').last().unwrap_or("model").to_string())
                .unwrap_or("model".to_string())
        });

    let model_id = format!("imported_{}", dir_name);

    // 提取到 models/{model_id}/
    let target_dir = models_dir.join(&model_id);
    std::fs::create_dir_all(&target_dir)
        .map_err(|e| format!("创建模型目录失败: {}", e))?;

    for (path, data) in &all_files {
        let dest = target_dir.join(path);
        if let Some(parent) = dest.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("创建子目录失败 ({}): {}", parent.display(), e))?;
        }
        std::fs::write(&dest, data)
            .map_err(|e| format!("写入文件失败 ({}): {}", dest.display(), e))?;
    }

    let model_dir_str = target_dir.to_string_lossy().to_string();
    let model_json_rel = model_json.clone();

    Ok(ExtractModelResult {
        model_id,
        model_name: dir_name,
        model_dir: model_dir_str,
        model_json_path: model_json_rel,
    })
}

/// 在文件管理器中打开指定路径
#[tauri::command]
pub async fn open_in_explorer(path: String) -> Result<(), String> {
    open::that(&path)
        .map_err(|e| format!("打开路径失败: {}", e))
}

#[tauri::command]
pub fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to Auralis.", name)
}

/// 调整 Pet 窗口大小，自动选择最佳扩展方向
#[tauri::command]
pub async fn resize_window(
    app: tauri::AppHandle,
    width: f64,
    height: f64,
    sprite_size: Option<f64>,
) -> Result<(), String> {
    let window = app.get_webview_window("pet")
        .ok_or("Window 'pet' not found")?;

    let pos = window.outer_position().map_err(|e| e.to_string())?;
    let size = window.outer_size().map_err(|e| e.to_string())?;
    let sprite = sprite_size.unwrap_or(96.0);

    let monitor = window.primary_monitor().map_err(|e| e.to_string())?
        .ok_or("Cannot get primary monitor")?;
    let screen = monitor.size();
    let screen_w = screen.width as f64;
    let screen_h = screen.height as f64;

    let sprite_screen_x = pos.x as f64 + size.width as f64 - sprite / 2.0;
    let sprite_screen_y = pos.y as f64 + size.height as f64 - sprite / 2.0;

    let space_right = screen_w - sprite_screen_x;
    let space_left = sprite_screen_x;
    let space_bottom = screen_h - sprite_screen_y;
    let space_top = sprite_screen_y;

    let (new_x, new_y) = if space_left >= width && space_top >= height {
        (sprite_screen_x - width + sprite / 2.0, sprite_screen_y - height + sprite / 2.0)
    } else if space_right >= width && space_top >= height {
        (sprite_screen_x - sprite / 2.0, sprite_screen_y - height + sprite / 2.0)
    } else if space_left >= width && space_bottom >= height {
        (sprite_screen_x - width + sprite / 2.0, sprite_screen_y - sprite / 2.0)
    } else if space_right >= width && space_bottom >= height {
        (sprite_screen_x - sprite / 2.0, sprite_screen_y - sprite / 2.0)
    } else {
        ((screen_w - width) / 2.0, (screen_h - height) / 2.0)
    };

    let max_x = (screen_w - width).max(0.0);
    let max_y = (screen_h - height).max(0.0);
    let final_x = new_x.max(0.0).min(max_x);
    let final_y = new_y.max(0.0).min(max_y);

    window.set_position(tauri::PhysicalPosition::new(final_x as i32, final_y as i32))
        .map_err(|e| e.to_string())?;
    window.set_size(tauri::PhysicalSize::new(width as u32, height as u32))
        .map_err(|e| e.to_string())?;
    window.set_always_on_top(true).ok();

    Ok(())
}

/// 执行 OS 操作能力
#[tauri::command]
pub async fn execute_capability(request: serde_json::Value) -> Result<serde_json::Value, String> {
    let req: CapabilityRequest = serde_json::from_value(request)
        .map_err(|e| format!("请求解析失败: {}", e))?;
    let result = OSAdapterRouter::execute(req).await;
    serde_json::to_value(result).map_err(|e| format!("结果序列化失败: {}", e))
}
