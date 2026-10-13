# Personal plugin → Secure MCP Tunnel route (official OpenAI docs)

**Research date:** 2026-10-13
**Scope:** Official OpenAI documentation only.[1][2][3] No tunnel, API key, Anki, DNS, nginx, VPS, or public-exposure changes were performed.

## Crisp conclusion

**The route is documented as technically supported.** The official “Add custom MCP server” guide says that ChatGPT connects an MCP server **as a plugin** and supports both read and write tools. It documents `Plugins → + → Add custom MCP server`, creation of a plugin, and selecting **Tunnel** / entering a `tunnel_id` as the connection method.[1][2][6] The quickstart explicitly calls the result a **personal plugin**.[1]

The docs do **not** say that the custom-plugin form is read-only: an MCP server exposes whatever tools it advertises, and the plugin test guidance explicitly includes “write actions that require authorization or confirmation.”[2] Therefore, the custom MCP plugin path supports read and write tools **where the account/workspace rollout and permissions allow them**; the server’s advertised tools and ChatGPT’s confirmation/security policy still govern actual use.[2]

For the account in scope (personal ChatGPT Plus), entitlement remains UI-gated and must not be overstated.[4][5]

- The Platform **ChatGPT Developer mode** page and the Help Center Developer Mode article have plan statements for the separate Developer Mode / MCP Apps surface.[4][5]
- Those Developer Mode statements must not be used to negate the separate Plugins connection guide, which says a custom MCP server connected as a Plugin supports read and write tools.[6]
- The Secure MCP Tunnel page explicitly provides a personal-account association path (“use the personal Platform organization that belongs to that account”), so the tunnel mechanism itself is not described as Enterprise-only.[3]

**Practical answer:** if the Plus account exposes **ChatGPT Plugins → + → Add custom MCP server**, it can create a personal Plugin from an MCP server with read and write tools according to the direct Plugin guide.[6] If that form also exposes **Tunnel**, the documented route is: create tunnel → run `tunnel-client` → select **Tunnel** → create the personal Plugin. Official pages still do not establish that every Plus account currently receives the Plugins/custom-MCP/Tunnel UI. If the UI does not show Add custom MCP server or Tunnel, this route is unavailable for that account at that time; do not substitute Developer Mode MCP Apps assumptions.

## What `Add custom MCP server` creates

The Quickstart says the flow is:

1. Open ChatGPT Plugins.
2. Select **+**, then **Add custom MCP server**.
3. Enter a name and server URL (or, in the newer connection flow, choose a connection method).
4. Configure authentication, accept the risk warning, and select **Create as a plugin**.
5. The resulting plugin appears in the user’s personal Plugins directory.[1][2]

The Quickstart is explicit that “this tutorial creates a personal plugin by connecting an MCP server.”[1] This is a personal plugin, not a workspace-published Developer Mode app. The plugin can package an MCP server and optionally skills/UI; UI is not required.[1]

### Read versus write

A custom MCP plugin is not inherently limited to read-only tools. The connect/test guide tells the developer to evaluate “write actions that require authorization or confirmation,” and says ChatGPT may request confirmation for such actions.[2] The Help Center separately distinguishes OpenAI-built apps (search-only) from custom MCP apps, which are the route for write/modify capabilities.[4]

This must be separated from the example Quickstart server: its sample `roll_dice` tool is explicitly read-only.[1] That example does not impose a read-only restriction on all custom plugins.

## Difference from Developer Mode MCP Apps

| Personal custom plugin flow | Developer Mode MCP Apps |
|---|---|
| ChatGPT Plugins → **+** → **Add custom MCP server** → **Create as a plugin**. Produces a personal plugin in the personal Plugins directory.[1][2] | ChatGPT **Settings → Apps → Advanced settings → Developer mode**, then **Create app** for a remote MCP server. The app is a draft and, for workspace deployment, is governed by workspace admins/owners and permissions.[4][5] |
| Designed for personal plugin installation/use; the Quickstart invokes it in ChatGPT Work.[1] | Designed for testing/deploying MCP-powered apps for a workspace, with workspace settings, admin/owner controls, publication, and (Enterprise/Edu) RBAC.[4] |
| The current plugin connection UI can use a public HTTPS MCP endpoint or **Secure MCP Tunnel**.[2] | Developer mode is the broader MCP client/app surface; the Help Center says private/local MCP servers can use Secure MCP Tunnel.[4] |
| A personal plugin is not the same object as a workspace custom app and does not inherit workspace publication/RBAC semantics. | A published app is workspace-approved; tool metadata/actions may be reviewed/frozen and access is controlled by workspace policy.[4] |

