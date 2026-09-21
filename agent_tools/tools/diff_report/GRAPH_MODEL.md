# Declarative Graph Model

The authoring API is `diff_report.graph_model.compile_graph(graph, model)`.
Applications provide source nodes, source edges, and an explicit model. The
compiler returns the renderer wire format, including traversal settings,
context memberships, provenance, and the model itself. Compile once, before
`write_report` or `report_from_payload`. Do not compile a stored graph again.
There is no inferred schema or legacy-model adapter.

```python
from diff_report.graph_model import compile_graph
from diff_report.sqlite_store import write_report

payload["relationship_graph"] = compile_graph(source_graph, model)
write_report(connection, payload)
```

The schema travels with the graph through SQLite, the Python provider, the
embedded WASM provider, and inline HTML. The browser consumes compiled
memberships; it does not recompute domain-specific rules or verdicts.

## Model Version 1

| Field | Meaning |
| --- | --- |
| `version` | Integer `1` |
| `entity_types` | Named entity declarations |
| `relation_types` | Named relation declarations |
| `derivations` | Finite paths producing summary associations |
| `contexts` | Joins producing parent-specific child memberships |

Entity declarations contain `rank` (non-negative display level),
`representation` (`node` or `leaf_table`), and optional `root: true`.
Ranks do not imply ownership. At most one root node may occur in a graph;
fragments may omit it. An ownership edge cannot target the root.

The same declarations control the report UI:

- `label`: display name used by graph nodes, search, and type filters.
- `shape`: `ellipse`, `round-rectangle`, `rectangle`, `diamond`, `hexagon`,
  `barrel`, `tag`, or `round-tag`. The default is `round-rectangle`.
- `scope`: `global` (default) or `isolated`. Isolated entities are available
  when their scope is opened, but are not mixed into the global graph.
- `scope_field`: an optional node/detail field; a non-empty value marks that
  particular node as isolated. This supports scope-owned artifacts without
  hardcoding application field names in the renderer.
- `terminal`: stop descendant expansion through this type in a focused graph.
  Focusing the terminal entity itself still allows inspecting its children.

The browser retains the model loaded from SQLite and uses it for roots,
ordering, labels, shapes, scope visibility and traversal. The renderer validates
loaded nodes and edges against the model. If a technical `traversal` snapshot
disagrees with the model, the model wins; application vocabulary is not duplicated
in browser constants. Leaf types never appear as graph filter options merely
because they are declared.

Leaf types describe the boundary of the entity model, but leaf records must not
be inserted into graph nodes. Their tables, queries, identifiers and row-level
validation remain application responsibilities. Declaring an ownership relation
to a leaf type does not validate records in an application table.

Every relation declares:

- `source` and `target`: non-empty lists of declared entity type names.
- `kind`: `ownership`, `association`, or `context`.
- `cardinality`: `one_to_one`, `one_to_many`, `many_to_one`, or `many_to_many`.
- `traversal`: `both`, `forward`, `reverse`, `none`, or `fallback`.
- `group`: required only for contextual relations, whose traversal is `none`.
- `grouping`: optional boolean on a contextual relation, default `false`.
  Enables the grouped presentation and entry behavior described below.

Cardinality describes maximum distinct neighbors, not a requirement that data
be complete. `one_to_many` limits each target to one source for that relation.
Ownership additionally enforces one owner across all ownership relations and
rejects cycles. Association cycles are permitted; association does not imply
ownership or automatic propagation to descendants. Duplicate source/target/
relation triples are rejected. Additional evidence belongs in edge metadata.

## Explicit Derivation Paths

### Nested Groups

An ownership relation may declare `hierarchy: true`. It preserves ordinary
single-owner and cycle validation, while allowing nested instances of the same
entity type. The browser places each nested instance below its owner without
creating a second entity type. An entity's optional `nested_label` supplies the
display name for nested instances; its type and stable ID do not change.

