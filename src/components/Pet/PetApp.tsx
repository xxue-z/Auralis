import { useState, useEffect, useCallback, useRef } from "react";
import {
  getCurrentWebviewWindow,
  WebviewWindow,
} from "@tauri-apps/api/webviewWindow";
import { PhysicalPosition } from "@tauri-apps/api/dpi";
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
  alwaysOnTop: true,
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

  const handlePointerDown = useCallback(
    (_e: React.PointerEvent) => {
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
        // Only open chat if click lands on actual rendered character content
        const target = _e.target as HTMLElement;
        const svg = target.closest("svg");
        if (svg && target !== svg) {
          // SVG mode: click on actual SVG child element (circle/path),
          // not on empty SVG viewport space
          openChatRef.current();
        } else if (target.closest("canvas")) {
          // Live2D mode: only open chat if Pixi detected a model hit
          const isModelHit = !!(window as any).__live2dModelClick;
          (window as any).__live2dModelClick = false;
          if (isModelHit) {
            openChatRef.current();
          }
        }
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
    const handler = () => openSettings();
    window.addEventListener("open-settings", handler);
    return () => window.removeEventListener("open-settings", handler);
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

  // ── Render ───────────────────────────────────────────────────
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
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
    >
      <Live2DViewer />
      <ConfirmDialog />
    </div>
  );
}
