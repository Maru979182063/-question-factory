# Material Line Goal Chain Audit

Date: 2026-04-26

## 1. User Goal Restatement

The user's goal is not merely to search URLs, crawl web pages, or write a `material_card`.

The real goal is:

> Given true-question packs, reverse-engineer the material production process behind those questions, then gradually build a system that can find, prepare, clean, slice, evaluate, and reuse suitable materials for this question family.

In product language, the material line should eventually let a user do this:

1. Upload or provide a true-question pack.
2. Reconstruct the question-wrapped material into natural human material and a reliable gold schema.
3. Split the true-question material into observation/tuning/eval/insurance sets so the system does not overfit to a small pack.
4. Use natural reconstructed material, not exam wording, to search for original or similar sources.
5. Keep source candidates separate from verified original sources.
6. Let the user review whether a source candidate is:
   - possible original source;
   - similar material worth keeping;
   - useful domain for future targeted crawling;
   - irrelevant;
   - question-bank or exam-training pollution.
7. When a source body is eventually available, compare it against reconstructed gold and infer how the true question material was selected or transformed.
8. Learn material processing patterns:
   - source type;
   - clean text boundary;
   - context window size;
   - span selection;
   - noise removal;
   - excerpt compression;
   - concept density;
   - answerable lexical or semantic anchors;
   - distractor-supporting contexts.
9. Produce draft material rules only after evidence accumulates.
10. Validate material rules against true-gold regression and generated comparison.
11. Only after human approval and regression should any material-card-like artifact approach formal writeback.

So the goal chain is not:

```text
search URL -> crawl -> material_card
```

It is closer to:

```text
true-question pack
-> reconstructed natural material
-> source candidates
-> human-reviewed source seeds
-> source body or similar body
-> source/gold alignment
-> material transformation understanding
-> cleaning/slicing recipe
-> material quality regression
-> material card draft
-> approved writeback later
```

The important conceptual shift is:

> Material distillation is the process of learning what kinds of source texts and transformations produce good question material, not simply collecting articles.

## 2. Current System Coverage

### 2.1 `model_based_gold_reconstruction`

What it covers:

- Converts raw true-question samples into a unified gold schema.
- Lets the model infer what must be reconstructed.
- Separates model semantic reconstruction from mechanical JSON/hash/field checks.
- Marks confidence, warnings, and `needs_human_review`.

Why it matters for material quality:

- This is the first genuinely material-quality-serving step.
- It tries to remove exam wrappers and restore source-like material.
- Without this, search queries tend to hit question banks and answer-analysis pages.

What it is not:

- It is not proof that the restored material is correct.
- It is not source verification.
- It is not material-card generation.

### 2.2 `truth_gold_regression`

What it covers:

- Splits true-question data into train/dev/eval/insurance holdout.
- Prefers reconstructed gold over raw samples when available.
- Creates a framework for original-vs-generated comparison.
- Marks overfit risk and quality dimensions.

Why it matters for material quality:

- It provides a quality feedback loop.
- It prevents the system from confusing surface similarity with real material competence.
- The insurance holdout gives the material line a way to test whether material processing rules generalize.

What it is not:

- It is not deep semantic quality judgment yet.
- It does not know whether a source article is original.
- It does not yet evaluate source cleaning or span selection because source bodies are not available.

### 2.3 `source_discovery_preparation`

What it covers:

- Converts reconstructed gold into source discovery queries.
- Removes or avoids question-bank terms.
- Produces initial material seeds and material source profile.
- Records contamination risk.

Why it matters for material quality:

- This is a bridge from reconstructed gold to source discovery.
- It directly addresses the user's insight: natural material queries can find source-like pages, while question wording finds training sites.

What it is not:

- It does not search the web.
- It does not know if the query is enough to find original sources.
- It does not confirm source quality.

### 2.4 `source_candidate_search`

What it covers:

- Executes bounded candidate search.
- Records URL/title/snippet/domain.
- Marks question-bank-like and exam-training-like candidates.
- Keeps every candidate `verified=false`.
- Produces a candidate alignment report for human review.

Why it matters for material quality:

- It makes source candidates visible.
- It proves the material line can move from reconstructed gold to actual web candidates.
- It creates the first concrete pool of possible source evidence.

What it is not:

- It is not source confirmation.
- It does not fetch article bodies.
- It does not determine whether the source text matches reconstructed gold.
- It does not produce material rules.

### 2.5 Engineering Preparation vs Material Quality

Current engineering preparation:

- artifact contracts;
- offline tools;
- optional CLI hooks;
- reports;
- no-writeback boundaries;
- test coverage;
- evidence attachment path.

Current material-quality-serving capabilities:

- model-based gold reconstruction;
- question-wrapper leakage checks;
- de-question-bank query generation;
- candidate source retrieval;
- contamination-risk labeling;
- truth-gold split and regression scaffolding.

