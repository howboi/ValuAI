# ValuAI - AI金融估價分析儀表板

結合基本面估價模型與技術面 K 線分析的台股 Dashboard，支援上市（TW）與上櫃（TWO）股票查詢，協助快速判斷合理價、安全邊際與關鍵支撐壓力位。

## ✨ 核心功能

- 🔍 **台股智慧搜尋**
  - 支援股票代碼查詢，例如 `2330`、`6488.TWO`
  - 支援中文名稱搜尋，例如 `台積電`、`環球晶`
  - 整合上市 / 上櫃官方公司清單，提升中文搜尋準確度

- 📊 **基本面估價模型**
  - DCF 現金流折現估價
  - P/E 本益比估價
  - 動態權重整合合理價

- 🛡️ **安全邊際計算**
  - 自動計算 10% 與 20% 安全邊際價格
  - 根據現價與合理價給出估值建議

- 📈 **技術面分析**
  - 自動計算近期支撐位與壓力位
  - 顯示均線、量能重心與近期高低點參考

- 🕯️ **互動式 K 線圖**
  - 使用 Lightweight Charts 繪製 6 個月日 K 線
  - 在圖表上標記：
    - 合理估價
    - 安全邊際買入價
    - 壓力位
    - 支撐位

## 🧰 技術棧

### Frontend

- Vite
- Vue 3
- Tailwind CSS
- Lightweight Charts
- Axios
- Chart.js / vue-chartjs

### Backend

- FastAPI
- yfinance
- Pandas
- NumPy
- Pydantic

## 🏗️ 架構說明
本專案採用前後端分離架構：

Vue 3 Frontend
      |
      |  Axios API Request
      v
FastAPI Backend
      |
      |  yfinance / 官方台股清單
      v
台股價格資料、基本面資料、技術分析資料

### 前端負責：

- 搜尋輸入與結果展示
- Dashboard 版面呈現
- K 線圖與估價水平線繪製

### 後端負責：

- 台股代碼與中文名稱解析
- yfinance 資料抓取
- DCF / P/E 估價計算
- 安全邊際與技術點位計算
- 回傳前端可直接使用的 JSON 資料

## ⚠️ 免責聲明

本專案產生之估價與技術分析結果僅供研究與作品展示用途，不構成任何投資建議。投資前請自行評估風險。

```bash
git clone https://github.com/your-username/stock-valuation-dashboard.git
cd stock-valuation-dashboard
