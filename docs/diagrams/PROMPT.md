# Reusable architecture-document prompt

Replace the parameters, then submit the prompt below. Use the same viewer navigation contract for a library, service, backend, analysis repository, or another kind of codebase.

```text
Repository: {repo}
Evidence ref: {evidence_ref} (default origin/dev; ask if absent)
PR base: {pr_base}
Style profile: {profile_path} (default ~/.diagram-design/profiles/aiomic.md)
Output directory: docs/diagrams/

Use the diagram-design skill to create a standalone logical architecture
explanation for {repo}. Start fresh, without Atlas or other runtime services.

PLAN FIRST. Refresh refs and inspect the chosen remote revision, preserving
working-tree changes. Record the SHA. Verify cross-repository claims in the
other repository's code; inspect the pinned dependency release when it differs
from that repository's current development branch. Record all revisions.
Do not copy private code outside its authorized repository/delivery scope.

Propose 3–5 diagrams as a table:
  # / question-title / diagram type / what it shows / opens from
Organize around responsibilities and real artifact/API boundaries, not folders.
Show the starting overview and every component-to-detail link. Distinguish
"look inside" from "related workflow". Include at least two successive genuine
drill-downs on one useful path, followed by a function or source excerpt.
Do not fabricate containment: training may produce a checkpoint consumed by
prediction; a workflow related to another is not automatically inside it.
State omissions and uncertainty. Wait for approval before implementation.

After approval, use /start to create a dedicated worktree on the approved base.
Use the saved profile, minimal light, 1280-wide diagrams, at most 9 nodes and
12 arrows each, and 1–2 accent elements. Use short labels, explicit relationship
labels, orthogonal rounded connectors, generous space, and a clear reading
order. A title and at most one short explanatory sentence should suffice.

Build self-contained HTML/SVG diagrams and PNG exports. Keep their complete
static versions usable without JavaScript. Generate the interactive index.html
from exactly the same diagram content. Do not fetch diagram files at runtime:
opening file:// directly must work offline. Embed required styles and viewer
code at build time. No backend, external scripts, or font service dependency.

Keep the viewer UI to a wordmark, title/diagram, compact location indicator,
Up and Overview. Make expandable nodes discoverable. On drill-down, keep the
selected node visually identifiable, move it briefly into a compact context
anchor at the top, fade its surroundings, and reveal the detail below. Related
views must use different navigation styling and must not animate as containment.

Use stable view/component IDs and a small explicit route mapping:
  "{view-id}:{component-id}":
    {to: "{destination-id}", kind: "inside", label: "...", node: "..."}
  "{view-id}:{related-view-id}":
    {to: "{destination-id}", kind: "related", label: "...", node: null}
The viewer interprets this mapping, not repository names or source paths.

Store a trail of actual visits, not a fixed parent tree. Up reverses the last
transition and restores layout, focus, selection and scroll. Overview returns
to the root. Breadcrumbs and browser Back/Forward share the same history.
Shared configuration may be reached from several views; Up returns to the
actual caller. Preserve this behavior for deep links and reloads. Support
native keyboard navigation, visible focus, reduced motion, and narrow screens.

At source endpoints, show function name, file, line range and full revision,
a simple exact code excerpt, and the same Up/Overview behavior. Label excerpts
as excerpts when partial. Keep evidence unobtrusive through collapsed source
references and revision-pinned links. Maintain a machine-readable evidence
manifest distinguishing inspected code from interpretation and uncertainty.

Validate:
- Run diagram-design/scripts/self_check.py on every standalone diagram.
- Render every diagram in headless Chrome, export its PNG, and inspect it.
- Inspect the viewer, a drill-down transition, source endpoint, and narrow view.
- Exercise every inside and related link, Up, Overview, breadcrumbs, Back/Forward,
  correct parents after shared-view visits, reload and deep links.
- Verify keyboard navigation, focus, view-state restoration and reduced motion.
- Check label/arrow overlap, node/arrow budgets, offline operation, and source
  excerpts against recorded revisions. Check standalone/viewer content equality.

Include opening/regeneration instructions and this reusable parameterized prompt.
Use /ship to validate, review, commit, push and create a PR against {pr_base}.
In the PR body list the questions, hierarchy, main paths, verified claims and
SHAs, known omissions/uncertainty, and actual visual/interaction checks performed.
Do not modify claude-settings, install a skill, merge, or deploy unless requested.
```
