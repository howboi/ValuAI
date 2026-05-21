<template>
  <!-- ── Gauge chart showing fair value vs current price ── -->
  <div class="gauge-wrap">
    <svg :viewBox="`0 0 ${W} ${H}`" :width="W" :height="H">
      <!-- Background arc -->
      <path :d="bgArc" fill="none" stroke="#30363d" :stroke-width="sw" stroke-linecap="round"/>
      <!-- Value arc -->
      <path :d="valArc" fill="none" :stroke="arcColor" :stroke-width="sw"
            stroke-linecap="round" class="arc-animate"/>
      <!-- Center text -->
      <text :x="cx" :y="cy + 6" text-anchor="middle"
            font-size="22" font-weight="700" fill="#e6edf3">
        {{ label }}
      </text>
      <text :x="cx" :y="cy + 26" text-anchor="middle"
            font-size="11" fill="#8b949e">
        {{ sub }}
      </text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value:  { type: Number, default: 0 },   // 0–100
  label:  { type: String, default: '' },
  sub:    { type: String, default: '' },
  color:  { type: String, default: '#58a6ff' },
})

const W = 180, H = 110, cx = W / 2, cy = H - 14
const r = 72, sw = 14
const startAngle = -Math.PI * 0.85
const endAngle   =  Math.PI * 0.85

function polarToXY(angle) {
  return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }
}

const s = polarToXY(startAngle)
const e = polarToXY(endAngle)

const bgArc  = `M ${s.x} ${s.y} A ${r} ${r} 0 1 1 ${e.x} ${e.y}`

const valArc = computed(() => {
  const pct   = Math.min(Math.max(props.value, 0), 100) / 100
  const angle = startAngle + (endAngle - startAngle) * pct
  const ep    = polarToXY(angle)
  const large = pct > 0.5 ? 1 : 0
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${ep.x} ${ep.y}`
})

const arcColor = computed(() => {
  if (props.value >= 60) return '#3fb950'
  if (props.value >= 30) return '#d29922'
  return '#f85149'
})
</script>

<style scoped>
.gauge-wrap { display: flex; justify-content: center; }
.arc-animate {
  stroke-dasharray: 1000;
  stroke-dashoffset: 0;
  transition: d 0.8s cubic-bezier(.4,0,.2,1);
}
</style>
