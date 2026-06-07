import { useConfirmStore } from "../../stores/confirmStore";

export function ConfirmDialog() {
  const pending = useConfirmStore((s) => s.pending);
  const respond = useConfirmStore((s) => s.respond);

  if (!pending) return null;

  const riskColor = {
    low: "border-yellow-300 bg-yellow-50",
    medium: "border-orange-300 bg-orange-50",
    high: "border-red-300 bg-red-50",
    critical: "border-red-500 bg-red-100",
  }[pending.riskLevel] || "border-gray-300 bg-gray-50";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className={`mx-4 w-80 rounded-2xl border-2 ${riskColor} p-4 shadow-xl`}>
        <h3 className="text-sm font-bold text-gray-800 mb-2">⚠️ 需要确认</h3>
        <p className="text-sm text-gray-600 mb-4">{pending.message}</p>
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => respond(false)}
            className="px-4 py-1.5 text-sm text-gray-600 bg-white rounded-full
                       border border-gray-300 hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            onClick={() => respond(true)}
            className="px-4 py-1.5 text-sm text-white bg-red-500 rounded-full
                       hover:bg-red-600 transition-colors"
          >
            确认执行
          </button>
        </div>
      </div>
    </div>
  );
}
