use crate::os_adapter::capability::CapabilityRequest;
use crate::os_adapter::router::OSAdapterRouter;
use serde::{Deserialize, Serialize};
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
    pub cubism_version: u32,
}

/// 提取 Live2D 模型压缩包到数据目录，递归查找 .model3.json / .model.json
/// 内部逻辑，供两个命令共用（内存 IPC 和 文件路径）
fn do_extract(app: &AppHandle, zip_data: &[u8], extensions_path: Option<&str>) -> Result<ExtractModelResult, String> {
    let models_dir = match extensions_path {
        Some(p) if !p.is_empty() => Path::new(p).join("models"),
        _ => app.path().app_data_dir()
            .map_err(|e| format!("获取数据目录失败: {}", e))?
            .join("models"),
    };

    std::fs::create_dir_all(&models_dir)
        .map_err(|e| format!("创建 models 目录失败: {}", e))?;

    // 确保 asset 协议可以访问此 models 目录（自定义 extensions_path 时默认 scope 不覆盖）
    let _ = app.asset_protocol_scope().allow_directory(&models_dir, true);

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
        let fname = Path::new(&lower).file_name()
            .and_then(|s| s.to_str()).unwrap_or("");
        let is_cubism4 = lower.ends_with(".model3.json");
        if is_cubism4 || fname == "model.json" || fname.ends_with(".model.json") {
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

    let cubism_version: u32 = if model_json.to_lowercase().ends_with(".model3.json") { 4 } else { 2 };

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
        cubism_version,
    })
}

/// 从内存数据提取（已有方式，保留兼容）
#[tauri::command]
pub async fn extract_model_zip(
    app: AppHandle,
    zip_data: Vec<u8>,
) -> Result<ExtractModelResult, String> {
    do_extract(&app, &zip_data, None)
}

/// 从文件路径提取（避免 JS 读取大文件阻塞 UI）
/// extensions_path: 可选，扩展文件夹路径，模型将保存在 {extensions_path}/models/ 下
#[tauri::command]
pub async fn extract_model_zip_from_path(
    app: AppHandle,
    zip_path: String,
    extensions_path: Option<String>,
) -> Result<ExtractModelResult, String> {
    let zip_data = std::fs::read(&zip_path)
        .map_err(|e| format!("读取 ZIP 文件失败 ({}): {}", zip_path, e))?;
    do_extract(&app, &zip_data, extensions_path.as_deref())
}

/// 在文件管理器中打开指定路径
#[tauri::command]
pub async fn open_in_explorer(path: String) -> Result<(), String> {
    open::that(&path)
        .map_err(|e| format!("打开路径失败: {}", e))
}

/// 递归删除已导入模型的目录
#[tauri::command]
pub async fn delete_model_dir(path: String) -> Result<(), String> {
    let dir = std::path::Path::new(&path);
    if !dir.exists() {
        return Ok(());
    }
    std::fs::remove_dir_all(dir)
        .map_err(|e| format!("删除模型目录失败 ({}): {}", path, e))
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

/// 获取应用数据默认目录路径
#[tauri::command]
pub async fn get_app_data_dir(app: AppHandle) -> Result<String, String> {
    app.path().app_data_dir()
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| format!("获取数据目录失败: {}", e))
}

