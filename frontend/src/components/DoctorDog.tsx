/**
 * DoctorDog – 可爱的医生小狗形象 (SVG 占位)
 *
 * 头上带语音泡泡，点击泡泡跳转到 chatbot。
 */

type Props = {
  message?: string
  onBubbleClick?: () => void
  hasAlert?: boolean
}

export function DoctorDog({ message = '你今天感觉怎么样？', onBubbleClick, hasAlert = false }: Props) {
  return (
    <div className="relative flex flex-col items-center select-none">
      {/* ── 对话泡泡 ── */}
      <button
        onClick={onBubbleClick}
        className={`group relative mb-2 max-w-[240px] rounded-2xl border px-4 py-2.5 text-sm text-slate-700 shadow-lg backdrop-blur transition hover:shadow-xl hover:scale-[1.03] active:scale-100 ${
          hasAlert
            ? 'border-rose-300 bg-rose-50/90 ring-2 ring-rose-300/50'
            : 'border-white/80 bg-white/90'
        }`}
      >
        {message}
        <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 text-white/90 text-lg leading-none">▼</span>
        {hasAlert ? (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-rose-500 text-[10px] text-white shadow animate-pulse">
            ⚠️
          </span>
        ) : (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[9px] text-white shadow">
            💬
          </span>
        )}
      </button>

      {/* ── 医生小狗 SVG ── */}
      <svg
        viewBox="0 0 200 220"
        className="h-52 w-52 drop-shadow-xl"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Body - white coat */}
        <ellipse cx="100" cy="160" rx="55" ry="50" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="2" />
        {/* Stethoscope cord */}
        <path d="M 80 130 Q 60 150 70 175" fill="none" stroke="#0ea5e9" strokeWidth="3" strokeLinecap="round" />
        <circle cx="70" cy="178" r="6" fill="#0ea5e9" />
        <circle cx="70" cy="178" r="3" fill="#bae6fd" />

        {/* Head */}
        <circle cx="100" cy="85" r="45" fill="#d4a574" />
        {/* Face lighter area */}
        <ellipse cx="100" cy="95" rx="30" ry="25" fill="#f0d9b5" />

        {/* Ears */}
        <ellipse cx="55" cy="60" rx="18" ry="28" fill="#b8855a" transform="rotate(-15 55 60)" />
        <ellipse cx="55" cy="60" rx="12" ry="20" fill="#d4a574" transform="rotate(-15 55 60)" />
        <ellipse cx="145" cy="60" rx="18" ry="28" fill="#b8855a" transform="rotate(15 145 60)" />
        <ellipse cx="145" cy="60" rx="12" ry="20" fill="#d4a574" transform="rotate(15 145 60)" />

        {/* Eyes */}
        <circle cx="82" cy="82" r="7" fill="#1e293b" />
        <circle cx="118" cy="82" r="7" fill="#1e293b" />
        <circle cx="84" cy="80" r="2.5" fill="white" />
        <circle cx="120" cy="80" r="2.5" fill="white" />

        {/* Nose */}
        <ellipse cx="100" cy="97" rx="8" ry="5" fill="#1e293b" />
        <ellipse cx="100" cy="96" rx="3" ry="1.5" fill="#475569" />

        {/* Mouth */}
        <path d="M 92 102 Q 100 110 108 102" fill="none" stroke="#1e293b" strokeWidth="2" strokeLinecap="round" />

        {/* Blush */}
        <circle cx="72" cy="97" r="8" fill="#fda4af" opacity="0.4" />
        <circle cx="128" cy="97" r="8" fill="#fda4af" opacity="0.4" />

        {/* Doctor hat / headband */}
        <rect x="72" y="43" width="56" height="14" rx="4" fill="white" stroke="#cbd5e1" strokeWidth="1.5" />
        <text x="100" y="54" textAnchor="middle" fontSize="9" fill="#0f766e" fontWeight="bold">Dr.Dog</text>

        {/* Arms with coat sleeves */}
        <path d="M 50 145 Q 35 155 40 170" fill="none" stroke="#cbd5e1" strokeWidth="8" strokeLinecap="round" />
        <path d="M 150 145 Q 165 155 160 170" fill="none" stroke="#cbd5e1" strokeWidth="8" strokeLinecap="round" />
        {/* Paws */}
        <circle cx="40" cy="173" r="6" fill="#d4a574" />
        <circle cx="160" cy="173" r="6" fill="#d4a574" />

        {/* Heart on coat */}
        <text x="100" y="160" textAnchor="middle" fontSize="18">❤️</text>
      </svg>
    </div>
  )
}
