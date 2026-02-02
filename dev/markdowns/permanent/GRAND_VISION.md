# The Grand Vision

*On Side-by-Side Blueprint, the Age of Verified AI, and Infrastructure for Trust*

---

## The Moment

In January 2026, Terence Tao noticed something strange in the dependency graph of Erdos 392. The final theorems floated disconnected from the rest of the proof structure. The AI-generated proofs were suspiciously short. Upon inspection, the problem revealed itself: the theorems proved that n! could be factored into **at least** a certain number of factors, when the actual conjecture asked for **at most**. The trivial factorization n! = 1 × 2 × ... × n satisfied the wrong statement perfectly.

The proof typechecked. Lean accepted it without complaint. The kernel was sound. And yet it proved nothing of interest.

"Another cautionary tale not to blindly trust AI auto-formalization, even when it typechecks..."

This incident crystallizes the challenge we now face. We have entered an era where AI systems can generate seemingly valid formal proofs at scale—proofs that pass every automated check yet miss the mark entirely. The gap between "typechecks" and "proves what we intended" has become the new frontier of mathematical rigor.

---

## The Convergence

Two forces are converging with unprecedented momentum:

**The first force** is the maturation of interactive theorem provers. Lean 4 has achieved something remarkable: a proof assistant that is simultaneously a well-designed modern programming language. The module system enables faster builds. Grind and bvdecide provide powerful automation. The standard library approaches completion with verified data structures. Verso enables documentation and papers to be written in the same language as proofs. The ecosystem has crossed a threshold from research curiosity to practical infrastructure.

**The second force** is the explosion of AI capability in formal reasoning. In 2019, when Daniel Selsam proposed the IMO Grand Challenge, the idea that AI could solve olympiad problems with formal proofs seemed impossible. By 2025, multiple systems achieved gold-medal performance. By 2026, AI systems are solving open conjectures through "vibe-proving"—iteratively prompting language models to generate and refine Lean code until something compiles. What was impossible became routine so quickly that people now dismiss IMO-level problems as trivial for AI.

These forces create both extraordinary opportunity and extraordinary risk. The opportunity: mathematics and software verification at scales previously unimaginable. The risk: an avalanche of superficially valid but meaningless or incorrect results that overwhelm human capacity to verify.

Leo de Moura, at Lean Together 2026, put it directly: "Because of AI, soundness is more important than ever."

---

## The Gap

Consider what happens when someone claims to have proven an important result using AI-assisted methods:

1. They produce a Lean file that compiles
2. The file contains no `sorry` statements
3. The types align with something resembling the theorem statement
4. The dependency graph shows... what, exactly?

The kernel verifies that the proof term inhabits the claimed type. It does not verify that the type means what you think it means. It does not verify that the proof connects to the mathematical concepts you intended. It does not verify that assumptions haven't been smuggled in through clever definitions. It does not verify that the "theorem" isn't actually proving a trivial special case.

The Tao incident was caught because someone looked at the dependency graph and noticed something was wrong. The visual representation—theorems floating disconnected from their purported foundations—made the error obvious at a glance. A human reviewing the code might have missed it. The graph made it legible.

This is the gap Side-by-Side Blueprint aims to fill: the space between "the kernel accepted it" and "we understand what was actually proven."

---

## The Tool

Side-by-Side Blueprint is, in its current form, a pure-Lean reimplementation of LeanBlueprint with an integrated deployment pipeline. The components:

**LeanArchitect** (forked): A general-purpose tagging system. Declarations are annotated with metadata—status, dependencies, prose descriptions, discussion links. This information is extracted during elaboration, not scraped after the fact.

**Dress**: Build-time asset generation. During compilation, Dress produces the artifacts needed for documentation: Verso-compatible info trees, TeX files, syntax-highlighted code blocks. The build process itself generates the evidence of what was built.

**Runway**: Documentation generation. The blueprint, dependency graph, and paper are constructed from Dress artifacts. HTML and PDF output. Side-by-side display of formal proofs alongside informal statements.

**dress-blueprint-action**: CI integration. One-click deployment for any Lean project using the template.

What makes this different from previous approaches is the coupling. The documentation isn't a separate artifact maintained alongside the code—it's generated from the same elaboration process that produces the proof terms. The dependency graph isn't reconstructed by parsing—it's extracted from the actual dependencies the kernel sees. The status indicators (proven, sorry, ready, not-ready) aren't manually updated—they're computed from the proof state.

This coupling is not merely convenient. It is a statement about what documentation should mean in an era of machine-generated proofs.

---

## The Vision

### Near Term: Infrastructure for Human Oversight

The immediate value proposition is human legibility. When an AI system generates a proof, or when a human uses AI assistance to construct one, the Side-by-Side Blueprint provides:

- **Dependency visualization**: Can you see the logical structure? Are there disconnected components? Do the dependencies match your mental model of the proof?

- **Status at a glance**: The six-color model (notReady, ready, sorry, proven, fullyProven, mathlibReady) answers the question "what is the state of this project?" without requiring deep inspection.

- **Prose alongside formalism**: The side-by-side display lets reviewers check whether the informal description matches the formal statement. Mismatches—like proving "at least" when you meant "at most"—become visible.

- **Provenance tracking**: The `discussion` field links declarations to their origins. Where did this lemma come from? Who claimed it? What was the context?

This is the minimal viable product: make machine-generated proofs legible to humans who need to trust them.

### Medium Term: Verified Documentation Pipeline

The deeper opportunity lies in verification of the documentation process itself.

Consider: the current system extracts information during elaboration, generates assets, and produces documentation. Each step could fail silently. The TeX could be malformed. The dependency graph could miss edges. The status could be stale.

