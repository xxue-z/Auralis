use crate::os_adapter::capability::CapabilityRequest;
use crate::os_adapter::router::OSAdapterRouter;
use tauri::Manager;

#[tauri::command]
pub fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to Auralis.", name)
}

/// 调整 Pet 窗口大小，自动选择最佳扩展方向
/// sprite_size: 精灵区域大小（用于计算锚点偏移）
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
    let sprite = sprite_size.unwrap_or(96.0); // 默认精灵 96px

    // 获取屏幕可用区域
    let monitor = window.primary_monitor().map_err(|e| e.to_string())?
        .ok_or("Cannot get primary monitor")?;
    let screen = monitor.size();
    let screen_w = screen.width as f64;
    let screen_h = screen.height as f64;

    // 精灵当前在窗口内的右下角，计算精灵在屏幕上的位置
    let sprite_screen_x = pos.x as f64 + size.width as f64 - sprite / 2.0;
    let sprite_screen_y = pos.y as f64 + size.height as f64 - sprite / 2.0;

    // 根据精灵在屏幕上的位置，选择扩展方向
    // 目标：让精灵保持在屏幕内，窗口尽量不超出屏幕
    let space_right = screen_w - sprite_screen_x;
    let space_left = sprite_screen_x;
    let space_bottom = screen_h - sprite_screen_y;
    let space_top = sprite_screen_y;

    let (new_x, new_y) = if space_left >= width && space_top >= height {
        // 左上空间足够 → 向左上扩展（精灵在右下）
        (sprite_screen_x - width + sprite / 2.0, sprite_screen_y - height + sprite / 2.0)
    } else if space_right >= width && space_top >= height {
        // 右上空间足够 → 向右上扩展（精灵在左下）
        (sprite_screen_x - sprite / 2.0, sprite_screen_y - height + sprite / 2.0)
    } else if space_left >= width && space_bottom >= height {
        // 左下空间足够 → 向左下扩展（精灵在右上）
        (sprite_screen_x - width + sprite / 2.0, sprite_screen_y - sprite / 2.0)
    } else if space_right >= width && space_bottom >= height {
        // 右下空间足够 → 向右下扩展（精灵在左上）
        (sprite_screen_x - sprite / 2.0, sprite_screen_y - sprite / 2.0)
    } else {
        // 四个方向都不够，居中显示
        ((screen_w - width) / 2.0, (screen_h - height) / 2.0)
    };

    // 确保不超出屏幕边界（clamp 在 min > max 时会 panic，用 max/min 替代）
    let max_x = (screen_w - width).max(0.0);
    let max_y = (screen_h - height).max(0.0);
    let final_x = new_x.max(0.0).min(max_x);
    let final_y = new_y.max(0.0).min(max_y);

    window.set_position(tauri::PhysicalPosition::new(final_x as i32, final_y as i32))
        .map_err(|e| e.to_string())?;
    window.set_size(tauri::PhysicalSize::new(width as u32, height as u32))
        .map_err(|e| e.to_string())?;
    // resize 后恢复置顶状态（Tauri 某些平台 resize 会丢失 alwaysOnTop）
    window.set_always_on_top(true).ok();

    Ok(())
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