The strongest material-quality step so far is `model_based_gold_reconstruction`.

The weakest current area is post-search source understanding: the system can see candidate URLs, but it cannot yet compare source bodies to gold material or learn material transformations.

## 3. Gap Analysis

### 3.1 Missing: User Source Review Decisions

The current system has candidates but no durable user decision layer.

This is a real gap because a URL can be useful in multiple ways:

- likely original source;
- similar material;
- useful domain;
- irrelevant;
- question-bank pollution.

Without capturing that distinction, later crawling or material-card work would have no auditable human basis.

Necessary? Yes.

Reason:

- The system must not infer user intent from search scores alone.
- Similar material must not be mislabeled as original source.

### 3.2 Missing: Source Body

The system currently stores only title/snippet/domain/URL.

Necessary? Eventually yes, but not necessarily immediately.

Reason:

- To learn source-to-question transformation, the system needs the actual article or page body.
- But fetching bodies before human review risks collecting junk, training pages, login pages, scraped pages, or copyright-sensitive content.

Correct timing:

- After source candidate human review creates approved crawl seeds.

### 3.3 Missing: Source/Gold Alignment

Once source body exists, the next meaningful quality step is alignment:

- Which source paragraph corresponds to reconstructed gold?
- Is the true-question material an exact excerpt, compressed excerpt, rewritten summary, or thematically similar passage?
- Which terms or context windows support the answer?

Necessary? Yes.

Reason:

- Material-card rules should be based on observed transformations, not vibes.

### 3.4 Missing: Cleaning And Slicing Recipe

The system does not yet know:

- whether boilerplate should be removed;
- how much context around target term is needed;
- whether titles/subtitles matter;
- how to handle source citations, author names, date lines;
- whether source passages should be shortened;
- which paragraph lengths are usable.

Necessary? Yes, but only after source/gold alignment.

Reason:

- Cleaning/slicing rules before alignment would be speculative.

### 3.5 Missing: Material Span Candidate Set

The system needs candidate spans that can become question material:

- full paragraph;
- local context window;
- multi-paragraph excerpt;
- definition-bearing sentence cluster;
- contrast/causal explanation cluster.

Necessary? Yes.

Reason:

- Generation needs candidate material spans, not whole articles.
- Truth-gold regression needs to compare generated material choices against gold-like spans.

### 3.6 Missing: Material Quality Stats

Examples:

- source type distribution;
- paragraph length distribution;
- lexical density;
- concept density;
- context-window size;
- target-term availability;
- question-bank contamination;
- duplicate/source reuse rate;
- domain quality;
- source/gold alignment confidence;
- human review acceptance rate.

Necessary? Yes, but stats must not replace semantic review.

Reason:

- Stats help monitor, compare, and regress material processing.
- They cannot declare semantic suitability by themselves.

### 3.7 Missing: Material Card Draft

Eventually needed:

- source types;
- material selection rules;
- cleaning recipe;
- span selection strategy;
- risk filters;
- quality thresholds;
- examples and counterexamples;
- evidence links.

Necessary? Yes, but later.

Reason:

- A material card before source/gold alignment would be premature.

### 3.8 Missing: Truth-Gold Material Regression

Current truth-gold regression is broader question quality scaffolding. It does not yet specifically evaluate:

- whether selected source body matches reconstructed gold;
- whether span selection matches true-question material span;
- whether cleaned material preserves answer mechanism;
- whether generated material supports distractors.

Necessary? Yes.

Reason:

- Material-line progress needs a loop that says: "This cleaning/slicing/source strategy got closer or farther from true-question material production."

## 4. Foundation Assets To Organize

The following are not just artifacts to collect; they are conceptual assets the material line needs.

### 4.1 Reconstructed Human Material

Role:

- The best available natural-language representation of what the true question likely came from.

Current status:

- Exists through `gold_reconstruction_results.jsonl`.

Risk:

- Model can hallucinate or leak question wording.

Needed controls:

- confidence;
- warnings;
- leakage risk;
- human review flags;
- insurance split.

### 4.2 Source Discovery Query

Role:

- Search-friendly, de-question-bank version of reconstructed material.

Current status:

- Exists through `source_discovery_queries.jsonl`.

Risk:

- Queries can still be too generic or too exact.

Needed controls:

- contamination risk;
- query type;
- query quality;
- source purpose.

### 4.3 Source Candidate

Role:

- A URL/title/snippet/domain candidate returned by search.

Current status:

- Exists through `source_candidate_results.jsonl`.

Risk:

- Candidate may be a training page, answer page, unrelated encyclopedia, or similar-but-not-original source.

Needed controls:

- source risk;
- candidate status;
- verification status;
- human review.