/// 迁移扩展文件夹内容
/// 将 old_path 下各子目录（models/ 等）全部复制到 new_path 对应子目录，然后清除 old_path 中已迁移的内容
#[tauri::command]
pub async fn migrate_extensions(
    old_path: String,
    new_path: String,
) -> Result<(), String> {
    let old = Path::new(&old_path);
    let new = Path::new(&new_path);

    if !old.exists() {
        // 旧路径不存在，无需迁移
        return Ok(());
    }

    std::fs::create_dir_all(new)
        .map_err(|e| format!("创建目标目录失败: {}", e))?;

    let dir = std::fs::read_dir(old)
        .map_err(|e| format!("读取旧目录失败: {}", e))?;

    for entry in dir {
        let entry = entry.map_err(|e| format!("遍历目录失败: {}", e))?;
        let entry_name = entry.file_name();
        let entry_path = entry.path();

        if !entry_path.is_dir() { continue; }

        let dest = new.join(&entry_name);
        log::info!("迁移扩展目录: {:?} -> {:?}", entry_path, dest);

        // 创建目标子目录
        std::fs::create_dir_all(&dest)
            .map_err(|e| format!("创建目标子目录失败 ({}): {}", dest.display(), e))?;

        // 递归复制文件
        fn copy_dir(src: &Path, dst: &Path) -> Result<(), String> {
            if src.is_file() {
                std::fs::copy(src, dst)
                    .map_err(|e| format!("复制文件失败 ({} -> {}): {}", src.display(), dst.display(), e))?;
                return Ok(());
            }
            std::fs::create_dir_all(dst)
                .map_err(|e| format!("创建目录失败 ({}): {}", dst.display(), e))?;
            let entries = std::fs::read_dir(src)
                .map_err(|e| format!("读取目录失败 ({}): {}", src.display(), e))?;
            for e in entries {
                let e = e.map_err(|e| format!("遍历目录失败: {}", e))?;
                copy_dir(&e.path(), &dst.join(e.file_name()))?;
            }
            Ok(())
        }

        copy_dir(&entry_path, &dest)?;

        // 清除已迁移的旧目录
        std::fs::remove_dir_all(&entry_path)
            .map_err(|e| format!("清除旧目录失败 ({}): {}", entry_path.display(), e))?;
    }

    Ok(())
}

/// 插件元信息
#[derive(Serialize, Deserialize, Clone)]
pub struct PluginInfo {
    pub id: String,
    pub name: String,
    pub version: String,
    pub description: String,
    pub author: String,
    pub source: String, // "system" 或 "user"
    pub added_at: String,
    pub enabled: bool,
}

/// 解析插件目录下的 plugin.json
fn read_plugin_json(plugin_dir: &Path, source: &str) -> Option<PluginInfo> {
    let json_path = plugin_dir.join("plugin.json");
    if !json_path.exists() {
        return None;
    }
    let content = std::fs::read_to_string(json_path).ok()?;
    let meta: serde_json::Value = serde_json::from_str(&content).ok()?;
    let name = meta.get("name")?.as_str()?;
    let folder_name = plugin_dir.file_name()?.to_string_lossy().to_string();
    Some(PluginInfo {
        id: folder_name.clone(),
        name: name.to_string(),
        version: meta.get("version").and_then(|v| v.as_str()).unwrap_or("0.0.0").to_string(),
        description: meta.get("description").and_then(|v| v.as_str()).unwrap_or("").to_string(),
        author: meta.get("author").and_then(|v| v.as_str()).unwrap_or("").to_string(),
        source: source.to_string(),
        added_at: "".to_string(),
        enabled: true,
    })
}

/// 列出系统插件目录下的所有插件
#[tauri::command]
pub async fn list_system_plugins() -> Result<Vec<PluginInfo>, String> {
    let exe_dir = std::env::current_exe()
        .map_err(|e| format!("获取可执行文件路径失败: {}", e))?
        .parent()
        .ok_or("无法获取可执行文件目录")?
        .to_path_buf();

    // Try multiple possible paths for the plugins directory
    // Dev mode: exe can be at target/debug/ or src-tauri/target/debug/
    let candidates = [
        exe_dir.join("../../plugins"),          // Project root /plugins
        exe_dir.join("../../../plugins"),       // src-tauri/target/debug -> project root /plugins
        exe_dir.join("../plugins"),             // One level up
        exe_dir.join("plugins"),                // Same dir
    ];

    let plugins_dir = candidates.iter().find(|p| p.exists());

    let plugins_dir = match plugins_dir {
        Some(p) => std::fs::canonicalize(p)
            .map_err(|e| format!("解析插件目录失败: {}", e))?,
        None => return Ok(vec![]),
    };

    log::info!("系统插件目录: {}", plugins_dir.display());

    let mut plugins = Vec::new();
    let dir = std::fs::read_dir(&plugins_dir)
        .map_err(|e| format!("读取插件目录失败: {}", e))?;

    for entry in dir {
        let entry = entry.map_err(|e| format!("遍历插件目录失败: {}", e))?;
        if !entry.path().is_dir() { continue; }
        if let Some(info) = read_plugin_json(&entry.path(), "system") {
            plugins.push(info);
        }
    }

    Ok(plugins)
}

