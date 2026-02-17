import { useMemo, useState } from "react";

const workflowSteps = [
  {
    id: "script",
    title: "Script Copilot",
    tagline: "Shape the narrative spine",
    detailTitle: "Beat map, dialogue rhythm, and tone lock",
    description:
      "Build scene-by-scene momentum with AI-guided rewrites, emotion tags, and pacing hints before moving to visual planning.",
    metrics: [
      { label: "Scene coherence", value: "94%" },
      { label: "Draft iterations", value: "6" },
      { label: "Dialogue variance", value: "High" },
      { label: "Narrative tempo", value: "2.4 min/beat" },
    ],
  },
  {
    id: "storyboard",
    title: "Storyboard Engine",
    tagline: "Convert words into shots",
    detailTitle: "Shot blocks with camera logic and mood continuity",
    description:
      "Turn script beats into camera-driven frames using focal-length presets, composition guides, and continuity-aware transitions.",
    metrics: [
      { label: "Shot coverage", value: "38 frames" },
      { label: "Camera setups", value: "11" },
      { label: "Continuity score", value: "A-" },
      { label: "Mood fidelity", value: "91%" },
    ],
  },
  {
    id: "edit",
    title: "Video Review",
    tagline: "Refine cut and impact",
    detailTitle: "Timing, sound accents, and emotional payoffs",
    description:
      "Review rough cuts with cadence analysis, impact heatmaps, and key-frame recommendations to sharpen tension and clarity.",
    metrics: [
      { label: "Pacing confidence", value: "89%" },
      { label: "Cut suggestions", value: "14" },
      { label: "Audio sync", value: "Frame-accurate" },
      { label: "Hook retention", value: "+22%" },
    ],
  },
];

const styleOptions = [
  {
    name: "Solar Noir",
    accent: "#ff6f3c",
    start: "#ff8e42",
    end: "#ce2d4f",
    descriptor: "Burnt highlights, long shadows, and compressed tension.",
  },
  {
    name: "Atlantic Neon",
    accent: "#28d2bd",
    start: "#1fb8d0",
    end: "#1550d9",
    descriptor: "Cool reflections, electric edge lights, and kinetic framing.",
  },
  {
    name: "Amber Realism",
    accent: "#f7b548",
    start: "#f0a137",
    end: "#7f4d2c",
    descriptor: "Warm practicals, natural skin tones, and subtle camera drift.",
  },
  {
    name: "Glass Horizon",
    accent: "#89a7ff",
    start: "#8ab8ff",
    end: "#4a5db8",
    descriptor: "Soft atmospheric haze, reflective surfaces, and airy depth.",
  },
];

const conceptSeeds = [
  "A rescue pilot returns to a city that no longer remembers her",
  "An aging stunt coordinator trains a teenage genius in secret",
  "A floating market hides a blackmail ring run by retired actors",
  "Three siblings race one night to recover a missing reel of film",
  "A climate lab intern discovers weather can be scored like music",
];

const recentProjects = [
  {
    title: "Last Train to Navira",
    phase: "Storyboard",
    status: "Needs 2 bridge shots",
    mood: "Brooding",
  },
  {
    title: "Paper Sun",
    phase: "Script",
    status: "Dialogue pass in progress",
    mood: "Tender",
  },
  {
    title: "Harbor Lights Protocol",
    phase: "Video Review",
    status: "Cut 4 awaiting notes",
    mood: "Urgent",
  },
];