Projection level menus use the instance's hierarchy rank and display label,
not only its base entity type. Thus `Topic` and `Subtopic` can be switched
independently without introducing another data entity. Selections and navigation
history are keyed by rank; focus protection applies only to the focused level.
Entity-level presets still select all levels of that entity type.

Hierarchy entity types do not trigger the implicit single-type or two-type
catalog-list shortcuts: a focused hierarchical node remains a neighborhood,
even when only its base type is enabled. A global flat catalog requires the
explicit Plain list mode, which also respects hierarchy-level selections.

Entry through a context relationship shows the complete target neighborhood.
All context parents and their ownership ancestors up to the product remain
visible. The entry source does not restrict membership. Clicking a parent
prioritizes and highlights its members without hiding alternative branches.
Visible ancestors outside the isolated neighborhood remain navigable: the
second click exits that isolation, and Back restores it.

For a nested focus, contextual parent paths pass through its declared hierarchy
owners when matching parent membership exists at each owner. This is a display
route only: source edges remain unchanged, and the route retains the original
focus membership so inspecting a requirement does not highlight unrelated domains.

Hierarchy branches may have different depths. A sole child is not automatically
redundant. For a reviewed equivalent pair, the source hierarchy edge may specify
`equivalent: true` and a non-empty `equivalence_basis`. Compilation contracts
that child into its same-type parent before deriving associations or contexts.
The child must be the parent's only hierarchy child. Conflicting statuses,
relationship facts, ambiguous aliases and invalid resulting ownership are
errors, not reasons to discard data. Unmarked singleton branches stay intact.

Contraction redirects relationships to the retained parent, preserves the
original child object and review basis in `collapsed_nodes`, and records old IDs
in the parent's `aliases`. Parent metadata remains authoritative; the producer
must supply its reviewed consolidated details. Browser focus links and view
`focus`, `isolate_root`, and `node_ids` resolve aliases to canonical IDs. Alias
IDs cannot identify another live node or belong to more than one node. Explicit
context subsets, including empty subsets, survive contraction; conflicting
explicit facts must be resolved by the author.

Grouping contexts propagate upward through these declared hierarchy edges.
Each inherited context refers to the immediate nested group, not copied links
to all its leaves. Existing source memberships at each nested group constrain
the next hop. Filter eligibility compares the full nested leaf memberships,
so two parents sharing a group can still highlight distinct subsets within it.
Explicit context overrides, including empty memberships, remain authoritative.

At a grouping parent's entry, only the outermost applicable groups are shown;
their covered nested members are collapsed without altering stored edges.
Entering a group opens its next level. This is presentation and set inclusion,
not inheritance of compliance, test results or evidence coverage.

For example, a policy relates to a segment; a package owns that segment.
This rule associates the policy with the package, without associating it with
the package's other segments:

```json
{
  "id": "segment-owner",
  "relation": "policy_package",
  "path": [
    {"relation": "policy_segment"},
    {"relation": "owns_segment", "direction": "reverse"}
  ]
}
```

Steps default to `forward`; only `forward` and `reverse` are accepted.
The compiler validates endpoint types and joins indexed source edges. It walks
only declared finite paths, not a transitive all-to-all closure. Paths may not
use contextual edges. Derived outputs must be associations with traversal
`none` or `fallback`, so summary shortcuts cannot expand contextual membership.
Rules read explicit facts only and cannot depend on derived output relations.
There is no recursive rule evaluation or dependence on rule ordering.

For each generated edge, `model_provenance` records the rule ID and
`source_edges`: positions in the compiled edge list. These references survive
SQLite round trips. A path keeps one deterministic witness per endpoint, not
every possible path through a branching graph. References are local to this
report, not stable identities across different report builds.

## Context Membership

```json
{
  "id": "policy-package-members",
  "relation": "policy_package_context",
  "membership_path": [{"relation": "policy_segment"}],
  "child_relation": "owns_segment"
}
```

