import AnnouncementHints from './components/AnnouncementHints.jsx'
import DeadlineTable from './components/DeadlineTable.jsx'
import StatusBanner from './components/StatusBanner.jsx'
import { useDashboard } from './hooks/useDashboard.js'

export default function App() {
  const { state, message, loading, connectionError, refresh, notify } = useDashboard()

  return (
    <div className="wrap">
      <header>
        <h1>NTUCOOL 截止面板</h1>
        <div className="actions">
          <button type="button" className="primary" disabled={loading.refresh} onClick={refresh}>
            {loading.refresh ? '處理中…' : '↻ 重新整理'}
          </button>
          <button type="button" className="tele" disabled={loading.notify} onClick={notify}>
            {loading.notify ? '處理中…' : '✈ 發送 Telegram 通知'}
          </button>
        </div>
      </header>

      {state?.last_refresh && <div className="meta">上次更新 {state.last_refresh}</div>}

      {connectionError && (
        <div className="flash bad">連線失敗,請確認 app.py 還在跑。</div>
      )}
      {message && <div className={`flash ${message.category}`}>{message.text}</div>}

      <StatusBanner state={state} loadingInitial={loading.initial} />

      {state?.has_data && (
        <>
          <DeadlineTable
            title="作業"
            itemLabel="作業"
            rows={state.assignments}
            emptyText="目前所有課程都沒有設截止日的作業。"
            showKind={false}
            ok={state.ok}
          />
          <DeadlineTable
            title="考試"
            itemLabel="考試 / 測驗"
            rows={state.exams}
            emptyText="來自 Canvas 測驗(New Quizzes)與行事曆事件,目前查無資料。"
            showKind={true}
            ok={state.ok}
          />
          <AnnouncementHints hints={state.hints} ok={state.ok} />
        </>
      )}
    </div>
  )
}
