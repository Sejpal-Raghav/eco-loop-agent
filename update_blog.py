import re

with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

header_part = re.search(r'(.*?<main>)', html, re.DOTALL).group(1)
footer_part = re.search(r'(</main>.*)', html, re.DOTALL).group(1)

new_html = """    <style>
      .blog-article {
        max-width: 920px;
        margin: 0 auto;
        padding: 4rem 0 6rem;
      }
      .blog-article h1 {
        font-size: clamp(2rem, 3.5vw, 2.8rem);
        line-height: 1.15;
        letter-spacing: -0.02em;
        margin-bottom: 2.5rem;
      }
      .blog-article h2 {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 3.5rem 0 1.5rem;
        letter-spacing: -0.01em;
        color: var(--text);
      }
      .blog-article h3 {
        font-size: 1.15rem;
        font-weight: 600;
        margin: 2.5rem 0 1rem;
        color: var(--text);
      }
      .blog-article p {
        font-size: 1.05rem;
        line-height: 1.75;
        color: var(--text-muted);
        margin-bottom: 1.5rem;
        max-width: 80ch;
      }
      .blog-article strong {
        color: var(--text);
        font-weight: 600;
      }
      .blog-article .mermaid-wrapper {
        margin: 3.5rem 0;
        padding: 2.5rem 1.5rem;
        background: var(--bg-raised);
        border: 1px solid var(--line);
        border-radius: 6px;
        overflow-x: auto;
        text-align: center;
      }
      .blog-article .mermaid svg {
        max-width: 100% !important;
        height: auto !important;
      }
      /* Specific override for wide diagrams so they don't render tiny */
      .blog-article .wide-diagram .mermaid {
        width: 100%;
        min-width: 700px;
      }
      .blog-article .wide-diagram .mermaid svg {
        width: 100% !important;
        max-width: none !important;
      }
    </style>
    
    <article class="blog-article">
      <span class="eyebrow" style="font-family:var(--font-mono); font-size:0.75rem; letter-spacing:0.1em; color:var(--accent); text-transform:uppercase; display:block; margin-bottom:1rem;">Architecture Deep Dive</span>
      <h1>Eco-Loop: Solving the 40% Global Energy Problem with Cognitive Buildings</h1>
      
      <p>Buildings consume approximately 40% of global energy and remain a primary driver of carbon emissions. Despite this massive footprint, the vast majority of commercial structures are surprisingly unintelligent.</p>
      
      <p>Traditional Building Management Systems (BMS) rely on rigid, rule-based schedules and isolated PID loops. They are programmed to follow static instructions regardless of context. When an unexpected heatwave rolls in, when occupancy suddenly drops, or when the local power grid faces a critical demand spike, these traditional systems fail to adapt dynamically. They blindly execute their programmed schedules, resulting in massive energy waste and compromised occupant comfort.</p>

      <p><strong>If</strong> our buildings remain passive, schedule-bound energy consumers incapable of reacting to real-world variables, <strong>then</strong> we will never hit our aggressive climate targets without sacrificing human comfort.</p>

      <h2>The Solution: A Paradigm Shift to Autonomous Structures</h2>
      
      <p>We decided to solve this by transforming the building from a passive consumer into an active, self-correcting agent capable of continuous, real-time optimization. Our objective was to build a live, operational Physical AI Proof-of-Concept that automates smart building operations through an autonomous closed-loop control pipeline.</p>
      
      <p>Instead of humans hardcoding daily schedules, we utilized open-source Large Language Models (LLMs) to serve as a cognitive engine. Communicating via the Model Context Protocol (MCP), this AI brain continuously ingests performance metrics, evaluates complex physical variables, and dynamically updates HVAC set-points.</p>
      
      <p>To safely develop, validate, and prove quantifiable energy savings for this cognitive engine, we needed a way to simulate high-fidelity physical data. Therefore, we integrated <strong>EnergyPlus</strong> as our digital building sandbox. While building a simulation engine is not the core AI problem statement, EnergyPlus served as our crucial testing ground. It streams continuous feedback (zone temperatures, air quality, energy consumption, and Predicted Mean Vote comfort indices) into our AI, allowing us to evaluate variables and verify the forward injection of our dynamic control actions back into a physical model.</p>
      
      <h2>Technical Decision 1: Abandoning the Monolithic LLM</h2>
      
      <p>Our initial instinct was to build a single "God Agent" to manage the entire building. We assumed we could simply dump the entire building state—all thermal zones, all historical data, the complete weather forecast, and current grid demands—into one massive LLM prompt every thirty minutes.</p>
      
      <p>This approach failed spectacularly. A single prompt digesting all building data quickly suffers from severe context bloat and hallucination.</p>
      
      <div class="mermaid-wrapper">
        <div class="mermaid">
graph LR
    subgraph The Monolithic Bottleneck
        Data[Massive Raw Data Stream] -->|Context Window Choke| Model[Single Monolithic LLM]
        Model -->|High Latency| Action1[Zone 1 Setpoint]
        Model -->|Hallucination| Action2[Zone 2 Setpoint]
        Model -->|Missed Constraints| Action3[Facility Cap]
    end
    style Model fill:#8b3a3a,stroke:#e8a33d,stroke-width:2px;
        </div>
      </div>
      
      <p>When asked to balance a localized temperature drop in a perimeter zone against a facility-wide peak demand cap, the model would lose the plot. It hallucinated set-points. It ignored physical constraints. Latency spiked to unusable levels because the model was attempting to act as a localized sensor, a long-term planner, and a strict safety gatekeeper simultaneously. We realized that forcing a probabilistic model into a monolithic architecture was a fundamental dead end.</p>
      
      <h2>Technical Decision 2: The 5-Layer Distributed Cognitive Stack</h2>
      
      <p>To reliably bridge open-source LLMs with physical infrastructure, we needed decentralization. We distributed the workload across seven distinct, highly specialized LLM agents. We organized them into a strict, hierarchical execution pipeline.</p>
      
      <p>This multi-layer approach ensures that high-level strategy never interferes with low-level zone control, and probabilistic reasoning is always caught by deterministic safety nets.</p>
      
      <div class="mermaid-wrapper">
        <div class="mermaid">
graph TD
    subgraph Perception Layer
        SC[State Compressor]
        AD[Anomaly Detector]
    end
    subgraph Memory Layer
        OM[Outcome Memory]
    end
    subgraph Planning Layer
        FP[Forecast Planner]
    end
    subgraph Reasoning Layer
        ZA1[Zone Agent 1]
        ZA2[Zone Agent 2]
        ZA3[Zone Agent 3]
        CO[Coordinator]
    end
    subgraph Safety Layer
        CA[Comfort Auditor]
        GE[Guardrail Engine]
    end
    SC --> OM
    AD --> OM
    OM --> FP
    FP --> ZA1
    FP --> ZA2
    FP --> ZA3
    ZA1 --> CO
    ZA2 --> CO
    ZA3 --> CO
    CO --> CA
    CA --> GE
        </div>
      </div>
      
      <h2>Technical Decision 3: Data Sanitization (The Perception Layer)</h2>
      
      <p>Raw telemetry from building sensors is incredibly noisy. Pumping raw, tick-by-tick temperature fluctuations directly into a reasoning engine burns tokens and confuses the model.</p>
      
      <p>The closed loop begins with our <strong>Perception Layer</strong>. The system ingests the raw stream of EnergyPlus simulation data. The <strong>State Compressor</strong> distills thousands of data points into a concise, semantic state summary. Concurrently, the <strong>Anomaly Detector</strong> flags potential sensor faults. This crucial technical decision ensures the downstream reasoning engine only evaluates high-confidence, token-efficient data, drastically reducing prompt latency.</p>
      
      <h2>Technical Decision 4: Decoupling Strategy from Tactics (Planning vs Reasoning)</h2>
      
      <p>Traditional BMS systems fight themselves because individual zones operate without macro-awareness. To solve this, we decoupled long-term strategy from immediate tactical control.</p>
      
      <div class="mermaid-wrapper">
        <div class="mermaid">
sequenceDiagram
    participant Weather as External Data
    participant FP as Forecast Planner
    participant ZA as Zone Agents
    Weather->>FP: 24h Weather & Grid Carbon
    FP->>FP: Establish Peak Demand Threshold
    FP->>ZA: Pass Global Strategy Cap
    ZA->>ZA: Calculate Local ECMs
        </div>
      </div>
      
      <p>The <strong>Planning Layer</strong> (the Forecast Planner) does not run every cycle. Instead, it wakes up every six hours. It ingests 24-hour weather projections and real-time local carbon grid intensity. It calculates a peak demand threshold for the entire facility. By isolating this task, we can utilize a larger, slower model to generate complex strategies without slowing down the rapid 30-minute tactical control loops executed by the Zone Agents.</p>
      
      <h2>Technical Decision 5: The Negotiation Protocol (The Coordinator)</h2>
      
      <p>Once the Planning layer establishes the global cap, the <strong>Reasoning Layer</strong> evaluates the building's state against our predefined targets: occupancy comfort and energy reduction.</p>
      
      <p>We deployed an independent <strong>Zone Agent</strong> for every thermal zone. These agents read local conditions and propose localized Energy Conservation Measures (ECMs) and set-points. However, if five independent agents blindly maximize their own comfort, they will inevitably breach the facility's demand cap.</p>
      
      <p>To prevent this, we introduced the <strong>Coordinator</strong>. All proposals are routed to this central arbiter. The Coordinator actively negotiates competing requests. It intelligently balances human comfort against energy efficiency. For example, if the grid is under strain, the Coordinator will deliberately relax the cooling set-point in a temporarily vacant hallway to subsidize necessary heating in a crowded boardroom. This solves the fundamental flaw of isolated PID loops.</p>
      
      <h2>Technical Decision 6: Deterministic Guardrails (The Safety Layer)</h2>
      
      <p>No matter how advanced the reasoning, we cannot trust generative AI with raw control over heavy physical machinery. Probabilistic models will eventually hallucinate, and in a physical building, hallucination means frozen pipes or roasted occupants.</p>
      
      <div class="mermaid-wrapper wide-diagram">
        <div class="mermaid">
flowchart LR
    A[Coordinator Decisions] --> B{Comfort Auditor}
    B -- PMV Exceeds ±0.5 --> C[Emergency Veto: Override Setpoint]
    B -- PMV Safe --> D{Guardrail Engine}
    D -- Delta > 3°C --> E[Clamp Rate Limit]
    D -- Within Bounds --> F[Forward Injection to EnergyPlus]
    C --> F
    E --> F
    style B fill:#313d47,stroke:#5fa8a0,stroke-width:2px;
    style D fill:#313d47,stroke:#5fa8a0,stroke-width:2px;
        </div>
      </div>
      
      <p>Before computed set-points are injected back into the active EnergyPlus instance, they pass through a strictly deterministic <strong>Safety Layer</strong>. The <strong>Comfort Auditor</strong> verifies that no LLM decision violates the established Predicted Mean Vote (PMV) thermal comfort boundaries. Finally, a hardcoded <strong>Guardrail Engine</strong> enforces strict rate limits (e.g., maximum 3°C shift per tick) and clamps any runaway set-point proposals.</p>
      <p>This technical decision guarantees that the physical AI safely interacts with hardware limits, regardless of what the neural networks decide.</p>
      
      <h2>Conclusion</h2>
      
      <p>By pairing physics-based energy simulation with a highly orchestrated, multi-agent LLM framework, Eco-Loop achieves a true paradigm shift. It proves that by replacing rigid schedules with closed-loop cognitive reasoning, we can drastically reduce net energy consumption while maintaining strict thermal comfort constraints. Decentralization, macro-awareness, active negotiation, and deterministic safety are the keys to autonomous structures.</p>
    </article>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({ startOnLoad: true, theme: 'dark', themeVariables: { fontFamily: 'IBM Plex Sans' } });
    </script>
"""

with open('dashboard/blog.html', 'w', encoding='utf-8') as f:
    f.write(header_part + new_html + footer_part)
