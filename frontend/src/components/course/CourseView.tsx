import { useState, useEffect } from "react";
import { courseApi, knowledgeApi } from "../../api";
import "./CourseView.css";

interface CourseInfo {
  id: string;
  title: string;
  subtitle: string | null;
  author: string | null;
  edition: string | null;
  publisher: string | null;
  isbn: string | null;
  language: string;
  description: string | null;
  total_chapters: number;
  difficulty_range: string | null;
  estimated_hours: number | null;
  sort_order: number;
}

interface ChapterInfo {
  id: string;
  course_id: string;
  part_number: number;
  part_title: string | null;
  chapter_number: number;
  chapter_title: string;
  estimated_minutes: number | null;
  difficulty: number;
  kp_ids: string[] | null;
  learning_objectives: string[] | null;
  key_concepts: string[] | null;
}

interface ChapterDetail {
  chapter: ChapterInfo;
  knowledge_points: {
    id: string;
    title: string;
    description: string | null;
    difficulty: number;
    learning_objectives: string[] | null;
    code_examples: string[] | null;
    mastery_level: string;
    bkt_p_know: number;
  }[];
  progress: { status: string; study_minutes: number; mastery_score: number } | null;
}

export default function CourseView() {
  const [courses, setCourses] = useState<CourseInfo[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null);
  const [chapters, setChapters] = useState<ChapterInfo[]>([]);
  const [courseDetail, setCourseDetail] = useState<{
    enrolled: boolean;
    completed_chapters: number;
    current_chapter_number: number | null;
  } | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<ChapterDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    try {
      const { data } = await courseApi.listCourses("python");
      setCourses(data);
      if (data.length > 0) {
        await selectCourse(data[0].id);
      }
    } catch {
      console.error("Failed to load courses");
    } finally {
      setLoading(false);
    }
  };

  const selectCourse = async (courseId: string) => {
    setSelectedCourse(courseId);
    setSelectedChapter(null);
    try {
      const { data } = await courseApi.getCourseDetail(courseId);
      setChapters(data.chapters);
      setCourseDetail({
        enrolled: data.enrolled,
        completed_chapters: data.completed_chapters,
        current_chapter_number: data.current_chapter_number,
      });
    } catch {
      console.error("Failed to load course detail");
    }
  };

  const enrollCourse = async () => {
    if (!selectedCourse) return;
    try {
      await courseApi.enrollCourse(selectedCourse);
      if (courseDetail) setCourseDetail({ ...courseDetail, enrolled: true });
    } catch (err: any) {
      if (err.response?.status !== 409) console.error("Enrollment failed");
      if (courseDetail) setCourseDetail({ ...courseDetail, enrolled: true });
    }
  };

  const selectChapter = async (chapter: ChapterInfo) => {
    if (!selectedCourse) return;
    try {
      const { data } = await courseApi.getChapterDetail(selectedCourse, chapter.id);
      setSelectedChapter(data);
    } catch {
      console.error("Failed to load chapter detail");
    }
  };

  const startChapterStudy = async (chapterId: string, kpId: string) => {
    const event = new CustomEvent("course-select-kp", { detail: { kpId } });
    window.dispatchEvent(event);
    try {
      await courseApi.updateChapterProgress(chapterId, { status: "in_progress" });
    } catch {}
  };

  const difficultyStars = (d: number) => "★".repeat(d) + "☆".repeat(5 - d);

  const groupedChapters = chapters.reduce<Record<number, { part_title: string; items: ChapterInfo[] }>>((acc, ch) => {
    if (!acc[ch.part_number]) acc[ch.part_number] = { part_title: ch.part_title || `Part ${ch.part_number}`, items: [] };
    acc[ch.part_number].items.push(ch);
    return acc;
  }, {});

  if (loading) return <div className="course-loading">加载课程中...</div>;

  return (
    <div className="course-view">
      <div className="course-sidebar">
        <h2 className="course-sidebar-title">📚 Python 参考书籍</h2>
        <div className="course-tabs">
          {courses.map((c) => (
            <button
              key={c.id}
              className={`course-tab ${selectedCourse === c.id ? "active" : ""}`}
              onClick={() => selectCourse(c.id)}
            >
              <span className="course-tab-title">{c.title}</span>
              <span className="course-tab-meta">{c.author} | {c.total_chapters}章</span>
            </button>
          ))}
        </div>

        {courseDetail && !courseDetail.enrolled && (
          <button className="enroll-btn" onClick={enrollCourse}>
            📖 加入学习
          </button>
        )}

        {courseDetail?.enrolled && (
          <div className="enrollment-info">
            ✅ 已加入 | 进度 {courseDetail.completed_chapters}/{chapters.length} 章
          </div>
        )}

        <div className="chapter-list">
          {Object.entries(groupedChapters).map(([partNum, part]) => (
            <div key={partNum} className="chapter-part">
              <div className="part-header">
                <span className="part-badge">Part {partNum}</span>
                <span className="part-title">{part.part_title}</span>
              </div>
              {part.items.map((ch) => (
                <button
                  key={ch.id}
                  className={`chapter-item ${selectedChapter?.chapter.id === ch.id ? "active" : ""}`}
                  onClick={() => selectChapter(ch)}
                >
                  <span className="chapter-num">Ch{ch.chapter_number}</span>
                  <span className="chapter-title">{ch.chapter_title}</span>
                  <span className="chapter-diff">{difficultyStars(ch.difficulty)}</span>
                  {ch.estimated_minutes && <span className="chapter-time">{ch.estimated_minutes}min</span>}
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="course-main">
        {selectedChapter ? (
          <div className="chapter-detail">
            <div className="chapter-header">
              <h2>
                第{selectedChapter.chapter.chapter_number}章：{selectedChapter.chapter.chapter_title}
              </h2>
              <div className="chapter-meta">
                <span>{difficultyStars(selectedChapter.chapter.difficulty)}</span>
                {selectedChapter.chapter.estimated_minutes && (
                  <span>⏱ {selectedChapter.chapter.estimated_minutes} 分钟</span>
                )}
                {selectedChapter.progress && (
                  <span className={`progress-badge ${selectedChapter.progress.status}`}>
                    {selectedChapter.progress.status === "completed" ? "✅ 已完成" :
                     selectedChapter.progress.status === "in_progress" ? "🔄 学习中" : "⬜ 未开始"}
                  </span>
                )}
              </div>
            </div>

            {selectedChapter.chapter.learning_objectives && (
              <div className="chapter-section">
                <h3>🎯 学习目标</h3>
                <ul>
                  {selectedChapter.chapter.learning_objectives.map((obj, i) => (
                    <li key={i}>{obj}</li>
                  ))}
                </ul>
              </div>
            )}

            {selectedChapter.chapter.key_concepts && (
              <div className="chapter-section">
                <h3>🔑 核心概念</h3>
                <div className="concept-tags">
                  {selectedChapter.chapter.key_concepts.map((c, i) => (
                    <span key={i} className="concept-tag">{c}</span>
                  ))}
                </div>
              </div>
            )}

            {selectedChapter.knowledge_points.length > 0 && (
              <div className="chapter-section">
                <h3>📖 关联知识点</h3>
                <div className="kp-cards">
                  {selectedChapter.knowledge_points.map((kp) => (
                    <div key={kp.id} className={`kp-card mastery-${kp.mastery_level}`}>
                      <div className="kp-card-header">
                        <h4>{kp.title}</h4>
                        <span className="kp-mastery">{kp.mastery_level}</span>
                      </div>
                      {kp.description && <p className="kp-desc">{kp.description.slice(0, 120)}...</p>}
                      <div className="kp-progress-bar">
                        <div className="kp-progress-fill" style={{ width: `${Math.round(kp.bkt_p_know * 100)}%` }} />
                        <span className="kp-progress-text">{Math.round(kp.bkt_p_know * 100)}%</span>
                      </div>
                      <button className="kp-study-btn" onClick={() => startChapterStudy(selectedChapter.chapter.id, kp.id)}>
                        开始学习
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="course-empty">
            <div className="course-empty-icon">📚</div>
            <h3>选择一本书籍开始学习</h3>
            <p>从左侧选择章节，按真实书籍章节顺序系统学习 Python</p>
            {selectedCourse && courses.find(c => c.id === selectedCourse) && (
              <div className="course-book-info">
                <h4>{courses.find(c => c.id === selectedCourse)!.title}</h4>
                <p>{courses.find(c => c.id === selectedCourse)!.description}</p>
                <div className="book-meta">
                  <span>👤 {courses.find(c => c.id === selectedCourse)!.author}</span>
                  <span>🏢 {courses.find(c => c.id === selectedCourse)!.publisher}</span>
                  <span>⏱ {courses.find(c => c.id === selectedCourse)!.estimated_hours}小时</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
