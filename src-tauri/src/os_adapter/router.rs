use super::capability::{Capability, CapabilityRequest, CapabilityResult, ConfirmationInfo};
use super::safety::{SafetyHooks, RiskLevel};
use super::audit::{AuditLogger, AuditEntry};
use super::windows;
use std::time::Instant;

pub struct OSAdapterRouter;

impl OSAdapterRouter {
    /// 执行 Capability 请求
    /// 流程：风险评估 → 确认检查 → 执行 → 审计日志
    pub async fn execute(request: CapabilityRequest) -> CapabilityResult {
        let start = Instant::now();

        // 1. 风险评估
        let risk = SafetyHooks::assess_risk(&request.capability);
        let risk_str = match risk {
            RiskLevel::Low => "low",
            RiskLevel::Medium => "medium",
            RiskLevel::High => "high",
            RiskLevel::Critical => "critical",
        };

        // 2. 确认检查：中/高风险操作需要用户确认
        //    如果请求中没有 confirmed=true，则返回 needs_confirmation
        let confirmed = request.policy.as_ref()
            .map(|p| p.require_confirmation)
            .unwrap_or(false);

        if (risk == RiskLevel::Medium || risk == RiskLevel::High || risk == RiskLevel::Critical)
            && !confirmed
        {
            let cap_type = Self::capability_type_name(&request.capability);
            let message = match risk {
                RiskLevel::Medium => format!("即将执行中等风险操作：{}", cap_type),
                RiskLevel::High => format!("即将执行高风险操作：{}，请确认", cap_type),
                RiskLevel::Critical => format!("即将执行关键操作：{}，此操作不可逆，请确认", cap_type),
                _ => unreachable!(),
            };

            return CapabilityResult {
                id: request.id,
                success: false,
                data: None,
                error: None,
                needs_confirmation: Some(ConfirmationInfo {
                    message,
                    risk_level: risk_str.to_string(),
                    capability_type: Self::capability_type_name(&request.capability),
                }),
            };
        }

        // 3. 执行操作
        let result = match &request.capability {
            Capability::FileRead { path } => windows::file::read(path).await,
            Capability::FileWrite { path, content } => windows::file::write(path, content).await,
            Capability::FileDelete { path, recursive } => windows::file::delete(path, *recursive).await,
            Capability::FileList { path, pattern } => windows::file::list(path, pattern.as_deref()).await,
            Capability::AppLaunch { app_id, args } => windows::app::launch(app_id, args.as_deref()).await,
            Capability::AppClose { app_id, pid } => windows::app::close(app_id, *pid).await,
            Capability::AppList => windows::app::list().await,
            Capability::SystemInfo => windows::system::info().await,
            Capability::SystemLock => windows::system::lock().await,
            Capability::UIClick { x, y } => windows::ui::click(*x, *y).await.map(|()| serde_json::json!({"clicked": true, "x": x, "y": y})),
            Capability::UIType { text } => windows::ui::type_text(text).await.map(|()| serde_json::json!({"typed": true, "length": text.len()})),
            Capability::UIScreenshot { region } => {
                windows::ui::screenshot(region.clone()).await.map(|b64| {
                    serde_json::json!({"image": b64, "format": "png"})
                })
            }
            Capability::FileMove { .. } | Capability::FileCopy { .. }
            | Capability::FileSearch { .. } | Capability::SystemShutdown { .. } => {
                Err("此操作暂未实现".to_string())
            }
        };

        let duration = start.elapsed().as_millis() as u64;

        // 4. 审计日志
        let (success, data, error) = match &result {
            Ok(data) => (true, Some(data.clone()), None),
            Err(err) => (false, None, Some(err.clone())),
        };

        AuditLogger::log(AuditEntry {
            id: request.id.clone(),
            timestamp: chrono::Utc::now().timestamp(),
            session_id: request.context.session_id.clone(),
            capability_type: Self::capability_type_name(&request.capability),
            risk_level: risk_str.to_string(),
            confirmed_by_user: confirmed,
            result: if success { "success".to_string() } else { "error".to_string() },
            error_message: error.clone(),
            duration_ms: duration,
        });

        // 5. 返回结果
        CapabilityResult {
            id: request.id,
            success,
            data,
            error,
            needs_confirmation: None,
        }
    }

    fn capability_type_name(cap: &Capability) -> String {
        match cap {
            Capability::FileRead { .. } => "file.read".to_string(),
            Capability::FileWrite { .. } => "file.write".to_string(),
            Capability::FileDelete { .. } => "file.delete".to_string(),
            Capability::FileList { .. } => "file.list".to_string(),
            Capability::FileMove { .. } => "file.move".to_string(),
            Capability::FileCopy { .. } => "file.copy".to_string(),
            Capability::FileSearch { .. } => "file.search".to_string(),
            Capability::AppLaunch { .. } => "app.launch".to_string(),
            Capability::AppClose { .. } => "app.close".to_string(),
            Capability::AppList => "app.list".to_string(),
            Capability::SystemInfo => "system.info".to_string(),
            Capability::SystemLock => "system.lock".to_string(),
            Capability::SystemShutdown { .. } => "system.shutdown".to_string(),
            Capability::UIClick { .. } => "ui.click".to_string(),
            Capability::UIType { .. } => "ui.type".to_string(),
            Capability::UIScreenshot { .. } => "ui.screenshot".to_string(),
        }
    }
}