What if the documentation pipeline itself produced proof certificates?

Not "the proof is correct" (that's the kernel's job), but "the documentation accurately reflects the proof." Verified claims:

- Every node in the dependency graph corresponds to an actual declaration
- Every edge represents a genuine dependency
- Every status indicator matches the computed proof state
- Every prose block is associated with its formal counterpart

This is not technically impossible. The build process has access to the elaboration state. The information needed to make these guarantees exists. The question is whether we build the infrastructure to certify it.

### Long Term: The Ledger of Mathematical Progress

Imagine a world where AI systems routinely generate thousands of formal proofs per day. Some prove interesting theorems. Some prove trivial lemmas. Some prove incorrect statements that happen to typecheck. Some are duplicates of known results. Some are novel but uninteresting. Some are breakthroughs.

How do we navigate this flood?

The tagging system in LeanArchitect is embryonic, but it points toward something larger: a structured ledger of mathematical claims. Each entry carries:

- The formal statement
- The proof status
- Dependencies on other entries
- Provenance (who/what generated it, when, under what circumstances)
- Quality indicators (human-reviewed, AI-generated, connection to published work)
- Discussion and context

Such a ledger, maintained with verified tooling, becomes infrastructure for mathematical collaboration at scale. Not a replacement for human judgment, but a substrate that makes human judgment possible even as the volume of machine-generated mathematics explodes.

The kernel arena that Leo announced—gamified competition between independent kernel implementations—addresses one dimension of trust: "is this proof valid?" The documentation infrastructure addresses another: "what does this proof mean, and should we care?"

---

## The Broader Implications

### For Mathematics

The practice of mathematics is being transformed whether mathematicians want it or not. The question is not whether AI will generate proofs, but how the mathematical community will relate to those proofs.

One path leads to a world where AI-generated results are treated as unverifiable black boxes—accepted on faith or rejected wholesale. This path leads to fragmentation: some mathematicians embrace AI tools uncritically, others refuse to engage with AI-generated work at all, and the common ground of shared understanding erodes.

Another path leads to a world where AI-generated mathematics is accompanied by infrastructure that makes it legible, auditable, and connectable to human understanding. This path requires tooling. It requires standards. It requires the kind of "full transparency" that some have called for: not just "here is a proof," but "here is how this proof was generated, here is what it depends on, here is how it connects to what we already know."

Side-by-Side Blueprint is a bet on the second path.

### For Software Verification

The same dynamics playing out in mathematics are coming for software verification. AI systems that generate code are already ubiquitous. AI systems that generate verified code—code with formal proofs of correctness—are emerging. The same questions arise:

- How do we know the specification is correct?
- How do we know the proof proves what we think it proves?
- How do we navigate thousands of verified programs to find the ones that matter?

The verification condition generators (Velvet, MVCGen, Strata) that Leo mentioned are attack surfaces for the same class of problems. A proof that a program satisfies a specification is only as meaningful as the specification is accurate. Infrastructure for understanding and auditing these claims becomes critical.

### For Trust in the Age of AI

Zoom out further. The challenge of trusting AI-generated formal proofs is a special case of the challenge of trusting AI-generated artifacts in general. Mathematics and formal verification are distinguished by having clear criteria for correctness—but "correct" and "meaningful" are not the same thing.

The broader question is: how do we build systems that allow humans to maintain understanding and oversight even as machine capabilities exceed human capacity to verify from first principles?

The answer, if there is one, involves infrastructure. Not just infrastructure for verification, but infrastructure for legibility, for provenance, for connecting machine outputs to human understanding.

Side-by-Side Blueprint is one small piece of that infrastructure, operating in a domain—formal mathematics—where the problems are relatively well-posed and the stakes, while real, are not yet existential.

---

## The Work Ahead

What remains to be built:

**Immediate priorities:**
- Robustness: The current implementation is "vibe-coded" and fragile. Production readiness requires systematic testing and error handling.
- Performance: Build times for large projects are painful. Caching, incremental compilation, and parallelization need attention.
- Integration: Deeper Verso integration following Jason Reed's vision—eliminating the TeX/Lean coordination complexity.

**Medium-term goals:**
- Verified documentation: Proof certificates for the documentation pipeline itself.
- Analytics: Understanding how humans and AI interact with the tooling. Which features help? Which confuse? Where do errors cluster?
- Soundness integration: Connection to comparator and the kernel arena. Multiple independent checks, not just the default kernel.

**Long-term aspirations:**
- The ledger: Infrastructure for tracking mathematical claims at scale.
- Community standards: Participation in developing norms for AI-generated proofs.
- Ecosystem integration: Becoming part of the standard toolkit for Lean projects.

---

## Closing Thought

In October 2023, before the current wave of AI breakthroughs in formal reasoning, someone wrote:

> "Just as Napster was the first warning shot to the music industry that everything was about to change, Sagredo is the first warning shot to mathematicians... the ability of this system to produce proofs is a function of our ability to engineer the system, rather than our ability to understand mathematics—it's engineering all the way down."

The music industry's response to Napster ranged from denial to litigation to eventual adaptation. The mathematical community now faces its own moment of disruption. The response will determine whether AI-assisted mathematics becomes a tool for expanding human understanding or a source of epistemic chaos.

Side-by-Side Blueprint is a small contribution to the adaptive response: infrastructure for maintaining human legibility and oversight as the volume and capability of machine-generated mathematics grows. It sits in the space between the kernel (which guarantees soundness) and the human (who must decide meaning and importance).

That space is about to become very crowded. We should build carefully.

---

*Last updated: February 2026*
