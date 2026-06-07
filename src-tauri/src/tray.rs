use tauri::{
    AppHandle, Manager,
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
};

/// 根据系统语言获取菜单文本
fn get_menu_texts() -> (&'static str, &'static str, &'static str, &'static str) {
    let locale = sys_locale::get_locale().unwrap_or_default();
    if locale.starts_with("zh") {
        ("显示窗口", "隐藏窗口", "设置", "退出")
    } else {
        ("Show Window", "Hide Window", "Settings", "Quit")
    }
}

/// 初始化系统托盘
pub fn setup(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let (show_text, hide_text, settings_text, quit_text) = get_menu_texts();

    // 创建菜单项
    let show_item = MenuItem::with_id(app, "show", show_text, true, None::<&str>)?;
    let hide_item = MenuItem::with_id(app, "hide", hide_text, true, None::<&str>)?;
    let settings_item = MenuItem::with_id(app, "settings", settings_text, true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", quit_text, true, None::<&str>)?;

    // 构建菜单
    let menu = Menu::with_items(
        app,
        &[&show_item, &hide_item, &settings_item, &quit_item],
    )?;

    // 加载托盘图标（缺失时不 panic，托盘仍可工作）
    let icon = app.default_window_icon().cloned().unwrap_or_else(|| {
        // 创建 1x1 透明像素作为 fallback
        tauri::image::Image::new_owned(vec![0u8; 4], 1, 1)
    });

    // 创建托盘图标
    let _tray = TrayIconBuilder::new()
        .icon(icon)
        .menu(&menu)
        .tooltip("Auralis — 桌面精灵")
        .on_menu_event(move |app, event| {
            match event.id().as_ref() {
                "show" => {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "hide" => {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.hide();
                    }
                }
                "settings" => {
                    // 显示窗口并通知前端打开设置
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                        let _ = window.eval("window.dispatchEvent(new CustomEvent('open-settings'))");
                    }
                }
                "quit" => {
                    app.exit(0);
                }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            // 左键点击托盘 → 显示/隐藏窗口
            if let tauri::tray::TrayIconEvent::Click {
                button: tauri::tray::MouseButton::Left,
                button_state: tauri::tray::MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    if window.is_visible().unwrap_or(false) {
                        let _ = window.hide();
                    } else {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
            }
        })
        .build(app)?;

    Ok(())
}