Here `policy_package_context` declares source `policy`, target `package`, kind
`context`, group `policy`, and traversal `none`. The compiler intersects a
policy's reachable segments with a package's direct children. It emits
`context_children` on the policy-to-package context edge. A context witness also
includes the package-to-segment edge and the specific child ID.

Multiple rules for the same context relation union their matching children.
An explicit context edge with the same source, target and relation overrides
the computed membership, including an explicitly empty child list. This is how
an application can express narrower contextual facts that cannot be recovered
from binary associations. Missing evidence never justifies inventing membership.

The renderer uses compiled memberships for inspection paths and ordering.
Selecting a parent does not restrict the focused neighborhood or mutate its
source memberships. Unrelated branches remain available as dimmed alternatives.

### Grouped Presentation

Set `grouping: true` on a context relation to use its target as a grouping node.
In the source's focused graph, visible grouping targets replace direct display
of their `context_children`. Children without such membership stay visible.
Membership is specific to the source: a grouping target shared by two parents
does not bring the second parent's children into the first parent's view.
Overlapping groups do not duplicate child nodes. Hidden or disabled grouping
targets do not collapse their members; explicit list views remain uncollapsed.
Targets remain visible across pagination so their collapsed members are reachable.
Outgoing contextual entry points respect the nearest visible child rank. They
cannot introduce a later layer alongside an earlier one. A context target that
owns its matched members replaces those members in this view, keeping owners and
their children on successive drill-down levels. These presentation rules do not
create new ownership or membership edges.
This is presentation only: source edges, SQLite data, search and metrics retain
the original memberships.

Opening a grouping target, directly or through a source, shows all its members.
All context parents remain visible, together with their ownership ancestors.
Inspection uses explicit compiled memberships, never labels, statuses or outcomes.
There are no parent checkboxes, orange filter outlines, or Ctrl+click filters.
Ctrl+click (Command+click on macOS) instead toggles parent inspection membership
without navigation or hiding children. Ordinary click replaces the comparison
with one inspected node; its next ordinary click navigates as before.
The comparison basket contains only one hierarchy rank at a time, including
the distinction between a topic and a nested subtopic. Ctrl/Command on another
rank starts a new basket. Every visible node is eligible, including leaf
requirements without visible descendants. Explicit Ctrl/Command initiators use
a separate magenta outline; ordinary inspection remains blue. Badge numbers
are consecutive within the selected basket, not indexes in the full parent
inventory, and scale with graph zoom after selection. Numbering follows the
selected nodes' visible row order, left to right and then top to bottom, not
entity IDs, types or click order. Shared-node badges follow the same numeric
order; their colors and partition contours use this mapping without moving nodes.

With several parents selected, children shared by all come first, followed by
partial intersections and individual memberships. Equal membership sets stay
together, retaining the normal order within each set. Membership partitions use
contours per hierarchy rank and shape; unrelated cells remain outside the stepped contour.
Numbered color markers on parents, their outgoing paths and children identify
membership, including multiple parents per child. Existing hierarchy paths
remain intact through the topic; a shared downstream arrow does not assert
every parent owns every child. Common children receive stronger outlines, and
the summary explicitly reports the common count, including zero.
Single-parent inspection needs no markers. Pagination and deactivation retain
the comparison; clearing inspection, navigation or changing filters resets it.
Parent positions stay fixed throughout selection; only descendants are sorted.
A downstream focus follows the resulting layout rather than remaining inside
an expanded descendant block when pagination changes its height.
Adjacent selected parents share contours when their incoming source/relation
sets match. Disconnected occupied components remain separate, with unrelated
cells outside every contour. Multiple components or individual parents with
a common endpoint use a shared connector with short branches, not repeated
long arrows. Connectors avoid both selected and dimmed nodes and preserve the
intermediate topic and relation identity. Membership markers render after all
paths, so crossing arrows cannot cover their numbers.
Single- and multiple-parent inspection use common-endpoint connectors across
highlighted hierarchy levels. The largest fan-in or fan-out is bundled first;
each underlying link is consumed once, and different relation types stay
separate. Individual routes try free local row and column gaps before taking
an exterior detour. This changes presentation only, not graph membership.
Equivalent highlighted segments with identical incoming and outgoing endpoint
and relation sets can share a frame at any level, including ancestor domains
and VSR requirements. Disconnected components stay separate; frames never
include unrelated cells. Context continuation checks the unpaginated focused
graph, not global memberships outside the current view, so an intermediate
group with no applicable descendant path is not highlighted as connected.

