# Route C addendum: ChatGPT Sites-hosted MCP

Research date: 2026-10-13
Scope: official OpenAI sources only. This addendum supersedes unsupported or over-broad claims in the earlier external-API/actions note where this document conflicts with it.

## Conclusion

**Can ChatGPT Sites host a Plugin MCP server? Yes.** OpenAI's current Help Center explicitly documents adding an MCP server to a new or existing ChatGPT Site; publishing the Site creates the associated Plugin, which can then be installed and used in ChatGPT.[1][2]

**Can a personal ChatGPT Plus user create and use that Site/Plugin? Yes, subject to rollout and account eligibility.** Sites are documented as available in public beta to Plus and Pro accounts, and OpenAI's plugin-hosting page says plugin hosting is available to all plans.[1][2] The page does not say that Plus users need Enterprise, Business, or an administrator to create their own personal Site/Plugin. This is distinct from custom remote MCP Developer Mode, whose full MCP/write-app availability is documented for Business and Enterprise/Edu; Pro is documented for read/fetch MCP use, but Plus is not listed there.[3]

**Does this prove Route C for the requested Anki architecture? No—not completely.** Route C is a supported product shape. OpenAI documents that Site owners configure owner-only settings such as secrets, but the official Site documentation reviewed does not specify the exact Site-runtime contract needed here: server-side outbound HTTPS behavior, custom request-header injection, secret exposure boundaries for execution/logging/model context, rotation behavior, or exact MCP execution, timeout, payload, file/binary, and outbound-call quotas. Therefore the defensible status is: **Route C = YES for hosting/using a Site-backed Plugin; NO/UNPROVEN for the requested secure private-backend proxy until OpenAI exposes or confirms those runtime guarantees.** Do not treat the product capability as proof that the Anki backend can safely be reached.

## What the official Sites flow establishes

1. Start or open a Site.
2. Ask ChatGPT or Codex to add an MCP server and describe the information the tools should read and the changes they should be able to make.
3. Review and test the tools.
4. The Site owner publishes the Site; publication creates the associated Plugin.
5. Install the Plugin, complete the connection flow, and invoke it in a supported ChatGPT or Codex chat.[1]

OpenAI says the MCP server can expose read and change tools in this Site flow.[1] This means the eight Anki operations could, in principle, be represented as eight MCP tools, including write tools, provided the Site runtime and backend implementation support them. OpenAI does not document an eight-tool cap or any Anki-specific restriction. Tool-level write confirmation, authorization, idempotency, and least privilege remain implementation/security requirements; the Site guide's example expressly includes tools that update status.[1]

## Backend reachability and private data

A Site can host an MCP server, but OpenAI's Site documentation does **not** promise arbitrary outbound networking from that server. The general Sites documentation says that supported capabilities depend on the Sites runtime and that some private networks, databases, background services, and hosting patterns may not be supported.[2] It also says Sites involve hosted code, storage, and logs, and do not support data or inference residency at launch.[4]

Accordingly:

- **Publicly reachable creator-owned HTTPS backend:** plausible, but the Site-specific page does not state a formal outbound-fetch guarantee or egress allowlist/contract.
- **Backend on a private network/VPC, localhost, or non-public address:** not established; the Sites documentation expressly warns that some private-network patterns may not be supported.[2]
- **Creator's API secret held by the Site runtime:** Site documentation establishes that secrets are an owner-only Site setting. It does not specify the user-configurable secret-manager interface, encryption-at-rest behavior, runtime scope, rotation semantics, request-header injection, or whether the execution system, model context, logs, visitors, or Plugin users can observe the value.

The Apps SDK/MCP build guidance is useful as a security baseline, but it is not a Site secret-storage guarantee: it says to configure production credentials through the host's secret-management system, keep secrets out of tool metadata/results, and treat `_meta` as hidden from the model rather than as secure storage.[5][6] That guidance does not identify a user-visible secret store for ChatGPT Sites.

**Exact storage/visibility guarantee:** OpenAI documents owner-only secret configuration, but no detailed execution/logging/visibility guarantee was found. Do not claim that a Site secret is encrypted, excluded from execution logs, unavailable to the model, or usable as an injected API header unless OpenAI documents that specific behavior.

## Authorization and custom headers

For authenticated remote MCP servers, OpenAI's Apps SDK guidance expects an OAuth 2.1 flow conforming to the MCP authorization specification. ChatGPT discovers protected-resource metadata, completes the flow, and attaches the resulting bearer token to subsequent MCP requests; the MCP server must validate the token and enforce scopes.[5] The Plugin/MCP guidance also says authorization must be enforced by the server, not delegated to the model.[6]

That is not evidence that a Site-hosted MCP can store and inject an arbitrary fixed `Authorization` header or custom header containing an Anki API token. OpenAI's GPT Actions documentation explicitly says custom headers are not supported, while API-key authentication and OAuth have separate documented flows.[7][8] Those Actions limits must not be silently generalized to MCP, but they also cannot be used to claim that Site-hosted MCP supports custom headers.

