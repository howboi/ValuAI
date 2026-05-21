<template>
  <div class="stock-chart">
    <div ref="chartContainer" class="chart-container" />
    <div v-if="!normalizedData.length" class="empty-state">暫無 K 線資料</div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CandlestickSeries, ColorType, LineStyle, createChart } from 'lightweight-charts'

const props = defineProps({
  chartData: {
    type: Array,
    default: () => [],
  },
  priceLevels: {
    type: Object,
    default: () => ({}),
  },
})

const chartContainer = ref(null)
let chart = null
let candleSeries = null
let resizeObserver = null
let priceLineRefs = []

const normalizedData = computed(() => (
  props.chartData
    .filter((item) => (
      item?.time
      && Number.isFinite(Number(item.open))
      && Number.isFinite(Number(item.high))
      && Number.isFinite(Number(item.low))
      && Number.isFinite(Number(item.close))
    ))
    .map((item) => ({
      time: item.time,
      open: Number(item.open),
      high: Number(item.high),
      low: Number(item.low),
      close: Number(item.close),
    }))
))

const normalizedPriceLevels = computed(() => {
  const levels = props.priceLevels ?? {}

  return [
    {
      key: 'fairValue',
      price: readFinitePrice(levels, ['fairValue', 'weightedFairValue', 'weighted_fair_value']),
      color: '#EAB308',
      lineStyle: LineStyle.Dashed,
      title: '合理估價',
    },
    {
      key: 'marginOfSafety10',
      price: readFinitePrice(levels, ['marginOfSafety10', 'discount10', 'discount_10']),
      color: '#22C55E',
      lineStyle: LineStyle.Solid,
      title: '安全邊際 (買入)',
    },
    {
      key: 'resistance',
      price: readFinitePrice(levels, ['resistance', 'recentResistance']),
      color: '#EF4444',
      lineStyle: LineStyle.Dotted,
      title: '壓力位',
    },
    {
      key: 'support',
      price: readFinitePrice(levels, ['support', 'recentSupport']),
      color: '#3B82F6',
      lineStyle: LineStyle.Dotted,
      title: '支撐位',
    },
  ].filter((level) => level.price != null)
})

function readFinitePrice(source, keys) {
  for (const key of keys) {
    const value = Number(source[key])
    if (Number.isFinite(value) && value > 0) return value
  }

  return null
}

function resizeChart() {
  if (!chart || !chartContainer.value) return

  const { width, height } = chartContainer.value.getBoundingClientRect()
  chart.resize(Math.max(Math.floor(width), 1), Math.max(Math.floor(height), 1))
  chart.timeScale().fitContent()
}

function clearPriceLines() {
  if (!candleSeries) {
    priceLineRefs = []
    return
  }

  priceLineRefs.forEach((line) => candleSeries.removePriceLine(line))
  priceLineRefs = []
}

function renderPriceLines() {
  if (!candleSeries) return

  clearPriceLines()
  priceLineRefs = normalizedPriceLevels.value.map((level) => (
    candleSeries.createPriceLine({
      price: level.price,
      color: level.color,
      lineWidth: 2,
      lineStyle: level.lineStyle,
      axisLabelVisible: true,
      title: level.title,
    })
  ))
}

function initChart() {
  if (!chartContainer.value || chart) return

  chart = createChart(chartContainer.value, {
    autoSize: false,
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#f0f6fc',
      fontFamily: 'Inter, system-ui, sans-serif',
    },
    grid: {
      vertLines: { color: 'rgba(139, 148, 158, 0.12)' },
      horzLines: { color: 'rgba(139, 148, 158, 0.12)' },
    },
    rightPriceScale: {
      borderColor: 'rgba(139, 148, 158, 0.24)',
    },
    timeScale: {
      borderColor: 'rgba(139, 148, 158, 0.24)',
      timeVisible: true,
      secondsVisible: false,
    },
    crosshair: {
      vertLine: { color: 'rgba(88, 166, 255, 0.45)' },
      horzLine: { color: 'rgba(88, 166, 255, 0.45)' },
    },
  })

  candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: '#3fb950',
    downColor: '#f85149',
    borderUpColor: '#3fb950',
    borderDownColor: '#f85149',
    wickUpColor: '#3fb950',
    wickDownColor: '#f85149',
  })

  candleSeries.setData(normalizedData.value)
  renderPriceLines()
  resizeChart()

  resizeObserver = new ResizeObserver(() => resizeChart())
  resizeObserver.observe(chartContainer.value)
}

watch(normalizedData, (nextData) => {
  if (!candleSeries) return
  candleSeries.setData(nextData)
  renderPriceLines()
  resizeChart()
})

watch(normalizedPriceLevels, () => {
  renderPriceLines()
})

onMounted(async () => {
  await nextTick()
  initChart()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null

  clearPriceLines()
  chart?.remove()
  chart = null
  candleSeries = null
})
</script>

<style scoped>
.stock-chart {
  position: relative;
  min-height: 360px;
}

.chart-container {
  width: 100%;
  height: 360px;
}

.empty-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #8b949e;
  font-size: 14px;
  pointer-events: none;
}

@media (max-width: 768px) {
  .stock-chart {
    min-height: 300px;
  }

  .chart-container {
    height: 300px;
  }
}
</style>
