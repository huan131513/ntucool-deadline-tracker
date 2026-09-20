import AnnouncementHints from './components/AnnouncementHints.jsx'
import CoursesPanel from './components/CoursesPanel.jsx'
import DeadlineTable from './components/DeadlineTable.jsx'
import MiniCalendar from './components/MiniCalendar.jsx'
import ProgressPanel from './components/ProgressPanel.jsx'
import StatusBanner from './components/StatusBanner.jsx'
import { useDashboard } from './hooks/useDashboard.js'
import { usePdfGuessStatus } from './hooks/usePdfGuessStatus.js'
import { useSeenTracker } from './hooks/useSeenTracker.js'

export default function App() {
  const { state, message, messageFading, progress, loading, connectionError, refresh, notify } = useDashboard()
  const assignmentsSeen = useSeenTracker('ntucool_seen_assignments')
  const examsSeen = useSeenTracker('ntucool_seen_exams')
  const pdfGuessStatus = usePdfGuessStatus()

  return (
    <div className="wrap">
      <header>
        <h1>NTUCOOL 作業截止通知網站</h1>
        <div className="actions">
          <button type="button" className="primary" disabled={loading.refresh} onClick={refresh}>
            {loading.refresh ? '處理中…' : '↻ 重新整理'}
          </button>
          <button
            type="button"
            className="tele"
            disabled={loading.notify || state?.telegram_configured === false}
            title={state?.telegram_configured === false ? 'config.json 尚未設定 telegram_bot_token / telegram_chat_id' : undefined}
            onClick={notify}
          >
            {loading.notify ? '處理中…' : '✈ 發送 Telegram 通知'}
          </button>
        </div>
      </header>

      {state?.last_refresh && <div className="meta">上次更新 {state.last_refresh}</div>}

      {connectionError && (
        <div className="flash bad">連線失敗,請確認 app.py 還在跑。</div>
      )}
      {message && (
        <div className={`flash ${message.category}${messageFading ? ' fade-out' : ''}`}>{message.text}</div>
      )}

      <div className="top-grid">
        <div className="top-left">
          <ProgressPanel progress={progress} />
          <StatusBanner state={state} loadingInitial={loading.initial} />
        </div>
        <MiniCalendar assignments={state?.assignments} exams={state?.exams} term={state?.term} />
      </div>

      {state?.has_data && (
        <>
          <CoursesPanel courses={state?.courses} />

          <DeadlineTable
            id="assignments-section"
            title="作業"
            itemLabel="作業"
            rows={state.assignments}
            emptyText="無資料"
            showKind={false}
            showCompleted={true}
            ok={state.ok}
            isNew={assignmentsSeen.isNew}
            onRowSeen={assignmentsSeen.markSeen}
            isPdfGuessDone={pdfGuessStatus.isCompleted}
            onTogglePdfGuess={pdfGuessStatus.toggle}
          />
          <AnnouncementHints
            title="課程首頁可能提到的作業"
            disclaimer="從課程首頁/課程大綱抓取關鍵字，不一定是真的作業，請自行點進去確認。"
            hints={state.assignment_hints}
            ok={state.ok}
          />

          <DeadlineTable
            id="exams-section"
            title="考試"
            itemLabel="考試 / 測驗"
            rows={state.exams}
            emptyText="無資料"
            showKind={true}
            showCompleted={true}
            ok={state.ok}
            isNew={examsSeen.isNew}
            onRowSeen={examsSeen.markSeen}
          />
          <AnnouncementHints
            title="公告中可能提到的考試"
            disclaimer="從公布欄抓取關鍵字，不一定正確，請自行點進去確認日期是否正確。"
            hints={state.hints}
            ok={state.ok}
          />
        </>
      )}
    </div>
  )
}