Ctrl/Command selection also applies to ordinary ancestors, including nested
grouping nodes. A module view completes missing contextual parents from its
nearest grouping ancestors through hierarchy owners to the root. An ordinary
parent already represented in the current projection keeps that path unless
the grouping hierarchy is already shown. In that case, membership follows the
hierarchy and replaces its direct display shortcut, rather than creating a
second branch. Frames replace only genuinely common same-relation paths;
partial links retain individual endpoints inside their own frame, with sibling
nodes retained as routing obstacles. Grouping applies at every highlighted
hierarchy level, not only immediately below the inspected node. Broader owners do not
introduce memberships absent from those nearer ancestors; this is a display
projection and never changes compiled relationships.

Frames use hierarchy rank and visual shape rather than entity type as their
boundary. Adjacent CTS and VTS modules can therefore share a frame when their
highlighted paths match; their types, statuses and relation identities remain
separate. Geometry checks all peers on the same rank to exclude unselected cells.

Inspecting one ancestor above two or more branching descendant levels uses a
set overview. Connected highlighted peers of the same rank and shape share
frames. The initiator retains its selection outline without magnification that
would cover adjacent blocks. Links are aggregated between displayed endpoints by relation identity,
retaining every underlying edge ID in `inspectionLinks[].edgeIds`. A dashed
arrow represents multiple connections between members, not an all-to-all
relationship; its tooltip reports the connection count. No source relationships
are added, removed or inferred. Selecting a narrower node rebuilds the view
and restores detailed paths when fewer than two descendant levels branch.
Disconnected occupied components stay separate, and unselected peers are never
absorbed into the frames. Multi-parent comparison partitions each descendant
rank and shape by the exact selected-parent membership set: `1`, `2`, and
`1+2` form separate blocks, not one union frame. Shared nodes appear once.
Single-parent partitions use their membership badge color for the contour;
intersection contours stay blue and each node retains its numbered badges.
Disconnected occupied components remain separate. Summary links between these
blocks retain all original edge IDs and relation identities; different relation
types can still produce separate links between the same displayed endpoints.

### Click Inspection

The first primary-button press enlarges a node and highlights its drawn ancestor
and descendant paths. The second press on that inspected node navigates immediately.
The first press does not darken or depress the node; pressed feedback is reserved
for the second, navigating press.
Both actions run on pointer down (Cytoscape tapstart), never on release; motion
with the button held does not cancel inspection. Clicking empty canvas clears
inspection on release; panning the canvas preserves it. Pointer movement does not
enlarge nodes or change highlighted paths.
Double-clicking empty canvas runs Fit; double-clicking a node does not.
An inspected node highlights descendants when multiple nodes at its rank are
visible, including peers whose children are on other pages. A sole parent remains highlighted without flooding
its children with blue paths; its own ancestor paths remain highlighted.
An active sorting priority keeps its member paths highlighted even when the
resulting page contains only that parent's children.
Node dragging is disabled; canvas panning, zoom and Fit remain available.
Inspection updates the detail panel without changing the graph's focus node.
Deactivation preserves inspection and details, while cancelling pending presses
and navigation. Leaving a pressed node, including with the pointer held down,
clears its dark pressed appearance. Open graph resets the view to the model root
and its first child layer, clearing the previous inspection and filters.