/// 列出用户导入的插件（扩展目录下）
#[tauri::command]
pub async fn list_user_plugins(extensions_path: String) -> Result<Vec<PluginInfo>, String> {
    let plugins_dir = Path::new(&extensions_path).join("plugins");
    if !plugins_dir.exists() {
        let _ = std::fs::create_dir_all(&plugins_dir);
        return Ok(vec![]);
    }
    let mut plugins = Vec::new();
    let dir = std::fs::read_dir(&plugins_dir)
        .map_err(|e| format!("读取用户插件目录失败: {}", e))?;
    for entry in dir {
        let entry = entry.map_err(|e| format!("遍历用户插件目录失败: {}", e))?;
        if !entry.path().is_dir() { continue; }
        if let Some(info) = read_plugin_json(&entry.path(), "user") {
            plugins.push(info);
        }
    }
    Ok(plugins)
}

/// 导入插件（复制目录到扩展目录下的 plugins/ 子目录）
#[tauri::command]
pub async fn import_plugin(source_path: String, extensions_path: String) -> Result<PluginInfo, String> {
    let src = Path::new(&source_path);
    if !src.exists() || !src.is_dir() {
        return Err("源目录不存在或不是一个目录".to_string());
    }

    let folder_name = src.file_name()
        .ok_or("无法获取目录名")?
        .to_string_lossy()
        .to_string();

    let plugins_dir = Path::new(&extensions_path).join("plugins");
    std::fs::create_dir_all(&plugins_dir)
        .map_err(|e| format!("创建插件目录失败: {}", e))?;
    let dest_base = plugins_dir.join(&folder_name);
    if dest_base.exists() {
        return Err(format!("插件 '{}' 已存在", folder_name));
    }

    // 验证源目录包含 plugin.json
    let meta = read_plugin_json(src, "user")
        .ok_or("源目录不包含有效的 plugin.json".to_string())?;

    // 递归复制目录
    fn copy_dir_all(src: &Path, dst: &Path) -> Result<(), String> {
        std::fs::create_dir_all(dst)
            .map_err(|e| format!("创建目录失败: {}", e))?;
        let entries = std::fs::read_dir(src)
            .map_err(|e| format!("读取目录失败: {}", e))?;
        for entry in entries {
            let entry = entry.map_err(|e| format!("遍历目录失败: {}", e))?;
            let file_type = entry.file_type().map_err(|e| format!("获取文件类型失败: {}", e))?;
            let dest = dst.join(entry.file_name());
            if file_type.is_dir() {
                copy_dir_all(&entry.path(), &dest)?;
            } else {
                std::fs::copy(&entry.path(), &dest)
                    .map_err(|e| format!("复制文件失败: {}", e))?;
            }
        }
        Ok(())
    }

    copy_dir_all(src, &dest_base)?;

    Ok(meta)
}

