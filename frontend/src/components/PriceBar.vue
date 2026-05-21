<template>
  <div class="price-bar">
    <div class="bar-track">
      <div class="bar-fill" :style="{ width: pct + '%', background: barColor }"/>
      <!-- current price marker -->
      <div class="marker" :style="{ left: pct + '%' }" :title="`現價 $${current}`"/>
    </div>
    <div class="bar-labels">
      <span>MOS 20% <strong>${{ fmt(mos20) }}</strong></span>
      <span>合理價 <strong>${{ fmt(fair) }}</strong></span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  current: Number,
  fair:    Number,
  mos10:   Number,
  mos20:   Number,
})

const fmt = v => v ? v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'

// pct = how far current price is between mos20 and fair*1.3
const pct = computed(() => {
  if (!props.current || !props.fair) return 50
  const lo = props.mos20 || props.fair * 0.8
  const hi = props.fair  * 1.25
  return Math.min(Math.max(((props.current - lo) / (hi - lo)) * 100, 0), 100)
})

const barColor = computed(() => {
  const p = pct.value
  if (p <= 40) return '#3fb950'
  if (p <= 70) return '#d29922'
  return '#f85149'
})
</script>

<style scoped>
.price-bar   { width: 100%; }
.bar-track   { position: relative; height: 8px; background: #30363d; border-radius: 99px; overflow: visible; }
.bar-fill    { height: 100%; border-radius: 99px; transition: width 0.8s cubic-bezier(.4,0,.2,1); }
.marker      {
  position: absolute; top: 50%; transform: translate(-50%, -50%);
  width: 14px; height: 14px; border-radius: 50%;
  background: #e6edf3; border: 2px solid #0d1117;
  box-shadow: 0 0 0 3px rgba(255,255,255,.2);
  transition: left 0.8s cubic-bezier(.4,0,.2,1);
}
.bar-labels  { display: flex; justify-content: space-between; margin-top: 6px; font-size: 11px; color: #8b949e; }
.bar-labels strong { color: #e6edf3; }
</style>
