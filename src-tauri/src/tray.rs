use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{
    menu::{CheckMenuItem, Menu, MenuItem, Submenu},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager,
};

use crate::AGENT_MANAGER;

/// 根据系统语言获取菜单文本
fn get_menu_texts() -> (&'static str, &'static str, &'static str, &'static str, &'static str, &'static str, &'static str, &'static str) {
    let locale = sys_locale::get_locale().unwrap_or_default();
    if locale.starts_with("zh") {
        ("模式切换", "交互模式", "专注模式", "隐藏模式", "置顶", "取消置顶", "设置", "退出")
    } else {
        ("Mode", "Interactive", "Focus", "Hidden", "Pin", "Unpin", "Settings", "Quit")
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
    let (mode_text, interactive_text, focus_text, hidden_text, pin_text, unpin_text, settings_text, quit_text) = get_menu_texts();

    // 创建模式子菜单项
    let interactive_item = CheckMenuItem::with_id(app, "mode_interactive", interactive_text, true, true, None::<&str>)?;
    let focus_item = CheckMenuItem::with_id(app, "mode_focus", focus_text, true, false, None::<&str>)?;
    let hidden_item = CheckMenuItem::with_id(app, "mode_hidden", hidden_text, true, false, None::<&str>)?;

    // 置顶切换按钮（小精灵默认置顶，初始显示"取消置顶"）
    let pin_item = MenuItem::with_id(app, "toggle_pin", unpin_text, true, None::<&str>)?;
    let is_pinned = AtomicBool::new(true);

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
    let menu = Menu::with_items(app, &[&mode_submenu, &pin_item, &settings_item, &quit_item])?;

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
                "toggle_pin" => {
                    let current = is_pinned.load(Ordering::SeqCst);
                    let new_pinned = !current;
                    is_pinned.store(new_pinned, Ordering::SeqCst);
                    // 菜单文字表示"点击后的动作"：已置顶 → 显示"取消置顶"，反之亦然
                    let text = if new_pinned { unpin_text } else { pin_text };
                    let _ = pin_item.set_text(text);
                    if let Some(window) = app.get_webview_window("pet") {
                        let _ = window.set_always_on_top(new_pinned);
                    }
                }
                "settings" => {
                    if let Some(window) = app.get_webview_window("pet") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                    let _ = app.emit("open-settings", ());
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
