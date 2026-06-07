use super::capability::Capability;

#[derive(Debug, Clone, PartialEq)]
pub enum RiskLevel { Low, Medium, High, Critical }

pub struct SafetyHooks;

impl SafetyHooks {
    pub fn assess_risk(capability: &Capability) -> RiskLevel {
        match capability {
            Capability::FileRead { .. } | Capability::FileList { .. }
            | Capability::FileSearch { .. } | Capability::AppList
            | Capability::SystemInfo => RiskLevel::Low,
            Capability::FileWrite { .. } | Capability::FileMove { .. }
            | Capability::FileCopy { .. } | Capability::FileDelete { .. }
            | Capability::AppLaunch { .. } | Capability::AppClose { .. } => RiskLevel::Medium,
            Capability::SystemLock => RiskLevel::High,
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