### 4.4 Source Review Decision

Role:

- Human decision about how a candidate may be used.

Current status:

- Missing.

Necessary? Yes, immediately.

Reason:

- This is the first point where the user's judgment should become durable data.

### 4.5 Source Seed Registry

Role:

- Stores user-approved seeds for future crawling or source alignment.

Current status:

- Missing.

Necessary? Yes, after source review decisions.

Reason:

- It lets the system build a reusable source/domain base without pretending anything is verified.

### 4.6 Source Body

Role:

- Actual page/article text.

Current status:

- Missing.

Necessary? Later.

Reason:

- Needed for alignment and cleaning, but should come after seed review and crawl approval.

### 4.7 Gold/Source Alignment

Role:

- Maps reconstructed gold material to candidate source text.

Current status:

- Missing.

Necessary? Yes, after source body exists.

Reason:

- This is where the system starts learning the actual material production process.

### 4.8 Cleaning Recipe

Role:

- Explains how source body becomes usable material.

Current status:

- Missing.

Necessary? Later.

Reason:

- Should be induced from source/gold alignment evidence.

### 4.9 Material Span Candidate

Role:

- Candidate chunks selected from source body for question generation or evaluation.

Current status:

- Missing.

Necessary? Later.

Reason:

- Generation does not need whole source pages; it needs usable spans.

### 4.10 Material Card Draft

Role:

- Draft formalization of material source/cleaning/slicing/quality rules.

Current status:

- Missing by design.

Necessary? Later, not now.

Reason:

- The system lacks enough verified alignment evidence.

## 5. Suggested Distillation Process

Do not define this as a rigid milestone ladder. Define it as an evidence maturation process.

### Evidence State 1: True Question Evidence

Input:

- true-question pack.

Question:

- What did the original test item contain?
- What material and mechanism must be reconstructed before evaluation?

Primary tool:

- model-based gold reconstruction.

Human role:

- inspect low-confidence or leakage-risk samples.

### Evidence State 2: Searchable Material Clue

Input:

- reconstructed gold material.

Question:

- Can the system produce natural source-like queries instead of exam-site queries?

Primary tool:

- source discovery preparation.

Human role:

- inspect query examples and contamination risk.

### Evidence State 3: Candidate Source Evidence

Input:

- source discovery query.

Question:

- Are there URLs that look like original or similar material?

Primary tool:

- source candidate search.

Human role:

- decide if candidates are useful, similar, risky, or irrelevant.

### Evidence State 4: Reviewed Source Seed

Input:

- source candidates.

Question:

- Which URLs/domains deserve later crawling or alignment?

Primary tool:

- source candidate human review.

Human role:

- primary decision maker.

### Evidence State 5: Source Body And Alignment

Input:

- reviewed source seeds.

Question:

- Does the page body actually contain the reconstructed material or a suitable similar material pattern?

Primary tool:

- source fetching and alignment.

Model role:

- semantic alignment and transformation explanation.

Mechanical role:

- hash, dedupe, boilerplate detection, basic text extraction metadata.

Human role:

- verify borderline cases.

### Evidence State 6: Material Transformation Understanding

Input:

- aligned source/gold pairs.

Question:

- How was the source transformed into true-question material?

Possible outputs:

- cleaning recipe;
- slicing rules;
- context window guidelines;
- quality criteria;
- negative examples.

Model role:

- infer transformation patterns and uncertainty.

Mechanical role:

- aggregate stats and regression deltas.

Human role:

- approve or reject recipe claims.

### Evidence State 7: Draft Material Card

Input:

- repeated evidence from reviewed/aligned material examples.

Question:

- Are there stable enough rules to draft a material card?

Output:

- draft only.

Human role:

- approve before formal writeback.

## 6. Model / Mechanical / Human Responsibility Boundaries

### 6.1 Model-Led

The model should lead:

- gold material reconstruction;
- identifying what material information is missing;
- explaining answer mechanism from reconstructed material;
- source/gold semantic alignment;
- identifying whether source body is exact, compressed, rewritten, or merely similar;
- proposing cleaning/slicing recipes;
- explaining material quality issues;
- summarizing why a span is or is not usable.

Reason:

- These tasks require semantic interpretation.
- Hard-coded mechanical rules would either fail across families or bias the system toward preconceived patterns.

### 6.2 Mechanical-Assisted

Mechanical code should handle:

- file parsing;
- sample IDs;
- hashes;
- truncation records;
- split manifests;
- schema validation;
- required-field checks;
- low-level answer/options consistency;
- URL/domain extraction;
- duplicate detection;
- source-risk keyword flags;
- basic text length and overlap statistics;
- report assembly;
- artifact contracts.

Reason:

- These are traceability and safety tasks.
- They should be deterministic and auditable.

### 6.3 Human-Required

