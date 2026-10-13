# OpenAI Plugin contract audit for Anki GPT vNext

Research date: 2026-10-13

Scope: official OpenAI documentation only.

## Executive conclusion

The durable current OpenAI product mechanism is a **Plugin**, but a Plugin that needs live data or write operations connects to external systems through an **MCP server**. A skills-only Plugin can package instructions and reference files, but cannot call the Anki GPT API v2 by itself.

The requested durable architecture:

```text
ChatGPT Plugin -> HTTPS -> Anki GPT API v2
```

is therefore not supported by the current Plugin contract.

The supported server-backed Plugin architecture is:

```text
ChatGPT Plugin -> HTTPS MCP server -> Anki GPT API v2
```

That architecture conflicts with the explicit Stage 7 decisions not to publish MCP and not to build `Plugin -> MCP -> API`.

The older direct HTTP mechanism, Custom GPT Actions with an OpenAPI schema, still exists during the retirement window, but OpenAI documents a standard Custom GPT retirement date of 2026-12-11 across ChatGPT plans, subject to the account/workspace notice that applies to the GPT's creator. Only affected Enterprise workspaces with a qualified approved deferral are documented with the later 2027-02-11 date. OpenAI states that custom actions do not transfer through the migration workflow and that rebuilding them may require a custom MCP server. Building the requested direct Action now would therefore create a short-lived integration that must be replaced before or at retirement.

Stage 7 must stop for an architectural decision before implementation, DNS, nginx, TLS, authentication changes, or the authorized production write.

## 1. Current terminology and definition

The current product term is **Plugin**. A Plugin packages one or more of:

- skills containing reusable workflow instructions and resources;
- an MCP server exposing live tools and structured results;
- optional MCP-backed UI resources and extensions.

A Plugin that only needs instructions can be skills-only. OpenAI's architecture guide says an MCP server is the mechanism to use when the Plugin must connect to a service, expose tools, authenticate users, or execute behavior on operated infrastructure.

Sources:

- https://developers.openai.com/plugins
- https://developers.openai.com/plugins/concepts/plugins
- https://help.openai.com/en/articles/20001256-plugins-in-chatgpt

## 2. How tools/actions are registered

Current Plugins do not register REST operations from an OpenAPI document as Plugin tools.

Server-backed tools are discovered from an MCP server. Each MCP tool defines:

- stable tool name;
- human-readable title;
- description explaining when to use it;
- input schema;
- optional output schema;
- safety annotations;
- handler implementation.

Relevant annotations include:

- `readOnlyHint`;
- `destructiveHint`;
- `openWorldHint`.

The MCP endpoint normally uses Streamable HTTP at a stable HTTPS URL ending in `/mcp`.

Sources:

- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/concepts/mcp-server

## 3. Schema format

### Plugin package