All nodes use a common scale factor at a given viewport and zoom, applied
immediately on press without animation. Width, height, padding, font size
and text wrapping width scale together; labels and border widths remain unchanged.
The factor targets readable text but is capped to fit the viewport. Only the
inspected node may move inward temporarily; clearing inspection restores its
position. Blue paths render over ordinary nodes, below the inspected node,
with zoom-compensated widths and arrowheads.

Inspecting a context parent previews its explicit members on the current page.
Shared and exclusive members use the same blue paths and group contours.
Inspecting another node follows its drawn ancestors and descendants, not sibling
branches reached through an ancestor. Context edges constrain traversal to their
declared members. Unrelated nodes use 35% opacity and unrelated edges 12% opacity.
This dimming applies only when visible parent branches offer alternatives.
Inspecting the current focus never dims its contents, even with multiple parents.
Inspecting a requirement under a sole domain does not dim its siblings. If the
highlighted paths would cover every drawn edge, only the inspected node is
highlighted instead of colouring the entire graph blue.

Selecting a parent prioritizes its related items in the current focus before
pagination and opens the first page. Each partition retains the existing general
ordering (status, level and name); no items are filtered out. Membership comes
from loaded focus edges, with context-child restrictions preserved. Ordinary
ancestor traversal stops at the focus, never spreading into unrelated children.
No SQLite query or new evidence edge is needed. Drawn blue paths still use only
the resulting visible page. Parents whose children are off-page stay available.

Switching parents changes the priority; identical memberships do not rebuild the
first page. Clearing inspection restores the original page and ordering. Zoom,
pan and parent positions are preserved across priority changes. The priority
lasts across pagination and deactivation but resets when the focus or filters
change. The second press still navigates. If all or none of the page items match,
no new priority is introduced.
Inspecting the focus node itself also restores the base page and ordering before
computing its highlighted paths; a previous parent's priority is not retained.
Priority also reorders fully visible ancestor rows without pagination. Within
the layout, types stay grouped and related items lead inside each type. Only
the inspected parent and higher levels retain anchored positions, not the child
requirements being reordered.

During parent inspection, multiple highlighted children of the same type share
one thin contour and one incoming arrow. If every member links to the same
downstream node, that fan-in also becomes one arrow. The contour follows occupied
row bands, including the stepped end of a partial row; unrelated nodes still fill
the remaining cells outside it. Disconnected runs retain individual paths.
Single children and individual child inspection retain their actual arrows.
The same grouping applies to repeated incoming paths when inspecting a child.
Incoming members are partitioned by entity type, relation to the inspected node,
and the exact visible upstream (node, relation) set. Only matching partitions
with a connected contour are bundled, so a frame never implies an upstream
link to a member that lacks it. Multiple genuinely shared upstream parents
retain one arrow each. The inspected node itself is never absorbed into a group.
Blue arrows prefer top/bottom centre ports with perpendicular curved approaches.
When enlargement leaves insufficient clearance, side ports and exterior rounded
detours avoid the endpoint bodies, other highlighted nodes and group interiors.
Ordinary dimmed nodes can still lie beneath paths. Group members with individual
outgoing links can exit their own contour. Routing changes neither layout nor
magnification; final geometry is used immediately on press and zoom. Pan-only
updates reuse the routes. Individual and grouped arrows share this renderer.
Zoom preserves the enlarged node's model position instead of bringing it back
inside the viewport; it may leave the screen normally during navigation.
The graph context menu offers `Open selection view` or `Exit selection view`.
Opening it never selects an object or changes highlighted paths, layering or
layout. Without an inspected selection, the open action is disabled.
Open selection view freezes the currently highlighted objects and actual edges
as an independent presentation. New inspections do not change its membership.
Exit selection view restores the original view, filters, page and inspected
objects, including comparisons. It reconstructs the highlighted paths without
replaying clicks, navigation, hover enlargement or rearrangement animation.
Back and Forward retain the frozen selection-view identity and return state.
This is a pointer-transparent presentation overlay, not new graph nodes or
evidence edges. It follows zoom/pan, survives deactivation, and is rebuilt for
the visible page. Clearing inspection or navigating restores ordinary edges.
Group contours occupy a separate layer below Cytoscape's node canvases, while
blue arrows stay above them. An enlarged node therefore covers any overlapping
contour with its actual shape. Both overlay layers follow the same viewport.
Hidden native edges beneath these overlays do not receive pointer events.
If native polygon hit-testing misses a diamond on its centre line, a geometric
diamond check forwards the same press to that node rather than clearing focus.