Human review is required for:

- accepting source candidates as useful seeds;
- distinguishing original-source candidate from similar material;
- confirming any source as verified original source;
- approving crawl seeds before body fetching at scale;
- approving cleaning recipes;
- approving material-card drafts;
- deciding when evidence is strong enough to affect the card/protocol line.

Reason:

- The system must not silently turn search results or model reconstructions into formal truth.

## 7. Material Line And Card Line Relationship

### 7.1 Separation

The material line must not automatically modify:

- `question_card`;
- `prompt_assets`;
- `validator_contract`;
- `runtime_mapping`;
- `card_specs`;
- generation service;
- validator logic.

Reason:

- Material evidence can suggest better question generation behavior, but it does not by itself define formal protocol.

### 7.2 Evidence Reference

The card line may reference material-line evidence after human review.

Examples:

- A question-card draft may cite aligned source/gold examples.
- A prompt guard draft may cite material cleaning failures.
- A validator candidate may cite material-span quality regressions.
- A material-card draft may cite reviewed source seeds and cleaning recipes.

The reference should be explicit:

```text
card/protocol draft
-> cites material evidence path
-> cites human review decision
-> cites regression result
```

No automatic writeback.

### 7.3 Shared Feedback Loop

The two lines should exchange evidence, not authority.

Material line provides:

- source quality evidence;
- material transformation evidence;
- span quality stats;
- source/gold alignment;
- material regression failures.

Card line provides:

- target question mechanism;
- required material features;
- prompt/validator failure cases;
- generated comparison output.

Both feed truth-gold regression and user review.

## 8. Recommended Next Step

The next step should be:

```text
source_candidate_human_review + source_seed_registry
```

Why this is the correct next step:

1. The system already has candidate URLs.
2. The user has already judged that some candidates are useful.
3. Before crawling or material-card drafting, the system must capture that judgment durably.
4. This step separates:
   - likely original source candidate;
   - similar material seed;
   - useful domain seed;
   - rejected question-bank page;
   - irrelevant result.
5. It creates a controlled input for future crawling.
6. It prevents the most dangerous error: treating similar material or search results as verified original source.

Why the next step should not be direct crawler:

- The current candidate pool contains many `unknown/blocked` results.
- Even low-risk candidates are only weak candidates.
- Crawling without review would collect noise and possibly training pages.

Why the next step should not be `material_card`:

- No source body has been fetched.
- No source/gold alignment exists.
- No cleaning/slicing recipe has been validated.
- No material-specific regression loop has proven quality.

Why the next step should not be UI/API first:

- The decision schema and evidence semantics should be stabilized offline first.
- UI can come after the review decision artifact proves useful.

## 9. Risks And Mitigations

### Risk 1: Question-Wrapped Text Finds Question Banks

Mitigation:

- Continue using reconstructed natural material.
- Keep leakage checks.
- Keep contamination risk labels.
- Do not search raw stems unless explicitly marked high risk.

### Risk 2: Model Reconstruction Hallucinates Source Material

Mitigation:

- Keep confidence/warnings/needs-human-review.
- Use source search and alignment as external pressure.
- Do not treat reconstructed material as verified source.

### Risk 3: Similar Material Becomes Mistaken For Original Source

Mitigation:

- Add explicit `source_use` labels:
  - `original_source_candidate`;
  - `similar_material`;
  - `domain_seed`.
- Keep `verified_original_source=false` until source alignment and human confirmation.

### Risk 4: Material Card Is Written Too Early

Mitigation:

- Keep material-card draft out of the next step.
- Require aligned source/gold evidence before material-card draft.
- Require human approval and regression before writeback.

### Risk 5: Mechanical Stats Hide Semantic Quality Problems

Mitigation:

- Mechanical stats can flag, sort, and summarize.
- Model and human review must judge semantic fit.
- Reports must label scoring method and limitations.

### Risk 6: User Feedback Does Not Enter Next Distillation Round

Mitigation:

- Make user review decisions first-class artifacts.
- Keep accepted/rejected/deferred reasons.
- Feed decisions into source seed registry and future regression reports.

## 10. This Round Is Audit Only

This document is an audit and planning artifact only.

No code was changed.

No new runtime artifact was generated.

No API or UI was added.

No crawler was implemented.

No source was confirmed.

No source body was fetched.

No `material_card` was written.

No `card_specs`, prompt, validator, runtime, generation, or card/protocol-line files were modified.

## Final Judgment

The material line is currently strong enough to support human review of source candidates. It is not yet strong enough to draft material cards or crawl automatically at scale.

The best next move is to capture human decisions over candidate sources and convert accepted candidates into seed-only registries for future controlled crawling and alignment.

That next move directly serves the user's actual goal: turning true-question packs into a growing, reviewed, source-aware material production system.