/// 从 ZIP 文件导入插件（解压到扩展目录下的 plugins/ 子目录）
#[tauri::command]
pub async fn import_plugin_zip(zip_path: String, extensions_path: String) -> Result<PluginInfo, String> {
    let zip_data = std::fs::read(&zip_path)
        .map_err(|e| format!("读取 ZIP 文件失败: {}", e))?;

    let mut archive = zip::ZipArchive::new(std::io::Cursor::new(zip_data))
        .map_err(|e| format!("ZIP 解析失败: {}", e))?;

    // 查找 plugin.json 在 ZIP 中的位置，确定插件根目录
    let mut plugin_json_entry: Option<(String, usize)> = None;
    for i in 0..archive.len() {
        let entry = archive.by_index(i).map_err(|e| format!("读取 ZIP 条目失败: {}", e))?;
        let name = entry.name().to_string();
        if name.ends_with("plugin.json") {
            plugin_json_entry = Some((name, i));
            break;
        }
    }

    let (plugin_rel_path, idx) = plugin_json_entry
        .ok_or("ZIP 中未找到 plugin.json".to_string())?;

    // 确定插件目录名：取 plugin.json 所在目录的顶层目录名
    let plugin_root = Path::new(&plugin_rel_path).parent()
        .and_then(|p| p.iter().next())
        .and_then(|s| s.to_str())
        .unwrap_or("imported_plugin")
        .to_string();

    if plugin_root.is_empty() {
        return Err("无法确定插件目录名".to_string());
    }

    let plugins_dir = Path::new(&extensions_path).join("plugins");
    std::fs::create_dir_all(&plugins_dir)
        .map_err(|e| format!("创建插件目录失败: {}", e))?;
    let dest_base = plugins_dir.join(&plugin_root);
    if dest_base.exists() {
        return Err(format!("插件 '{}' 已存在", plugin_root));
    }

    // 读取 plugin.json 验证
    let mut plugin_json_content = String::new();
    {
        let mut entry = archive.by_index(idx).map_err(|e| format!("读取 plugin.json 失败: {}", e))?;
        std::io::Read::read_to_string(&mut entry, &mut plugin_json_content)
            .map_err(|e| format!("读取 plugin.json 内容失败: {}", e))?;
    }
    let _meta: serde_json::Value = serde_json::from_str(&plugin_json_content)
        .map_err(|e| format!("plugin.json 格式无效: {}", e))?;

    // 解压所有文件
    for i in 0..archive.len() {
        let mut entry = archive.by_index(i).map_err(|e| format!("读取 ZIP 条目失败: {}", e))?;
        let name = entry.name().to_string();
        let dest_path = dest_base.join(&name);

        if entry.is_dir() {
            std::fs::create_dir_all(&dest_path)
                .map_err(|e| format!("创建目录失败 ({}): {}", dest_path.display(), e))?;
        } else {
            if let Some(parent) = dest_path.parent() {
                std::fs::create_dir_all(parent)
                    .map_err(|e| format!("创建目录失败: {}", e))?;
            }
            let mut buf = Vec::new();
            std::io::Read::read_to_end(&mut entry, &mut buf)
                .map_err(|e| format!("读取文件失败: {}", e))?;
            std::fs::write(&dest_path, &buf)
                .map_err(|e| format!("写入文件失败 ({}): {}", dest_path.display(), e))?;
        }
    }

    read_plugin_json(&dest_base, "user")
        .ok_or("解压完成后读取插件信息失败".to_string())
}

/// 删除用户导入的插件
#[tauri::command]
pub async fn delete_user_plugin(plugin_id: String, extensions_path: String) -> Result<(), String> {
    let plugin_dir = Path::new(&extensions_path).join("plugins").join(&plugin_id);
    if !plugin_dir.exists() {
        return Ok(());
    }
    std::fs::remove_dir_all(&plugin_dir)
        .map_err(|e| format!("删除插件目录失败: {}", e))
}

/// 执行 OS 操作能力
#[tauri::command]
pub async fn execute_capability(request: serde_json::Value) -> Result<serde_json::Value, String> {
    let req: CapabilityRequest = serde_json::from_value(request)
        .map_err(|e| format!("请求解析失败: {}", e))?;
    let result = OSAdapterRouter::execute(req).await;
    serde_json::to_value(result).map_err(|e| format!("结果序列化失败: {}", e))
}