**OAuth mandatory for a creator-owned backend?** Not for every MCP server: an anonymous/public MCP server can omit user authentication. For private user-specific data or writes, OpenAI says authenticated MCP servers are expected to implement OAuth 2.1.[5] A fixed creator credential would be a different, undocumented Site-hosted secret/header capability. Therefore, for a private creator-owned Anki backend, OAuth is the documented path if authentication is required; OAuth is not proven technically mandatory for a public/no-auth backend, but no official Site guarantee was found for safely substituting a creator-held API key.

## Limits and media/execution behavior

The official Sites and Apps SDK pages reviewed do not publish a complete Site-hosted MCP quota table. Specifically, no official Site-hosted MCP guarantee was found for:

- per-tool or whole-request timeout;
- request/response body-size ceiling;
- maximum tool count or execution duration;
- number/rate of outbound calls from one tool invocation;
- file size or file-count limits for MCP results;
- binary/image/audio/video response support;
- retries, concurrency, or egress IP ranges.

The **45-second round-trip, 100,000-character payload, text-only, and no-custom-headers** limits belong to GPT Actions, not to the Site-hosted MCP contract.[7] They are relevant only if the project chooses the legacy Custom GPT Actions route. Apps SDK guidance instead says to apply suitable timeouts and rate limits to expensive or externally visible tools, without supplying ChatGPT-hosted MCP numbers.[6]

## Product distinctions

| Product/surface | What it is | Current relevance to Route C |
|---|---|---|
| **Plugin** | A packaged workflow/capability that can include apps, skills, and app templates; the Plugin Directory is the discovery/distribution surface.[4] | The Site owner publishes a Site and OpenAI creates the associated Plugin.[1] |
| **ChatGPT Site** | A hosted interactive website/lightweight app with preview, deployment, sharing, and Site runtime.[2] | The Site can host the MCP server used by its associated Plugin.[1][2] |
| **Site-hosted MCP** | MCP server added to a Site and exposed through the generated Plugin.[1] | Route C. Supported for hosting/use; private-backend security limits remain undocumented. |
| **Custom remote MCP / Developer Mode** | A separate custom-app/MCP connection flow for remote MCP servers. Full MCP including writes is documented for Business and Enterprise/Edu; Pro is documented for read/fetch MCP use.[3] | Do not conflate its plan matrix or controls with Sites. Plus is not listed in the cited Developer Mode plan statement. |
| **Apps SDK** | OpenAI's developer toolkit for building the MCP-backed app logic and optional UI that runs in ChatGPT.[5][6] | A development framework, not proof of Site-hosted secret/network guarantees. |
| **Custom GPT Actions** | OpenAPI-described calls from a Custom GPT to external APIs, with None/API-key/OAuth authentication and documented Action limits.[7][8] | Legacy/direct HTTP alternative; not the same as MCP or Sites. |
| **Plugins (legacy terminology)** | Older ChatGPT plugin concepts and current Plugin-directory packaging are not interchangeable with an OpenAPI Action. | A Plugin does not imply direct REST/OpenAPI calls; Site-hosted MCP is the documented server-backed route.[1][4] |

## Custom GPT retirement scope correction

The current OpenAI Help Center says the transition affects all ChatGPT plans. It documents a planned **December 11, 2026 standard retirement** and a **February 11, 2027 date only for affected Enterprise workspaces with a qualified, approved deferral**; dates may change and the applicable account/workspace notice governs.[9] Restrictions on creating or publishing GPTs are separate from retirement of existing GPTs.[9][10]

The same FAQ says custom actions do not transfer automatically through migration and rebuilding the integration may require a custom MCP server.[9] Thus:

- the Enterprise deferral is not a Plus-user extension;
- the published standard retirement date is 2026-12-11 for the cross-plan transition, while the account/workspace notice remains controlling;
- existing personal GPT use/editability and new personal GPT creation are separate questions;
- Custom GPT Actions and Site-hosted MCP are separate mechanisms.

## Route C decision for Anki

**Product-level answer: YES.** A Plus account can, if the feature is available to that account, create a ChatGPT Site, add an MCP server, publish the Site-backed Plugin, install it, and use it.[1][2]

**Architecture-level answer: NO/UNPROVEN for now.** The requested design depends on a private creator backend, secure credential storage/injection, authenticated outbound HTTPS, write execution, and known limits. Official OpenAI documentation confirms the Site/MCP hosting workflow but does not confirm those Site-runtime guarantees. The eight Anki operations are conceptually proxyable as MCP tools, but that is not proof that the hosted runtime can safely or reliably proxy them. Route C should remain unapproved until OpenAI documents the missing guarantees or a non-production test proves them without real Anki writes.

## Sources

[1] https://help.openai.com/en/articles/20001547
[2] https://help.openai.com/en/articles/20001339
[3] https://help.openai.com/en/articles/12584461
[4] https://help.openai.com/en/articles/11487775
[5] https://developers.openai.com/apps-sdk/build/auth
[6] https://developers.openai.com/apps-sdk/build/mcp-server
[7] https://platform.openai.com/docs/actions/production
[8] https://platform.openai.com/docs/actions/authentication/oauth
[9] https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq
[10] https://help.openai.com/en/articles/8554397-creating-a-custom-gpt