export default function App() {
  const [activeStepId, setActiveStepId] = useState(workflowSteps[0].id);
  const [energy, setEnergy] = useState(68);
  const [pace, setPace] = useState(57);
  const [styleIndex, setStyleIndex] = useState(1);
  const [seedIndex, setSeedIndex] = useState(0);
  const [spotlight, setSpotlight] = useState({ x: 50, y: 14 });

  const activeStep =
    workflowSteps.find((step) => step.id === activeStepId) ?? workflowSteps[0];

  const activeStyle = styleOptions[styleIndex];
  const activeConcept = conceptSeeds[seedIndex];

  const energyLabel = useMemo(() => {
    if (energy > 80) return "Explosive";
    if (energy > 55) return "Balanced";
    if (energy > 30) return "Controlled";
    return "Brooding";
  }, [energy]);

  const paceLabel = useMemo(() => {
    if (pace > 75) return "Rapid";
    if (pace > 50) return "Flowing";
    if (pace > 25) return "Measured";
    return "Deliberate";
  }, [pace]);

  const sceneLine = useMemo(() => {
    return `${activeConcept}. ${activeStyle.descriptor} Energy: ${energyLabel}. Pace: ${paceLabel}.`;
  }, [activeConcept, activeStyle, energyLabel, paceLabel]);

  function updateSpotlight(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const nextX = ((event.clientX - rect.left) / rect.width) * 100;
    const nextY = ((event.clientY - rect.top) / rect.height) * 100;
    setSpotlight({ x: nextX, y: nextY });
  }

  function rotateStyle() {
    setStyleIndex((current) => (current + 1) % styleOptions.length);
  }

  function cycleConcept() {
    setSeedIndex((current) => (current + 1) % conceptSeeds.length);
  }

  return (
    <main
      className="app-shell"
      onMouseMove={updateSpotlight}
      style={{
        "--spot-x": `${spotlight.x}%`,
        "--spot-y": `${spotlight.y}%`,
        "--accent": activeStyle.accent,
      }}
    >
      <header className="topbar reveal" style={{ "--delay": "30ms" }}>
        <div className="brand-wrap">
          <div className="brand-mark">IF</div>
          <div>
            <p className="eyebrow">Infinity Film Studio</p>
            <h1>Director Desk</h1>
          </div>
        </div>
        <button className="ghost-btn" onClick={cycleConcept}>
          Shuffle Concept
        </button>
      </header>

      <section className="hero-grid reveal" style={{ "--delay": "90ms" }}>
        <div className="hero-copy">
          <p className="hero-tag">Creative Pipeline</p>
          <h2>Block scenes fast before cameras roll.</h2>
          <p>
            Write the beats, plan the shots, and stress-test the cut in one
            place.
          </p>
          <div className="hero-actions">
            <button className="primary-btn" onClick={rotateStyle}>
              Change Visual Style
            </button>
            <button
              className="secondary-btn"
              onClick={() => setEnergy((value) => Math.min(100, value + 7))}
            >
              Nudge Energy
            </button>
          </div>
        </div>

        <aside className="card stat-panel">
          <p className="kicker">Current Session</p>
          <h3>{activeStyle.name}</h3>
          <div className="stat-grid">
            <div>
              <span>Creative score</span>
              <strong>96</strong>
            </div>
            <div>
              <span>Scene drafts</span>
              <strong>18</strong>
            </div>
            <div>
              <span>Visual consistency</span>
              <strong>93%</strong>
            </div>
            <div>
              <span>Audience tension</span>
              <strong>High</strong>
            </div>
          </div>
        </aside>
      </section>

      <section className="workflow reveal" style={{ "--delay": "140ms" }}>
        <div className="section-head">
          <h3>Workflow</h3>
          <p>Select a stage to inspect active insights.</p>
        </div>

        <div className="workflow-shell">
          <div className="step-list">
            {workflowSteps.map((step, index) => (
              <button
                key={step.id}
                className={`step-btn ${
                  step.id === activeStep.id ? "is-active" : ""
                }`}
                onClick={() => setActiveStepId(step.id)}
              >
                <span className="step-index">{String(index + 1).padStart(2, "0")}</span>
                <span className="step-copy">
                  <strong>{step.title}</strong>
                  <small>{step.tagline}</small>
                </span>
              </button>
            ))}
          </div>

          <article className="card step-detail">
            <p className="kicker">{activeStep.title}</p>
            <h4>{activeStep.detailTitle}</h4>
            <p>{activeStep.description}</p>
            <ul className="metric-list">
              {activeStep.metrics.map((metric) => (
                <li key={metric.label}>
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                </li>
              ))}
            </ul>
          </article>
        </div>
      </section>

      <section className="lab reveal" style={{ "--delay": "190ms" }}>
        <div className="section-head">
          <h3>Control Room</h3>
          <p>Adjust cinematic behavior with live controls.</p>
        </div>

        <div className="lab-grid">
          <div className="card controls-card">
            <label className="slider-field">
              <div>
                <span>Energy</span>
                <strong>{energy}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={energy}
                onChange={(event) => setEnergy(Number(event.target.value))}
              />
            </label>

            <label className="slider-field">
              <div>
                <span>Pace</span>
                <strong>{pace}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={pace}
                onChange={(event) => setPace(Number(event.target.value))}
              />
            </label>

            <div className="chip-row">
              {styleOptions.map((option, index) => (
                <button
                  key={option.name}
                  className={`chip ${index === styleIndex ? "is-active" : ""}`}
                  onClick={() => setStyleIndex(index)}
                >
                  {option.name}
                </button>
              ))}
            </div>
          </div>

          <article
            className="card preview-card"
            style={{
              "--preview-start": activeStyle.start,
              "--preview-end": activeStyle.end,
            }}
          >
            <p className="kicker">Live Scene Line</p>
            <h4>{activeStyle.name}</h4>
            <p>{sceneLine}</p>
            <div className="preview-meta">
              <span>{energyLabel}</span>
              <span>{paceLabel}</span>
              <span>{activeStep.title}</span>
            </div>
            <button className="link-btn" onClick={cycleConcept}>
              Try Another Prompt
            </button>
          </article>
        </div>
      </section>

      <section className="projects reveal" style={{ "--delay": "240ms" }}>
        <div className="section-head">
          <h3>Recent Projects</h3>
          <p>Jump back into current work with one click.</p>
        </div>

        <div className="project-grid">
          {recentProjects.map((project) => (
            <article className="card project-card" key={project.title}>
              <p className="kicker">{project.phase}</p>
              <h4>{project.title}</h4>
              <p>{project.status}</p>
              <span className="pill">{project.mood}</span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
