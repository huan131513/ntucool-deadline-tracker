export default function StatusBanner({ state, loadingInitial }) {
  if (loadingInitial) {
    return (
      <div className="status">
        <span className="dot none" /> 載入中…
      </div>
    )
  }
  if (!state?.has_data) {
    return (
      <div className="status">
        <span className="dot none" /> 還沒有資料,點右上角「重新整理」抓一次。
      </div>
    )
  }
  if (state.ok) {
    return (
      <div className="status">
        <span className="dot ok" /> Canvas 連線正常
      </div>
    )
  }
  return (
    <div className="status">
      <span className="dot bad" /> <span className="err">{state.error}</span>
    </div>
  )
}
