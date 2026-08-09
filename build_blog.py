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
      <h1>Evolving Eco-Loop: The Leap from Monolithic Scripts to a 5-Layer Cognitive Architecture</h1>
      
      <p>Commercial HVAC systems are notoriously stubborn. They operate on rigid schedules, relying heavily on isolated PID loops that remain oblivious to the outside world. When we first set out to build Eco-Loop, our goal was simple. We wanted to inject artificial intelligence directly into building management systems. By allowing an LLM to read sensor data and write setpoints, we figured we could easily optimize energy consumption against grid carbon intensity and occupant comfort.</p>
      
      <p>However, reality quickly humbled our initial designs. This post explores how we crashed into the limitations of single-agent control, why we tore everything down, and exactly how we engineered the robust 5-layer cognitive architecture that powers Eco-Loop today.</p>
      
      <h2>The Single-Agent Bottleneck</h2>
      
      <p>Our prototype relied on a single monolithic agent. Every thirty minutes, we dumped the entire building state into a massive prompt. This included telemetry from five thermal zones, twenty-four hour weather forecasts, grid carbon signals, and historical performance data.</p>
      
      <p>The agent was expected to digest this colossal wall of text, reason about thermal dynamics, and output precise heating and cooling setpoints for every single zone.</p>
      
      <p>It failed spectacularly.</p>
      
      <p>Token limits choked the context window. Latency spiked to unusable levels. More alarmingly, the monolithic approach degraded the model's reasoning capabilities. When asked to balance a localized temperature drop in the perimeter zone against a facility-wide peak demand cap, the model would lose the plot. It hallucinated setpoints. It ignored physical constraints. We realized that forcing a single probabilistic model to act as a localized sensor, a long-term planner, and a strict safety gatekeeper simultaneously was an architectural dead end.</p>
      
      <p>We needed decentralization. We needed specialized intelligence.</p>
      
      <h2>Designing the 5-Layer Cognitive Stack</h2>
      
      <p>Taking inspiration from human cognition and microservice architectures, we dismantled the monolith. We distributed the workload across seven distinct LLM agents, organizing them into a strict, hierarchical execution pipeline.</p>
      
      <p>This multi-layer approach ensures that high-level strategy never interferes with low-level zone control, and probabilistic reasoning is always caught by deterministic safety nets.</p>
      
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
      
      <h3>Layer 1: Perception</h3>
      <p>Raw telemetry from building sensors is noisy and overwhelming. Before any decision making occurs, the Perception layer sanitizes the data.</p>
      <p>The <strong>State Compressor</strong> agent distills thousands of data points into a concise, token-efficient state summary. Concurrently, the <strong>Anomaly Detector</strong> scans the raw feed for faulty sensor readings or sudden equipment failures. By filtering out the noise early, we drastically reduce token consumption for downstream agents and ensure the reasoning engine only operates on high-confidence data.</p>
      
      <h3>Layer 2: Memory</h3>
      <p>A smart building must learn from its mistakes without requiring constant model retraining. The Memory layer acts as a specialized vector store that retrieves the outcomes of similar past conditions. If a specific cooling strategy previously resulted in an unacceptable comfort violation on a humid afternoon, the Memory layer injects that historical context directly into the current execution cycle. This grants the system a form of synthetic intuition.</p>
      
      <h3>Layer 3: Planning</h3>
      <p>We decoupled long-term strategy from immediate tactical control. The <strong>Forecast Planner</strong> does not run every cycle. Instead, it wakes up every six hours to analyze macro variables. It ingests 24-hour weather projections and real-time grid carbon intensity signals.</p>
      <p>Its sole job is to establish a global facility strategy and set a strict peak demand cap. By isolating this task, the Planner can utilize a larger, more capable model to generate complex strategies without slowing down the rapid 30-minute control loops.</p>
      
      <h3>Layer 4: Reasoning (The Negotiation Protocol)</h3>
      <p>This is where the magic happens. Instead of one brain managing the entire building, we deployed an independent agent for every thermal zone.</p>
      <p>Operating in parallel via <code>asyncio.gather</code>, these <strong>Zone Agents</strong> care only about their specific environment. They evaluate local temperatures against occupant comfort metrics and propose localized heating and cooling setpoints. Because their scope is microscopically focused, their reasoning is incredibly sharp.</p>
      <p>However, five independent agents maximizing their own comfort could easily spike the building's energy usage past the grid limit. To solve this, proposals are routed to the <strong>Coordinator</strong>. The Coordinator reviews all zone requests against the global peak demand cap established by the Planning layer. If the combined requests exceed the limit, the Coordinator acts as a strict arbiter. It forces zones to negotiate, dialing back non-critical cooling requests in empty areas to subsidize crucial heating in occupied spaces.</p>
      
      <h3>Layer 5: Safety</h3>
      <p>We cannot trust generative AI with raw control over heavy machinery. Probabilistic models hallucinate. They make mistakes.</p>
      <p>The final stage of the pipeline is entirely deterministic. The <strong>Comfort Auditor</strong> ensures no proposed setpoint violates established safety bands. Finally, the <strong>Guardrail Engine</strong> acts as the ultimate physical safety check. If a software glitch or an aggressive Coordinator decision attempts to push an actuator beyond its mechanical limits, the Guardrail Engine clamps the value. This hardcoded, non-LLM layer guarantees that physical hardware remains protected regardless of what the neural networks decide.</p>
      
      <h2>The Result</h2>
      <p>Moving from a single script to a 5-layer cognitive architecture completely transformed Eco-Loop.</p>
      <p>By compartmentalizing perception, planning, and reasoning, we achieved a system that is both incredibly responsive to local microclimates and strictly obedient to global energy constraints. Token usage plummeted. Decision latency dropped by an order of magnitude. Most importantly, the system stopped fighting itself. The building now negotiates its own energy footprint smoothly, intelligently, and safely.</p>
    </article>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({ startOnLoad: true, theme: 'dark', themeVariables: { fontFamily: 'IBM Plex Sans' } });
    </script>
"""

with open('dashboard/blog.html', 'w', encoding='utf-8') as f:
    f.write(header_part + blog_content + footer_part)
