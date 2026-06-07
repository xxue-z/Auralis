//! UI 自动化操作 — 鼠标点击、键盘输入、屏幕截图

use crate::os_adapter::capability::ScreenRegion;

/// UI 操作结果
pub type UIResult<T> = Result<T, String>;

/// 鼠标点击指定坐标
pub async fn click(x: i32, y: i32) -> UIResult<()> {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;

        // 使用 PowerShell 的 Windows.Forms 鼠标模拟（更可靠）
        let script = format!(
            "Add-Type -AssemblyName System.Windows.Forms; \
             [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({}, {}); \
             Start-Sleep -Milliseconds 50; \
             [System.Windows.Forms.SendKeys]::SendWait('{{LBUTTON}}')",
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
        use std::io::Write;
        use std::process::{Command, Stdio};

        // 使用 stdin 传递文本，避免命令行注入
        let mut child = Command::new("powershell")
            .args(["-command", "-"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("启动 PowerShell 失败: {}", e))?;

        // 通过 stdin 传递脚本（文本通过变量传递，不拼接到命令行）
        if let Some(stdin) = child.stdin.as_mut() {
            let script = format!(
                "$text = [System.IO.StreamReader]::new([Console]::In).ReadToEnd(); \
                 Set-Clipboard -Value $text; \
                 Add-Type -AssemblyName System.Windows.Forms; \
                 [System.Windows.Forms.SendKeys]::SendWait('^v')",
            );
            stdin.write_all(script.as_bytes())
                .map_err(|e| format!("写入脚本失败: {}", e))?;
            stdin.write_all(text.as_bytes())
                .map_err(|e| format!("写入文本失败: {}", e))?;
        }

        let output = child.wait_with_output()
            .map_err(|e| format!("等待 PowerShell 完成失败: {}", e))?;

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
