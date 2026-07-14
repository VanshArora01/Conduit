'use client';

import { motion } from 'framer-motion';

interface FlowConnectorProps {
  active?: boolean;
}

export function FlowConnector({ active = false }: FlowConnectorProps) {
  return (
    <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-16 h-[2px] z-0 overflow-visible">
      <svg className="w-full h-[20px] overflow-visible" style={{ position: 'absolute', top: -9 }}>
        <motion.path
          d="M 0 10 C 20 10, 40 10, 64 10"
          className="flow-line"
          style={{ strokeWidth: active ? 2 : 1.5, opacity: active ? 1 : 0.3 }}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        />
        {active && (
          <motion.circle
            cx="0"
            cy="10"
            r="3"
            fill="var(--accent)"
            animate={{ cx: 64 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          />
        )}
      </svg>
    </div>
  );
}
