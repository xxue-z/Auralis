//! UI 自动化操作 — 鼠标点击、键盘输入、屏幕截图

use crate::os_adapter::capability::ScreenRegion;

/// UI 操作结果
pub type UIResult<T> = Result<T, String>;

/// UI 操作
pub struct UIOps;

impl UIOps {
    /// 鼠标点击指定坐标
    pub async fn click(x: i32, y: i32) -> UIResult<()> {
        #[cfg(target_os = "windows")]
        {
            use std::process::Command;

            // 使用 PowerShell 设置光标位置并模拟点击
            let script = format!(
                "Add-Type -AssemblyName System.Windows.Forms; \
                 [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({}, {}); \
                 Add-Type '{{ \
                     [DllImport(\"user32.dll\")] \
                     public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo); \
                 }}'; \
                 [mouse_event]::mouse_event(0x0002, 0, 0, 0, 0); \
                 [mouse_event]::mouse_event(0x0004, 0, 0, 0, 0);",
                x, y
            );

            Command::new("powershell")
                .args(["-command", &script])
                .output()
                .map_err(|e| format!("点击失败: {}", e))?;

            log::info!("UI 点击: ({}, {})", x, y);
            Ok(())
        }

        #[cfg(not(target_os = "windows"))]
        {
            let _ = (x, y);
            Ok(())
        }
    }

    /// 键盘输入文本
    pub async fn type_text(text: &str) -> UIResult<()> {
        #[cfg(target_os = "windows")]
        {
            use std::process::Command;

            // 使用剪贴板 + Ctrl+V 输入（避免 SendKeys 转义问题）
            let script = format!(
                "Set-Clipboard -Value '{}'; \
                 Add-Type -AssemblyName System.Windows.Forms; \
                 [System.Windows.Forms.SendKeys]::SendWait('^v')",
                text.replace('\'', "''")
            );

            let output = Command::new("powershell")
                .args(["-command", &script])
                .output()
                .map_err(|e| format!("输入失败: {}", e))?;

            if !output.status.success() {
                let stderr = String::from_utf8_lossy(&output.stderr);
                return Err(format!("输入失败: {}", stderr));
            }

            log::info!("UI 输入: {} 个字符", text.len());
            Ok(())
        }

        #[cfg(not(target_os = "windows"))]
        {
            let _ = text;
            Ok(())
        }
    }

    /// 屏幕截图（返回 Base64 编码的 PNG）
    pub async fn screenshot(region: Option<ScreenRegion>) -> UIResult<String> {
        #[cfg(target_os = "windows")]
        {
            use std::process::Command;

            let ps_script = match region {
                Some(r) => format!(
                    "Add-Type -AssemblyName System.Drawing; \
                     $b = New-Object System.Drawing.Bitmap({}, {}); \
                     $g = [System.Drawing.Graphics]::FromImage($b); \
                     $g.CopyFromScreen({}, {}, 0, 0, $b.Size); \
                     $ms = New-Object System.IO.MemoryStream; \
                     $b.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); \
                     [System.Convert]::ToBase64String($ms.ToArray())",
                    r.w, r.h, r.x, r.y
                ),
                None => "\
                    Add-Type -AssemblyName System.Drawing; \
                    $b = [System.Drawing.Bitmap]::FromHwnd([IntPtr]::Zero); \
                    $g = [System.Drawing.Graphics]::FromImage($b); \
                    $g.CopyFromScreen(0, 0, 0, 0, $b.Size); \
                    $ms = New-Object System.IO.MemoryStream; \
                    $b.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); \
                    [System.Convert]::ToBase64String($ms.ToArray())"
                    .to_string(),
            };

            let output = Command::new("powershell")
                .args(["-command", &ps_script])
                .output()
                .map_err(|e| format!("截图失败: {}", e))?;

            if !output.status.success() {
                let stderr = String::from_utf8_lossy(&output.stderr);
                return Err(format!("截图失败: {}", stderr));
            }

            let b64 = String::from_utf8_lossy(&output.stdout).trim().to_string();
            log::info!("UI 截图: {} 字符", b64.len());
            Ok(b64)
        }

        #[cfg(not(target_os = "windows"))]
        {
            let _ = region;
            Ok(String::new())
        }
    }
}
