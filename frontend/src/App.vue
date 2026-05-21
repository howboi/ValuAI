<template>
  <div class="app-shell">

    <header class="header">
      <div class="logo">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="8" fill="#1f6feb"/>
          <polyline
            points="4,20 10,12 16,16 24,7"
            stroke="#58a6ff"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
            fill="none"
          />
        </svg>
        <span>ValuAI</span>
      </div>
      <div class="tagline">台股智能估價儀表板</div>
    </header>

    <section class="search-section">
      <div ref="searchRoot" class="search-card">
        <h1 class="search-title">輸入股票，立即取得估價分析</h1>
        <p class="search-hint">支援台灣上市櫃（例如：2330、6488.TWO、台積電）</p>

        <form class="search-form" @submit.prevent="handleSearch">
          <div class="input-wrap">
            <svg
              class="search-icon"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>

            <input
              v-model="ticker"
              class="search-input"
              placeholder="2330 / 6488.TWO / 台積電"
              :disabled="loading"
              autocomplete="off"
              spellcheck="false"
              @focus="handleInputFocus"
            />

            <ul
              v-if="showDropdown && suggestions.length"
              class="absolute left-0 right-0 top-[calc(100%+8px)] z-30 max-h-72 overflow-auto rounded-xl border border-slate-200 bg-white shadow-lg"
            >
              <li
                v-for="item in suggestions"
                :key="item.code"
                class="border-b border-slate-100 last:border-b-0"
              >
                <button
                  type="button"
                  class="block w-full px-4 py-3 text-left text-sm text-slate-700 transition hover:bg-sky-50 hover:text-sky-800"
                  @click="selectSuggestion(item)"
                >
                  {{ item.display }}
                </button>
              </li>
            </ul>
          </div>

          <button class="search-btn" :disabled="loading || !ticker.trim()" type="submit">
            <span v-if="!loading">估價</span>
            <svg
              v-else
              class="spin"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
            >
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83 M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
          </button>
        </form>

        <p v-if="searchLoading" class="searching-msg">搜尋中...</p>
        <p v-if="error" class="error-msg">{{ error }}</p>
      </div>
    </section>

    <section v-if="loading" class="dashboard fade-in">
      <div class="card skeleton" style="height:120px"/>
      <div class="card skeleton" style="height:280px"/>
      <div class="card skeleton" style="height:280px"/>
      <div class="card skeleton" style="height:200px"/>
    </section>

    <section v-else-if="data" class="dashboard fade-in">
      <div class="card price-card">
        <div class="price-meta">
          <span class="badge">{{ data.sector || '未提供產業別' }}</span>
          <span class="symbol-label">{{ data.symbol }}</span>
        </div>
        <div class="price-main">
          <span class="price-value">${{ fmt(data.current_price) }}</span>
          <span :class="['upside-chip', upsideClass]">
            {{ data.upside_pct > 0 ? '+' : '' }}{{ data.upside_pct?.toFixed(1) }}% {{ upsideLabel }}
          </span>
        </div>
        <div class="price-sub">{{ data.name }}</div>

        <div class="meta-grid">
          <div class="meta-item"><span>市值</span><strong>{{ marketCapStr }}</strong></div>
          <div class="meta-item"><span>Beta</span><strong>{{ data.beta ?? '--' }}</strong></div>
          <div class="meta-item"><span>EPS</span><strong>{{ data.trailing_eps?.toFixed(2) ?? '--' }}</strong></div>
          <div class="meta-item"><span>P/E</span><strong>{{ data.trailing_pe ?? '--' }}</strong></div>
          <div class="meta-item"><span>營收成長</span><strong>{{ data.revenue_growth ?? '--' }}%</strong></div>
          <div class="meta-item"><span>獲利成長</span><strong>{{ data.earnings_growth ?? '--' }}%</strong></div>
        </div>
      </div>

      <div class="card half-card">
        <div class="card-title">估價結果</div>

        <GaugeChart
          :value="gaugeValue"
          :label="`$${fmt(data.valuation.weighted_fair_value)}`"
          sub="加權合理價"
        />

        <div class="val-rows">
          <div class="val-row">
            <span class="val-label">
              <i class="dot" style="background:#58a6ff"/>DCF 估值
              <small>{{ data.valuation.dcf_weight }}%</small>
            </span>
            <span class="val-price">{{ data.valuation.dcf_price ? `$${fmt(data.valuation.dcf_price)}` : '無法計算' }}</span>
          </div>
          <div class="val-row">
            <span class="val-label">
              <i class="dot" style="background:#3fb950"/>P/E 估值
              <small>{{ data.valuation.pe_weight }}%</small>
            </span>
            <span class="val-price">{{ data.valuation.pe_price ? `$${fmt(data.valuation.pe_price)}` : '無法計算' }}</span>
          </div>
        </div>

        <div class="divider"/>

        <div class="mos-grid">
          <div class="mos-item">
            <span>10% 安全邊際</span>
            <strong>${{ fmt(data.margin_of_safety.discount_10) }}</strong>
          </div>
          <div class="mos-item">
            <span>20% 安全邊際</span>
            <strong>${{ fmt(data.margin_of_safety.discount_20) }}</strong>
          </div>
        </div>

        <PriceBar
          :current="data.current_price"
          :fair="data.valuation.weighted_fair_value"
          :mos10="data.margin_of_safety.discount_10"
          :mos20="data.margin_of_safety.discount_20"
          class="mt-4"
        />

        <div class="rec-chip" :class="recClass">{{ data.recommendation }}</div>
      </div>

      <div class="card half-card">
        <div class="card-title">技術面參考</div>
        <div class="current-tag">現價 ${{ fmt(data.current_price) }}</div>

        <div v-if="Object.keys(data.technical.resistance).length" class="level-section">
          <div class="level-header resist">壓力位</div>
          <div v-for="(val, key) in data.technical.resistance" :key="key" class="level-row">
            <span class="level-name">{{ key }}</span>
            <div class="level-bar-wrap">
              <div class="level-bar resist" :style="{ width: levelPct(val, 'resist') + '%' }"/>
            </div>
            <span class="level-price resist">${{ fmt(val) }}</span>
            <span class="level-dist resist">+{{ distPct(val) }}%</span>
          </div>
        </div>

        <div v-if="Object.keys(data.technical.support).length" class="level-section">
          <div class="level-header support">支撐位</div>
          <div v-for="(val, key) in data.technical.support" :key="key" class="level-row">
            <span class="level-name">{{ key }}</span>
            <div class="level-bar-wrap">
              <div class="level-bar support" :style="{ width: levelPct(val, 'support') + '%' }"/>
            </div>
            <span class="level-price support">${{ fmt(val) }}</span>
            <span class="level-dist support">-{{ distPct(val) }}%</span>
          </div>
        </div>
      </div>

      <div class="card chart-card">
        <div class="card-title">歷史 K 線</div>
        <StockChart
          :chart-data="data.chart_data || []"
          :price-levels="chartPriceLevels"
        />
      </div>

      <div class="card summary-card">
        <div class="card-title">摘要總覽</div>
        <div class="summary-grid">
          <div class="summary-item">
            <span>加權合理價</span>
            <strong>${{ fmt(data.valuation.weighted_fair_value) }}</strong>
          </div>
          <div class="summary-item">
            <span>潛在報酬</span>
            <strong :style="{ color: data.upside_pct >= 0 ? '#3fb950' : '#f85149' }">{{ data.upside_pct > 0 ? '+' : '' }}{{ data.upside_pct?.toFixed(1) }}%</strong>
          </div>
          <div class="summary-item">
            <span>第一壓力位</span>
            <strong style="color:#f85149">${{ fmt(firstResist) }}</strong>
          </div>
          <div class="summary-item">
            <span>第一支撐位</span>
            <strong style="color:#3fb950">${{ fmt(firstSupport) }}</strong>
          </div>
          <div class="summary-item">
            <span>DCF 權重</span>
            <strong>{{ data.valuation.dcf_weight }}%</strong>
          </div>
          <div class="summary-item">
            <span>P/E 權重</span>
            <strong>{{ data.valuation.pe_weight }}%</strong>
          </div>
        </div>
        <div class="disclaimer">本頁為自動估值結果，僅供研究參考，請自行評估風險。</div>
      </div>
    </section>

    <footer class="footer">
      Powered by <a href="https://github.com/ranaroussi/yfinance" target="_blank" rel="noopener">yfinance</a>
    </footer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import GaugeChart from './components/GaugeChart.vue'
