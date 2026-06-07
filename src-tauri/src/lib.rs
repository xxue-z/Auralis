mod commands;
mod os_adapter;
mod tray;

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            tray::setup(app.handle())?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::greet,
            commands::execute_capability,
            commands::resize_window,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
