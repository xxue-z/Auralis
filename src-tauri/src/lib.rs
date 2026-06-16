mod commands;
mod os_adapter;
mod tray;

use std::path::PathBuf;
use std::sync::Mutex;
use tauri::{Emitter, Manager};

/// 全局资源目录（设置阶段写入，供 start_agent 使用）
static AGENT_BIN: once_cell::sync::OnceCell<PathBuf> = once_cell::sync::OnceCell::new();

/// Agent 进程管理器
pub struct AgentProcessManager {
    /// Agent 子进程句柄
    child: Mutex<Option<std::process::Child>>,
    /// Agent 进程 PID
    pid: Mutex<Option<u32>>,
}

impl AgentProcessManager {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
            pid: Mutex::new(None),
        }
    }

    /// 启动 Agent 进程
    pub fn start_agent(&self) -> Result<u32, String> {
        let mut child_guard = self.child.lock().map_err(|e| e.to_string())?;
        let mut pid_guard = self.pid.lock().map_err(|e| e.to_string())?;

        // 如果已有进程在运行，先停止
        if let Some(ref mut child) = *child_guard {
            log::info!("停止已运行的 Agent 进程...");
            let _ = child.kill();
            let _ = child.wait();
        }

        // 确定 Agent 可执行文件路径
        let (agent_exe, agent_dir) = if let Some(bin_path) = AGENT_BIN.get() {
            // 发布模式：使用 bundle 中的 exe
            let dir = bin_path.parent().ok_or("无法获取 agent 目录")?;
            (bin_path.clone(), dir.to_path_buf())
        } else {
            // 开发模式：使用 venv python + server.py
            let current_exe = std::env::current_exe().map_err(|e| e.to_string())?;
            let exe_dir = current_exe.parent().ok_or("无法获取可执行文件目录")?;

            let agent_dir = if exe_dir.join("../../agent").exists() {
                exe_dir.join("../../agent")
            } else if exe_dir.join("../agent").exists() {
                exe_dir.join("../agent")
            } else {
                return Err("找不到 agent 目录".to_string());
            };

            let venv_python = agent_dir.join(".venv/Scripts/python.exe");
            if !venv_python.exists() {
                return Err(format!("Python 虚拟环境不存在: {}", venv_python.display()));
            }
            (venv_python, agent_dir)
        };

        log::info!("Agent 可执行文件: {}", agent_exe.display());
        log::info!("Agent 工作目录: {}", agent_dir.display());

        // 启动 Agent 进程
        // 发布模式：agent_exe 是 PyInstaller 打包的单文件 exe（不含 server.py 参数）
        // 开发模式：agent_exe 是 python.exe，需要传入 server.py
        let is_release = AGENT_BIN.get().is_some();
        let mut cmd = std::process::Command::new(&agent_exe);
        if !is_release {
            cmd.arg("server.py");
        }
        let child = cmd
            .current_dir(&agent_dir)
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .map_err(|e| format!("启动 Agent 失败: {}", e))?;

        let pid = child.id();
        *child_guard = Some(child);
        *pid_guard = Some(pid);

        log::info!("Agent 进程已启动, PID: {}", pid);
        Ok(pid)
    }

    /// 停止 Agent 进程
    pub fn stop_agent(&self) -> Result<(), String> {
        let mut child_guard = self.child.lock().map_err(|e| e.to_string())?;
        let mut pid_guard = self.pid.lock().map_err(|e| e.to_string())?;

        if let Some(ref mut child) = *child_guard {
            let pid = child.id();
            log::info!("正在停止 Agent 进程 (PID: {})...", pid);

            // Windows: taskkill /F /T 杀整个进程树
            #[cfg(target_os = "windows")]
            {
                let _ = std::process::Command::new("taskkill")
                    .args(["/F", "/T", "/PID", &pid.to_string()])
                    .output();
            }
            #[cfg(not(target_os = "windows"))]
            {
                let _ = child.kill();
            }

            *child_guard = None;
            *pid_guard = None;
            log::info!("Agent 进程清理完成");
        } else {
            log::warn!("没有找到 Tauri 管理的 Agent 进程");
        }

        Ok(())
    }

    /// 获取 Agent 进程 PID
    pub fn get_pid(&self) -> Option<u32> {
        *self.pid.lock().ok()?
    }
}

/// 全局 Agent 进程管理器
static AGENT_MANAGER: once_cell::sync::Lazy<AgentProcessManager> =
    once_cell::sync::Lazy::new(AgentProcessManager::new);

/// 获取 Agent 管理器（供其他模块使用）
pub fn get_agent_manager() -> &'static AgentProcessManager {
    &AGENT_MANAGER
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // 设置托盘
            tray::setup(app.handle())?;

            // 允许 asset:// 协议访问 models 目录（用于加载本地 Live2D 模型文件）
            {
                let scope = app.handle().asset_protocol_scope();
                let models_dir = app.path().app_data_dir()
                    .unwrap_or_default()
                    .join("models");
                if models_dir.exists() || std::fs::create_dir_all(&models_dir).is_ok() {
                    let _ = scope.allow_directory(&models_dir, true);
                    log::info!("允许 asset 协议访问: {}", models_dir.display());
                }
            }

            // 检查资源目录中的 Agent 可执行文件（发布模式）
            if let Ok(resource_dir) = app.path().resource_dir() {
                let bundled_agent = resource_dir.join("agent").join("auralis-agent.exe");
                if bundled_agent.exists() {
                    let _ = AGENT_BIN.set(bundled_agent);
                    log::info!("找到 bundled agent 可执行文件");
                }
            }

            // 启动 Agent 进程
            match AGENT_MANAGER.start_agent() {
                Ok(pid) => {
                    log::info!("Agent 启动成功, PID: {}", pid);
                }
                Err(e) => {
                    let msg = format!("Agent 启动失败: {}", e);
                    log::error!("{}", msg);
                    let _ = app.handle().emit("agent-error", &msg);
                }
            }

            // 监听 Pet 窗口关闭事件
            if let Some(window) = app.get_webview_window("pet") {
                window.on_window_event(|event| {
                    if let tauri::WindowEvent::Destroyed = event {
                        log::info!("Pet 窗口已关闭，停止 Agent 进程...");
                        let _ = AGENT_MANAGER.stop_agent();
                    }
                });
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::greet,
            commands::execute_capability,
            commands::resize_window,
            commands::extract_model_zip,
            commands::extract_model_zip_from_path,
            commands::open_in_explorer,
            commands::delete_model_dir,
            commands::get_app_data_dir,
            commands::migrate_extensions,
            commands::list_system_plugins,
            commands::list_user_plugins,
            commands::import_plugin,
            commands::import_plugin_zip,
            commands::delete_user_plugin,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app_handle, event| {
            match event {
                tauri::RunEvent::ExitRequested { .. } => {
                    log::info!("收到退出请求，停止 Agent 进程...");
                    let _ = AGENT_MANAGER.stop_agent();
                }
                tauri::RunEvent::Exit => {
                    log::info!("应用退出");
                }
                _ => {}
            }
        });
}
