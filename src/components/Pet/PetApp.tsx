import { useState, useEffect, useCallback, useRef } from "react";
import {
  getCurrentWebviewWindow,
  WebviewWindow,
} from "@tauri-apps/api/webviewWindow";
import { listen } from "@tauri-apps/api/event";
import { PhysicalPosition } from "@tauri-apps/api/dpi";
import { cursorPosition } from "@tauri-apps/api/window";
import { useSettingsStore } from "../../stores/settingsStore";
import { useAgentStore } from "../../stores/agentStore";
import { Live2DViewer } from "../Character/Live2DViewer";
import { OnboardingWizard } from "../Onboarding/Wizard";
import { ConfirmDialog } from "../Chat/ConfirmDialog";
import { wsService } from "../../services/websocket";
import { useWindowPosition } from "../../hooks/useWindowPosition";

/** Minimum pointer movement (px) before native drag activates */
const DRAG_THRESHOLD = 4;

/** Tracks whether the chat window has been positioned at least once.
 *  After the first positioning, hide/show cycles keep the user's manual position. */
let _chatHasBeenPositioned = false;
let _settingsHasBeenPositioned = false;

/** Reusable chat window options (avoids reconstructing on every open) */
const CHAT_WIN_OPTIONS = {
  url: "/chat.html",
  title: "Auralis Chat",
  width: 320,
  height: 480,
  decorations: false,
  transparent: true,
  alwaysOnTop: false,
  resizable: false,
  skipTaskbar: true,
  shadow: false,
  backgroundColor: { red: 0, green: 0, blue: 0, alpha: 0 },
} as const;

/** Reusable settings window options */
const SETTINGS_WIN_OPTIONS = {
  url: "/settings.html",
  title: "Auralis Settings",
  width: 640,
  height: 440,
  decorations: false,
  transparent: true,
  alwaysOnTop: true,
  resizable: false,
  skipTaskbar: true,
  backgroundColor: { red: 0, green: 0, blue: 0, alpha: 0 },
} as const;

/**
 * Pet App — the main desktop companion window.
 *
 * - Shows onboarding wizard on first run
 * - Shows Live2D character with drag-to-move support
 * - Click to open chat window
 * - Listens for agent-commands to open settings
 */