The compact canvas overlay partitions direct parent members into visible,
filtered by ordinary controls, other pages, and outside the current presentation.
A separate dimmed count covers visible peer members, without duplicates;
inspection never labels these still-visible alternatives as filtered.
The overlay clears with inspection and does not change canvas dimensions.

### Contextual Help

The question-mark control toggles a contextual help mode. Pointer hover and
keyboard focus identify a control, graph object or group and show a compact
tooltip next to it. Descriptions cover search, filtering, levels, statuses,
navigation, pagination, selection views, details and graph relationships.
The active target receives an accessible description and visible outline.
Clicks and editing keys explain controls without invoking their normal actions.
Escape or the question-mark control exits help; closing the graph clears it.
Tooltip positioning stays within the viewport and follows scrolling.

### Renderer Selection

Graph rendering uses WebGL2 only when a caveat-checked context exposes an
unmasked renderer name that is neither generic nor a known software backend.
SwiftShader, llvmpipe, softpipe, lavapipe and WARP remain on Canvas. Missing
WebGL2, privacy-restricted renderer information and probe errors also use Canvas.
This is a conservative browser-reported capability check, not proof of a
physical GPU behind a virtual device or a guarantee of higher frame rates.

The actual Cytoscape context is checked again before use. Initialization errors
or context loss disable further WebGL attempts for the page session. Context
loss rebuilds Canvas while preserving inspection, node positions and viewport.
Destroyed graphs release WebGL contexts. The graph container exposes
`data-graph-renderer` and `data-graph-renderer-reason` for diagnostics.
SQLite queries, graph layout and SVG inspection connectors are not accelerated
by this renderer switch. The pinned vendor patch and rebuild steps live in
`vendor/README.md`.

## Application Boundary

Legacy context metadata `filter_mode: "shared_children"` and `filter_mode: "none"`
remain accepted by model validation for compatibility, but do not activate
parent filtering. Grouping, inspection and source membership remain independent.
Regular status and hierarchy-level filters and explicit Plain list still apply.

Parent inspection preserves the focus and full member set, prioritizes matching
children using the normal per-type ordering, and highlights their paths.
Clearing inspection restores ordinary ordering; navigation history restores the
neighborhood without inherited parent restrictions. Large ancestor rows use
ordinary pagination. No all-pairs table or invented test coverage is required.

`tests/test_graph_model.py` uses a non-AOSP portfolio/division/label/policy/
package/segment model. It covers ownership, explicit overrides, leaf rejection,
summary derivation, SQLite serialization and desktop/mobile parent inspection.

The AOSP vocabulary lives in `src/scripts/aosp_graph_model.py`. Filtering is enabled
for domain-to-topic and requirement-to-module contexts, using shared requirements
and test groups respectively. Analysis-entity and topic-to-module contexts remain
presentation links without parent filtering. The model replaces the
handwritten custom-scope/domain intersection with two context rules, one each
for CDD and VSR. Requirement-to-domain links are associations despite their
existing `domain_contains_*` names. No new topics, test groups, case nodes or
test coverage claims are synthesized. Membership beyond existing traversable
paths still requires evidence-backed rules in the application model.
