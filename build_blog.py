import re

with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

header_part = re.search(r'(.*?<main>)', html, re.DOTALL).group(1)
footer_part = re.search(r'(</main>.*)', html, re.DOTALL).group(1)

blog_content = """
    <style>
      .blog-article {
        max-width: 680px;
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
      }
      .blog-article strong {
        color: var(--text);
        font-weight: 600;
      }
      .blog-article .mermaid-wrapper {
        margin: 3rem 0;
        padding: 1.5rem;
        background: var(--bg-raised);
        border: 1px solid var(--line);
        border-radius: 4px;
        display: flex;
        justify-content: center;
      }
    </style>
    
    <article class="blog-article">
      <span class="eyebrow" style="font-family:var(--font-mono); font-size:0.75rem; letter-spacing:0.1em; color:var(--accent); text-transform:uppercase; display:block; margin-bottom:1rem;">Architecture Deep Dive</span>
      <h1>Eco-Loop: Solving the 40% Global Energy Problem with Cognitive Buildings</h1>
      
      <p>Buildings consume approximately 40% of global energy and remain a primary driver of carbon emissions. Despite this massive footprint, the vast majority of commercial structures are surprisingly unintelligent.</p>
      
      <p>Traditional Building Management Systems (BMS) rely on rigid, rule-based schedules and isolated PID loops. They are programmed to follow static instructions regardless of context. When an unexpected heatwave rolls in, when occupancy suddenly drops, or when the local power grid faces a critical demand spike, these traditional systems fail to adapt dynamically. They blindly execute their programmed schedules, resulting in massive energy waste and compromised occupant comfort.</p>

      <p><strong>If</strong> our buildings remain passive, schedule-bound energy consumers incapable of reacting to real-world variables, <strong>then</strong> we will never hit our aggressive climate targets without sacrificing human comfort.</p>

      <h2>The Solution: A Paradigm Shift to Autonomous Structures</h2>
      
      <p>We decided to solve this by transforming the building from a passive consumer into an active, self-correcting agent capable of continuous, real-time optimization.</p>
      
      <p>Our objective was to build a live, operational Physical AI Proof-of-Concept. We set out to create an autonomous closed-loop control pipeline driven entirely by open-source Large Language Models (LLMs) communicating via the Model Context Protocol (MCP). Instead of humans hardcoding daily schedules, an AI brain would ingest continuous performance metrics, evaluate complex variables, and dynamically update set-points.</p>
      
      <p>To safely develop and validate this cognitive engine, we needed a way to simulate high-fidelity physical data. Therefore, we integrated <strong>EnergyPlus</strong> as our digital building sandbox. While not part of the core AI problem statement, EnergyPlus served as our crucial testing ground. It streams continuous feedback (zone temperatures, air quality, energy consumption, and Predicted Mean Vote comfort indices) into our AI, and allows us to verify the forward injection of our dynamic control actions.</p>
      
      <h2>Architecting the Closed-Loop Execution Framework</h2>
      
      <p>To reliably bridge open-source LLMs with physical infrastructure, we couldn't rely on a single, monolithic script. A single prompt digesting all building data quickly suffers from context bloat and hallucination.</p>
      
      <p>Instead, we engineered a distributed, 5-layer cognitive architecture. This ensures our closed-loop pipeline executes robustly without crashing over extended time horizons.</p>
      
      <div class="mermaid-wrapper">
        <div class="mermaid">
graph TD
    subgraph Perception
        SC[State Compressor]
        AD[Anomaly Detector]
    end
    subgraph Memory
        OM[Outcome Memory]
    end
    subgraph Planning
        FP[Forecast Planner]
    end
    subgraph Reasoning
        ZA1[Zone Agents]
        CO[Coordinator]
    end
    subgraph Safety
        CA[Comfort Auditor]
        GE[Guardrail Engine]
    end
    SC --> OM
    AD --> OM
    OM --> FP
    FP --> ZA1
    ZA1 --> CO
    CO --> CA
    CA --> GE
        </div>
      </div>
      
      <h3>1. Feedback (EnergyPlus to AI)</h3>
      <p>The closed loop begins with our <strong>Perception Layer</strong>. The system ingests the raw stream of EnergyPlus simulation data. Because raw telemetry is noisy, our <em>State Compressor</em> distills thousands of data points into a concise state summary, while the <em>Anomaly Detector</em> flags potential sensor faults. This ensures the reasoning engine only evaluates high-confidence data, drastically reducing prompt latency.</p>
      
      <h3>2. Planning and Macro-Awareness</h3>
      <p>Before executing local control actions, the system establishes a global strategy. The <strong>Planning Layer</strong> ingests 24-hour weather projections and real-time local carbon grid intensity. It calculates a peak demand threshold for the entire facility. This solves the fundamental flaw of traditional BMS by providing macro-awareness before micro-adjustments are made.</p>
      
      <h3>3. Reasoning and Control Actions</h3>
      <p>This is where the LLM evaluates the building's state against our predefined targets: occupancy comfort and energy reduction. We deployed an independent <strong>Zone Agent</strong> for every thermal zone. These agents read local conditions and propose localized Energy Conservation Measures (ECMs) and set-points.</p>
      <p>However, to prevent zones from fighting each other and breaching the facility's demand cap, proposals are routed to a <strong>Coordinator</strong>. The Coordinator actively negotiates competing requests. It intelligently balances human comfort against energy efficiency, perhaps slightly relaxing the cooling in a vacant hallway to subsidize necessary heating in a crowded boardroom.</p>
      
      <h3>4. Forward Injection (AI to EnergyPlus)</h3>
      <p>Before computed set-points are injected back into the active EnergyPlus instance, they pass through a strictly deterministic <strong>Safety Layer</strong>. The <em>Comfort Auditor</em> verifies that no LLM decision violates the established PMV thermal comfort boundaries. Finally, a hardcoded <em>Guardrail Engine</em> clamps any runaway set-point proposals, ensuring the physical AI safely interacts with hardware limits.</p>
      
      <h2>Conclusion</h2>
      <p>By pairing physics-based energy simulation with a highly orchestrated, multi-agent LLM framework, Eco-Loop achieves a true paradigm shift. It proves that by replacing rigid schedules with closed-loop cognitive reasoning, we can drastically reduce net energy consumption while maintaining strict thermal comfort constraints.</p>
    </article>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({ startOnLoad: true, theme: 'dark', themeVariables: { fontFamily: 'IBM Plex Sans' } });
    </script>
"""

with open('dashboard/blog.html', 'w', encoding='utf-8') as f:
    f.write(header_part + blog_content + footer_part)