import PriceBar from './components/PriceBar.vue'
import StockChart from './components/StockChart.vue'

const ticker = ref('')
const loading = ref(false)
const error = ref('')
const data = ref(null)

const suggestions = ref([])
const showDropdown = ref(false)
const searchLoading = ref(false)
const selectedCode = ref('')
const selectedName = ref('')
const searchRoot = ref(null)

let debounceTimer = null
let latestSearchToken = 0

watch(ticker, (newValue) => {
  if (newValue !== selectedName.value) {
    selectedCode.value = ''
  }
  const keyword = newValue.trim()

  if (debounceTimer) clearTimeout(debounceTimer)

  if (!keyword) {
    suggestions.value = []
    showDropdown.value = false
    return
  }

  debounceTimer = setTimeout(() => {
    fetchSuggestions(keyword)
  }, 300)
})

function handleInputFocus() {
  if (suggestions.value.length > 0) showDropdown.value = true
}

function selectSuggestion(item) {
  ticker.value = item.name
  selectedCode.value = item.code
  selectedName.value = item.name
  showDropdown.value = false
  suggestions.value = []
  handleSearch(item.code)
}

function resolveStockCode(value) {
  const raw = value.trim()
  const matchedSuggestion = suggestions.value.find((item) => (
    item.code.toUpperCase() === raw.toUpperCase()
    || item.name === raw
    || item.display === raw
  ))

  if (matchedSuggestion) return matchedSuggestion.code
  if (selectedCode.value && raw === selectedName.value) return selectedCode.value
  if (/^\d{4}$/.test(raw)) return raw
  return raw.toUpperCase()
}