Do not infer that seeing Developer mode proves the personal plugin flow is enabled, or vice versa. They are distinct UI/product surfaces.

## Can Secure MCP Tunnel be selected as the custom-plugin Connection?

**Yes, according to the official plugin connection page.** Under **Connection**, it says:

- public endpoint: enter the MCP server URL, including `/mcp`;
- Secure MCP Tunnel: select **Tunnel**, then choose an available tunnel or enter its `tunnel_id`;
- configure authentication, accept the risk warning, then select **Create as a plugin**.[2]

The Secure MCP Tunnel guide repeats the same ChatGPT route: ChatGPT Plugins → + → Add custom MCP server → choose **Tunnel** → select an available tunnel or paste a valid `tunnel_id` → configure authentication → Create as a plugin.[3]

The tunnel guide also states that Secure MCP Tunnel **does not support public plugin submission or distribution**; public plugins require a stable publicly reachable HTTPS MCP endpoint.[3] That restriction does not contradict creating/testing a personal plugin locally in ChatGPT; it means the tunnel route is not the route for publishing a public directory plugin.

## Personal accounts, Plus, rollout, and prerequisites

### Personal account / Plus

The tunnel guide says personal accounts should use “the personal Platform organization that belongs to that account” when associating tunnels.[3] This is positive evidence that personal Platform organizations are supported by the tunnel mechanism.

It also says a tunnel can be associated with ChatGPT workspaces and Platform organizations, and that a tunnel associated only with a personal Platform organization does not automatically appear in an Enterprise/Edu workspace.[3]

The unresolved point is **ChatGPT Plus entitlement/rollout for this UI**. The direct Plugin guide documents the custom-MCP Plugin flow and write tools but does not publish a Plus-specific entitlement matrix.[6] The Platform Developer Mode page and the Help Center article describe a separate Developer Mode / MCP Apps surface with plan-specific policy.[4][5] This report therefore does not claim universal Plus availability. Verify the actual account UI and workspace policy; the presence of the Plugin form and Tunnel choice is the concrete eligibility signal.

### Required permissions and associations

The tunnel guide states:

- creating/editing a tunnel requires **Tunnels Read + Manage**;
- running `tunnel-client` or selecting a tunnel while creating an app requires **Tunnels Read + Use**;
- tunnel permissions are organization-level and granted by the Platform organization owner/RBAC administrator;
- adding/using custom MCP servers in ChatGPT remains subject to ChatGPT workspace permissions and security restrictions.[3]

Associate both:

1. the personal Platform organization that owns/manages the tunnel; and
2. the target ChatGPT workspace, if the tunnel must appear there.[3]

For a personal account, the target is normally the personal Platform organization and the personal ChatGPT context. A tunnel may be invisible if it is associated with the wrong context or the operator lacks Tunnels Read + Use.[3]

The Help Center describes Developer Mode/workspace prerequisites separately: Business admins, and Enterprise/Edu admins/owners or RBAC-authorized users, may need to enable developer mode and custom MCP permissions; only admins/owners can publish workspace apps.[4] Those workspace requirements are not proof that the personal plugin flow has the same admin model.

## Exact manual OpenAI steps (do not invent identifiers)

The following are manual instructions transcribed from the official tunnel and plugin documentation; they are not execution instructions for this task.[2][3]

### A. Create/manage the tunnel and obtain `tunnel_id`

