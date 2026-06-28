export default function ResultSkeleton() {
  return (
    <div className="skeleton-wrap" aria-busy="true" aria-label="Считаем…">
      <div className="verdict">
        <div className="sk sk-tag" />
        <div className="sk sk-h2" />
        <div className="sk sk-line" style={{ width: "60%" }} />
        <div className="metrics">
          {[0, 1, 2, 3].map((i) => (
            <div className="metric" key={i}>
              <div className="sk sk-line" style={{ width: "70%", height: 12 }} />
              <div className="sk sk-line" style={{ width: "50%", marginTop: 10 }} />
            </div>
          ))}
        </div>
      </div>
      <div className="section">
        <div className="sk sk-line" style={{ width: "40%" }} />
        <div className="sk sk-chart" />
      </div>
    </div>
  );
}
