interface CharacterSVGProps {
  state: "idle" | "speaking" | "thinking" | "happy";
  size: number;
}

export function CharacterSVG({ state, size }: CharacterSVGProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* 身体 */}
      <g className={`character-${state}`}>
        {/* 头部 */}
        <circle cx="60" cy="45" r="30" fill="#FFE4B5" stroke="#DEB887" strokeWidth="2" />

        {/* 眼睛 */}
        <g className="eyes">
          {state === "happy" ? (
            // 开心：星星眼
            <>
              <text x="45" y="48" fontSize="12" className="sparkle">⭐</text>
              <text x="65" y="48" fontSize="12" className="sparkle">⭐</text>
            </>
          ) : state === "thinking" ? (
            // 思考：看向右上方
            <>
              <circle cx="50" cy="42" r="4" fill="#4A4A4A" />
              <circle cx="70" cy="42" r="4" fill="#4A4A4A" />
              <circle cx="51" cy="41" r="1.5" fill="white" />
              <circle cx="71" cy="41" r="1.5" fill="white" />
            </>
          ) : (
            // 默认：正常眼睛
            <>
              <circle cx="48" cy="42" r="4" fill="#4A4A4A" />
              <circle cx="72" cy="42" r="4" fill="#4A4A4A" />
              <circle cx="49" cy="41" r="1.5" fill="white" />
              <circle cx="73" cy="41" r="1.5" fill="white" />
            </>
          )}
        </g>

        {/* 嘴巴 */}
        <g className="mouth">
          {state === "speaking" ? (
            <ellipse cx="60" cy="58" rx="6" ry="4" fill="#FF6B6B" />
          ) : state === "happy" ? (
            <path d="M 50 55 Q 60 65 70 55" stroke="#FF6B6B" strokeWidth="2" fill="none" />
          ) : (
            <path d="M 52 56 Q 60 60 68 56" stroke="#DEB887" strokeWidth="2" fill="none" />
          )}
        </g>

        {/* 腮红 */}
        <circle cx="38" cy="52" r="5" fill="#FFB6C1" opacity="0.5" />
        <circle cx="82" cy="52" r="5" fill="#FFB6C1" opacity="0.5" />

        {/* 身体 */}
        <ellipse cx="60" cy="90" rx="25" ry="20" fill="#87CEEB" stroke="#5F9EA0" strokeWidth="2" />

        {/* 手臂 */}
        <ellipse cx="32" cy="85" rx="8" ry="5" fill="#FFE4B5" stroke="#DEB887" strokeWidth="1" />
        <ellipse cx="88" cy="85" rx="8" ry="5" fill="#FFE4B5" stroke="#DEB887" strokeWidth="1" />

        {/* 翅膀（精灵特征） */}
        <path
          d="M 35 70 Q 15 50 25 35 Q 30 45 35 55"
          fill="#E6E6FA"
          stroke="#DDA0DD"
          strokeWidth="1"
          opacity="0.7"
        />
        <path
          d="M 85 70 Q 105 50 95 35 Q 90 45 85 55"
          fill="#E6E6FA"
          stroke="#DDA0DD"
          strokeWidth="1"
          opacity="0.7"
        />
      </g>

      {/* 思考气泡 */}
      {state === "thinking" && (
        <g className="thinking-bubble">
          <circle cx="95" cy="25" r="3" fill="#DDD" />
          <circle cx="102" cy="18" r="4" fill="#DDD" />
          <circle cx="110" cy="10" r="6" fill="#DDD" />
        </g>
      )}

      {/* 开心星星 */}
      {state === "happy" && (
        <g className="sparkle">
          <text x="20" y="20" fontSize="10">✨</text>
          <text x="90" y="20" fontSize="10">✨</text>
          <text x="15" y="70" fontSize="8">💫</text>
          <text x="95" y="70" fontSize="8">💫</text>
        </g>
      )}
    </svg>
  );
}
