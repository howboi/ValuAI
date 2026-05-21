<template>
  <section class="mx-auto w-full max-w-3xl">
    <div
      ref="searchRoot"
      class="relative rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 class="text-xl font-bold text-slate-900">台股智能搜尋</h2>
      <p class="mt-1 text-sm text-slate-500">輸入代碼或中文名稱，選取後自動執行估價</p>

      <form class="mt-4" @submit.prevent="handleSubmit">
        <label for="stock-search" class="mb-2 block text-sm font-medium text-slate-700">
          股票查詢
        </label>
        <div class="relative">
          <input
            id="stock-search"
            v-model="query"
            type="text"
            autocomplete="off"
            spellcheck="false"
            placeholder="例如：2330、台積電、聯發科"
            class="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-800 outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
            @focus="handleInputFocus"
          />

          <ul
            v-if="showDropdown && suggestions.length > 0"
            class="absolute left-0 top-full z-30 mt-2 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg"
          >
            <li
              v-for="item in suggestions"
              :key="item.code"
              class="cursor-pointer border-b border-slate-100 last:border-b-0"
              @click="selectSuggestion(item)"
            >
              <button
                type="button"
                class="block w-full px-4 py-3 text-left text-sm text-slate-700 transition hover:bg-sky-50 hover:text-sky-800"
              >
                {{ item.display }}
              </button>
            </li>
          </ul>
        </div>
      </form>

      <p v-if="searchLoading" class="mt-2 text-sm text-slate-500">搜尋中...</p>
      <p v-if="valuationError" class="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
        {{ valuationError }}
      </p>
    </div>

    <div
      v-if="valuationLoading"
      class="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <p class="text-sm text-slate-500">估價資料載入中...</p>
    </div>

    <div
      v-else-if="valuationData"
      class="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-xs text-slate-500">{{ valuationData.symbol }}</p>
          <h3 class="text-lg font-bold text-slate-900">
            {{ valuationData.name || "未提供名稱" }}
          </h3>
          <p class="text-sm text-slate-500">{{ valuationData.sector || "未提供產業別" }}</p>
        </div>
        <div class="rounded-xl bg-sky-50 px-4 py-3 text-right">
          <p class="text-xs text-sky-700">目前股價</p>
          <p class="text-xl font-bold text-sky-900">${{ fmt(valuationData.current_price) }}</p>
        </div>
      </div>

      <div class="mt-4 grid gap-3 sm:grid-cols-2">
        <div class="rounded-xl border border-slate-200 p-4">
          <p class="text-xs text-slate-500">加權合理價</p>
          <p class="mt-1 text-lg font-semibold text-slate-900">
            ${{ fmt(valuationData.valuation?.weighted_fair_value) }}
          </p>
        </div>
        <div class="rounded-xl border border-slate-200 p-4">
          <p class="text-xs text-slate-500">潛在漲跌幅</p>
          <p
            class="mt-1 text-lg font-semibold"
            :class="(valuationData.upside_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'"
          >
            {{ signedPct(valuationData.upside_pct) }}
          </p>
        </div>
        <div class="rounded-xl border border-slate-200 p-4">
          <p class="text-xs text-slate-500">安全邊際（10%）</p>
          <p class="mt-1 text-lg font-semibold text-slate-900">
            ${{ fmt(valuationData.margin_of_safety?.discount_10) }}
          </p>
        </div>
        <div class="rounded-xl border border-slate-200 p-4">
          <p class="text-xs text-slate-500">安全邊際（20%）</p>
          <p class="mt-1 text-lg font-semibold text-slate-900">
            ${{ fmt(valuationData.margin_of_safety?.discount_20) }}
          </p>
        </div>
      </div>

      <p class="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
        建議：{{ valuationData.recommendation || "暫無建議" }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios from 'axios'

const query = ref('')
const suggestions = ref([])
const showDropdown = ref(false)
const searchLoading = ref(false)
const valuationLoading = ref(false)
const valuationError = ref('')
const valuationData = ref(null)
const selectedCode = ref('')
const searchRoot = ref(null)

let debounceTimer = null
let latestSearchToken = 0

watch(query, (newValue) => {
  selectedCode.value = ''
  const keyword = newValue.trim()

  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }

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
  if (suggestions.value.length > 0) {
    showDropdown.value = true
  }
}

function handleSubmit() {
  const code = resolveStockCode(query.value)
  if (code) fetchValuation(code)
}

function resolveStockCode(value) {
  const raw = value.trim()
  const matchedSuggestion = suggestions.value.find((item) => (
    item.code.toUpperCase() === raw.toUpperCase()
    || item.name === raw
    || item.display === raw
  ))

  if (matchedSuggestion) return matchedSuggestion.code
  if (selectedCode.value) return selectedCode.value
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

function selectSuggestion(item) {
  query.value = item.name
  selectedCode.value = item.code
  showDropdown.value = false
  suggestions.value = []
  fetchValuation(item.code)
}

async function fetchValuation(code) {
  valuationLoading.value = true
  valuationError.value = ''
  valuationData.value = null
  try {
    const res = await axios.get('/api/valuation', {
      params: { code },
    })
    valuationData.value = res.data?.data ?? null
  } catch (err) {
    valuationError.value =
      err?.response?.data?.message ||
      err?.response?.data?.detail ||
      '估價失敗，請稍後再試'
  } finally {
    valuationLoading.value = false
  }
}

function onClickOutside(event) {
  if (searchRoot.value && !searchRoot.value.contains(event.target)) {
    showDropdown.value = false
  }
}

function fmt(value) {
  if (value == null) return '--'
  return Number(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function signedPct(value) {
  if (value == null) return '--'
  const num = Number(value)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(1)}%`
}

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onClickOutside)
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>