async function fetchSuggestions(keyword) {
  const token = ++latestSearchToken
  searchLoading.value = true

  try {
    const res = await axios.get('/api/search', {
      params: { q: keyword },
    })

    if (token !== latestSearchToken) return

    suggestions.value = Array.isArray(res.data) ? res.data : []
    showDropdown.value = suggestions.value.length > 0
  } catch {
    suggestions.value = []
    showDropdown.value = false
  } finally {
    if (token === latestSearchToken) {
      searchLoading.value = false
    }
  }
}

function onClickOutside(event) {
  if (searchRoot.value && !searchRoot.value.contains(event.target)) {
    showDropdown.value = false
  }
}

async function handleSearch(codeFromSelection = '') {
  const input = typeof codeFromSelection === 'string' ? codeFromSelection : ticker.value
  const code = resolveStockCode(input || ticker.value)
  if (!code) return

  loading.value = true
  error.value = ''
  data.value = null
  showDropdown.value = false

  try {
    const res = await axios.get('/api/valuation', {
      params: { code },
    })
    data.value = res.data?.data ?? null
  } catch (e) {
    error.value = e.response?.data?.message || e.response?.data?.detail || '查詢失敗，請確認股票代碼'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onClickOutside)
  if (debounceTimer) clearTimeout(debounceTimer)
})

const fmt = (v) => (v != null
  ? Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  : '--')

const marketCapStr = computed(() => {
  const b = data.value?.market_cap_b
  if (!b) return '--'
  return b >= 1000 ? `$${(b / 1000).toFixed(1)}T` : `$${b.toFixed(1)}B`
})

const upsideClass = computed(() => {
  const u = data.value?.upside_pct ?? 0
  if (u > 15) return 'chip-green'
  if (u > 0) return 'chip-blue'
  if (u > -15) return 'chip-yellow'
  return 'chip-red'
})

const upsideLabel = computed(() => {
  const u = data.value?.upside_pct ?? 0
  if (u > 15) return '偏低估'
  if (u > 0) return '可留意'
  if (u > -15) return '接近合理'
  return '偏高估'
})