New portable packages use a root `plugin.json` manifest following the Agent Plugins schema:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "anki-gpt",
  "version": "1.0.0",
  "description": "Anki study workflows."
}
```

A package may also contain:

```text
plugin.json
skills/
mcp.json
assets/
.codex-plugin/plugin.json
```

The `.codex-plugin/plugin.json` form remains a compatibility fallback.

### Tool schemas

Tool input and output schemas are MCP tool schemas. They are not generated from the Anki REST OpenAPI contract. The MCP server may internally call a REST API, but that is its implementation detail.

Sources:

- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/build/mcp-server

## 4. Calling external HTTP APIs

A Plugin does not have a manifest facility that converts arbitrary OpenAPI REST endpoints directly into current Plugin tools.

The documented path is:

1. ChatGPT connects to the Plugin's MCP server.
2. The model selects an MCP tool.
3. The MCP server validates and authorizes the call.
4. The MCP handler calls the external API or service.
5. The MCP server returns structured content and model-readable content.

Therefore a thin MCP adapter may call Anki GPT API v2, but the Plugin cannot skip the MCP protocol layer under the current documented contract.

Sources:

- https://developers.openai.com/plugins/concepts/plugins
- https://developers.openai.com/plugins/concepts/mcp-server
- https://developers.openai.com/plugins/build/app-quickstart

## 5. HTTPS requirements

A production remote MCP server must be deployed at a stable publicly reachable HTTPS endpoint and support MCP Streamable HTTP. The endpoint must remain reachable for review and domain verification for public submission.

A private server may be reached through OpenAI's Secure MCP Tunnel for development/private use, but the tunnel alone does not satisfy public submission requirements.

Sources:

- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/deploy/app-review

## 6. Supported authentication

For current Plugin MCP servers, the documented primary authentication choices are:

- no authentication for genuinely public capabilities;
- OAuth 2.1 for user-authenticated capabilities;
- mixed public and OAuth-protected access;
- API-key declarations in package manifests, subject to important tooling limitations.

The MCP server must enforce authorization on every protected request. Model instructions and annotations are not authorization controls.

Sources:

- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/deploy/submission

## 7. Secret storage

Secrets must not be committed in `plugin.json`, `mcp.json`, tool metadata, or source control.

For OAuth, the submission flow or managed client configuration handles OAuth client details. The MCP server stores its server-side secrets in its deployment secret manager or environment. OAuth access tokens are presented to the MCP resource server and must be validated there.

The Plugin package manifest describes connection requirements; it does not contain a fixed bearer token.

Sources:

- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/deploy/submission

## 8. Bearer or static-secret support

The package schema can declare API-key authentication with `headerScheme: "bearer"`, `"basic"`, or `"custom_header"`. This declaration describes a credential supplied during connection setup and does not embed the credential.

However, OpenAI's current public submission portal supports only no-auth, OAuth, and mixed no-auth/OAuth connections. It does not provide a bearer/API-key input flow. OpenAI explicitly says that uploading an API-key declaration does not complete public MCP setup and directs developers to contact OpenAI when public submission requires it.

Consequences for this project:

- a dedicated fixed Plugin bearer token is not a documented, self-service public submission path;
- Basic Auth must not be used as a workaround;
- embedding a token in MCP server headers is rejected for public submission;
- if the Plugin must be publicly submitted and authenticated, OAuth 2.1 is the documented self-service path.

Sources:

- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/deploy/submission

## 9. When OAuth is required

OAuth 2.1 is required when a protected Plugin integration must authenticate individual users through the supported public connection flow.

OpenAI documents the MCP authorization model as:

- MCP resource server;
- OAuth authorization server;
- protected-resource metadata;
- authorization-server metadata;
- PKCE-capable authorization-code flow;
- supported client identification or registration through CIMD, DCR, or a predefined client.

OpenAI does not support machine-to-machine OAuth grants such as client credentials or service-account grants for ChatGPT Plugin connections.

OpenAI-managed mTLS can identify ChatGPT as the connecting client, but it does not replace user authentication or authorization.

Sources:

- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/build/mcp-server

## 10. Request and response limits

The Plugin documentation does not publish the former GPT Actions limits as a universal MCP request/response contract. MCP tools should return concise structured results and text, and deployment operators must set suitable timeouts, payload limits, rate limits, and observability.

Documented package/skill import limits include:

- up to five imported skills across ten catalog pages;
- up to 100 files per skill;
- `SKILL.md` up to 256 KiB;
- each supporting file up to 1 MiB;
- all resources for one skill up to 5 MiB;
- generated skill archive up to 8 MiB.

Public package listing fields and manifests have separate validation limits documented by the submission reference.

Sources:

- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/deploy/submission

## 11. Files and binary support

MCP resources can return UTF-8 text or base64-encoded blobs where the resource protocol permits it. Optional MCP Apps UI and file-viewer extensions have their own contracts.

This does not create a direct REST binary bridge from ChatGPT to `/v2/media/{filename}`. Any media exposed to the Plugin would have to be represented through MCP content/resources or a supported UI/file mechanism.

For initial Anki reads and the controlled note update, JSON/text MCP tool results are sufficient. Image/media workflows need a separate design and must not assume the retired GPT Actions file conventions.

Sources:

- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/reference

## 12. Error handling

MCP tool results may contain:

- `structuredContent` matching the declared output schema;
- model-readable `content`;
- hidden `_meta` for a component.

Authentication failures should use an appropriate `WWW-Authenticate` challenge. For OAuth-aware tool errors, the MCP result can include `_meta["mcp/www_authenticate"]`.

The Anki API's structured HTTP errors can remain its internal contract. A thin MCP adapter should map those errors to concise MCP tool errors without exposing tracebacks, tokens, or private payloads.

Sources:

- https://developers.openai.com/plugins/reference
- https://developers.openai.com/plugins/deploy/troubleshooting

## 13. Installation and testing

The current documented development path is:

1. implement and expose the MCP server;
2. validate it with MCP Inspector;
3. in ChatGPT Plugins, choose `Add custom MCP server`;
4. enter the HTTPS `/mcp` URL and configure authentication;
5. create the connection as a Plugin;
6. inspect discovered tools and metadata;
7. install the resulting Plugin;
8. start a new chat, select it with `@`, and execute an evaluation set.

A complete packaged Plugin is then tested from a local marketplace or submitted through the Plugin submission flow.

Sources:

- https://developers.openai.com/plugins/build/app-quickstart
- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://developers.openai.com/plugins/quickstart

## 14. Development mode

The practical development modes are:

- MCP Inspector against a local or remote Streamable HTTP server;
- a public development endpoint or approved secure tunnel;
- `Add custom MCP server` in ChatGPT Plugins;
- a local Plugin marketplace for packaging and installation tests;
- rescanning or refreshing the Plugin connection after tool metadata/schema changes.

There is no current documented OpenAPI-based Plugin dev mode equivalent to the old Custom GPT Action editor.

Sources:

- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/app-quickstart
- https://developers.openai.com/plugins/deploy/connect-chatgpt

## 15. Plan and workspace differences that affect deployment

The Plugin directory is broadly available, but installation and capabilities depend on plan, workspace, role, region, product surface, and included capabilities.

Managed workspaces can control:

- whether a Plugin is available or installed;
- access by role;
- underlying app availability;
- allowed read and write actions;
- approval behavior;
- provider-account and domain restrictions.

Personal Skills are generally documented for Business, Enterprise, Healthcare, and Edu, subject to rollout and workspace controls. Some Plugins or integrations may be desktop-only or otherwise surface-specific.

Sources:

- https://help.openai.com/en/articles/20001256-plugins-in-chatgpt
- https://help.openai.com/en/articles/11509118-admin-controls-security-and-compliance-for-plugins-and-apps

## Custom GPT Actions are a retiring compatibility path

The older mechanism remains documented during the transition:

```text
Custom GPT -> GPT Action -> external REST API described by OpenAPI
```

It supports direct HTTPS API calls and could technically call Anki GPT API v2 without MCP. It is not the durable Plugin contract.

OpenAI currently states:

- the standard scheduled retirement across ChatGPT plans is 2026-12-11, subject to the account/workspace notice that applies to the GPT's creator;
- only affected Enterprise workspaces with a qualified approved deferral may retire on 2027-02-11;
- Custom GPT instructions can migrate to a Plugin skill;
- connected apps can migrate as apps;
- custom actions do not transfer automatically;
- rebuilding custom-action integrations may require a custom MCP server.

Sources:

- https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq
- https://help.openai.com/en/articles/9442513-configuring-actions-in-gpts

## Historical Anki GPT capability matrix

This matrix separates capabilities that belong in Anki GPT API v2 from legacy transport, queue, snapshot, FO, and editorial concerns. It does not authorize implementation while the platform decision is blocked.

| Historical capability | Still needed? | API v2 today | Decision after platform choice |
|---|---|---|---|
| Health and collection/sync state | Yes | Supported by `GET /v2/health` | Keep |
| List decks and subdecks | Yes | Supported by `GET /v2/decks` with root filter and pagination | Keep |
| Search notes and cards using Anki syntax | Yes | Supported by `POST /v2/search` | Keep; document multi-deck queries rather than invent another parser |
| Get one canonical note | Yes | Supported by `GET /v2/notes/{note_id}` | Keep; add explicit version/precondition fields before broad editing workflows |
| Get one rendered card | Yes | Supported by `GET /v2/cards/{card_id}` | Keep |
| Update note fields and incremental tags | Yes | Supported by `PATCH /v2/notes/{note_id}` | Keep; preserve sync-before/write/sync-after and card-set guard |
| Read collection media | Yes for image/audio-aware auditing | Supported by `GET /v2/media/{filename}` | Keep in API; Plugin/MCP transport needs a separate media representation design |
| Large-deck query-all and bounded materialization | Yes for historical whole-deck audits | Search returns IDs with pagination; no bounded multi-ID materialize endpoint | Implement in API v2 after platform choice, with response-size limits and no partial-write semantics |
| Optimistic preconditions (`content_hash`, `mod`, `usn`, model ID) | Yes for safe edits based on prior reads | Not exposed or required by current v2 patch | Implement in API v2 before general GPT writes; stale state must return conflict without mutation |
| Bounded batch note updates | Yes for historical normalization/highlighting workflows | Single-note patch only | Implement in API v2 after preconditions, with a small maximum batch and explicit per-item outcome/atomicity contract |
| Add/remove tags in bulk | Useful as part of batch editing | Single-note patch supports incremental tags | Provide through the bounded batch update; do not revive the legacy tagging queue |
| Create notes/cards | Historical, but not required for the validated read/update migration | Unsupported | Defer until a concrete creation workflow and duplicate policy are approved |
| Delete notes/cards | Not required for Stage 7 and broadly destructive | Unsupported | Discard from initial scope; any future endpoint needs narrow safeguards and explicit confirmation |
| Move cards/notes between decks | Historical organization workflow | Unsupported | Defer as a separately protected operation; never fold into generic note patch |
| List note types/templates | Needed only for future creation or structural conversion | Note reads return the current note type; no catalog endpoints | Defer until creation/conversion is approved |
| Basic-to-Cloze conversion in place | Real historical workflow | Unsupported by design | Implement only as a dedicated protected API v2 operation after baseline Plugin validation |
| Global reorder/Created manipulation | Historical but high risk | Unsupported | Defer; require complete materialization, global preconditions, bounded scope, and rollback design |
| Media upload | Not required for current validated workflows | Unsupported/read-only | Defer; requires filename collision, media sync, size, type, and reference policies |
| Legacy snapshot publication and JSON indexes | No for live Service Collection reads | Intentionally bypassed | Keep legacy untouched until Stage 8; do not port to API v2 |
| Legacy operation/tagging queues and add-on polling | No for synchronous API v2 owner-thread writes | Replaced by collection actor and synchronous result | Keep legacy untouched until Stage 8; do not port |
| FO materials/transcripts | Yes for source-grounded editorial workflows, but not Anki collection semantics | Not in API v2 | Keep as a separate domain service/knowledge source; do not add to the Anki collection API |
| Recurrence/prioritization knowledge | Useful editorial knowledge, not collection mutation | Not in API v2 | Keep in Plugin skills/knowledge or a separate service |
| Editorial instructions and card-quality rules | Yes | API-neutral | Migrate into Plugin skills regardless of transport choice |

Repository evidence includes:

- `apps/anki-gpt/gpt-knowledge/INSTRUCTIONS_CURTAS_GPT_BUILDER.md`;
- `apps/anki-gpt/gpt-knowledge/05_fluxo_decks_grandes.md`;
- `apps/anki-gpt/gpt-knowledge/06_fluxo_fo_materiais_transcricoes.md`;
- `apps/anki-gpt/gpt-knowledge/07_conversao_basic_para_cloze.md`;
- `contracts/openapi/gpt-action-compact.openapi.json`;
- `contracts/openapi/anki-api.openapi.json`;
- `apps/anki-gpt/addon-local/organization.py`;
- `packages/anki-contracts/note_preconditions.py`;
- `services/anki-api-v2/README.md`;
- `services/anki-api-v2/anki_api_v2/service.py`.

## Architectural decision required

The project owner must choose one of these paths before implementation:

### Option A — durable current Plugin architecture

```text
ChatGPT Plugin
  -> public HTTPS MCP v2
  -> localhost Anki GPT API v2
  -> Service Collection
  -> Sync Server