1. Open the official Platform tunnel settings page: <https://platform.openai.com/settings/organization/tunnels>.[3]
2. Sign in to the intended personal Platform organization.
3. Create or manage an OpenAI-hosted MCP tunnel endpoint using the tunnel settings UI. The documentation requires a `tunnel_id`; it does not provide a real ID for a user account. Copy the actual `tunnel_id` shown by the UI; do not use any example ID from documentation.
4. Associate the tunnel with the personal Platform organization and the ChatGPT workspace/context that will create the plugin.[3]
5. Ensure the operator has **Tunnels Read + Manage** for creation/editing and **Tunnels Read + Use** for running/selecting it.[3]

### B. Create the runtime credential

The Secure MCP Tunnel guide requires “a runtime API key for `tunnel-client`.”[3] It does **not** provide a user-specific key, and the docs retrieved here do not specify a separate literal key-creation button/name beyond the Platform tunnel/API-key controls. Therefore:

1. In the intended Platform organization, use the official Platform credential/key management UI available to the account.
2. Create/select the runtime credential intended for `tunnel-client`, following the UI’s displayed runtime/API-key option and organization policy.
3. Store the secret only in the operator’s secret manager/environment; never commit or paste it into the repo/chat.
4. Export it to the documented variable at runtime, `CONTROL_PLANE_API_KEY`.[3]

No concrete key, `tunnel_id`, or credential identifier is supplied here because none can be safely or correctly invented. If the Platform UI does not expose a runtime credential for the personal organization, stop: the tunnel client cannot be authenticated from the documented flow.

### C. Install and run `tunnel-client` (not executed)

The official guide says to use the download link in Platform tunnel settings or the latest public release at <https://github.com/openai/tunnel-client/releases/latest>, and to begin with `tunnel-client help quickstart`.[3] The exact documented local-stdio sequence is:

```sh
export CONTROL_PLANE_API_KEY="sk-..."
tunnel-client init \
  --sample sample_mcp_stdio_local \
  --profile local-stdio \
  --tunnel-id tunnel_0123456789abcdef0123456789abcdef \
  --mcp-command "python /path/to/server.py"
tunnel-client doctor --profile local-stdio --explain
tunnel-client run --profile local-stdio
```

The `sk-...` value and `tunnel_012...` value above are documentation placeholders only. Replace them with the actual secret and actual tunnel ID from the account; never copy them as real credentials. For an HTTP MCP server, the guide says to use `--mcp-server-url https://mcp.internal.example.com/mcp` instead of `--mcp-command`.[3]

Keep `tunnel-client run` healthy while creating/testing the app. The guide says the local admin UI is at `/ui`; it also exposes `/healthz`, `/readyz`, and `/metrics`, with the admin UI loopback-only by default.[3]

### D. Associate/select it in the personal plugin UI

1. Open ChatGPT → **Plugins**.
2. Select **+** → **Add custom MCP server**.[1][2]
3. Enter the user-facing name and description.[2]
4. Under **Connection**, choose **Tunnel**.
5. Select the available tunnel, or enter the actual `tunnel_id` copied from Platform tunnel settings.[2][3]
6. Configure the MCP server authentication as required by the server; do not assume the tunnel runtime key is the server’s application OAuth credential.[2][3]
7. Review the risk warning and select **I understand and want to continue**.
8. Select **Create as a plugin**.[1][2]
9. Review discovered tools/metadata, install the plugin from personal Plugins, then test in a new ChatGPT Work conversation.[1][2]

If Tunnel is absent, the tunnel is not listed, or creation fails, check workspace association, Tunnels Read + Use, the running client, and account/workspace custom-MCP policy.[3]

## Sources

[1] Quickstart – Plugins — <https://learn.chatgpt.com/plugins/quickstart>
[2] Connect and test your plugin – Plugins — <https://developers.openai.com/apps-sdk/deploy/connect-chatgpt>
[3] Secure MCP Tunnel — <https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>
[4] Developer mode and MCP apps in ChatGPT — <https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt>
[5] ChatGPT Developer mode — <https://platform.openai.com/docs/guides/developer-mode>
[6] Add custom MCP server — <https://developers.openai.com/api/docs/guides/custom-mcp-server>