const gaugeValue = computed(() => {
  const u = data.value?.upside_pct ?? 0
  return Math.min(Math.max(50 + u, 0), 100)
})

const recClass = computed(() => {
  const r = data.value?.recommendation ?? ''
  if (r.includes('優先') || r.includes('布局')) return 'rec-green'
  if (r.includes('合理')) return 'rec-blue'
  return 'rec-yellow'
})

const firstResist = computed(() => Object.values(data.value?.technical.resistance ?? {})[0])
const firstSupport = computed(() => Object.values(data.value?.technical.support ?? {})[0])

const chartPriceLevels = computed(() => ({
  fairValue: data.value?.valuation.weighted_fair_value,
  marginOfSafety10: data.value?.margin_of_safety.discount_10,
  resistance: firstResist.value,
  support: firstSupport.value,
}))

function distPct(val) {
  const cur = data.value?.current_price
  if (!cur) return '0.0'
  return Math.abs(((val - cur) / cur) * 100).toFixed(1)
}

const maxResist = computed(() => Math.max(...Object.values(data.value?.technical.resistance ?? { _: 1 })))

function levelPct(val, dir) {
  const cur = data.value?.current_price ?? 1
  if (dir === 'resist') {
    const hi = maxResist.value
    return hi === cur ? 30 : Math.min((((val - cur) / (hi - cur)) * 85) + 15, 100)
  }

  const lo = Math.min(...Object.values(data.value?.technical.support ?? { _: cur * 0.7 }))
  return lo === cur ? 30 : Math.min((((cur - val) / (cur - lo)) * 85) + 15, 100)
}
</script>

<style scoped>
.app-shell { min-height: 100vh; background: var(--bg-base); }

.header {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 32px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.logo { display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 700; color: #e6edf3; }
.tagline { margin-left: auto; font-size: 13px; color: var(--muted); }

.search-section { padding: 48px 24px 32px; display: flex; justify-content: center; }
.search-card {
  width: 100%; max-width: 680px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 36px 40px;
  box-shadow: 0 8px 40px rgba(0,0,0,.4);
}
.search-title { font-size: 22px; font-weight: 700; margin-bottom: 6px; }
.search-hint  { font-size: 13px; color: var(--muted); margin-bottom: 24px; }
.search-form  { display: flex; gap: 12px; }
.input-wrap   { flex: 1; position: relative; }
.search-icon  { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--muted); z-index: 1; }
.search-input {
  width: 100%; padding: 12px 16px 12px 42px;
  background: var(--bg-base); color: var(--text);
  border: 1px solid var(--border); border-radius: 10px;
  font-size: 15px; font-family: inherit;
  transition: border-color .2s, box-shadow .2s;
  outline: none;
}
.search-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-dim);
}
.search-btn {
  padding: 12px 28px;
  background: var(--accent); color: #0d1117;
  border: none; border-radius: 10px;
  font-size: 15px; font-weight: 600; font-family: inherit;
  cursor: pointer; display: flex; align-items: center; gap: 8px;
  transition: opacity .2s, transform .1s;
}
.search-btn:hover:not(:disabled) { opacity: .88; transform: translateY(-1px); }
.search-btn:disabled { opacity: .45; cursor: not-allowed; }
.searching-msg { margin-top: 12px; color: var(--muted); font-size: 13px; }
.error-msg { margin-top: 12px; color: var(--red); font-size: 13px; }

.dashboard {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 20px;
  padding: 0 24px 48px;
  max-width: 1400px;
  margin: 0 auto;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,.3);
}
.card-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 600; color: var(--muted);
  text-transform: uppercase; letter-spacing: .6px;
  margin-bottom: 20px;
}

.price-card,
.chart-card { grid-column: 1 / -1; }
.half-card { grid-column: span 6; }
.price-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.badge {
  background: var(--accent-dim); color: var(--accent);
  padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600;
}
.symbol-label { font-size: 14px; color: var(--muted); font-family: monospace; }
.price-main { display: flex; align-items: center; gap: 16px; margin-bottom: 4px; }
.price-value { font-size: 40px; font-weight: 800; color: var(--text); letter-spacing: -1px; }
.price-sub   { font-size: 14px; color: var(--muted); margin-bottom: 20px; }
.upside-chip { padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: 600; }

