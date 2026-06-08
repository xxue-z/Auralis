use super::capability::Capability;

#[derive(Debug, Clone, PartialEq)]
pub enum RiskLevel { Low, Medium, High, Critical }

pub struct SafetyHooks;

impl SafetyHooks {
    /// 风险评估 — 与 Python risk_engine 保持一致
    ///
    /// Python 侧已做风险评估，只把 LOW/MEDIUM 操作发给 Rust。
    /// Rust 不应再对这些操作要求确认，否则会超时。
    /// 仅 SystemShutdown (Critical) 和 SystemLock (High) 保留拦截。
    pub fn assess_risk(capability: &Capability) -> RiskLevel {
        match capability {
            // 低风险：读取、列表、截图
            Capability::FileRead { .. } | Capability::FileList { .. }
            | Capability::FileSearch { .. } | Capability::AppList
            | Capability::SystemInfo | Capability::UIScreenshot { .. } => RiskLevel::Low,
            // 中低风险：写入、应用启动/关闭、UI 操作
            // Python 侧视为 LOW/MEDIUM 且直接执行，Rust 也应放行
            Capability::FileWrite { .. } | Capability::FileMove { .. }
            | Capability::FileCopy { .. } | Capability::FileDelete { .. }
            | Capability::AppLaunch { .. } | Capability::AppClose { .. }
            | Capability::UIClick { .. } | Capability::UIType { .. } => RiskLevel::Low,
            // 高风险：锁屏（Python 侧也要求确认）
            Capability::SystemLock => RiskLevel::High,
            // 关键风险：关机（Python 侧也要求确认）
            Capability::SystemShutdown { .. } => RiskLevel::Critical,
        }
    }

    pub fn check_delete_path(path: &str) -> Result<(), String> {
        let path_lower = path.to_lowercase().replace('\\', "/");
        for pattern in &["c:/windows", "c:/program files", "c:/programdata"] {
            if path_lower.starts_with(pattern) {
                return Err(format!("禁止删除系统目录: {}", path));
            }
        }
        Ok(())
    }
}
