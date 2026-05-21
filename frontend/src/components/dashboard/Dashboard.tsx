import { useEffect } from "react";
import { useLearningStore } from "../../store";
import { Target, Brain, Flame, Clock, TrendingUp, AlertTriangle } from "lucide-react";

const MASTERY_COLORS: Record<string, string> = {
  unlearned: "#94a3b8",
  weak: "#f97316",
  surface: "#eab308",
  learned: "#22c55e",
  mastered: "#6366f1",
};

export default function Dashboard() {
  const { learningPath, knowledgeStates, dailyPlan, cognitiveLoad, loadLearningPath, loadKnowledgeStates, loadDailyPlan, loadCognitiveLoad } = useLearningStore();

  useEffect(() => {
    loadLearningPath();
    loadKnowledgeStates();
    loadDailyPlan();
    loadCognitiveLoad();
  }, []);

  const totalKps = learningPath?.total_kps || 0;
  const masteredCount = learningPath?.mastered_count || 0;
  const progress = totalKps > 0 ? Math.round((masteredCount / totalKps) * 100) : 0;

  const avgMastery = knowledgeStates.length > 0
    ? knowledgeStates.reduce((sum, s) => sum + s.bkt_p_know, 0) / knowledgeStates.length
    : 0;

  const weakPoints = knowledgeStates.filter((s) => s.bkt_p_know < 0.6);
  const reviewDue = knowledgeStates.filter((s) => {
    if (!s.next_review_at) return false;
    return new Date(s.next_review_at) <= new Date();
  });

  return (
    <div className="dashboard">
      <h2>学习仪表盘</h2>

      <div className="stats-grid">
        <div className="stat-card">
          <Target size={24} />
          <div className="stat-info">
            <span className="stat-value">{progress}%</span>
            <span className="stat-label">总体进度</span>
          </div>
        </div>

        <div className="stat-card">
          <Brain size={24} />
          <div className="stat-info">
            <span className="stat-value">{Math.round(avgMastery * 100)}%</span>
            <span className="stat-label">平均掌握度</span>
          </div>
        </div>

        <div className="stat-card">
          <Flame size={24} />
          <div className="stat-info">
            <span className="stat-value">{masteredCount}</span>
            <span className="stat-label">已掌握</span>
          </div>
        </div>

        <div className="stat-card">
          <Clock size={24} />
          <div className="stat-info">
            <span className="stat-value">{reviewDue.length}</span>
            <span className="stat-label">待复习</span>
          </div>
        </div>
      </div>

      {cognitiveLoad && cognitiveLoad.load_level !== "optimal" && (
        <div className={`cognitive-alert ${cognitiveLoad.load_level}`}>
          <AlertTriangle size={20} />
          <span>{cognitiveLoad.message}</span>
        </div>
      )}

      <div className="dashboard-sections">
        <div className="section">
          <h3><TrendingUp size={18} /> 知识点掌握分布</h3>
          <div className="mastery-distribution">
            {knowledgeStates.map((state) => (
              <div key={state.kp_id} className="mastery-bar-item">
                <div
                  className="mastery-bar"
                  style={{
                    width: `${Math.round(state.bkt_p_know * 100)}%`,
                    backgroundColor: MASTERY_COLORS[state.mastery_level] || "#94a3b8",
                  }}
                />
                <span className="mastery-pct">{Math.round(state.bkt_p_know * 100)}%</span>
              </div>
            ))}
          </div>
        </div>

        {weakPoints.length > 0 && (
          <div className="section weak-points">
            <h3><AlertTriangle size={18} /> 薄弱知识点</h3>
            <ul>
              {weakPoints.map((s) => (
                <li key={s.kp_id}>
                  <span className="kp-id">{s.kp_id.slice(0, 8)}...</span>
                  <span className="bkt-value">BKT: {Math.round(s.bkt_p_know * 100)}%</span>
                  <span className="mastery-badge" style={{ backgroundColor: MASTERY_COLORS[s.mastery_level] }}>
                    {s.mastery_level}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {dailyPlan && (
          <div className="section daily-plan">
            <h3><Clock size={18} /> 今日计划</h3>
            <div className="plan-items">
              {dailyPlan.review_items.length > 0 && (
                <div className="plan-group">
                  <span className="plan-label">复习</span>
                  <span className="plan-count">{dailyPlan.review_items.length} 项</span>
                </div>
              )}
              {dailyPlan.new_items.length > 0 && (
                <div className="plan-group">
                  <span className="plan-label">新学</span>
                  <span className="plan-count">{dailyPlan.new_items.length} 项</span>
                </div>
              )}
              {dailyPlan.challenge_items.length > 0 && (
                <div className="plan-group">
                  <span className="plan-label">挑战</span>
                  <span className="plan-count">{dailyPlan.challenge_items.length} 项</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