.meta-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }
.meta-item { display: flex; flex-direction: column; gap: 4px; }
.meta-item span { font-size: 11px; color: var(--muted); }
.meta-item strong { font-size: 15px; font-weight: 600; }

.val-rows   { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.val-row    { display: flex; align-items: center; justify-content: space-between; }
.val-label  { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--muted); }
.val-label small { font-size: 11px; background: #30363d; padding: 1px 6px; border-radius: 4px; }
.val-price  { font-size: 16px; font-weight: 600; }
.dot        { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.divider    { height: 1px; background: var(--border); margin: 16px 0; }
.mos-grid   { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.mos-item   { background: var(--bg-card2); border-radius: 10px; padding: 12px; }
.mos-item span   { display: block; font-size: 11px; color: var(--muted); margin-bottom: 4px; }
.mos-item strong { font-size: 17px; font-weight: 700; }
.mt-4 { margin-top: 16px; }
.rec-chip {
  margin-top: 16px; text-align: center; padding: 10px; border-radius: 10px;
  font-size: 14px; font-weight: 600;
}
.rec-green  { background: rgba(63,185,80,.15);  color: #3fb950; }
.rec-blue   { background: rgba(88,166,255,.15); color: #58a6ff; }
.rec-yellow { background: rgba(210,153,34,.15); color: #d29922; }

.current-tag {
  background: var(--bg-card2); display: inline-block;
  padding: 4px 12px; border-radius: 6px;
  font-size: 13px; font-weight: 600; margin-bottom: 16px;
}
.level-section { margin-bottom: 16px; }
.level-header { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }
.level-header.resist  { color: var(--red); }
.level-header.support { color: var(--green); }
.level-row { display: grid; grid-template-columns: 90px 1fr 80px 50px; align-items: center; gap: 8px; margin-bottom: 6px; }
.level-name  { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.level-bar-wrap { height: 6px; background: var(--border); border-radius: 99px; overflow: hidden; }
.level-bar { height: 100%; border-radius: 99px; transition: width .6s ease; }
.level-bar.resist  { background: rgba(248,81,73,.5); }
.level-bar.support { background: rgba(63,185,80,.5); }
.level-price { font-size: 13px; font-weight: 600; text-align: right; }
.level-price.resist  { color: var(--red); }
.level-price.support { color: var(--green); }
.level-dist  { font-size: 11px; color: var(--muted); text-align: right; }

.summary-card { grid-column: 1 / -1; }
.summary-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; margin-bottom: 20px; }
.summary-item { display: flex; flex-direction: column; gap: 6px; }
.summary-item span   { font-size: 12px; color: var(--muted); }
.summary-item strong { font-size: 18px; font-weight: 700; }
.disclaimer { font-size: 12px; color: var(--muted); border-top: 1px solid var(--border); padding-top: 16px; }

.chip-green  { background: rgba(63,185,80,.2);  color: #3fb950; }
.chip-blue   { background: rgba(88,166,255,.2); color: #58a6ff; }
.chip-yellow { background: rgba(210,153,34,.2); color: #d29922; }
.chip-red    { background: rgba(248,81,73,.2);  color: #f85149; }

@media (max-width: 768px) {
  .header { padding: 12px 16px; }
  .tagline { display: none; }
  .dashboard { grid-template-columns: 1fr; }
  .search-card { padding: 24px 20px; }
  .search-form { flex-direction: column; }
  .half-card { grid-column: 1 / -1; }
  .meta-grid { grid-template-columns: repeat(3, 1fr); }
  .summary-grid { grid-template-columns: repeat(3, 1fr); }
  .level-row { grid-template-columns: 70px 1fr 70px 44px; }
}

.footer {
  text-align: center;
  padding: 20px;
  font-size: 12px;
  color: var(--muted);
  border-top: 1px solid var(--border);
  margin-top: 8px;
}
.footer a {
  color: var(--accent);
  text-decoration: none;
}
.footer a:hover { text-decoration: underline; }
</style>