```

This requires reversing the Stage 7 prohibition on publishing MCP. The existing MCP v2 can remain a thin adapter; Anki semantics, sync, validation, locking, and writes remain in API v2.

Authentication must then be selected. For public self-service submission, OAuth 2.1 is the documented protected path. A private/custom connection may have different account-specific setup options, which must be verified in the actual ChatGPT account before deployment.

### Option B — temporary direct Custom GPT Action

```text
Custom GPT Action
  -> public HTTPS Anki GPT API v2
```

This preserves the requested direct API architecture temporarily, but it targets a product scheduled to retire on 2026-12-11 and does not migrate the custom action. A second integration project would be required shortly afterward.

### Option C — skills-only Plugin

```text
ChatGPT Plugin skill only
```

This can migrate instructions and Knowledge/reference material, but it cannot read or update live Anki data. It does not satisfy Stage 7.

## Recommendation

Choose Option A if the goal is a durable current OpenAI integration. The existing MCP v2 is already intentionally thin and has validated reads, writes, sync-before/sync-after, ID preservation, and fail-closed behavior. Publishing it behind an authenticated HTTPS endpoint is the architecture the current Plugin platform expects.

Do not implement Option B unless the owner explicitly accepts the 2026-12-11 retirement deadline and the duplicate migration work.

Do not proceed with DNS, nginx, TLS, OAuth, API token changes, Plugin packaging, or the single production write until the owner chooses between Option A and Option B.