export function PetApp() {
  const appWindow = getCurrentWebviewWindow();
  const { savePosition, loadPosition } = useWindowPosition("pet");

  const onboardingComplete = useSettingsStore(
    (s) => s.settings["onboarding.complete"],
  );
  const [showOnboarding, setShowOnboarding] = useState(!onboardingComplete);

  // ── Cached pet window position (avoids IPC calls on click) ────
  const petPosRef = useRef({ x: 0, y: 0 });
  const petSizeRef = useRef({ width: 240, height: 260 });

  // ── Drag-to-move ──────────────────────────────────────────────
  const dragRef = useRef({
    pointerDown: false,
    startX: 0,
    startY: 0,
    moved: false,
    draggingStarted: false,
  });

  /** Ref to openChat so pointerUp can call it without ordering issues */
  const openChatRef = useRef<() => void>(() => {});

  const clickZoneRef = useRef<HTMLDivElement>(null);
  const guideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [showClickGuide, setShowClickGuide] = useState(false);

  // ── Listen for click-zone-preview events (from settings) ──────
  useEffect(() => {
    const unlisten = listen<{ show: boolean }>("click-zone-preview", (event) => {
      setShowClickGuide(event.payload.show);
      if (event.payload.show) {
        if (guideTimerRef.current) clearTimeout(guideTimerRef.current);
        guideTimerRef.current = setTimeout(() => {
          setShowClickGuide(false);
        }, 1500);
      }
    });
    return () => {
      unlisten.then((fn) => fn());
      if (guideTimerRef.current) clearTimeout(guideTimerRef.current);
    };
  }, []);

  const handlePointerDown = useCallback(
    (_e: React.PointerEvent) => {
      if (_e.button !== 0) return;
      // Ignore if the event target is inside a no-drag region
      const target = _e.target as HTMLElement;
      if (target.closest("[data-tauri-no-drag]")) return;

      // Only record start position — DO NOT startDragging yet.
      // Native drag will be initiated on first significant move.
      dragRef.current = {
        pointerDown: true,
        startX: _e.clientX,
        startY: _e.clientY,
        moved: false,
        draggingStarted: false,
      };
    },
    [],
  );

  // ── Save pet position ─────────────────────────────────────────
  const updatePetPosition = useCallback(async () => {
    try {
      const pos = await appWindow.outerPosition();
      petPosRef.current = { x: pos.x, y: pos.y };
      savePosition(pos.x, pos.y);
    } catch {
      // ignore
    }
  }, [appWindow, savePosition]);

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      const drag = dragRef.current;
      if (!drag.pointerDown || drag.draggingStarted) return;

      const dx = e.clientX - drag.startX;
      const dy = e.clientY - drag.startY;
      if (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD) {
        // User has moved enough — start native window drag
        // startDragging() returns a Promise that resolves when the drag completes
        appWindow.startDragging().then(updatePetPosition).catch(() => {});
        dragRef.current.draggingStarted = true;
        dragRef.current.moved = true;
      }
    },
    [appWindow, updatePetPosition],
  );

  const handlePointerUp = useCallback(
    (_e: React.PointerEvent) => {
      // Only left-click opens chat / triggers actions
      if (_e.button !== 0) return;

      const wasDrag = dragRef.current.moved;

      // Reset drag state
      dragRef.current = {
        pointerDown: false,
        startX: 0,
        startY: 0,
        moved: false,
        draggingStarted: false,
      };

      if (wasDrag) {
        // Native drag may have completed — save final position
        updatePetPosition();
      } else {
        // Click zone is the only interactive area — any click opens chat
        openChatRef.current();
      }
    },
    [updatePetPosition],
  );

  const handlePointerCancel = useCallback(() => {
    const wasDragging = dragRef.current.draggingStarted;
    dragRef.current = {
      pointerDown: false,
      startX: 0,
      startY: 0,
      moved: false,
      draggingStarted: false,
    };
    // Native drag triggers pointercancel — save the final position
    if (wasDragging) {
      updatePetPosition();
    }
  }, [updatePetPosition]);

  // ── Connect agent websocket ──────────────────────────────────
  const agentUrl = useAgentStore((s) => s.url);
  useEffect(() => {
    wsService.connect(agentUrl);
  }, [agentUrl]);

  // ── Pre-create windows at startup (avoids WebView2 init delay) ──
  useEffect(() => {
    // Chat window
    new WebviewWindow("chat", {
      ...CHAT_WIN_OPTIONS,
      x: -1000,
      y: -1000,
      visible: false,
    }).once("tauri://error", (e) => {
      console.error("[PetApp] Failed to pre-create chat window:", e);
    });
    // Settings window
    new WebviewWindow("settings", {
      ...SETTINGS_WIN_OPTIONS,
      x: -1000,
      y: -1000,
      visible: false,
    }).once("tauri://error", (e) => {
      console.error("[PetApp] Failed to pre-create settings window:", e);
    });
  }, []);

  // ── Open chat window ─────────────────────────────────────────
  const openChat = useCallback(async () => {
    try {
      const existing = await WebviewWindow.getByLabel("chat");
      const petPos = await appWindow.outerPosition();
      const petSize = await appWindow.outerSize();
      const chatX = petPos.x + petSize.width + 8;
      const chatY = petPos.y;

      // Update cache for any non-drag position saves (e.g. onboarding close)
      petPosRef.current = { x: petPos.x, y: petPos.y };
      petSizeRef.current = { width: petSize.width, height: petSize.height };

      if (existing) {
        const ops: Promise<void>[] = [existing.show()];
        // Only position on first open — subsequent hide/show keeps manual position
        if (!_chatHasBeenPositioned) {
          ops.push(existing.setPosition(new PhysicalPosition(chatX, chatY)));
          _chatHasBeenPositioned = true;
        }
        await Promise.all(ops);
        await existing.setFocus();
        return;
      }

      // Window was destroyed (e.g. closed), recreate at current pet position
      _chatHasBeenPositioned = true;
      new WebviewWindow("chat", {
        ...CHAT_WIN_OPTIONS,
        x: chatX,
        y: chatY,
      }).once("tauri://error", (e) => {
        console.error("[PetApp] Failed to recreate chat window:", e);
      });
    } catch (e) {
      console.warn("[PetApp] openChat failed:", e);
    }
  }, [appWindow]);

  // Keep openChatRef in sync so pointerUp always calls the latest version
  openChatRef.current = openChat;

  // ── Cache pet window size on mount ──────────────────────────
  useEffect(() => {
    appWindow.outerSize().then((s) => {
      petSizeRef.current = { width: s.width, height: s.height };
    }).catch(() => {});
    appWindow.outerPosition().then((p) => {
      petPosRef.current = { x: p.x, y: p.y };
    }).catch(() => {});
  }, [appWindow]);

  // ── Open settings window ─────────────────────────────────────
  const openSettings = useCallback(async () => {
    try {
      const existing = await WebviewWindow.getByLabel("settings");
      const petPos = await appWindow.outerPosition();
      const petSize = await appWindow.outerSize();
      const sx = petPos.x + petSize.width + 8;
      const sy = petPos.y;

      if (existing) {
        const ops: Promise<void>[] = [existing.show()];
        if (!_settingsHasBeenPositioned) {
          ops.push(existing.setPosition(new PhysicalPosition(sx, sy)));
          _settingsHasBeenPositioned = true;
        }
        await Promise.all(ops);
        await existing.setFocus();
        return;
      }

      // Window was destroyed, recreate
      _settingsHasBeenPositioned = true;
      new WebviewWindow("settings", {
        ...SETTINGS_WIN_OPTIONS,
        x: sx,
        y: sy,
      }).once("tauri://error", (e) => {
        console.error("[PetApp] Failed to recreate settings window:", e);
      });
    } catch (e) {
      console.warn("[PetApp] openSettings failed:", e);
    }
  }, [appWindow]);

  // ── Handle onboarding complete ───────────────────────────────
  const handleOnboardingComplete = useCallback(() => {
    setShowOnboarding(false);
    // Save position after onboarding
    appWindow
      .outerPosition()
      .then((pos) => savePosition(pos.x, pos.y))
      .catch(() => {});
  }, [appWindow, savePosition]);

  // ── Listen for events ────────────────────────────────────────
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail === "open-settings" || detail === "open_settings") {
        openSettings();
      }
    };
    window.addEventListener("agent-command", handler as EventListener);
    return () =>
      window.removeEventListener("agent-command", handler as EventListener);
  }, [openSettings]);

  useEffect(() => {
    const unlisten = listen<{}>("open-settings", () => {
      openSettings();
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, [openSettings]);

  // ── Restore saved position on mount ──────────────────────────
  useEffect(() => {
    const saved = loadPosition();
    if (saved) {
      appWindow
        .setPosition(new PhysicalPosition(saved.x, saved.y))
        .catch(() => {});
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Listen for mode-changed events from tray ─────────────────
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail) {
        useSettingsStore.getState().setSetting("appearance.mode", detail);
      }
    };
    window.addEventListener("mode-changed", handler);
    return () => window.removeEventListener("mode-changed", handler);
  }, []);

  // ── Interactive mode: polling + pointerleave hybrid ──────────
  //     Default: setIgnoreCursorEvents(true) — clicks pass through to desktop.
  //     Polling detects mouse entry into the click zone → toggle to false.
  //     pointerleave on the click zone → toggle back to true (instant exit).
  const mode =
    useSettingsStore((s) => s.settings["appearance.mode"]) || "interactive";
  const ignoringRef = useRef(true);
  const clickZoneSizeRef = useRef({ w: 0, h: 0, win: 0 });

  useEffect(() => {
    if (mode !== "interactive") return;

    let cancelled = false;

    // Always start with pass-through enabled
    appWindow.setIgnoreCursorEvents(true).catch(() => {});
    ignoringRef.current = true;

    const poll = async () => {
      if (cancelled) return;
      try {
        const cursorPos = await cursorPosition();
        const winPos = await appWindow.outerPosition();
        const winW = window.innerWidth;
        const winH = window.innerHeight;
        const { w: czW, h: czH } = clickZoneSizeRef.current;
        if (czW <= 0 || czH <= 0) {
          requestAnimationFrame(poll);
          return;
        }
        const halfW = (winW - czW) / 2;
        const halfH = (winH - czH) / 2;
        const czLeft = winPos.x + halfW;
        const czRight = czLeft + czW;
        const czTop = winPos.y + halfH;
        const czBottom = czTop + czH;

        const isOver =
          cursorPos.x >= czLeft && cursorPos.x <= czRight &&
          cursorPos.y >= czTop && cursorPos.y <= czBottom;

        // Only toggle when the state actually changes (avoids redundant IPC)
        if (isOver && ignoringRef.current) {
          ignoringRef.current = false;
          await appWindow.setIgnoreCursorEvents(false);
        }
        // Exit is handled by pointerleave on the click zone div
      } catch {
        // ignore polling errors
      }
      requestAnimationFrame(poll);
    };
    requestAnimationFrame(poll);

    return () => {
      cancelled = true;
    };
  }, [appWindow, mode]);

  // pointerleave on click zone: immediate cursor exit detection
  const handleClickZoneLeave = useCallback(() => {
    if (mode === "interactive" && !ignoringRef.current) {
      ignoringRef.current = true;
      appWindow.setIgnoreCursorEvents(true).catch(() => {});
    }
  }, [appWindow, mode]);

  // ── Mode switch (show/hide + focus-mode override) ────────────
  useEffect(() => {
    if (mode === "hidden") {
      appWindow.hide().catch(() => {});
    } else {
      appWindow.show().catch(() => {});
      if (mode === "focus") {
        appWindow.setIgnoreCursorEvents(true).catch(() => {});
        ignoringRef.current = true;
      }
      // "interactive" mode: the polling / pointerleave hybrid handles it
    }
  }, [appWindow, mode]);

  // ── Render ───────────────────────────────────────────────────
  const settings = useSettingsStore((s) => s.settings);
  const modelId = settings["appearance.model_id"] || "svg_fallback";
  const spriteSize = settings[`model:${modelId}:sprite_size`] ?? settings["appearance.sprite_size"] ?? 96;
  const winSize = spriteSize + 40;
  const czWPct = settings["appearance.click_zone_w"] ?? 60;
  const czHPct = settings["appearance.click_zone_h"] ?? 80;
  const clickZoneW = Math.round(winSize * czWPct / 100);
  const clickZoneH = Math.round(winSize * czHPct / 100);

  // Sync click zone dimensions into ref for polling loop
  clickZoneSizeRef.current = { w: clickZoneW, h: clickZoneH, win: winSize };

  if (showOnboarding) {
    return (
      <div
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        style={{ width: "100vw", height: "100vh" }}
      >
        <OnboardingWizard onComplete={handleOnboardingComplete} />
        <ConfirmDialog />
      </div>
    );
  }

  return (
    <div
      className="pet-app-root"
      style={{ pointerEvents: "none" }}
    >
      <Live2DViewer />

      {/* Transparent click zone overlay — the only interactive area */}
      <div
        ref={clickZoneRef}
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          width: clickZoneW,
          height: clickZoneH,
          pointerEvents: "auto" as any,
          cursor: "default",
          zIndex: 10,
          ...(showClickGuide
            ? {
                outline: "2px dashed #0ea5e9",
                outlineOffset: -2,
                background: "rgba(14,165,233,0.08)",
              }
            : {}),
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        onPointerLeave={handleClickZoneLeave}
        onContextMenu={(e) => e.preventDefault()}
      >
        {/* Guide mouse icon at center */}
        {showClickGuide && (
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              transform: "translate(-50%, -50%)",
              width: 32,
              height: 32,
              background: "rgba(14,165,233,0.4)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              pointerEvents: "none",
            }}
          >
            🖱
          </div>
        )}
      </div>

      <ConfirmDialog />
    </div>
  );
}
