use tauri::{
    menu::{CheckMenuItem, Menu, MenuItem, Submenu},
    tray::TrayIconBuilder,
    AppHandle, Manager,
};

use crate::AGENT_MANAGER;

/// 根据系统语言获取菜单文本
fn get_menu_texts() -> (&'static str, &'static str, &'static str, &'static str, &'static str, &'static str) {
    let locale = sys_locale::get_locale().unwrap_or_default();
    if locale.starts_with("zh") {
        ("模式切换", "交互模式", "专注模式", "隐藏模式", "设置", "退出")
    } else {
        ("Mode", "Interactive", "Focus", "Hidden", "Settings", "Quit")
    }
}

fn set_mode_via_eval(window: &tauri::WebviewWindow, mode: &str) {
    let ignore = mode == "focus";
    let js = format!(
        r#"(async () => {{
            window.__TAURI_INTERNALS__.invoke('plugin:window|set_ignore_cursor_events', {{ ignore: {ignore} }}).catch(() => {{}});
            window.dispatchEvent(new CustomEvent('mode-changed', {{ detail: '{mode}' }}));
        }})()"#,
        ignore = if ignore { "true" } else { "false" },
        mode = mode
    );
    let _ = window.eval(&js);
}

/// 初始化系统托盘
pub fn setup(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let (mode_text, interactive_text, focus_text, hidden_text, settings_text, quit_text) = get_menu_texts();

    // 创建模式子菜单项
    let interactive_item = CheckMenuItem::with_id(app, "mode_interactive", interactive_text, true, true, None::<&str>)?;
    let focus_item = CheckMenuItem::with_id(app, "mode_focus", focus_text, true, false, None::<&str>)?;
    let hidden_item = CheckMenuItem::with_id(app, "mode_hidden", hidden_text, true, false, None::<&str>)?;

    // 通用设置与退出
    let settings_item = MenuItem::with_id(app, "settings", settings_text, true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", quit_text, true, None::<&str>)?;

    // 构建模式子菜单
    let mode_submenu = Submenu::with_items(app, mode_text, true, &[
        &interactive_item,
        &focus_item,
        &hidden_item,
    ])?;

    // 构建主菜单
    let menu = Menu::with_items(app, &[&mode_submenu, &settings_item, &quit_item])?;

    // 加载托盘图标（缺失时不 panic，托盘仍可工作）
    let icon = app.default_window_icon().cloned().unwrap_or_else(|| {
        tauri::image::Image::new_owned(vec![0u8; 4], 1, 1)
    });

    // 创建托盘图标
    let _tray = TrayIconBuilder::new()
        .icon(icon)
        .menu(&menu)
        .tooltip("Auralis — 桌面精灵")
        .on_menu_event(move |app, event| {
            match event.id().as_ref() {
                "mode_interactive" => {
                    let _ = interactive_item.set_checked(true);
                    let _ = focus_item.set_checked(false);
                    let _ = hidden_item.set_checked(false);
                    if let Some(window) = app.get_webview_window("pet") {
                        set_mode_via_eval(&window, "interactive");
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "mode_focus" => {
                    let _ = interactive_item.set_checked(false);
                    let _ = focus_item.set_checked(true);
                    let _ = hidden_item.set_checked(false);
                    if let Some(window) = app.get_webview_window("pet") {
                        set_mode_via_eval(&window, "focus");
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "mode_hidden" => {
                    let _ = interactive_item.set_checked(false);
                    let _ = focus_item.set_checked(false);
                    let _ = hidden_item.set_checked(true);
                    if let Some(window) = app.get_webview_window("pet") {
                        set_mode_via_eval(&window, "hidden");
                        let _ = window.hide();
                    }
                }
                "settings" => {
                    if let Some(window) = app.get_webview_window("pet") {
                        let _ = window.show();
                        let _ = window.set_focus();
                        let _ =
                            window.eval("window.dispatchEvent(new CustomEvent('open-settings'))");
                    }
                }
                "quit" => {
                    log::info!("托盘退出：正在停止 Agent 进程...");
                    let _ = AGENT_MANAGER.stop_agent();
                    app.exit(0);
                }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            if let tauri::tray::TrayIconEvent::Click {
                button: tauri::tray::MouseButton::Left,
                button_state: tauri::tray::MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("pet") {
                    if window.is_visible().unwrap_or(false) {
                        let _ = window.hide();
                        set_mode_via_eval(&window, "hidden");
                    } else {
                        let _ = window.show();
                        let _ = window.set_focus();
                        set_mode_via_eval(&window, "interactive");
                    }
                }
            }
        })
        .build(app)?;

    Ok(())
}
